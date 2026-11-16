"""STK-095 schema-independent private receipts; domain parsing runs in the worker."""
from datetime import timezone
import hashlib
import json
import re
from .chartink import IST, digest, normalize, Scanner
from .chartink_diagnostics import decode_payload, payload_shape, kind
from .chartink_columns import COLUMNS

VERSION='chartink-raw-v1'
SENSITIVE=re.compile(r'webhook_url|password|passwd|secret|token|credential|authorization|cookie|api.?key|capability|private.?key',re.I)
URL=re.compile(r'(?:[a-z][a-z0-9+.-]*://|/hooks/chartink/)[^\s"<>]+',re.I)
REDACTED='[REDACTED]'
REASONS=frozenset(('invalid_payload_fields','invalid_payload_values','scanner_identity_mismatch',
 'invalid_symbol','invalid_symbol_price_count','invalid_trigger_price','invalid_trigger_time',
 'scanner_authorization_expired','timezone_required','duplicate_payload_field','invalid_provider_test_payload',
 'invalid_columns_count','invalid_columns_fields','column_symbol_mismatch','conflicting_payload_versions',
 'invalid_enrichment_text','invalid_enrichment_number','invalid_enrichment_range','synthetic_scanner_required',
 'invalid_enrichment_symbols','invalid_json','privacy_redaction_collision'))


def clean_text(text,secrets=()):
    for value in secrets:
        if value:text=text.replace(value,REDACTED)
    text=URL.sub(REDACTED,text)
    return re.sub(r'(?i)\b(?:bearer|basic)\s+\S+',REDACTED,text)


def capture(body,scanner,received_at,secrets=()):
    # Syntax checking only prevents redaction from repairing invalid JSON. The raw
    # document (including unknown fields and duplicate keys) survives for replay;
    # domain parsing, identity, columns and classification are worker-only.
    error=None
    try:decode_payload(body)
    except (ValueError,UnicodeError,RecursionError) as exc:
        error=str(exc) if str(exc) in REASONS else 'invalid_json'
    text=body.decode('utf-8',errors='replace')
    tokens=list(re.finditer(r'"(?:[^"\\]|\\.)*"',text))
    edits=[];covered=0
    for token in tokens:
        if token.start()<covered:continue
        try:value=json.loads(token.group())
        except ValueError:
            edits.append((token.start(),token.end(),json.dumps(REDACTED)));continue
        tail=token.end()
        while tail<len(text) and text[tail].isspace():tail+=1
        if tail<len(text) and text[tail]==':' and SENSITIVE.search(value):
            start=tail+1
            while start<len(text) and text[start].isspace():start+=1
            try:_,end=json.JSONDecoder().raw_decode(text,start)
            except (ValueError,RecursionError):end=len(text)
            edits.append((start,end,json.dumps(REDACTED)));covered=end
        cleaned=clean_text(value,secrets)
        if cleaned!=value:edits.append((token.start(),token.end(),json.dumps(cleaned)))
    for start,end,replacement in sorted(edits,reverse=True):text=text[:start]+replacement+text[end:]
    # Unquoted secrets in malformed requests still cannot escape into storage.
    text=clean_text(text,secrets) if error else text
    if error:text=re.sub(r'(?i)(password|secret|token|credential|authorization|capability)\s*=\s*[^\s,;]+',REDACTED,text)
    if error is None:
        try:decode_payload(text)
        except (ValueError,UnicodeError,RecursionError):error='privacy_redaction_collision'
    return envelope(text,error,scanner,received_at,hashlib.sha256(body).hexdigest(),len(body))


def envelope(raw,error,scanner,received_at,body_hash,body_bytes):
    day=received_at.astimezone(IST).date().isoformat()
    payload_hash=digest([decode_payload(raw) if error is None else raw,error,body_hash if error else None])
    return dict(version=VERSION,event_id=digest([VERSION,scanner.key,day,payload_hash]),
        scanner=scanner.model_dump(mode='json'),scanner_key=scanner.key,
        received_at=received_at.astimezone(timezone.utc).isoformat(),session_date=day,
        payload_hash=payload_hash,raw_json=raw,syntax_error=error,body_sha256=body_hash,body_bytes=body_bytes,
        symbols=[],completeness='unparsed',mode=scanner.mode,
        delivery_kind='unclassified',historical_pit_qualified=False,evaluation_eligible=False)


def validate_receipt(e,scanner):
    from datetime import datetime
    if e['scanner_key']!=scanner.key:raise ValueError('receiver_scanner_not_approved')
    at=datetime.fromisoformat(e['received_at'])
    remote=Scanner.model_validate(e['scanner'])
    if at.tzinfo is None or not isinstance(e['raw_json'],(str,type(None))):raise ValueError('invalid_raw_receipt')
    if type(e['body_bytes']) is not int or not 0<=e['body_bytes']<=65536:raise ValueError('invalid_raw_receipt')
    if not re.fullmatch('[0-9a-f]{64}',e['body_sha256']):raise ValueError('invalid_raw_receipt')
    if e['syntax_error'] is not None and e['syntax_error'] not in REASONS:raise ValueError('invalid_raw_receipt')
    if not isinstance(e['raw_json'],str) or len(e['raw_json'].encode())>6*65536:raise ValueError('invalid_raw_receipt')
    if e!=envelope(e['raw_json'],e['syntax_error'],remote,at,e['body_sha256'],e['body_bytes']):
        raise ValueError('receiver_envelope_mismatch')
    return e


def parse(e, *, scanner=None):
    from datetime import datetime
    if e['syntax_error']:raise ValueError(e['syntax_error'])
    original=Scanner.model_validate(e['scanner'])
    approved=scanner or original
    if approved.key!=e['scanner_key']:raise ValueError('scanner_identity_mismatch')
    at=datetime.fromisoformat(e['received_at'])
    payload=decode_payload(e['raw_json'])
    result=normalize(payload,original,at)
    if scanner is not None:normalize(payload,approved,at)
    return result


def diagnostics(e,reason):
    try:payload=decode_payload(e['raw_json']) if e['raw_json'] is not None else None
    except (ValueError,UnicodeError,RecursionError):payload=None
    result={'reason':reason,'received_at':e['received_at'],**payload_shape(payload)}
    rows=payload.get('columns') if isinstance(payload,dict) else None
    if isinstance(rows,list):
        result['columns']=[]
        for i,row in enumerate(rows[:10]):
            report={'index':i,'type':kind(row)}
            if isinstance(row,dict):
                # Arbitrary keys stay in the private raw receipt; UI labels must be
                # ordinary field names, never URLs/capabilities or arbitrary strings.
                name=lambda k:k if re.fullmatch(r'[a-zA-Z_%][a-zA-Z0-9_% ]{0,29}',k) and not SENSITIVE.search(k) else REDACTED
                report.update(missing=sorted(set(COLUMNS)-row.keys()),
                    extra=[name(k) for k in sorted(row.keys()-set(COLUMNS))[:20]],
                    types={name(k):kind(v) for k,v in list(row.items())[:20]})
            result['columns'].append(report)
        result['columns_truncated']=len(rows)>10
    return result
