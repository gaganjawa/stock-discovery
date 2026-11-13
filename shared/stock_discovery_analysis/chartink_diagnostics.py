"""STK-095 bounded structure-only rejection diagnostics. Never retain scalar values.

Only recognized schema/column labels are disclosed. Arbitrary JSON keys can be
secrets or stock symbols too, so unrecognized names are counted, never copied.
"""
import json
from collections import Counter

VERSION='chartink-rejection-shape-v1'
KNOWN_FIELDS=frozenset(('stocks','trigger_prices','triggered_at','scan_name','scan_url',
    'alert_name','webhook_url','columns','symbol','stock_name','stockname','close',
    '%_change','change_pct','volume','marketcapname','sector','industry','EMA10',
    'ema10','ema30','sma50','rsi14','AVG_VOLUME20','avg_volume20','avg_true_range',
    'PREV20_HIGH','previous_20_session_high','synthetic_enrichment_v1'))
MAX_DEPTH=4
MAX_ITEMS=16
MAX_NODES=160


def kind(value):
    if value is None:return 'null'
    if isinstance(value,bool):return 'boolean'
    if isinstance(value,str):return 'string'
    if isinstance(value,(int,float)):return 'number'
    if isinstance(value,list):return 'array'
    if isinstance(value,dict):return 'object'
    return 'unknown'


def payload_shape(payload):
    remaining=MAX_NODES
    def visit(value,depth):
        nonlocal remaining
        remaining-=1
        result={'type':kind(value)}
        if isinstance(value,(dict,list)):
            result['count']=len(value)
            if depth>=MAX_DEPTH or remaining<=0:
                result['truncated']=True
                return result
        if isinstance(value,dict):
            fields={};redacted=0;redacted_types=Counter()
            for key,item in value.items():
                if key not in KNOWN_FIELDS:
                    redacted+=1;redacted_types[kind(item)]+=1;continue
                if len(fields)>=MAX_ITEMS or remaining<=0:
                    result['truncated']=True;continue
                fields[key]=visit(item,depth+1)
            result.update(fields=fields,redacted_field_count=redacted,redacted_value_types=dict(redacted_types))
        elif isinstance(value,list):
            result['item_types']=dict(Counter(kind(item) for item in value))
            # Deduplicate sampled structures; never retain array positions/values.
            shapes=[];sampled=0
            for item in value[:MAX_ITEMS]:
                if remaining<=0:break
                sampled+=1
                shape=visit(item,depth+1)
                if shape not in shapes:shapes.append(shape)
            result['sampled_shapes']=shapes
            result['sampled_count']=sampled
            if len(value)>MAX_ITEMS or remaining<=0:result['truncated']=True
        return result
    return {'version':VERSION,'shape':visit(payload,0)}


def decode_payload(body):
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('duplicate_payload_field')
            result[key]=value
        return result
    def invalid_constant(_):raise ValueError('invalid_json')
    return json.loads(body,object_pairs_hook=unique,parse_constant=invalid_constant)
