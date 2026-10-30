"""STK-074: transaction-scoped, fail-closed authorization of MVP read dependencies.

Content may be assembled privately before locking; it cannot leave this boundary
until all dependencies are locked and revalidated. No fence registration or writes.
"""
import json
from contextlib import contextmanager
from contextvars import ContextVar

import psycopg
from stock_discovery_contracts.rights import Grant, authorize
from .grant_fences import database_request, identity
from .revisions import Revision
from .revision_storage import Stream

_active = ContextVar('real_read_fence', default=None)
DENIED = 'real_read_access_denied'
MAX_REVISIONS = 10000


def track_revision(conn, revision_id):
    guard = _active.get()
    if guard is not None and guard.conn is conn:
        guard.add(revision_id)


def track_use(access, stream, uses):
    guard = _active.get()
    if guard is not None and guard.access is access:
        guard.uses.setdefault((stream.source_id,stream.account_ref,stream.scope),set()).update(uses)


class ReadGuard:
    def __init__(self,conn,access,lock_conn=None):
        self.conn,self.access = conn,access
        self.lock_conn=lock_conn if lock_conn is not None else conn
        self.revisions=set(); self.uses={}; self.bundles=set()

    def add(self,rid):
        if not isinstance(rid,str) or not rid or len(self.revisions)>=MAX_REVISIONS and rid not in self.revisions:
            raise PermissionError(DENIED)
        self.revisions.add(rid)

    def collect(self,value,depth=0):
        """Known serialized citation/manifests only; never parse arbitrary prose."""
        if depth>64:raise PermissionError(DENIED)
        if isinstance(value,dict):
            for key,item in value.items():
                if key=='revision_id' or key=='instrument_revision_id' and item is not None:self.add(item)
                elif key in ('source_revision_ids','source_revisions','input_revision_ids','universe_revision_ids'):
                    if not isinstance(item,(list,tuple)):raise PermissionError(DENIED)
                    for rid in item:self.add(rid)
                elif key in ('bundle_hash','baseline_hash','final_bundle_hash') and item:
                    self.bundle(item)
                self.collect(item,depth+1)
        elif isinstance(value,(list,tuple)):
            for item in value:self.collect(item,depth+1)

    def bundle(self,key):
        from .rag_contracts import Bundle
        if not isinstance(key,str):raise PermissionError(DENIED)
        if key in self.bundles:return
        if len(self.bundles)>=100:raise PermissionError(DENIED)
        self.bundles.add(key)
        row=self.conn.execute('SELECT payload FROM discovery.rag_bundles WHERE bundle_hash=%s',(key,)).fetchone()
        if not row:raise PermissionError(DENIED)
        bundle=Bundle.model_validate_json(json.dumps(row[0]))
        if bundle.content_hash!=key or bundle.query.mode!='live_paper':raise PermissionError(DENIED)
        for rid in bundle.documents:self.add(rid)
        self.collect(row[0])
        if bundle.embedding:
            for rid in bundle.documents:
                from .evidence_storage import stored_stream
                stream=stored_stream(self.conn,rid)
                self.uses.setdefault((stream.source_id,stream.account_ref,stream.scope),set()).add('embed')

    def dependencies(self):
        result={}; pending=set(self.revisions)
        while pending:
            rid=min(pending);pending.remove(rid)
            if rid in result:continue
            row=self.conn.execute('''SELECT r.payload,r.grant_id,r.grant_version,g.payload,
                s.stream_id,s.source_id,s.account_ref,s.scope FROM discovery.revisions r
                JOIN discovery.streams s USING(stream_id)
                JOIN discovery.grants g ON (g.grant_id,g.version)=(r.grant_id,r.grant_version)
                WHERE r.revision_id=%s''',(rid,)).fetchone()
            if not row:raise PermissionError(DENIED)
            revision=Revision.model_validate(row[0]); grant=Grant.model_validate_json(json.dumps(row[3]))
            stream=Stream(stream_id=row[4],source_id=row[5],account_ref=row[6],scope=row[7])
            if (revision.revision_id!=rid or revision.source_id!=stream.source_id or revision.scope!=stream.scope
                or (grant.grant_id,grant.version)!=(row[1],row[2]) or grant.synthetic
                or revision.availability_basis!='observed'
                or (grant.source_id,grant.account_ref)!=(stream.source_id,stream.account_ref)):
                raise PermissionError(DENIED)
            uses={'derive','store'}|self.uses.get((stream.source_id,stream.account_ref,stream.scope),set())
            scopes={stream.scope:uses}
            if self.conn.execute('SELECT 1 FROM discovery.financial_facts WHERE revision_id=%s LIMIT 1',(rid,)).fetchone():
                scopes['financial_facts']={'derive','store'}|self.uses.get((stream.source_id,stream.account_ref,'financial_facts'),set())
            result[rid]=(grant,stream,scopes)
            if revision.instrument_revision_id:
                self.add(revision.instrument_revision_id);pending.add(revision.instrument_revision_id)
        return result

    def authorize(self):
        deps=self.dependencies()
        # Consistent identity ordering; each SQL function locks provider/account/grant.
        # No validity check is relied on until every potentially blocking lock is held.
        for key in sorted({identity(g) for g,_,_ in deps.values()}):
            self.lock_conn.execute('SELECT discovery.lock_grant_fences(%s,%s,%s,%s)',key)
        for grant,stream,scopes in deps.values():
            current=self.access.load_grant(stream)
            if current is None or identity(current)!=identity(grant):raise PermissionError(DENIED)
            for scope,uses in scopes.items():
                request=database_request(self.lock_conn,self.access.request_for(stream.model_copy(update={'scope':scope})),sorted(uses))
                if not authorize(grant,request).allowed or not authorize(current,request).allowed:
                    raise PermissionError(DENIED)
        # The private file is not a transactional revocation authority. Durable
        # restrictions are serialized above; file rights are reloaded at this gate.


