"""Explicit owner-authorized read-only API diagnostic, not source activation.

Does not create a D3-02 storage/AI grant. Retains only connection metadata and
record counts, never response bodies, prices or tokens. No orders or paid APIs.
"""
import argparse
import gzip
import io
import json
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import quote
import httpx


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--token-file',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--financial-news',action='store_true',help='also probe documented financial/news endpoints; retain only counts')
    args=p.parse_args()
    token=args.token_file.read_text().strip()
    assert token and '\n' not in token
    result={'checked_at':datetime.now(timezone.utc).isoformat(),'status':'partial',
            'scope':'owner_authorized_read_only_connectivity_probe','storage_activated':False,'ai_processing_activated':False,'requests':[]}
    with httpx.Client(timeout=20,trust_env=False,follow_redirects=False) as client:
        def fetch(url,auth=True):
            headers={'Accept':'application/json'}
            if auth:headers['Authorization']='Bearer '+token
            with client.stream('GET',url,headers=headers) as r:
                result['requests'].append({'url':url,'status':r.status_code,'fetched_at':datetime.now(timezone.utc).isoformat()})
                if r.status_code!=200:raise RuntimeError('provider_http_'+str(r.status_code))
                raw=bytearray()
                for chunk in r.iter_bytes():
                    raw.extend(chunk)
                    if len(raw)>32_000_000:raise RuntimeError('response_limit')
                return bytes(raw)
        try:
            url='https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz'
            raw=fetch(url,False)
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as gz:body=gz.read(64_000_001)
            if len(body)>64_000_000:raise RuntimeError('master_limit')
            rows=json.loads(body)
            matches=[r for r in rows if r.get('trading_symbol')=='INFY' and r.get('segment')=='NSE_EQ' and r.get('instrument_type')=='EQ']
            if len(matches)!=1:raise RuntimeError('ambiguous_identity')
            row=matches[0]
            result['instrument']={k:row[k] for k in ('name','trading_symbol','isin','instrument_key')}
            url='https://api.upstox.com/v3/historical-candle/'+quote(row['instrument_key'],safe='')+'/days/1/2026-10-16/2026-10-01'
            candles=json.loads(fetch(url))
            if candles.get('status')!='success':raise RuntimeError('provider_status')
            bars=candles['data']['candles']
            result['candles']={'count':len(bars),'first_label':min((r[0] for r in bars),default=None),'last_label':max((r[0] for r in bars),default=None),'values_retained':False}
            calendar=json.loads(fetch('https://api.upstox.com/v2/market/timings/2026-10-16'))
            result['calendar']={'status':calendar.get('status'),'nse_rows':sum(r.get('exchange')=='NSE' for r in calendar.get('data',[]))}
            if args.financial_news:
                base='https://api.upstox.com/v2/fundamentals/'+quote(row['isin'],safe='')
                result['financial_access']={}
                for endpoint in ('income-statement','balance-sheet','cash-flow'):
                    payload=json.loads(fetch(base+'/'+endpoint+'?type=consolidated&time_period=yearly'))
                    data=payload.get('data',{})
                    result['financial_access'][endpoint]={'status':payload.get('status'),'fields':sorted(data),'scope':data.get('type'),'units':data.get('units_in'),'values_retained':False}
                news=json.loads(fetch('https://api.upstox.com/v2/news?category=instrument_keys&instrument_keys='+quote(row['instrument_key'],safe='')+'&page_number=1&page_size=10'))
                result['news_access']={'status':news.get('status'),'count':len(news.get('data',{}).get(row['instrument_key'],[])),'text_retained':False,'official_announcements':False}
            result['status']='access_verified'
        except (httpx.HTTPError,RuntimeError,ValueError,KeyError) as e:
            result['error']=str(e) if isinstance(e,RuntimeError) else type(e).__name__
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    if result['status']!='access_verified':raise SystemExit(1)


if __name__=='__main__':main()
