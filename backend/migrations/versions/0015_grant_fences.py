"""STK-014/074: durable restrictions and fenced revision/evidence persistence."""
from alembic import op

revision = '0015'
down_revision = '0014'
branch_labels = depends_on = None


def upgrade():
    op.execute('''
    DO $$ BEGIN
      IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='stk_restriction_operator') THEN
        CREATE ROLE stk_restriction_operator NOLOGIN;
      END IF;
    END $$;
    CREATE FUNCTION discovery.fence_key(k text,s text,a text,g text,v text) RETURNS text
      LANGUAGE sql IMMUTABLE STRICT AS $$
      SELECT encode(sha256(convert_to(jsonb_build_array(k,s,a,g,v)::text,'UTF8')),'hex') $$;
    CREATE TABLE discovery.grant_fences (
      scope_id text PRIMARY KEY, kind text NOT NULL CHECK(kind IN ('provider','account','grant')),
      source_id text NOT NULL CHECK(source_id<>''), account_ref text NOT NULL DEFAULT '',
      grant_id text NOT NULL DEFAULT '', grant_version text NOT NULL DEFAULT '',
      state text NOT NULL DEFAULT 'OPEN' CHECK(state IN ('OPEN','FENCED')),
      generation bigint NOT NULL DEFAULT 0 CHECK(generation>=0),
      CHECK(scope_id=discovery.fence_key(kind,source_id,account_ref,grant_id,grant_version)),
      CHECK((kind='provider' AND account_ref='' AND grant_id='' AND grant_version='') OR
            (kind='account' AND account_ref<>'' AND grant_id='' AND grant_version='') OR
            (kind='grant' AND account_ref<>'' AND grant_id<>'' AND grant_version<>''))
    );
    CREATE TABLE discovery.restriction_requests (
      request_id uuid PRIMARY KEY, scope_id text NOT NULL REFERENCES discovery.grant_fences,
      operator_name name NOT NULL, reason text NOT NULL CHECK(reason IN ('revoked','policy_unverified','deletion_pending','expired')),
      policy_hash text CHECK(policy_hash ~ '^[a-f0-9]{64}$'),
      decided_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      decision text NOT NULL CHECK(decision IN ('fenced','already_fenced')),
      generation bigint NOT NULL CHECK(generation>0),
      deletion_authorized boolean NOT NULL DEFAULT false CHECK(NOT deletion_authorized)
    );
    CREATE TRIGGER immutable_restriction_requests BEFORE UPDATE OR DELETE ON discovery.restriction_requests
      FOR EACH ROW EXECUTE FUNCTION research.reject_mutation();
    CREATE FUNCTION discovery.protect_fence() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
      IF TG_OP='DELETE' OR NEW.scope_id<>OLD.scope_id OR
        (to_jsonb(NEW)-'state'-'generation')<>(to_jsonb(OLD)-'state'-'generation') OR
        OLD.state<>'OPEN' OR NEW.state<>'FENCED' OR NEW.generation<>OLD.generation+1 THEN
        RAISE EXCEPTION 'invalid_fence_transition' USING ERRCODE='42501';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER protect_fence BEFORE UPDATE OR DELETE ON discovery.grant_fences
      FOR EACH ROW EXECUTE FUNCTION discovery.protect_fence();
    CREATE FUNCTION discovery.protect_stream_identity() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
      IF ROW(NEW.stream_id,NEW.source_id,NEW.account_ref,NEW.scope) IS DISTINCT FROM
         ROW(OLD.stream_id,OLD.source_id,OLD.account_ref,OLD.scope) THEN
        RAISE EXCEPTION 'stream_identity_immutable' USING ERRCODE='42501';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER protect_stream_identity BEFORE UPDATE ON discovery.streams
      FOR EACH ROW EXECUTE FUNCTION discovery.protect_stream_identity();
    CREATE FUNCTION discovery.register_fence(k text,s text,a text,g text,v text) RETURNS text
      LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,discovery AS $$
      DECLARE key text := discovery.fence_key(k,s,a,g,v);
      BEGIN
        INSERT INTO discovery.grant_fences(scope_id,kind,source_id,account_ref,grant_id,grant_version)
          VALUES(key,k,s,a,g,v) ON CONFLICT DO NOTHING;
        RETURN key;
      END $$;
    CREATE FUNCTION discovery.register_grant_fences(s text,a text,g text,v text) RETURNS void
      LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,discovery AS $$ BEGIN
        PERFORM discovery.register_fence('provider',s,'','','');
        PERFORM discovery.register_fence('account',s,a,'','');
        PERFORM discovery.register_fence('grant',s,a,g,v);
      END $$;
    -- OPEN is absence of a restriction, never an authorization. Existing grants
    -- remain immutable; scope initialization does not infer page attribution.
    SELECT discovery.register_grant_fences(payload->>'source_id',payload->>'account_ref',grant_id,version)
      FROM discovery.grants ORDER BY grant_id,version;
    CREATE FUNCTION discovery.restrict_grant_scope(req uuid,k text,s text,a text,g text,v text,why text,policy text)
      RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,discovery AS $$
      DECLARE key text; prior discovery.restriction_requests; f discovery.grant_fences; changed boolean;
      BEGIN
        IF NOT pg_has_role(session_user,'stk_restriction_operator','MEMBER') THEN
          RAISE EXCEPTION 'restriction_operator_required' USING ERRCODE='42501';
        END IF;
        IF why NOT IN ('revoked','policy_unverified','deletion_pending','expired') OR why IS NULL OR
           (policy IS NOT NULL AND policy !~ '^[a-f0-9]{64}$') THEN
          RAISE EXCEPTION 'invalid_restriction_request';
        END IF;
        PERFORM pg_advisory_xact_lock(hashtextextended('restriction:'||req::text,0));
        key := discovery.fence_key(k,s,a,g,v);
        SELECT * INTO prior FROM discovery.restriction_requests WHERE request_id=req;
        IF FOUND THEN
          IF prior.scope_id<>key OR prior.reason<>why OR prior.policy_hash IS DISTINCT FROM policy OR prior.operator_name<>session_user THEN
            RAISE EXCEPTION 'restriction_idempotency_conflict';
          END IF;
          RETURN prior.generation;
        END IF;
        PERFORM discovery.register_fence(k,s,a,g,v);
        SELECT * INTO f FROM discovery.grant_fences WHERE scope_id=key FOR UPDATE;
        changed := f.state='OPEN';
        IF changed THEN
          UPDATE discovery.grant_fences SET state='FENCED',generation=generation+1 WHERE scope_id=key RETURNING * INTO f;
        END IF;
        INSERT INTO discovery.restriction_requests(request_id,scope_id,operator_name,reason,policy_hash,decision,generation)
          VALUES(req,key,session_user,why,policy,CASE WHEN changed THEN 'fenced' ELSE 'already_fenced' END,f.generation);
        RETURN f.generation;
      END $$;
    CREATE FUNCTION discovery.lock_grant_fences(s text,a text,g text,v text) RETURNS bigint[]
      LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,discovery AS $$
      DECLARE key text; f discovery.grant_fences; generations bigint[] := '{}';
      BEGIN
        FOREACH key IN ARRAY ARRAY[discovery.fence_key('provider',s,'','',''),
          discovery.fence_key('account',s,a,'',''),discovery.fence_key('grant',s,a,g,v)] LOOP
          SELECT * INTO f FROM discovery.grant_fences WHERE scope_id=key FOR SHARE;
          IF NOT FOUND OR f.state<>'OPEN' THEN
            RAISE EXCEPTION 'grant_fenced_or_unregistered' USING ERRCODE='42501';
          END IF;
          generations := array_append(generations,f.generation);
        END LOOP;
        RETURN generations;
      END $$;
    -- Validation deliberately acquires no row locks. Call after the entire
    -- operation's dependency lock pass, not between potentially blocking locks.
    CREATE FUNCTION discovery.validate_ingestion_grant(g text,v text) RETURNS void
      LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,discovery AS $$
      DECLARE p jsonb;
      BEGIN
        SELECT payload INTO p FROM discovery.grants WHERE grant_id=g AND version=v;
        IF (p->>'status'='active' AND (p->'allowed_uses' ? 'store') AND
          (p->>'valid_from_at')::timestamptz<=clock_timestamp() AND
          (p->>'expires_at')::timestamptz>clock_timestamp()) IS NOT TRUE THEN
          RAISE EXCEPTION 'ingestion_grant_unavailable' USING ERRCODE='42501';
        END IF;
      END $$;
    CREATE FUNCTION discovery.check_ingestion_grant(g text,v text) RETURNS void
      LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,discovery AS $$
      DECLARE p jsonb;
      BEGIN
        SELECT payload INTO p FROM discovery.grants WHERE grant_id=g AND version=v;
        PERFORM discovery.lock_grant_fences(p->>'source_id',p->>'account_ref',g,v);
        PERFORM discovery.validate_ingestion_grant(g,v);
      END $$;
    CREATE FUNCTION discovery.revision_data_scope(k text,p jsonb) RETURNS text
      LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
      SELECT CASE k WHEN 'instrument' THEN 'universe' WHEN 'membership' THEN 'universe'
        WHEN 'candle' THEN 'prices' WHEN 'action' THEN 'corporate_actions' WHEN 'session' THEN 'calendar'
        WHEN 'document' THEN CASE p->'data'->>'document_type' WHEN 'filing' THEN 'filings' WHEN 'news' THEN 'news' END END $$;
    CREATE FUNCTION discovery.validate_ingestion_scope(g text,v text,s text,uses text[] DEFAULT ARRAY['store']) RETURNS void
      LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,discovery AS $$
      DECLARE p jsonb;
      BEGIN
        PERFORM discovery.validate_ingestion_grant(g,v);
        SELECT payload INTO p FROM discovery.grants WHERE grant_id=g AND version=v;
        IF (s=ANY(ARRAY['prices','universe','calendar','corporate_actions','benchmark','filings','news','financial_facts']) AND
          jsonb_typeof(p->'scopes')='array' AND (p->'scopes' ? s) AND
          jsonb_typeof(p->'allowed_uses')='array' AND (p->'allowed_uses' ?& uses)) IS NOT TRUE THEN
          RAISE EXCEPTION 'ingestion_data_scope_denied' USING ERRCODE='42501';
        END IF;
      END $$;
    CREATE TABLE discovery.ingestion_grants (
      stream_id text NOT NULL, cursor_key text NOT NULL, grant_id text NOT NULL, grant_version text NOT NULL,
      PRIMARY KEY(stream_id,cursor_key,grant_id,grant_version),
      FOREIGN KEY(stream_id,cursor_key) REFERENCES discovery.pages DEFERRABLE INITIALLY DEFERRED,
      FOREIGN KEY(grant_id,grant_version) REFERENCES discovery.grants
    );
    CREATE FUNCTION discovery.new_page_dependency() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
      IF EXISTS(SELECT FROM discovery.pages WHERE stream_id=NEW.stream_id AND cursor_key=NEW.cursor_key) THEN
        RAISE EXCEPTION 'historical_page_attribution_immutable' USING ERRCODE='42501';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER new_page_dependency BEFORE INSERT ON discovery.ingestion_grants
      FOR EACH ROW EXECUTE FUNCTION discovery.new_page_dependency();
    CREATE TRIGGER immutable_ingestion_grants BEFORE UPDATE OR DELETE ON discovery.ingestion_grants
      FOR EACH ROW EXECUTE FUNCTION research.reject_mutation();
    CREATE FUNCTION discovery.validate_revision_grant(rid text) RETURNS void
      LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,discovery AS $$
      DECLARE r discovery.revisions; st discovery.streams; p jsonb; required_scope text;
      BEGIN
        SELECT * INTO r FROM discovery.revisions WHERE revision_id=rid;
        IF NOT FOUND THEN RAISE EXCEPTION 'revision_dependency_unavailable' USING ERRCODE='42501'; END IF;
        SELECT * INTO st FROM discovery.streams WHERE stream_id=r.stream_id;
        SELECT payload INTO p FROM discovery.grants WHERE grant_id=r.grant_id AND version=r.grant_version;
        required_scope := discovery.revision_data_scope(r.kind,r.payload);
        IF (st.scope=required_scope AND r.source_id=p->>'source_id' AND
          st.source_id=p->>'source_id' AND st.account_ref=p->>'account_ref') IS NOT TRUE THEN
          RAISE EXCEPTION 'ingestion_grant_scope_mismatch' USING ERRCODE='42501';
        END IF;
        PERFORM discovery.validate_ingestion_scope(r.grant_id,r.grant_version,required_scope);
      END $$;
    CREATE FUNCTION discovery.check_revision_grant(rid text) RETURNS void
      LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,discovery AS $$
      DECLARE r discovery.revisions;
      BEGIN
        SELECT * INTO r FROM discovery.revisions WHERE revision_id=rid;
        IF NOT FOUND THEN RAISE EXCEPTION 'revision_dependency_unavailable' USING ERRCODE='42501'; END IF;
        PERFORM discovery.check_ingestion_grant(r.grant_id,r.grant_version);
        PERFORM discovery.validate_revision_grant(rid);
      END $$;
    CREATE FUNCTION discovery.check_ingestion_page(s text,c text,evidence boolean DEFAULT false) RETURNS void
      LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,discovery AS $$
      DECLARE r record; dep jsonb; grants jsonb; revisions text[]; rid text; stream_scope text;
      BEGIN
        SELECT scope INTO stream_scope FROM discovery.streams WHERE stream_id=s;
        SELECT jsonb_agg(jsonb_build_array(grant_id,grant_version) ORDER BY grant_id,grant_version) INTO grants
          FROM discovery.ingestion_grants WHERE stream_id=s AND cursor_key=c;
        IF grants IS NULL THEN RAISE EXCEPTION 'page_grant_unattributed' USING ERRCODE='42501'; END IF;
        SELECT array_agg(revision_id ORDER BY revision_id) INTO revisions FROM discovery.stream_revisions WHERE stream_id=s;
        FOR dep IN SELECT value FROM jsonb_array_elements(grants) LOOP
          PERFORM discovery.check_ingestion_grant(dep->>0,dep->>1);
          IF NOT EXISTS(SELECT FROM discovery.grants g JOIN discovery.streams st
            ON st.source_id=g.payload->>'source_id' AND st.account_ref=g.payload->>'account_ref'
            WHERE g.grant_id=dep->>0 AND g.version=dep->>1 AND st.stream_id=s) THEN
            RAISE EXCEPTION 'page_grant_scope_mismatch' USING ERRCODE='42501';
          END IF;
        END LOOP;
        FOREACH rid IN ARRAY coalesce(revisions,ARRAY[]::text[]) LOOP
          PERFORM discovery.check_revision_grant(rid);
          SELECT kind,payload INTO r FROM discovery.revisions WHERE revision_id=rid;
          IF (stream_scope=discovery.revision_data_scope(r.kind,r.payload)) IS NOT TRUE THEN
            RAISE EXCEPTION 'membership_data_scope_mismatch' USING ERRCODE='42501';
          END IF;
        END LOOP;
        IF evidence AND (stream_scope=ANY(ARRAY['filings','news'])) IS NOT TRUE THEN
          RAISE EXCEPTION 'evidence_data_scope_denied' USING ERRCODE='42501';
        END IF;
        -- Revalidate the captured dependencies only: this final pass must not
        -- discover another dependency or acquire another blocking row lock.
        FOR dep IN SELECT value FROM jsonb_array_elements(grants) LOOP
          PERFORM discovery.validate_ingestion_scope(dep->>0,dep->>1,stream_scope,
            CASE WHEN evidence THEN ARRAY['store','extract','derive'] ELSE ARRAY['store'] END);
        END LOOP;
        FOREACH rid IN ARRAY coalesce(revisions,ARRAY[]::text[]) LOOP
          PERFORM discovery.validate_revision_grant(rid);
        END LOOP;
      END $$;
    CREATE FUNCTION discovery.enforce_ingestion_fence() RETURNS trigger
      LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,discovery AS $$
      DECLARE r record; p jsonb; destination discovery.streams;
        destination_scope text; destination_state text; revisions text[] := '{}'; rid text;
      BEGIN
        IF TG_TABLE_NAME='revisions' THEN
          revisions := array_remove(ARRAY[NEW.revision_id,NEW.instrument_revision_id,NEW.supersedes_id],NULL);
        ELSIF TG_TABLE_NAME IN ('pages','quarantine','evidence_batches','ingestion_grants') THEN
          PERFORM discovery.check_ingestion_page(NEW.stream_id,NEW.cursor_key,TG_TABLE_NAME='evidence_batches');
        ELSIF TG_TABLE_NAME='stream_revisions' THEN
          revisions := ARRAY[NEW.revision_id];
          PERFORM discovery.check_revision_grant(NEW.revision_id);
          -- Membership also writes into the destination account. Pin its identity
          -- and lock both destination restrictions until the INSERT commits.
          SELECT * INTO destination FROM discovery.streams WHERE stream_id=NEW.stream_id FOR SHARE;
          IF NOT FOUND THEN RAISE EXCEPTION 'destination_stream_unavailable' USING ERRCODE='42501'; END IF;
          SELECT kind,payload INTO r FROM discovery.revisions WHERE revision_id=NEW.revision_id;
          IF (destination.scope=discovery.revision_data_scope(r.kind,r.payload)) IS NOT TRUE THEN
            RAISE EXCEPTION 'membership_data_scope_mismatch' USING ERRCODE='42501';
          END IF;
          FOREACH destination_scope IN ARRAY ARRAY[
            discovery.fence_key('provider',destination.source_id,'','',''),
            discovery.fence_key('account',destination.source_id,destination.account_ref,'','')] LOOP
            SELECT state INTO destination_state FROM discovery.grant_fences
              WHERE scope_id=destination_scope FOR SHARE;
            IF NOT FOUND OR destination_state<>'OPEN' THEN
              RAISE EXCEPTION 'destination_fenced_or_unregistered' USING ERRCODE='42501';
            END IF;
          END LOOP;
        ELSIF TG_TABLE_NAME='evidence_blobs' THEN
          SELECT array_agg(revision_id ORDER BY revision_id) INTO revisions FROM discovery.evidence_documents WHERE content_hash=NEW.content_hash;
          IF revisions IS NULL THEN RAISE EXCEPTION 'unattributed_evidence_blob' USING ERRCODE='42501'; END IF;
        ELSE
          revisions := ARRAY[NEW.revision_id];
          IF NOT EXISTS(SELECT FROM discovery.revisions WHERE revision_id=NEW.revision_id AND kind='document') THEN
            RAISE EXCEPTION 'evidence_data_scope_denied' USING ERRCODE='42501';
          END IF;
          SELECT g.payload INTO p FROM discovery.grants g JOIN discovery.revisions rev
            ON (rev.grant_id,rev.grant_version)=(g.grant_id,g.version) WHERE rev.revision_id=NEW.revision_id;
          IF (p->'allowed_uses' ?& ARRAY['store','extract','derive']) IS NOT TRUE OR
             (TG_TABLE_NAME='financial_facts' AND (p->'scopes' ? 'financial_facts') IS NOT TRUE) THEN
            RAISE EXCEPTION 'evidence_grant_use_denied' USING ERRCODE='42501';
          END IF;
          IF TG_TABLE_NAME='evidence_documents' THEN
            SELECT array_agg(revision_id ORDER BY revision_id) INTO revisions FROM discovery.evidence_documents WHERE content_hash=NEW.content_hash;
          END IF;
        END IF;
        -- Stable per-operation dependency list. Acquire every grant lock before
        -- the final nonblocking wall-clock/scope validation pass.
        FOR rid IN SELECT DISTINCT unnest(revisions) ORDER BY 1 LOOP
          PERFORM discovery.check_revision_grant(rid);
        END LOOP;
        FOR rid IN SELECT DISTINCT unnest(revisions) ORDER BY 1 LOOP
          PERFORM discovery.validate_revision_grant(rid);
        END LOOP;
        RETURN NEW;
      END $$;
    REVOKE ALL ON discovery.grant_fences, discovery.restriction_requests FROM PUBLIC;
    REVOKE ALL ON FUNCTION discovery.register_fence(text,text,text,text,text) FROM PUBLIC;
    ''')
    for table in ('revisions','stream_revisions','pages','quarantine','ingestion_grants','evidence_blobs',
                  'evidence_documents','evidence_chunks','financial_facts','evidence_claims','evidence_batches'):
        op.execute(f'''CREATE CONSTRAINT TRIGGER ingestion_fence_{table} AFTER INSERT ON discovery.{table}
          DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION discovery.enforce_ingestion_fence()''')


