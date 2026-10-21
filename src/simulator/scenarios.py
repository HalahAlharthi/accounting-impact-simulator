"""Load and save scenario files (data/sample_inputs/*.json).

Amounts are stored as text ("100000.00") so no float ever enters the file;
the engine boundary (validation/coerce.py) converts and validates them.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from simulator.models import (
    AssetInput,
    EntityFinancials,
    EstimateRevision,
    OpeningPosition,
    ReportingPeriod,
    SimulationInput,
)

SAMPLE_DIR = Path(__file__).resolve().parents[2] / "data" / "sample_inputs"


@dataclass(frozen=True)
class Scenario:
    title: str
    description: str
    currency: str
    inputs: SimulationInput
    financials: EntityFinancials
    opening: OpeningPosition


def scenario_from_dict(d: dict) -> Scenario:
    a, p, r = d["asset"], d["period"], d.get("revision")
    inputs = SimulationInput(
        asset=AssetInput(a.get("cost"), a.get("residual_value"), a.get("useful_life_months"),
                         a.get("available_for_use_date"), a.get("method", "straight_line")),
        period=ReportingPeriod(p.get("start_date"), p.get("end_date")),
        revision=None if r is None else EstimateRevision(r.get("effective_date"), r.get("revised_useful_life_months"),
                                                         r.get("revised_residual_value")),
        opening_accumulated_depreciation=d.get("opening_accumulated_depreciation"),
    )
    f, o = d.get("financials", {}), d.get("opening_position", {})
    financials = EntityFinancials(f.get("revenue"), f.get("other_operating_expenses"), f.get("other_income"),
                                  f.get("finance_costs"), f.get("other_assets_closing"),
                                  f.get("total_liabilities_closing"), f.get("opening_equity"))
    opening = OpeningPosition(o.get("total_assets"), o.get("total_liabilities"))
    return Scenario(d.get("title", "Untitled"), d.get("description", ""), d.get("currency", ""), inputs, financials,
                    opening)


def load_scenario(path: str | Path) -> Scenario:
    return scenario_from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def list_samples() -> dict[str, Path]:
    """{title: path} for every sample file, sorted by file name."""
    return {load_scenario(p).title: p for p in sorted(SAMPLE_DIR.glob("*.json"))}
