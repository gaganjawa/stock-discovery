"""Fabricated tiny contract tables, never real-provider acceptance."""
import pytest
from worker.providers.upstox_financials import statement_report


def payload(lines):
    return {'status':'success','data':{'type':'consolidated','time_period':'yearly','units_in':'crore',
        'full_statement':[{'particular':label,'history':[{'period':'Mar 2026','value':value}]} for label,value in lines.items()]}}


def test_revenue_uses_precise_line_and_tax_reconciles():
    data=payload({'Revenue':100,'Other Income':10,'Total Revenue':110,'Profit Before Tax':30,'Tax':5,'Profit After Tax':25})
    report=statement_report(data,'income-statement')
    assert report.facts[0].metric=='revenue' and report.facts[0].value=='100'
    assert report.facts[0].period_start_at=='2025-03-31T18:30:00Z'
    assert report.facts[0].period_end_at=='2026-03-31T18:29:59Z'
    assert 'Operating margin' in report.text
    data['data']['full_statement'][2]['history'][0]['value']=111
    with pytest.raises(ValueError,match='revenue_reconciliation'):statement_report(data,'income-statement')


def test_unknown_units_periods_and_duplicates_fail_closed():
    data=payload({'Revenue':100,'Profit After Tax':25})
    data['data']['units_in']='million'
    with pytest.raises(ValueError,match='unsupported_statement'):statement_report(data,'income-statement')
    data['data']['units_in']='crore'
    data['data']['full_statement'][0]['history'][0]['period']='Jun 2026'
    with pytest.raises(ValueError,match='unsupported_reporting_period'):statement_report(data,'income-statement')
    data=payload({'Revenue':100,'Profit After Tax':25})
    data['data']['full_statement'].append(data['data']['full_statement'][0])
    with pytest.raises(ValueError,match='duplicate_statement_label'):statement_report(data,'income-statement')


def test_cash_mismatch_stays_visible_not_corrected_by_invention():
    data=payload({'Cash flow from Operations':20,'Cash flow from Investing':-5,'Cash flow from Financing':-10,
        'Total Cash Flow':5,'Cash (Start of the year)':50,'Cash (End of the year)':60})
    report=statement_report(data,'cash-flow')
    assert len(report.facts)==1 and report.facts[0].metric=='operating_cash_flow'
    assert 'reconciliation items are unavailable' in report.text


def test_liabilities_are_reported_and_cross_checked():
    data=payload({'Total Assets':100,'Current Assets':60,'Non-Current Assets':40,'Current Liabilities':20,'Non-Current Liabilities':10})
    data['data']['history']=[{'period':'Mar 2026','total_liability':30}]
    report=statement_report(data,'balance-sheet')
    assert report.facts[-1].locator=='$.data.history[0].total_liability'
    data['data']['history'][0]['total_liability']=31
    with pytest.raises(ValueError,match='liability_reconciliation'):statement_report(data,'balance-sheet')


def test_financial_permissions_checked_before_network_or_storage():
    from types import SimpleNamespace
    from worker.providers.upstox_financials import ingest_financials
    calls=[]
    def require(stream,uses):
        calls.append(stream.scope)
        if stream.scope=='filings':raise PermissionError('scope_denied')
    access=SimpleNamespace(clock=lambda:'2026-10-21T00:00:00Z',require=require)
    client=SimpleNamespace(access=access)
    identity=SimpleNamespace(source_id='upstox',data=SimpleNamespace(kind='instrument'),availability_basis='observed',listing_id='test')
    with pytest.raises(PermissionError,match='scope_denied'):ingest_financials(None,client,identity,'test')
    assert calls==['financial_facts','filings']


def test_endpoint_subset_cannot_add_an_unrecognized_provider_route():
    from types import SimpleNamespace
    from worker.providers.upstox_financials import ingest_financials
    identity=SimpleNamespace(source_id='upstox',data=SimpleNamespace(kind='instrument'),availability_basis='observed')
    with pytest.raises(ValueError,match='invalid_financial_endpoints'):
        ingest_financials(None,None,identity,'test',endpoints=('orders',))
