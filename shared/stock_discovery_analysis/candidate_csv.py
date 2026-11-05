"""Exceptional recovery/development adapter; never a daily production workflow.

Column mapping is explicit because the supplied CSVs were not available during
implementation. Imports do not certify completeness or historical availability.
"""
import csv
import hashlib
import io
from datetime import date, datetime
from .chartink import normalize, normalize_symbol, digest


def events(raw,scanner,received_at,*,symbol_column='Symbol',date_column='Date',session=None,date_format='%Y-%m-%d'):
    if len(raw)>10*1024*1024:raise ValueError('csv_too_large')
    reader=csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
    if not reader.fieldnames or symbol_column not in reader.fieldnames or (session is None and date_column not in reader.fieldnames):
        raise ValueError('csv_column_mapping_required')
    grouped={};labels={};count=0
    for row in reader:
        count+=1
        if count>50000:raise ValueError('csv_row_limit')
        day=(date.fromisoformat(session) if session else datetime.strptime(row[date_column].strip(),date_format).date()).isoformat()
        if day>received_at.date().isoformat():raise ValueError('future_csv_session')
        symbol=normalize_symbol(row[symbol_column])
        grouped.setdefault(day,set()).add(symbol)
        if row.get('Stock Name'):
            label=row['Stock Name'].strip()
            if len(label)>200:raise ValueError('company_label_too_long')
            labels[symbol]=label
    file_hash=hashlib.sha256(raw).hexdigest()
    result=[]
    for day,symbols in sorted(grouped.items()):
        ordered=sorted(symbols)
        for offset in range(0,len(ordered),500):
            part=ordered[offset:offset+500]
            # The normalizer's price field is not used as evidence. Strip the
            # placeholder immediately and label the distinct recovery contract.
            e=normalize(dict(stocks=','.join(part),trigger_prices=','.join('1' for _ in part),
                triggered_at='6:00 pm',scan_name=scanner.scan_name,scan_url=scanner.scan_url,alert_name=scanner.alert_name),scanner,received_at)
            e['payload'].pop('trigger_prices');e['payload'].pop('triggered_at')
            e.update(session_date=day,timestamp_basis='csv_session_unverified',
                mode='synthetic_fixture' if scanner.mode=='synthetic_fixture' else 'csv_recovery',
                csv_provenance=dict(file_sha256=file_hash,adapter_version='csv-recovery-v1',
                    symbol_column=symbol_column,date_column=date_column if session is None else None,date_format=date_format))
            e['labels']={symbol:labels[symbol] for symbol in part if symbol in labels}
            e['payload_hash']=digest(e['payload'])
            e['event_id']=digest([scanner.key,day,file_hash,part])
            result.append(e)
    return result,dict(rows=count,matches=sum(len(v) for v in grouped.values()),
        stocks=len(set().union(*grouped.values())) if grouped else 0,sessions=len(grouped),
        first_session=min(grouped,default=None),last_session=max(grouped,default=None),
        completeness='partial_unverified',historical_pit_qualified=False)
