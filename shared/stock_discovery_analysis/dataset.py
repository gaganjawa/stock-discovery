"""Content-addressed synthetic dataset, quality checks and reproducible demo."""
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
from .data import Candle, Provenance, HistoricalClock, SyntheticAdapter
from .calendar import Calendar, Session, CorporateAction, action_crosses_window
from .identity import Instrument, SymbolMapping
from .universe import Membership, universe_asof


def encode(value):
    if isinstance(value, datetime): return value.isoformat()
    if isinstance(value, Decimal): return str(value)
    raise TypeError(type(value).__name__)


def canonical(value) -> str:
    return json.dumps(value,default=encode,sort_keys=True,separators=(',',':'),allow_nan=False)


@dataclass(frozen=True)
class Dataset:
    instruments: tuple[Instrument, ...]
    mappings: tuple[SymbolMapping, ...]
    memberships: tuple[Membership, ...]
    calendar: Calendar
    actions: tuple[CorporateAction, ...]
    candles: tuple[Candle, ...]
    label: str = 'SYNTHETIC DEMO — no profitability inference'
    rights_ref: str = 'synthetic-only'

    def __post_init__(self):
        ids={i.instrument_id for i in self.instruments}
        if len(ids)!=len(self.instruments) or not ids:
            raise ValueError('unique instrument identities required')
        if self.rights_ref != 'synthetic-only' or any(not i.synthetic for i in self.instruments):
            raise ValueError('real integrations disabled pending explicit rights/access')
        records=(*self.mappings,*self.memberships,*self.actions,*self.candles)
        if any(r.instrument_id not in ids for r in records):
            raise ValueError('unknown instrument reference')
        if any(r.provenance.availability_basis!='fictional_fixture' for r in (*records,self.calendar)):
            raise ValueError('synthetic provenance required')
        SyntheticAdapter(self.candles)
        if any(c.adjustment_version!='raw-v1' for c in self.candles):
            raise ValueError('datasets must preserve raw candles')
        if len({a.action_id for a in self.actions}) != len(self.actions):
            raise ValueError('duplicate corporate action')

    @property
    def version(self) -> str:
        return 'SYN-'+hashlib.sha256(canonical(asdict(self)).encode()).hexdigest()

    def asof(self, instrument_id: str, cutoff: datetime) -> tuple[Candle,...]:
        return SyntheticAdapter(self.candles).candles(instrument_id,HistoricalClock(cutoff))

    def quality(self, instrument_id: str, cutoff: datetime, warmup: int) -> tuple[str,...]:
        if warmup < 1: raise ValueError("positive warmup required")
        errors=[]
        if instrument_id not in universe_asof(self.memberships,cutoff): errors.append('instrument_not_eligible')
        bars=self.asof(instrument_id,cutoff)
        if len(bars)<warmup: errors.append('insufficient_warmup')
        sessions=self.calendar.through(cutoff)
        expected={(s.opens_at,s.closes_at) for s in sessions[-warmup:]}
        actual={(c.starts_at,c.ends_at) for c in bars[-warmup:]}
        if actual != expected: errors.append('missing_or_off_calendar_candles')
        if any(c.volume==0 for c in bars[-warmup:]): errors.append('zero_volume')
        if bars and action_crosses_window(self.actions,instrument_id,bars[-warmup:][0].starts_at,cutoff,cutoff):
            errors.append('corporate_action_in_feature_window')
        return tuple(errors)

    def manifest(self) -> dict:
        return {'version':self.version,'synthetic':True,'rights_ref':self.rights_ref,
                'label':self.label,'calendar_version':self.calendar.version,
                'adjustment_basis':'raw-v1','candle_count':len(self.candles),
                'source_versions':sorted({c.provenance.source_version for c in self.candles}),
                'coverage':'fictional calendar/universe only; no historical news or real constituent coverage',
                'payload':asdict(self)}


def demo_dataset() -> Dataset:
    """Fixed fictional weekdays, not an NSE calendar or invented real prices."""
    t=datetime(2025,5,1,tzinfo=timezone.utc)
    known=t-timedelta(days=1)
    p=Provenance('fixture:daily-demo','1',known,known,known,'fictional_fixture')
    sessions=[]
    day=t
    while len(sessions)<100:
        if day.weekday()<5:
            sessions.append(Session(day+timedelta(hours=3,minutes=45),day+timedelta(hours=10)))
        day+=timedelta(days=1)
    instruments=tuple(Instrument('SYN-'+name,None,'SYNTHETIC_NSE','EQ') for name in ('ALPHA','BETA','GAMMA'))
    bars=[]
    for n,inst in enumerate(instruments):
        for j,s in enumerate(sessions):
            base=Decimal(100+n*40)+Decimal(j)*Decimal('0.30')
            close=base+Decimal((j%7)-3)*Decimal('0.10')
            # Repeatable high-volume breakouts among otherwise quiet fictional bars.
            volume=10000
            if j in (39,59,79): close+=Decimal(3); volume=24000
            bars.append(Candle(inst.instrument_id,s.opens_at,s.closes_at,base,
                max(base,close)+Decimal('0.50'),min(base,close)-Decimal('0.50'),close,volume,
                Provenance('fixture:daily-demo','1',s.closes_at,s.closes_at+timedelta(minutes=1),
                           datetime(2026,10,11,tzinfo=timezone.utc),'fictional_fixture')))
    return Dataset(instruments,
        tuple(SymbolMapping(i.instrument_id,'SYNTHETIC_NSE:EQ',i.instrument_id,known,None,p) for i in instruments),
        tuple(Membership(i.instrument_id,known,'listed',p) for i in instruments),
        Calendar('fictional-weekdays-v1',tuple(sessions),p),(),tuple(bars))
