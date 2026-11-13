import importlib.util
from pathlib import Path
import pytest
spec=importlib.util.spec_from_file_location('health',Path(__file__).resolve().parents[2]/'scripts/stk095_health.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def good():return dict(receiver_healthy=True,observed_at=1000,consumer_completed_at=1000,backup_restore_verified_at=1000,high_water=5,cursor=5)


def test_good_and_no_symbol_or_url_output():
    s=good();s.update(symbol='PRIVATE',url='SECRET');assert m.codes(s,1000)==[]


@pytest.mark.parametrize('change,expected',[
 ({'consumer_completed_at':0},'consumer_stale'),({'observed_at':1001},'observation_stale'),
 ({'cursor':6},'cursor_ahead_recovery_required'),({'cursor':4},'consumer_backlog'),
 ({'cursor':True},'cursor_observation_invalid'),({'receiver_healthy':False},'receiver_unavailable'),
 ({'backup_restore_verified_at':None},'backup_unverified_or_stale'),
 ({'expected_alert_due':True},'expected_delivery_unverified'),({'new_rejections':1},'receiver_rejections')])
def test_failures(change,expected):
    s=good();s.update(change);assert expected in m.codes(s,1000)


def test_missing_observations_fail_closed():
    assert len(m.codes({},1000))==5
