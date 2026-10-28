"""Documented numerical API statements into D3-06; never issuer PDF content.

Summary labels are not interchangeable with audited line-item labels. All clocks
are observations; reporting dates are never claimed as publication dates.
"""
import json
import re
from decimal import Decimal
from stock_discovery_contracts.v2 import check, digest
from stock_discovery_analysis.evidence import FinancialRow, StructuredReport, Document, content_hash
from stock_discovery_analysis.revisions import DocumentData
from .upstox import observed_revision

ENDPOINTS = ('income-statement', 'balance-sheet', 'cash-flow')


def statement_report(payload, endpoint):
    check(endpoint in ENDPOINTS, 'unsupported_financial_endpoint')
    check(payload.get('status') == 'success', 'provider_status_failed')
    data = payload['data']
    check(data['type'] == 'consolidated' and data['time_period'] == 'yearly'
          and data['units_in'] == 'crore', 'unsupported_statement_scope_period_units')
    table = data['full_statement']
    check(isinstance(table, list) and 0 < len(table) <= 100, 'statement_shape')
    rows = {}; pointers = {}
    for i, line in enumerate(table):
        label = line['particular']
        check(label not in rows, 'duplicate_statement_label')
        rows[label] = {}
        for j, observation in enumerate(line['history']):
            period = observation['period']; value = observation['value']
            check(re.fullmatch(r'Mar 20[0-9]{2}', period) is not None, 'unsupported_reporting_period')
            check(period not in rows[label], 'duplicate_statement_period')
            check(type(value) in (int, float, str) and Decimal(str(value)).is_finite(), 'invalid_financial_value')
            rows[label][period] = Decimal(str(value))
            pointers[label, period] = f'$.data.full_statement[{i}].history[{j}].value'
    maps = {'income-statement': {'Revenue': 'revenue', 'Profit After Tax': 'earnings'},
            'balance-sheet': {'Total Assets': 'assets'},
            'cash-flow': {'Cash flow from Operations': 'operating_cash_flow'}}
    facts=[]; lines=[]
    for label, metric in maps[endpoint].items():
        check(label in rows, 'required_statement_line_missing:'+label)
        for period,value in rows[label].items():
            year=int(period[-4:]);end=f'{year}-03-31T18:29:59Z'
            instant=metric=='assets'
            facts.append(FinancialRow(metric=metric,value=str(value),missing_reason=None,unit='INR_crore',
                period_start_at=end if instant else f'{year-1}-03-31T18:30:00Z',period_end_at=end,
                period_kind='instant' if instant else 'annual',scope='consolidated',locator=pointers[label,period]))
            lines.append(f'{period}, consolidated: {label} = {value} INR crore ({pointers[label,period]}).')
    # Keep provider inconsistencies as explicit evidence, never infer missing debt,
    # operating margins, EPS units or equity from ambiguous aggregate labels.
    findings=[]
    if endpoint=='income-statement':
        for period in rows.get('Revenue',{}):
            if all(period in rows.get(k,{}) for k in ('Other Income','Total Revenue')):
                check(rows['Revenue'][period]+rows['Other Income'][period]==rows['Total Revenue'][period], 'revenue_reconciliation')
            if all(period in rows.get(k,{}) for k in ('Profit Before Tax','Tax','Profit After Tax')):
                check(rows['Profit Before Tax'][period]-rows['Tax'][period]==rows['Profit After Tax'][period], 'tax_reconciliation')
        findings.append('Summary revenue includes other income; use the Revenue line for business revenue. Operating margin and per-share units are not verified.')
    if endpoint=='balance-sheet':
        for period in rows['Total Assets']:
            if all(period in rows.get(k,{}) for k in ('Current Assets','Non-Current Assets')):
                check(rows['Current Assets'][period]+rows['Non-Current Assets'][period]==rows['Total Assets'][period], 'asset_reconciliation')
            if all(period in rows.get(k,{}) for k in ('Current Liabilities','Non-Current Liabilities')):
                value=rows['Current Liabilities'][period]+rows['Non-Current Liabilities'][period]
                year=int(period[-4:]);end=f'{year}-03-31T18:29:59Z'
                summary=[(i,r) for i,r in enumerate(data['history']) if r['period']==period]
                check(len(summary)==1 and Decimal(str(summary[0][1]['total_liability']))==value, 'liability_reconciliation')
                facts.append(FinancialRow(metric='liabilities',value=str(value),missing_reason=None,unit='INR_crore',period_start_at=end,period_end_at=end,period_kind='instant',scope='consolidated',locator=f'$.data.history[{summary[0][0]}].total_liability'))
                lines.append(f'{period}, consolidated: total liabilities = {value} INR crore, reported total verified against current plus non-current liabilities.')
        findings.append('Debt and total equity are unavailable as unambiguous verified line items; Equity Capital is not silently treated as total equity.')
    if endpoint=='cash-flow':
        for period in rows['Cash flow from Operations']:
            keys=('Cash flow from Investing','Cash flow from Financing','Total Cash Flow')
            if all(period in rows.get(k,{}) for k in keys):
                total=sum(rows[k][period] for k in ('Cash flow from Operations',*keys[:2]))
                if total!=rows['Total Cash Flow'][period]:findings.append(f'{period}: reported total cash flow does not reconcile with operating, investing and financing components.')
            if all(period in rows.get(k,{}) for k in ('Cash (Start of the year)','Cash (End of the year)','Total Cash Flow')):
                if rows['Cash (End of the year)'][period]-rows['Cash (Start of the year)'][period]!=rows['Total Cash Flow'][period]:
                    findings.append(f'{period}: cash balance movement differs from reported total cash flow; reconciliation items are unavailable.')
    lines.extend(findings)
    return StructuredReport(schema_version='1.0.0',text='\n'.join(lines),facts=tuple(facts),events=())


