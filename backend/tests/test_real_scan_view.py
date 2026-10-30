from types import SimpleNamespace as NS
import pytest
from stock_discovery_analysis import real_scan_view as views


def test_scan_financial_scope_revocation_blocks_cached_findings(monkeypatch):
    scan={'universe':{'account_ref':'test'},'rows':[{'financial_fact_count':1,'source_revisions':[],'financial_findings':[]}]}
    class DB:
        def execute(self,sql,args):
            return NS(fetchall=lambda:[],fetchone=lambda:(scan,))
    calls=[]
    def require(stream,uses):
        calls.append(stream.scope)
        if stream.scope=='financial_facts':raise PermissionError('scope_denied')
    monkeypatch.setattr(views,'source_access',lambda config:NS(require=require))
    with pytest.raises(PermissionError):views._scan_view(DB(),NS(pilot_scope_id='test',sources=None),NS(require=require))
    assert calls==['universe','financial_facts']


def test_unconfigured_scan_never_reads_or_falls_back_to_fixtures():
    assert views.scan_view(None,NS(pilot_scope_id=None))==dict(status='not_configured',scan=None,jobs=[])
