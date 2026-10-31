from stock_discovery_analysis.financial_evaluation import score_rows


def test_failures_abstentions_and_zero_denominators_are_explicit():
    expected=dict(value='100',unit='INR',scope='consolidated',period='2025',evidence_id='source',quote='row')
    rows=[dict(case_id='good',expected=expected,proposal=dict(expected,status='extracted'),accepted=True),
          dict(case_id='failure',expected=expected,proposal=None,accepted=False,error='TimeoutError'),
          dict(case_id='missing',expected=None,proposal={'status':'insufficient_evidence'},accepted=False)]
    r=score_rows(rows,dataset_hash='a'*64,protocol_hash='b'*64)
    assert r['metrics']['numeric_accuracy']==dict(numerator=1,denominator=2,value=.5)
    assert r['metrics']['required_abstention']['value']==1 and r['metrics']['runtime_failure']['numerator']==1
    assert not r['human_verified'] and not r['quality_accepted'] and not r['holdout_used']
    empty=score_rows([],dataset_hash='a'*64,protocol_hash='b'*64)
    assert all(x['value'] is None for x in empty['metrics'].values())


def test_wrong_field_and_unsupported_acceptance_are_not_hidden():
    e=dict(value='100',unit='INR',scope='consolidated',period='2025',evidence_id='source',quote='row')
    r=score_rows([dict(case_id='wrong',expected=e,proposal=dict(e,status='extracted',unit='USD'),accepted=True),
        dict(case_id='contradiction',expected=None,proposal=dict(e,status='extracted'),accepted=True)],dataset_hash='a'*64,protocol_hash='b'*64)
    assert r['metrics']['numeric_accuracy']['value']==1 and r['metrics']['unit_accuracy']['value']==0
    assert r['metrics']['unsupported_accepted']['value']==1 and r['metrics']['required_abstention']['value']==0