def financial_document(payload, endpoint, *, identity, fetched, previous=None):
    check(identity.source_id=='upstox' and identity.data.kind=='instrument' and identity.availability_basis=='observed', 'observed_upstox_identity_required')
    report=statement_report(payload,endpoint)
    body=report.model_dump_json()
    url='https://api.upstox.com/v2/fundamentals/'+identity.data.isin+'/'+endpoint+'?type=consolidated&fs=true'+('&time_period=yearly' if endpoint=='income-statement' else '')
    revision=observed_revision(DocumentData(kind='document',document_id='upstox-'+endpoint+'-'+identity.data.isin,
        document_type='filing',url=url,content_hash=content_hash(body),locator='structured numerical API observation; response_hash='+digest(payload),metadata_only=True),
        listing=identity.listing_id,fetched=fetched,parent=identity.revision_id,previous=previous)
    return Document(revision=revision,issuer_id=identity.data.issuer_id,title='Upstox consolidated annual '+endpoint+' (structured API, not issuer filing)',
        attribution='Upstox',category='annual_report',authority='secondary',media_type='application/vnd.stock-evidence+json',body=body)


def ingest_financials(conn, client, identity, account_ref, *, endpoints=ENDPOINTS):
    """Use the existing D3-06 transaction and permissions, one endpoint per page."""
    import time
    from stock_discovery_analysis.evidence import EvidencePage
    from stock_discovery_analysis.evidence_storage import ingest_evidence_page
    from stock_discovery_analysis.revision_storage import Stream
    from stock_discovery_analysis.revisions import Revision
    from stock_discovery_contracts.v2 import digest
    check(identity.source_id=='upstox' and identity.data.kind=='instrument' and identity.availability_basis=='observed', 'observed_upstox_identity_required')
    results=[]
    check(bool(endpoints) and len(set(endpoints))==len(endpoints) and all(e in ENDPOINTS for e in endpoints), 'invalid_financial_endpoints')
    for endpoint in endpoints:
        source=Stream(stream_id='REAL-FIN-'+digest([identity.listing_id,endpoint,client.access.clock()]),
            source_id='upstox',account_ref=account_ref,scope='financial_facts')
        # Check every downstream use before any authenticated request.
        client.access.require(source,('acquire','store','extract','derive'))
        stream=source.model_copy(update={'scope':'filings'})
        grant,request=client.access.require(stream,('acquire','store','extract','derive'))
        from stock_discovery_analysis.grant_fences import capture
        permit=capture(conn,grant,request,('acquire','store','extract','derive'))
        url='https://api.upstox.com/v2/fundamentals/'+identity.data.isin+'/'+endpoint+'?type=consolidated&fs=true'+('&time_period=yearly' if endpoint=='income-statement' else '')
        payload=json.loads(client._get(url,source));fetched=client.access.clock()
        prior=conn.execute("SELECT payload FROM discovery.revisions WHERE source_id='upstox' AND listing_id=%s AND kind='document' AND payload->'data'->>'document_id'=%s ORDER BY sequence DESC LIMIT 1",(identity.listing_id,'upstox-'+endpoint+'-'+identity.data.isin)).fetchone()
        document=financial_document(payload,endpoint,identity=identity,fetched=fetched,previous=Revision.model_validate(prior[0]) if prior else None)
        result=ingest_evidence_page(conn,stream,EvidencePage(cursor=None,next_cursor=None,complete=True,records=(document.model_dump(mode='json'),)),access=client.access,permit=permit)
        check(result['status']=='complete','financial_evidence_quarantined')
        results.append(result)
        time.sleep(.6)
    return results