def downgrade():
    # A downgrade must not silently erase restrictions or dependency records.
    op.execute("""DO $$ BEGIN IF EXISTS(SELECT FROM discovery.restriction_requests) OR
      EXISTS(SELECT FROM discovery.ingestion_grants) THEN RAISE EXCEPTION 'grant_fence_history_present'; END IF; END $$""")
    for table in ('revisions','stream_revisions','pages','quarantine','ingestion_grants','evidence_blobs',
                  'evidence_documents','evidence_chunks','financial_facts','evidence_claims','evidence_batches'):
        op.execute(f'DROP TRIGGER ingestion_fence_{table} ON discovery.{table}')
    op.execute('''DROP TRIGGER protect_stream_identity ON discovery.streams;
      DROP FUNCTION discovery.protect_stream_identity();
      DROP FUNCTION discovery.enforce_ingestion_fence();
      DROP FUNCTION discovery.check_ingestion_page(text,text,boolean);
      DROP FUNCTION discovery.check_revision_grant(text);
      DROP FUNCTION discovery.validate_revision_grant(text);
      DROP FUNCTION discovery.check_ingestion_grant(text,text);
      DROP FUNCTION discovery.validate_ingestion_scope(text,text,text,text[]);
      DROP FUNCTION discovery.validate_ingestion_grant(text,text);
      DROP FUNCTION discovery.revision_data_scope(text,jsonb);
      DROP FUNCTION discovery.lock_grant_fences(text,text,text,text);
      DROP FUNCTION discovery.restrict_grant_scope(uuid,text,text,text,text,text,text,text);
      DROP FUNCTION discovery.register_grant_fences(text,text,text,text);
      DROP FUNCTION discovery.register_fence(text,text,text,text,text);
      DROP TABLE discovery.ingestion_grants;
      DROP FUNCTION discovery.new_page_dependency();
      DROP TABLE discovery.restriction_requests;
      DROP TABLE discovery.grant_fences;
      DROP FUNCTION discovery.protect_fence();
      DROP FUNCTION discovery.fence_key(text,text,text,text,text);
    ''')
