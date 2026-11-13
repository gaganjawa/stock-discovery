"""STK-095 synthetic enrichment contract; not a verified Chartink wire format."""
from decimal import Decimal, DecimalException
import re

FIELDS = ('stock_name','close','change_pct','volume','market_cap_category','sector',
          'industry','ema10','ema30','sma50','rsi14','avg_volume20','atr14',
          'previous_20_session_high')
TEXT = {'stock_name','market_cap_category','sector','industry'}
ALIASES = {'stockname':'stock_name','marketcapname':'market_cap_category',
           'change':'change_pct','changepct':'change_pct','prev20high':'previous_20_session_high',
           'avgtruerange':'atr14'}
ALIASES.update({re.sub('[^a-z0-9]','',k):k for k in FIELDS})


def normalize_fields(row, *, atr_period=None):
    # Every decimal conversion/comparison and derived metric shares this boundary.
    try:
        return _normalize_fields(row, atr_period=atr_period)
    except DecimalException:
        raise ValueError('invalid_enrichment_number') from None


def _normalize_fields(row, *, atr_period=None):
    if not isinstance(row,dict): raise ValueError('invalid_enrichment')
    values={}; provenance={}
    for alias, raw in row.items():
        key=ALIASES.get(re.sub('[^a-z0-9]','',alias.lower()))
        if key is None: raise ValueError('unknown_enrichment_field')
        if raw is None or raw=='': value=None
        elif key in TEXT:
            if not isinstance(raw,str) or len(raw)>200 or any(ord(c)<32 for c in raw):
                raise ValueError('invalid_enrichment_text')
            value=raw.strip() or None
        else:
            if isinstance(raw,bool) or not isinstance(raw,(str,int,float)) or len(str(raw))>32:
                raise ValueError('invalid_enrichment_number')
            number=Decimal(str(raw))
            if number.is_finite():
                parts=number.as_tuple()
                if len(parts.digits)>28 or not -28<=parts.exponent<=12:
                    raise ValueError('invalid_enrichment_number')
            low=-100 if key=='change_pct' else 0
            high=100 if key=='rsi14' else 1000000000000
            if not number.is_finite() or not low<=number<=high:
                raise ValueError('invalid_enrichment_range')
            if key in {'close','ema10','ema30','sma50','previous_20_session_high'} and number==0:
                raise ValueError('invalid_enrichment_range')
            value=str(number)
        if key in values and values[key]!=value: raise ValueError('ambiguous_enrichment_alias')
        values[key]=value
        provenance.setdefault(key,[]).append(alias)
    states={k:('present' if values.get(k) is not None else 'missing') for k in FIELDS}
    if values.get('atr14') is not None and atr_period!=14:
        states['atr14']='period_unverified';values['atr14']=None
    metrics={}
    for name,a,b,subtract in [('relative_volume','volume','avg_volume20',False),
        ('distance_from_previous_high_pct','close','previous_20_session_high',True),
        ('atr_pct','atr14','close',False),('ema_trend_distance_pct','ema10','ema30',True)]:
        if values.get(a) is not None and values.get(b) is not None and Decimal(values[b])!=0:
            ratio=Decimal(values[a])/Decimal(values[b])
            metrics[name]=str((ratio-1)*100 if subtract else ratio if name=='relative_volume' else ratio*100)
    return dict(values=values,field_states=states,field_provenance=provenance,
        source='chartink',qualification='unverified_snapshot_not_market_evidence',
        metrics=metrics,completeness='complete' if all(v=='present' for v in states.values()) else 'partial')
