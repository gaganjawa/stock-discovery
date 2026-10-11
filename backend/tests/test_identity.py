from datetime import timedelta
from dataclasses import replace
import pytest
from stock_discovery_analysis.identity import Instrument, SymbolMapping, resolve
from test_data import T, candle


def test_symbol_reuse_and_namespaces_do_not_join_securities():
    p = replace(candle().provenance, published_at=T, available_at=T, fetched_at=T)
    old = SymbolMapping('SYN-old', 'NSE:EQ', 'ABC', T, T+timedelta(days=2), p)
    new = SymbolMapping('SYN-new', 'NSE:EQ', 'ABC', T+timedelta(days=2), None, p)
    mappings = (old,new)
    assert resolve(mappings, 'NSE:EQ','ABC',T,T) == 'SYN-old'
    later = T+timedelta(days=2)
    assert resolve(mappings, 'NSE:EQ','ABC',later,later) == 'SYN-new'
    assert resolve(mappings, 'BSE','ABC',later,later) is None
    assert resolve((replace(old, provenance=replace(p, available_at=later, fetched_at=later)),),
                   'NSE:EQ','ABC',T,T) is None
    with pytest.raises(ValueError):
        resolve(mappings, 'NSE:EQ','ABC',later,T)
    with pytest.raises(ValueError):
        resolve((old,replace(old,instrument_id='other')), 'NSE:EQ','ABC',T,T)


def test_synthetic_identity_is_separate():
    Instrument('SYN-A',None,'SYNTHETIC_NSE','EQ')
    with pytest.raises(ValueError):
        Instrument('SYN-A',None,'NSE','EQ')
    with pytest.raises(ValueError):
        Instrument('real',None,'NSE','EQ',False)
