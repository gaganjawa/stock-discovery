"""Chartink's documented JSON adapter. No prices become market-data evidence.

The documented triggered_at is a time, not a dated market timestamp. Receipt
date is only an unverified session hint; never backdate availability to it.
"""
import hashlib
import json
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field

IST = ZoneInfo('Asia/Kolkata')
MAX_BYTES = 65536
MAX_SYMBOLS = 500


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


class Scanner(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    scan_name: str = Field(min_length=1, max_length=200)
    scan_url: str = Field(pattern=r'^[a-z0-9][a-z0-9-]{0,199}$')
    alert_name: str = Field(min_length=1, max_length=200)
    version: str = Field(min_length=1, max_length=80)
    rules: str = Field(min_length=1, max_length=4000)
    rights_reference: str = Field(min_length=1, max_length=500)
    enabled_until: datetime
    mode: Literal['provider_alert', 'synthetic_fixture'] = 'provider_alert'

    @property
    def key(self):
        return digest([self.scan_url,self.version,self.rules,self.mode])


def normalize_symbol(value):
    # No guessed ISIN, broker key, alias, exchange prefix or share class.
    symbol = value.strip().upper()
    if not re.fullmatch(r'[A-Z0-9][A-Z0-9&.-]{0,29}', symbol):
        raise ValueError('invalid_symbol')
    return symbol


def normalize(payload, scanner, received_at):
    if received_at.tzinfo is None or scanner.enabled_until.tzinfo is None:
        raise ValueError('timezone_required')
    if received_at >= scanner.enabled_until:
        raise ValueError('scanner_authorization_expired')
    enrichment = None
    if isinstance(payload, dict) and 'synthetic_enrichment_v1' in payload:
        if scanner.mode != 'synthetic_fixture': raise ValueError('synthetic_scanner_required')
        payload = dict(payload)
        enrichment = payload.pop('synthetic_enrichment_v1')
    columns = payload.get('columns') if isinstance(payload,dict) and 'columns' in payload else None
    has_columns = isinstance(payload,dict) and 'columns' in payload
    if has_columns and enrichment is not None:raise ValueError('conflicting_payload_versions')
    required = {'stocks','trigger_prices','triggered_at','scan_name','scan_url','alert_name'}
    if not isinstance(payload, dict) or not required <= payload.keys() or payload.keys() - required - {'webhook_url','columns'}:
        raise ValueError('invalid_payload_fields')
    if any(not isinstance(v, str) or len(v)>20000 for k,v in payload.items() if k!='columns'):
        raise ValueError('invalid_payload_values')
    if any(payload[k] != getattr(scanner,k) for k in ('scan_name','scan_url','alert_name')):
        raise ValueError('scanner_identity_mismatch')
    if has_columns:
        from .chartink_columns import provider_test
        if provider_test(payload):
            envelope=_envelope(payload,scanner,received_at,[])
            envelope.update(version='chartink-provider-test-v1',delivery_kind='provider_test',
                adapter_version='chartink-columns-v1',completeness='provider_test_not_market_delivery')
            return envelope
    symbols = [normalize_symbol(s) for s in payload['stocks'].split(',')]
    prices = payload['trigger_prices'].split(',')
    if not 1 <= len(symbols) <= MAX_SYMBOLS or len(prices) != len(symbols) or len(set(symbols)) != len(symbols):
        raise ValueError('invalid_symbol_price_count')
    for value in prices:
        try: price = Decimal(value)
        except InvalidOperation: raise ValueError('invalid_trigger_price') from None
        if not price.is_finite() or not 0 < price <= 1000000000 or len(value)>32:
            raise ValueError('invalid_trigger_price')
    if not re.fullmatch(r'(?:[1-9]|1[0-2]):[0-5][0-9] [ap]m',payload['triggered_at']):
        raise ValueError('invalid_trigger_time')
    envelope=_envelope(payload,scanner,received_at,symbols)
    safe=envelope['payload']
    if has_columns:
        from .chartink_columns import adapt,ADAPTER
        envelope.update(version='chartink-event-columns-v1',adapter_version=ADAPTER,
            enrichment=adapt(columns,symbols))
    if enrichment is not None:
        from .chartink_enrichment import normalize_fields
        if not isinstance(enrichment, dict) or set(enrichment) - set(symbols):
            raise ValueError('invalid_enrichment_symbols')
        envelope['enrichment'] = {symbol: normalize_fields(row) for symbol,row in enrichment.items()}
        safe['synthetic_enrichment_v1'] = enrichment
        envelope['payload_hash'] = digest(safe)
        envelope['version'] = 'chartink-event-synthetic-enriched-v1'
    envelope['event_id'] = digest([scanner.key,envelope['session_date'],safe])
    return envelope


def _envelope(payload,scanner,received_at,symbols):
    # webhook_url may contain the bearer capability: never retain or export it.
    safe = {k:v for k,v in payload.items() if k != 'webhook_url'}
    session = received_at.astimezone(IST).date().isoformat()
    envelope = dict(version='chartink-event-v1',scanner=scanner.model_dump(mode='json'),
        scanner_key=scanner.key,source_url='https://chartink.com/screener/'+scanner.scan_url,
        received_at=received_at.astimezone(timezone.utc).isoformat(),session_date=session,
        event_at=None, timestamp_basis='receipt_date_unverified_provider_time_only',
        payload_hash=digest(safe),payload=safe,symbols=sorted(symbols),
        completeness='partial_unverified',mode=scanner.mode,
        historical_pit_qualified=False,evaluation_eligible=False)
    envelope['event_id']=digest([scanner.key,session,safe])
    return envelope


def fixture_snapshot(scanner, symbols, session_date, received_at, *, complete=False):
    """Explicit test fixture; never reachable from the public webhook."""
    if scanner.mode != 'synthetic_fixture': raise ValueError('fixture_scanner_required')
    envelope = normalize(dict(stocks=','.join(symbols),trigger_prices=','.join('100' for _ in symbols),
        triggered_at='6:00 pm',scan_name=scanner.scan_name,scan_url=scanner.scan_url,
        alert_name=scanner.alert_name),scanner,received_at)
    datetime.strptime(session_date,'%Y-%m-%d')
    envelope.update(session_date=session_date,timestamp_basis='synthetic_fixture_session',
                    completeness='verified_fixture_snapshot' if complete else 'partial_unverified')
    envelope['event_id']=digest([scanner.key,session_date,envelope['payload'],envelope['completeness']])
    return envelope
