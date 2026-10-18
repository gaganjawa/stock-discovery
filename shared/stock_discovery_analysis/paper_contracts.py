"""Separate fictional simulation contracts; never alter v2 recommendation admission."""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

VERSION = 'paper-1.0.0'
FICTIONAL = 'fictional-simulation-1.0.0'
HORIZONS = ('swing', 'short_term', 'long_term')


def instant(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None: raise ValueError('timezone_required')
    return result.astimezone(timezone.utc)


class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class PortfolioConfig(Contract):
    name: str = Field(min_length=1, max_length=80)
    mode: Literal['fictional_simulation', 'forward_paper']
    contract_version: Literal['fictional-simulation-1.0.0', 'paper-1.0.0']
    starting_capital: Decimal = Field(gt=0, le=1000000000, max_digits=16, decimal_places=2)
    cash_reserve_fraction: Decimal = Field(default=Decimal('.10'), ge=0, lt=1)
    per_trade_risk: Decimal = Field(default=Decimal('.01'), gt=0, le=1)
    combined_risk: Decimal = Field(default=Decimal('.05'), gt=0, le=1)
    issuer_limit: Decimal = Field(default=Decimal('.20'), gt=0, le=1)
    sector_limit: Decimal = Field(default=Decimal('.40'), gt=0, le=1)
    gross_limit: Decimal = Field(default=Decimal('.80'), gt=0, le=1)
    horizon_limit: Decimal = Field(default=Decimal('.60'), gt=0, le=1)
    daily_loss_limit: Decimal = Field(default=Decimal('.05'), gt=0, le=1)
    monthly_loss_limit: Decimal = Field(default=Decimal('.10'), gt=0, le=1)
    fixed_fee: Decimal = Field(default=Decimal('1'), ge=0, le=10000)
    fee_bps: Decimal = Field(default=Decimal('10'), ge=0, le=1000)
    slippage_bps: Decimal = Field(default=Decimal('10'), ge=0, le=1000)
    entry_gap_cap: Decimal = Field(default=Decimal('.02'), ge=0, le=1)
    mark_max_age_seconds: int = Field(default=432000, ge=1, le=604800)
    simulation_start_at: str | None = None

    @model_validator(mode='after')
    def coherent(self):
        if not self.per_trade_risk <= self.combined_risk: raise ValueError('risk_limits')
        if not self.issuer_limit <= self.sector_limit <= self.gross_limit: raise ValueError('exposure_limits')
        if self.mode == 'fictional_simulation':
            if self.contract_version != FICTIONAL or not self.simulation_start_at: raise ValueError('explicit_fictional_contract_required')
            instant(self.simulation_start_at)
        elif self.contract_version != VERSION or self.simulation_start_at is not None:
            raise ValueError('forward_clock_cannot_be_simulated')
        return self


class Admission(Contract):
    recommendation_id: str = Field(min_length=1, max_length=200)


class Bar(Contract):
    listing_id: str = Field(min_length=1, max_length=200)
    session_open_at: str
    session_close_at: str
    available_at: str
    open: Decimal = Field(gt=0)
    high: Decimal = Field(gt=0)
    low: Decimal = Field(gt=0)
    close: Decimal = Field(gt=0)
    # Explicit fixture allocation at the deterministic fill, NOT inferred from daily volume.
    entry_capacity: int | None = Field(default=None, ge=0, le=100000000)
    exit_capacity: int | None = Field(default=None, ge=0, le=100000000)
    corporate_action: bool = False

    @model_validator(mode='after')
    def coherent(self):
        if not self.low <= min(self.open,self.close) <= max(self.open,self.close) <= self.high:
            raise ValueError('invalid_ohlc')
        if not instant(self.session_open_at) < instant(self.session_close_at) <= instant(self.available_at):
            raise ValueError('invalid_observation_clocks')
        return self


class Observation(Contract):
    contract_version: Literal['fictional-simulation-1.0.0']
    session_close_at: str
    observed_at: str
    bars: list[Bar] = Field(max_length=100)
    source: Literal['SYN-D310-observations'] = 'SYN-D310-observations'

    @model_validator(mode='after')
    def coherent(self):
        if instant(self.session_close_at) > instant(self.observed_at): raise ValueError('future_session')
        if len({b.listing_id for b in self.bars}) != len(self.bars): raise ValueError('duplicate_listing')
        for b in self.bars:
            if instant(b.session_close_at) != instant(self.session_close_at) or instant(b.available_at) > instant(self.observed_at):
                raise ValueError('lookahead_observation')
        return self


class AdmissionBatch(Contract):
    recommendation_ids: list[str] = Field(min_length=1, max_length=100)

    @model_validator(mode='after')
    def unique(self):
        if len(set(self.recommendation_ids))!=len(self.recommendation_ids):raise ValueError('duplicate_recommendation_ids')
        if any(not rid or len(rid)>200 for rid in self.recommendation_ids):raise ValueError('invalid_recommendation_id')
        return self
