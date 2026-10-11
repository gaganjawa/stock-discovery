from dataclasses import replace
from datetime import timedelta
import pytest
from stock_discovery_analysis.universe import Membership, universe_asof
from test_data import T, candle


def test_delisted_stocks_exist_in_past_and_late_revisions_do_not_leak():
    p=replace(candle().provenance,published_at=T,available_at=T,fetched_at=T)
    listed=Membership('SYN-A',T,'listed',p)
    later=T+timedelta(days=1)
    gone=Membership('SYN-A',later,'delisted',p)
    assert universe_asof((listed,gone),T)==('SYN-A',)
    assert universe_asof((listed,gone),later)==()
    suspended=replace(gone,state='suspended')
    assert universe_asof((listed,suspended),later)==()
    assert universe_asof((listed,replace(gone,provenance=replace(p,available_at=later+timedelta(days=1),fetched_at=later+timedelta(days=1)))),later)==('SYN-A',)
    with pytest.raises(ValueError): universe_asof((gone,suspended),later)
