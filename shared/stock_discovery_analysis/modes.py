"""STK-010 synthetic, non-actionable analysis boundary."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum


class AnalysisMode(str, Enum):
    HISTORICAL = "historical"
    LIVE = "live"


@dataclass(frozen=True)
class SyntheticRecommendation:
    recommendation_id: str
    instrument: str
    decision: str
    mode: AnalysisMode
    is_synthetic: bool = True
    is_actionable: bool = False


def synthetic_recommendation(mode: AnalysisMode) -> dict[str, object]:
    """Return deterministic fixture-shaped data without consulting market sources."""
    return asdict(
        SyntheticRecommendation(
            recommendation_id=f"SYN-STK010-{mode.value.upper()}-001",
            instrument="SYNTHETIC-EQUITY",
            decision="wait",
            mode=mode,
        )
    )
