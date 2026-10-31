"""STK-079 arithmetic/contract boundaries; entirely invented inputs."""
from decimal import Decimal as D
import pytest
from pydantic import ValidationError
from stock_discovery_analysis.strategy import swing_levels, swing_conditions, tick
from stock_discovery_analysis.swing_research import CoverageReview, HypotheticalRisk, unavailable, valid_geometry, current_identity


@pytest.mark.parametrize('step',['0.01','0.05','0.25','1'])
def test_levels_use_explicit_tick_grid(step):
    levels=swing_levels(D('123.12'),D('2.32'),D(step))
    assert all(v%D(step)==0 for v in levels.values())
    assert levels['stop']<levels['entry']<levels['target']
    assert levels['entry']>=D('123.12')+D(step)
    assert levels['target']-levels['entry']>=2*(levels['entry']-levels['stop'])


@pytest.mark.parametrize('high,atr',[('123.12','2.32'),('10.25','1.2345'),('2500.33','75.12')])
def test_extracted_geometry_preserves_legacy_exactly(high,atr):
    h,a=D(high),D(atr);entry=tick(h+D('.01'),True);stop=tick(entry-2*a)
    assert swing_levels(h,a,D('.01'))==dict(entry=entry,stop=stop,
        target=tick(entry+2*(entry-stop),True),entry_cap=tick(entry*D('1.01'),True))


@pytest.mark.parametrize('step',['0','-1','NaN','Infinity'])
def test_unknown_or_invalid_tick_never_defaults(step):
    with pytest.raises(ValueError):swing_levels(D(100),D(2),D(step))


@pytest.mark.parametrize('volume,close,expected',[('1.49','103',False),('1.5','103',True),('2','102',False)])
def test_unchanged_strategy_thresholds(volume,close,expected):
    assert swing_conditions(dict(ema10=D(102),ema30=D(100),breakout20=D(102),relative_volume20=D(volume)),D(close))==expected


def test_no_risk_defaults_or_authorization_from_empty_inputs():
    with pytest.raises(ValidationError):HypotheticalRisk.model_validate({})
    with pytest.raises(ValidationError):CoverageReview.model_validate({})
    result=unavailable('NSE:TEST','2026-10-30T12:00:00Z',['missing','missing'])
    assert result['reasons']==['missing'] and result['levels'] is None
    assert not any(result[k] for k in ('actionable','publication_authorized','paper_admission_authorized','trading_authorized'))


@pytest.mark.parametrize('cap,expected',[('102.05',False),('102.00',False),('101.95',True),('100.00',True),('99.95',False),('101.951',False)])
def test_real_cap_target_and_tick_boundaries(cap,expected):
    assert valid_geometry(dict(stop=D(99),entry=D(100),entry_cap=D(cap),target=D(102)),D('.05'))==expected


@pytest.mark.parametrize('field,value',[('stop','100'),('stop','-1'),('target','NaN'),('entry','Infinity'),
    ('stop','98.999'),('target','102.001')])
def test_invalid_real_geometry_never_authorizes_sizing(field,value):
    levels=dict(stop=D(99),entry=D(100),entry_cap=D(101),target=D(102));levels[field]=D(value)
    assert not valid_geometry(levels,D('.05'))


@pytest.mark.parametrize('step',['0.00001','0.05','0.25','5'])
def test_one_tick_below_target_exact_decimal(step):
    step=D(step)
    assert valid_geometry(dict(stop=100*step,entry=101*step,entry_cap=102*step,target=103*step),step)
    assert not valid_geometry(dict(stop=100*step,entry=101*step,entry_cap=103*step,target=103*step),step)


def instrument(rid,effective,sequence=1,parent=None,source='test',tick_size='0.05'):
    from stock_discovery_analysis.revisions import Revision
    return Revision(schema_version='1.0.0',revision_id=rid,source_id=source,source_revision='upstream-'+rid,
        sequence=sequence,listing_id='NSE:TEST',instrument_revision_id=None,published_at='2026-10-30T10:00:00Z',
        available_at='2026-10-30T10:00:00Z',fetched_at='2026-10-30T10:00:00Z',availability_basis='observed',
        archive_evidence_ref=None,archive_revision_id=None,supersedes_id=parent,data=dict(kind='instrument',issuer_id='TEST',
        symbol='TEST',isin='INE000TEST00',series='EQ',status='active',lot_size=1,tick_size=tick_size,effective_at=effective))


def test_current_identity_uses_effective_time_then_correction_not_identifier_or_order():
    old=instrument('zzz-old','2026-10-01T00:00:00Z')
    current=instrument('aaa-current','2026-10-20T00:00:00Z',2,old.revision_id)
    # Higher sequence acquired later does not make a future-effective record current.
    future=instrument('middle-future','2026-11-01T00:00:00Z',3,current.revision_id)
    rows=[future,old,current];cutoff='2026-10-30T12:00:00Z'
    assert current_identity(rows,cutoff)==current_identity(list(reversed(rows)),cutoff)==current
    correction=instrument('correction','2026-10-20T00:00:00Z',4,future.revision_id,tick_size='0.10')
    assert current_identity(rows+[correction],cutoff)==correction
    # Effective time outranks sequence; no implied valid-until field exists.
    backdated=instrument('backdated','2026-10-02T00:00:00Z',5,correction.revision_id)
    assert current_identity(rows+[correction,backdated],cutoff)==correction


def test_current_identity_missing_future_unobserved_and_ambiguous_fail_closed():
    cutoff='2026-10-30T12:00:00Z';one=instrument('one','2026-10-20T00:00:00Z')
    other=instrument('two','2026-10-20T00:00:00Z',source='other',tick_size='0.10')
    for rows in ([],[instrument('future','2026-11-01T00:00:00Z')],
                 [one.model_copy(update={'fetched_at':'2026-10-31T00:00:00Z'})], [one,other],[other,one],
                 [one,one.model_copy(update={'revision_id':'conflict','data':one.data.model_copy(update={'tick_size':'0.10'})})]):
        assert current_identity(rows,cutoff) is None
    assert current_identity([one,one],cutoff)==one
