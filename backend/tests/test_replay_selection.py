import pytest
from pydantic import ValidationError
from app.research import Selection
from stock_discovery_analysis.strategy import STRATEGY_VERSION


def test_replay_only_accepts_implemented_strategy_version():
    inputs=dict(dataset_version='SYN-test',instrument_id='SYN-ALPHA',date='2026-01-01')
    assert Selection(**inputs).strategy_version == STRATEGY_VERSION
    assert Selection(**inputs,strategy_version=STRATEGY_VERSION).strategy_version == STRATEGY_VERSION
    for unsupported in ('future-strategy', 'ema-breakout-1.0.1', ''):
        with pytest.raises(ValidationError):
            Selection(**inputs,strategy_version=unsupported)
