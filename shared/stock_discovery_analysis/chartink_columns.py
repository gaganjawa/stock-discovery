"""STK-095 adapter for the provider-observed columns array (13 Nov 2026).

Provider Test webhook uses numeric placeholders even for text/symbol columns.
Only that exact observed test template bypasses candidate value validation, and
it produces a delivery-test receipt with zero candidates. Live rows must satisfy
the independent typed snapshot contract and align with the validated stock list.
"""
from decimal import Decimal
import re
from .chartink_enrichment import normalize_fields

ADAPTER='chartink-columns-v1'
COLUMNS=('symbol','close','%_change','volume','marketcapname','sector','industry',
         'EMA10','ema30','sma50','rsi14','AVG_VOLUME20','avg_true_range','PREV20_HIGH')
# Observed provider Test webhook values, not market data or a simulated strategy.
TEST_OFFSETS={'symbol':4,'close':1,'%_change':2,'volume':3,'marketcapname':5,
              'sector':6,'industry':7,'EMA10':8,'ema30':9,'sma50':10,
              'rsi14':11,'AVG_VOLUME20':12,'avg_true_range':13,'PREV20_HIGH':14}


def provider_test(payload):
    if payload['stocks']!='SYMBOL 1, SYMBOL 2, SYMBOL 3':return False
    # The owner observed the same provider template at 11:45 am and 7:43 pm.
    # Its clock varies; keep the documented time grammar and every placeholder.
    if (payload['trigger_prices']!='2500.00,600.00,3400.00'
        or not re.fullmatch(r'(?:[1-9]|1[0-2]):[0-5][0-9] [ap]m',payload['triggered_at'])):
        raise ValueError('invalid_provider_test_payload')
    rows=payload['columns']
    if not isinstance(rows,list) or len(rows)!=3:raise ValueError('invalid_provider_test_payload')
    for index,row in enumerate(rows,1):
        if not isinstance(row,dict) or set(row)!=set(COLUMNS):raise ValueError('invalid_provider_test_payload')
        for key,offset in TEST_OFFSETS.items():
            value=row[key]
            if type(value) not in (int,float) or Decimal(str(value))!=Decimal(index*100)+Decimal(offset)/10:
                raise ValueError('invalid_provider_test_payload')
    return True


def adapt(rows,symbols):
    from .chartink import normalize_symbol
    if not isinstance(rows,list) or len(rows)!=len(symbols):raise ValueError('invalid_columns_count')
    result={}
    for symbol,row in zip(symbols,rows):
        if not isinstance(row,dict) or set(row)!=set(COLUMNS):raise ValueError('invalid_columns_fields')
        if not isinstance(row['symbol'],str) or normalize_symbol(row['symbol'])!=symbol:
            raise ValueError('column_symbol_mismatch')
        result[symbol]=normalize_fields({key:value for key,value in row.items() if key!='symbol'})
    return result
