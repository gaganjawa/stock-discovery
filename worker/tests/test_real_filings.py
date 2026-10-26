import pytest
from worker.providers.filings import extract_html,financial_number

HTML='<h1>Consolidated results · INR crore</h1><table><tr><th>Metric</th><th>2026</th></tr><tr><td>Revenue</td><td>1,23,456</td></tr><tr><td>Profit</td><td>(250)</td></tr></table>'
KW=dict(table_header=['Metric','2026'],column_header='2026',unit_marker='INR crore',scope_marker='Consolidated',unit='INR_crore',scope='consolidated',period_start_at='2025-04-01T00:00:00Z',period_end_at='2026-03-31T00:00:00Z',period_kind='annual',rows={'revenue':'Revenue','earnings':'Profit','operating_cash_flow':'Cash flow'})


def test_exact_table_and_missing_values():
    report=extract_html(HTML,**KW)
    assert [f.value for f in report.facts]==['123456','-250',None]
    assert report.facts[2].missing_reason=='not_reported'
    assert report.facts[0].locator=='html:table[0]/tr[1]/td[1]'
    from stock_discovery_analysis.evidence import normalize
    assert normalize(report.facts[0])['value']=='1234560000000'


@pytest.mark.parametrize('html',[HTML+HTML,HTML.replace('INR crore','USD million'),HTML.replace('<td>Profit</td>','<td>Revenue</td>'),HTML.replace('<td>(250)</td>','<td colspan="2">250</td>')])
def test_fail_closed_on_ambiguous_tables(html):
    with pytest.raises(ValueError):extract_html(html,**KW)


@pytest.mark.parametrize('text',['12,34','12%','1e9','NaN','100*','₹100','(-5)'])
def test_no_inferred_numbers(text):
    with pytest.raises(ValueError):financial_number(text)