@contextmanager
def guarded_read(conn,access,*,_lock_conn=None):
    existing=_active.get()
    if existing is not None:
        if existing.conn is not conn or existing.access is not access:raise PermissionError(DENIED)
        yield existing
        # Tool reads must authorize newly discovered dependencies before handing
        # evidence to local embeddings/calculations. Locks survive the whole tool.
        if existing.lock_conn is not existing.conn:existing.authorize()
        return
    try:
        with conn.transaction():
            # Bounded waits; no automatic retry against a potentially new snapshot.
            conn.execute("SET LOCAL lock_timeout='5s'")
            guard=ReadGuard(conn,access,_lock_conn); token=_active.set(guard)
            try:
                yield guard
                guard.authorize()
            finally:_active.reset(token)
    except (PermissionError,psycopg.Error,ValueError,KeyError,TypeError,OSError):
        raise PermissionError(DENIED) from None


@contextmanager
def tool_read_transaction(conn,access,bundle):
    """Keep tool SQL READ ONLY; a private sibling transaction holds fence locks.

    Both sessions use the same server/database/login. The sibling never reaches
    tool adapters and only runs fence SELECTs. Its locks outlive the reader
    transaction, including rollback. No persisted content is written here.
    """
    if bundle.query.mode!='live_paper':
        with conn.transaction():
            conn.execute('SET TRANSACTION READ ONLY')
            yield
        return
    if _active.get() is not None:raise PermissionError(DENIED)
    try:
        with psycopg.connect(conn.info.dsn,password=conn.info.password,host=conn.info.host,
                             hostaddr=conn.info.hostaddr,port=conn.info.port,
                             dbname=conn.info.dbname,user=conn.info.user,autocommit=True,connect_timeout=5) as locks:
            with locks.transaction():
                locks.execute("SET LOCAL lock_timeout='5s'")
                with guarded_read(conn,access,_lock_conn=locks) as guard:
                    conn.execute('SET TRANSACTION READ ONLY')
                    for rid in bundle.documents:guard.add(rid)
                    guard.collect(bundle.model_dump(mode='json'))
                    guard.authorize()
                    yield
    except (psycopg.Error,ValueError,OSError):
        raise PermissionError(DENIED) from None
