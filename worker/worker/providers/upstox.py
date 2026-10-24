"""Read-only Upstox V3 daily adapter, gated by D3-02 before every request.

Calendar sessions must come from approved dated observations. A weekday is not
proof of an NSE session, and a midnight daily-bar label is not a session close.
No endpoint for trading exists here. API availability is not a storage licence.
"""
import gzip
import io
import json
import re
import time
from datetime import date, datetime, timezone
from decimal import Decimal
from urllib.parse import quote
from zoneinfo import ZoneInfo

import httpx
from stock_discovery_contracts.v2 import at, check, digest
from stock_discovery_analysis.revisions import CandleData, InstrumentData, Revision, SessionData
from stock_discovery_analysis.revision_storage import Page

SOURCE = 'upstox'
MASTER = 'https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz'
IST = ZoneInfo('Asia/Kolkata')


class Upstox:
    def __init__(self, *, access, token=None, transport=None, monotonic=time.monotonic, request_gate=None):
        self.access, self.token, self.monotonic = access, token, monotonic
        self.client = httpx.Client(transport=transport, trust_env=False, follow_redirects=False)
        self.calls = []
        self.request_gate = request_gate

    def close(self):
        self.client.close()

    def _get(self, url, stream, *, authenticated=True):
        check(stream.source_id == SOURCE, 'source_mismatch')
        self.access.require(stream, ('acquire',))
        if self.request_gate:self.request_gate()
        # Conservative per-process cap (below documented aggregate limits).
        # The single durable scheduler worker owns this adapter; other clients
        # on the same account must share the owner's aggregate quota allocation.
        now = self.monotonic()
        self.calls = [t for t in self.calls if t > now-1800]
        check(len(self.calls) < 1000 and sum(t > now-60 for t in self.calls) < 100
              and sum(t > now-1 for t in self.calls) < 2, 'source_rate_limited')
        headers = {'Accept':'application/json'}
        if authenticated:
            if not self.token:
                raise PermissionError('upstox_credentials_missing')
            headers['Authorization'] = 'Bearer '+self.token
        self.calls.append(now)
        try:
            with self.client.stream('GET', url, headers=headers, timeout=20) as response:
                if response.status_code in (401,403):
                    raise PermissionError('upstox_credentials_rejected')
                if response.status_code == 429:
                    raise RuntimeError('upstox_rate_limited')
                if response.status_code != 200:
                    raise RuntimeError('upstox_http_'+str(response.status_code))
                raw = bytearray()
                started = self.monotonic()
                for chunk in response.iter_bytes():
                    raw.extend(chunk)
                    check(len(raw) <= 32_000_000, 'provider_response_limit')
                    if self.monotonic()-started > 30:
                        raise TimeoutError('provider_deadline')
            self.access.require(stream, ('acquire',))
            return bytes(raw)
        except httpx.TimeoutException:
            raise TimeoutError('upstox_timeout') from None
        except httpx.HTTPError:
            raise RuntimeError('upstox_unavailable') from None

    def instrument_master(self, stream):
        check(stream.scope == 'universe', 'universe_scope_required')
        raw = self._get(MASTER, stream, authenticated=False)
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as archive:
            decoded = archive.read(64_000_001)
        check(len(decoded) <= 64_000_000, 'master_decompression_limit')
        rows = json.loads(decoded)
        check(isinstance(rows, list), 'invalid_instrument_master')
        self.access.require(stream, ('derive',))
        return rows, digest(rows)

    def instruments(self, stream, symbols):
        check(stream.scope == 'universe', 'universe_scope_required')
        check(0 < len(symbols) <= 100 and len(set(symbols)) == len(symbols), 'universe_limit')
        check(all(re.fullmatch(r'[A-Z0-9&-]{1,30}', s) for s in symbols), 'invalid_symbol')
        rows, _ = self.instrument_master(stream)
        result = []
        for symbol in symbols:
            matches = [r for r in rows if r.get('segment') == 'NSE_EQ' and r.get('exchange') == 'NSE'
                       and r.get('instrument_type') == 'EQ' and r.get('trading_symbol') == symbol]
            check(len(matches) == 1, 'instrument_missing_or_ambiguous:'+symbol)
            row = matches[0]
            check(re.fullmatch(r'IN[A-Z0-9]{10}', row.get('isin','')) is not None, 'invalid_isin')
            check(row.get('instrument_key') == 'NSE_EQ|'+row['isin'], 'instrument_key_mismatch')
            check(isinstance(row.get('name'), str) and row['name'].strip(), 'company_name_missing')
            check(type(row.get('lot_size')) is int and row['lot_size'] > 0, 'lot_size_missing')
            # Upstox instrument-file tick_size is expressed in paise.
            tick = Decimal(str(row['tick_size']))/100
            check(tick.is_finite() and tick > 0, 'invalid_tick')
            result.append(dict(symbol=symbol, name=row['name'], isin=row['isin'],
                               instrument_key=row['instrument_key'], lot_size=row['lot_size'], tick_size=str(tick)))
        return result

    def session(self, stream, day):
        """Observe the dated NSE cash session; absence is not a weekday guess."""
        check(stream.scope == 'calendar', 'calendar_scope_required')
        date.fromisoformat(day)
        payload = json.loads(self._get('https://api.upstox.com/v2/market/timings/'+day, stream))
        check(payload.get('status') == 'success' and isinstance(payload.get('data'), list), 'invalid_market_timings')
        matches = [r for r in payload['data'] if r.get('exchange') == 'NSE']
        check(len(matches) <= 1, 'ambiguous_market_timings')
        if not matches: return None
        row = matches[0]
        check(type(row['start_time']) is int and type(row['end_time']) is int, 'invalid_session_timestamp')
        opens = datetime.fromtimestamp(row['start_time']/1000, timezone.utc)
        closes = datetime.fromtimestamp(row['end_time']/1000, timezone.utc)
        check(opens.astimezone(IST).date().isoformat() == day and closes.astimezone(IST).date().isoformat() == day, 'session_date_mismatch')
        self.access.require(stream, ('derive',))
        return SessionData(kind='session', calendar_version='upstox-dated-NSE-v1',
            opens_at=opens.isoformat().replace('+00:00','Z'), closes_at=closes.isoformat().replace('+00:00','Z'))

    def candles(self, stream, instrument, start, end, sessions):
        check(stream.scope == 'prices', 'prices_scope_required')
        check(instrument.source_id == SOURCE and instrument.data.kind == 'instrument'
              and instrument.availability_basis == 'observed', 'real_upstox_instrument_required')
        first, last = date.fromisoformat(start), date.fromisoformat(end)
        check(first <= last and (last-first).days <= 366, 'bounded_daily_range')
        key = 'NSE_EQ|'+instrument.data.isin
        url = 'https://api.upstox.com/v3/historical-candle/'+quote(key,safe='')+'/days/1/'+end+'/'+start
        payload = json.loads(self._get(url, stream))
        check(payload.get('status') == 'success', 'provider_status_failed')
        rows = payload.get('data',{}).get('candles')
        check(isinstance(rows,list) and len(rows) <= 367, 'invalid_candle_response')
        self.access.require(stream, ('derive',))
        fetched = self.access.clock()
        result, seen = [], set()
        for row in rows:
            check(isinstance(row,list) and len(row) == 7, 'invalid_candle_shape')
            labelled = datetime.fromisoformat(row[0])
            check(labelled.tzinfo is not None, 'naive_provider_time')
            day = labelled.astimezone(IST).date().isoformat()
            check(start <= day <= end and day not in seen, 'duplicate_or_out_of_range_bar')
            seen.add(day)
            check(day in sessions, 'unverified_market_session:'+day)
            opens, closes = sessions[day]
            check(at(opens).replace(tzinfo=timezone.utc).astimezone(IST).date().isoformat() == day
                  and at(closes).replace(tzinfo=timezone.utc).astimezone(IST).date().isoformat() == day, 'session_date_mismatch')
            check(at(closes) <= at(fetched), 'unclosed_candle')
            check(type(row[5]) is int, 'invalid_volume')
            data = CandleData(kind='candle', interval='1d', starts_at=opens, ends_at=closes,
                              open=str(row[1]), high=str(row[2]), low=str(row[3]), close=str(row[4]),
                              volume=row[5], adjustment_basis='split_bonus_adjusted')
            result.append((data, fetched))
        return tuple(sorted(result, key=lambda r:r[0].ends_at))


