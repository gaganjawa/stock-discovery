"""STK-004/014: bounded, unregistered Breeze read-only probe contract.

Caller owns an already authenticated official SDK and rights/fence Access. No SDK
import, login, order API, persistence or conversion to qualified candles occurs.
Unknown adjustment, volume and availability semantics remain unknown.
"""
import csv
import io
from datetime import date, datetime, timezone

from stock_discovery_contracts.v2 import at, check

SOURCE = 'icici_breeze'
ISIN = 'INE009A01021'
SYMBOL = 'INFY'


def resolve_infy(master_csv):
    """Resolve the official NSE cash master by ISIN, never by a company-name hint.

    SecurityMaster.zip's NSEScripMaster.txt uses spaces before quoted headings.
    get_names() supplies a cross-check but does not itself supply ISIN ownership.
    """
    check(isinstance(master_csv, str) and len(master_csv) <= 16_000_000,
          'breeze_master_limit')
    reader = csv.DictReader(io.StringIO(master_csv), skipinitialspace=True)
    fields = reader.fieldnames or []
    check(len(fields) == len(set(fields)) and
          {'ShortName', 'ExchangeCode', 'ISINCode', 'Series'} <= set(fields),
          'breeze_master_columns')
    candidates = []
    for row in reader:
        check(None not in row, 'breeze_master_row_shape')
        if row.get('ISINCode') == ISIN or row.get('ExchangeCode') == SYMBOL:
            candidates.append(row)
    check(len(candidates) == 1, 'breeze_identity_missing_or_ambiguous')
    row = candidates[0]
    check(row['ISINCode'] == ISIN and row['ExchangeCode'] == SYMBOL and
          row['Series'] == 'EQ' and isinstance(row['ShortName'], str) and
          row['ShortName'].isascii() and row['ShortName'].isalnum(),
          'breeze_identity_mismatch')
    return row['ShortName']


def _sdk_read(call, stream, access):
    access.require(stream, ('acquire', 'derive'))
    try:
        response = call()
    except Exception:
        # SDK exceptions can include API keys, session URLs or provider bodies.
        raise RuntimeError('breeze_sdk_read_failed') from None
    access.require(stream, ('acquire', 'derive'))
    check(isinstance(response, dict), 'breeze_response_shape')
    status = response.get('Status')
    if type(status) is int and status in (401, 403):
        raise PermissionError('breeze_authentication_rejected' if status == 401
                              else 'breeze_authorization_rejected')
    return response


def probe_infy(sdk, *, access, universe, prices, master_csv, start, end):
    """At most two SDK reads. All returned counts remain INSUFFICIENT_EVIDENCE.

    Only get_names and get_historical_data_v2 are called. No automatic retry or
    authentication refresh. The caller must enforce aggregate account quotas and
    SDK timeout/logging controls before any future real execution.
    """
    check(universe.source_id == prices.source_id == SOURCE and
          universe.account_ref == prices.account_ref and
          universe.scope == 'universe' and prices.scope == 'prices',
          'breeze_stream_mismatch')
    access.require(universe, ('acquire', 'derive'))
    access.require(prices, ('acquire', 'derive'))
    stock_code = resolve_infy(master_csv)
    try:
        first, last = date.fromisoformat(start), date.fromisoformat(end)
    except (TypeError, ValueError):
        raise ValueError('breeze_date_range') from None
    cutoff = at(access.clock()).replace(tzinfo=timezone.utc)
    check(start == first.isoformat() and end == last.isoformat() and
          first <= last and (last - first).days <= 90 and last < cutoff.date(),
          'breeze_date_range')
    names = _sdk_read(lambda: sdk.get_names(exchange_code='NSE', stock_code=SYMBOL),
                      universe, access)
    check((names.get('exchange_code'), names.get('exchange_stock_code'),
           names.get('isec_stock_code')) == ('NSE', SYMBOL, stock_code),
          'breeze_sdk_identity_mismatch')
    response = _sdk_read(lambda: sdk.get_historical_data_v2(
        interval='1day', from_date=start+'T00:00:00.000Z',
        to_date=end+'T23:59:59.000Z', stock_code=stock_code,
        exchange_code='NSE', product_type='cash'), prices, access)
    status = response.get('Status')
    check(type(status) is int and status == 200 and 'Error' in response and response['Error'] is None,
          'breeze_provider_failed')
    rows = response.get('Success')
    check(isinstance(rows, list) and len(rows) <= 91, 'breeze_response_limit')
    days = set()
    for row in rows:
        check(isinstance(row, dict) and row.get('stock_code') == stock_code and
              row.get('exchange_code') == 'NSE' and
              row.get('product_type') in (None, 'Cash', 'cash') and
              {'open', 'high', 'low', 'close', 'volume', 'datetime'} <= row.keys(),
              'breeze_foreign_or_invalid_row')
        try:
            # Inspect date labels only. A naive provider label is not session
            # close, publication, first availability or proof of a timezone.
            label = datetime.fromisoformat(row['datetime']).date()
        except (TypeError, ValueError):
            raise ValueError('breeze_date_label') from None
        check(first <= label <= last and label not in days,
              'breeze_duplicate_or_out_of_range_date')
        days.add(label)
    access.require(universe, ('acquire', 'derive'))
    access.require(prices, ('acquire', 'derive'))
    return dict(status='INSUFFICIENT_EVIDENCE', source_id=SOURCE,
        instrument_id='NSE:'+ISIN, provider_stock_code=stock_code,
        fetched_at=access.clock(), provider_status=status, provider_error=None,
        row_count=len(rows), unique_date_labels=tuple(sorted(d.isoformat() for d in days)),
        minimum_30_date_labels=len(days) >= 30,
        price_basis='unknown', volume_basis='unknown', session_coverage='unverified',
        ohlcv_values_validated=False, corporate_actions_verified=False,
        published_at=None, first_available_at=None, immutable_revisions_persisted=False,
        actionable=False, publication_authorized=False, paper_admission_authorized=False,
        storage_activated=False)
