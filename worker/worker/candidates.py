"""Bounded stored-only work in the existing worker process. Outbound HTTPS only."""
import json
import os
from pathlib import Path
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.parse import urlsplit
from stock_discovery_analysis import candidate_store as store
from stock_discovery_analysis.candidate_research import analyze
from stock_discovery_analysis.chartink import Scanner, normalize
from stock_discovery_analysis.real_views import ViewConfig
from stock_discovery_analysis.runtime import setting
from datetime import datetime


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


def pull(conn, url):
    parts=urlsplit(url)
    if parts.scheme!='https' or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment:
        raise ValueError('receiver_https_url_required')
    receiver_id=store.digest(url)
    with conn.transaction():
        # A second local worker must not overwrite a newer committed cursor.
        if not conn.execute('SELECT pg_try_advisory_xact_lock(94004)').fetchone()[0]:return 0
        conn.execute('INSERT INTO discovery.candidate_receivers(receiver_id) VALUES (%s) ON CONFLICT DO NOTHING',(receiver_id,))
        cursor=conn.execute('SELECT cursor FROM discovery.candidate_receivers WHERE receiver_id=%s FOR UPDATE',(receiver_id,)).fetchone()[0]
        secret=setting('CHARTINK_PULL_SECRET')
        if len(secret)<32:raise ValueError('pull_secret_required')
        request=Request(url.rstrip('/')+'/candidate-feed?limit=25&after='+str(cursor),headers={'Authorization':'Bearer '+secret})
        with build_opener(NoRedirect()).open(request,timeout=15) as response:
            raw=response.read(2*1024*1024+1)
        if len(raw)>2*1024*1024:raise ValueError('receiver_response_too_large')
        page=json.loads(raw)
        if not isinstance(page['events'],list) or len(page['events'])>25:raise ValueError('invalid_receiver_page')
        expected=cursor
        # Pin local scanner approval: the remote receiver cannot grant itself rights.
        scanner=Scanner.model_validate_json(Path(os.environ['CHARTINK_SCANNER_CONFIG']).read_text())
        for item in page['events']:
            e=item['envelope'];sequence=item['sequence']
            if type(sequence) is not int or sequence<=expected:raise ValueError('invalid_receiver_sequence')
            remote_scanner=Scanner.model_validate(e['scanner'])
            if remote_scanner.key!=scanner.key:raise ValueError('receiver_scanner_not_approved')
            validated=normalize(e['payload'],remote_scanner,datetime.fromisoformat(e['received_at']))
            if validated!=e:raise ValueError('receiver_envelope_mismatch')
            store.accept(conn,validated)
            expected=sequence
        if page['next_cursor']!=expected:raise ValueError('invalid_receiver_cursor')
        conn.execute('UPDATE discovery.candidate_receivers SET cursor=%s WHERE receiver_id=%s',(expected,receiver_id))
        return len(page['events'])


def cycle(conn, *, config=None):
    # Five events / five companies per tick; independent of research UI requests.
    receiver=os.environ.get('CHARTINK_RECEIVER_URL')
    if receiver:pull(conn,receiver)
    events=research=0
    for _ in range(5):
        if store.materialize_one(conn) is None:break
        events+=1
    if config is None and os.environ.get('REAL_RESEARCH_VIEW_CONFIG'):
        try:config=ViewConfig.model_validate_json(Path(os.environ['REAL_RESEARCH_VIEW_CONFIG']).read_text())
        except (OSError,ValueError):config=None
    for _ in range(5):
        if store.research_one(conn,lambda c,s,d:analyze(c,config,s,d)) is None:break
        research+=1
    return dict(events=events,research=research,provider_requests=0,model_requests=0)
