# Assumptions and limitations (Phase 3, with approved Phase 4 prerequisites)

## Scope

- Single asset, cost model, straight-line, one component.
- Out of scope: impairment (IAS 36), revaluation, held for sale, componentisation, prior-period errors, tax.

## Time basis

- Monthly. Available-for-use and change dates must be the 1st of a month; periods end on the last day of a month.
- Depreciation starts in the month the asset becomes available for use.

## Change date

- Entered by the user as the date of the change in estimate. There is no default (IAS 8.38, corroborated via AASB 108; IFRS primary text pending).
- Practice differs on whether a change found in the annual review applies from the start of the year or from a specific date. The user's input decides.

## Inputs

- Numbers may arrive as floats or text and are converted once to `Decimal` at the boundary.
- Amounts must be in cents (at most 2 decimal places).

## Opening accumulated depreciation

- **Entered:** used as entered. A differing implied figure raises warning V08; no correcting entry is generated.
- **Blank:** calculated from the original estimate and labelled as not verified against the ledger (V20).

## Rounding

- Exact fractions internally.
- Half-up to cents for each posted journal entry.
- Ledger balances carried forward are the posted amounts.
- Each period re-derives its charge from the posted carrying amount, so the asset closes exactly at its residual value.

## Sign rules for statement inputs (V24)

| Input | May be negative? | Reason |
|---|---|---|
| Revenue, other operating expenses, finance costs | No | MVP assumption |
| Other assets (closing), total liabilities (closing) | No | MVP assumption |
| Opening total assets, opening total liabilities | No | MVP assumption |
| Other income | **Yes** | A net other expense is negative |
| Opening equity | **Yes** | Accumulated losses |

Any further exception must be documented here before it is allowed. `tests/test_v24_fields.py` fails if a field has no documented rule.

## Opening position

- Opening total assets and opening total liabilities are collected; opening equity is the existing input.
- Checked: opening assets = opening liabilities + opening equity (V26), and opening assets include this asset (V27).
- Not checked: the roll-forward from opening to closing balances, because other movements are not collected.
- An asset not yet in use at the period start is exempt from V27 (info V28), because its acquisition date is not collected.

## Partial results

- Sections that passed their own checks stay visible and are labelled "validated independently".
- Everything after a failed check is withheld, and the scenario is reported as "partial", never as successful.

## Statements

- Rest-of-entity figures are identical in both scenarios.
- Closing equity = opening equity + PBT (no tax, dividends or OCI).
- Depreciation is classified within operating expenses.
- The accounting equation is checked at the closing date and is never forced.

## Ratios

- Simplified definitions, labelled as such: closing rather than average assets; total liabilities rather than interest-bearing debt.

## Interface

- The Streamlit app collects inputs and displays results; it performs no accounting calculations.
- Dates are picked by month (1st of a month), and the change date is chosen from the months in the period, so the monthly convention is built into the inputs. The engine still validates it.
- Widget numbers arrive as floats and are converted exactly to Decimal at the engine boundary.
- The comparison chart converts figures to float for drawing only. The tables are the authoritative figures.

## References

- Unverified paragraph references are labelled pending.
- Nothing is claimed as IFRS-verified on the strength of secondary sources alone.