def observed_revision(data, *, listing, fetched, parent=None, previous=None):
    """Append corrected observations; never claim historical availability.

    Caller selects the previous revision by source + logical key under the
    existing ingestion lock. Identical content reuses its first observed clock.
    """
    if previous and previous.data == data and not (data.kind == 'candle' and data.adjustment_basis != 'raw'):
        return previous
    raw = data.model_dump(mode='json')
    sequence = previous.sequence+1 if previous else 1
    return Revision(schema_version='1.0.0', revision_id='UP-'+digest([listing,raw,fetched,sequence]),
        source_id=SOURCE, source_revision=digest([raw,fetched,sequence]), sequence=sequence,
        listing_id=listing, instrument_revision_id=parent,
        published_at=fetched, available_at=fetched, fetched_at=fetched,
        availability_basis='observed', archive_evidence_ref=None, archive_revision_id=None,
        supersedes_id=previous.revision_id if previous else None, data=data)


class RevisionPages:
    """Frozen response paging into existing D3-03 transactional ingestion."""
    def __init__(self, records):
        self.records = tuple(r.model_dump(mode='json') for r in records)

    def fetch(self, cursor, limit):
        check(0 < limit <= 100, 'page_limit')
        offset = int(cursor) if cursor else 0
        check(0 <= offset <= len(self.records), 'invalid_cursor')
        rows = self.records[offset:offset+limit]
        end = offset+len(rows)
        return Page(cursor=cursor, next_cursor=str(end) if end < len(self.records) else None,
                    complete=end == len(self.records), records=rows)
