# Accounting methodology — IAS 16 useful-life change (MVP)

> Educational tool. Whether a change is a change in accounting estimate, a correction of an error, or a change in policy depends on the facts and circumstances and requires professional judgment.

## 1. Classification comes first

The simulator models a **change in accounting estimate** (IAS 8): new information or developments change the expected useful life and/or residual value. The user must conclude this first.

| Situation | Treatment | In the MVP? |
|---|---|---|
| New information changes useful life or residual value | Prospective (IAS 8) | Yes |
| Original estimate ignored information available at the time | Prior-period error, retrospective restatement | No |
| Change of depreciation method | Treated as a change in estimate | No (straight-line only) |
| Cost model to revaluation model | Policy change with special IAS 16 rules | No |

## 2. Rules and how each becomes a calculation

Summaries are in our own words. Verification status follows the approved labelling rule:

- **Confirmed**: checked against the official IFRS Foundation issued-standard text on ifrs.org.
- **Corroborated (AASB)**: checked against Australia's AASB text, which keeps IFRS numbering; the IFRS primary text is still pending.
- **Pending**: the cited paragraph has not been checked against the official IFRS Foundation text.

| Rule (our summary) | Reference | Status | Calculation |
|---|---|---|---|
| Defines carrying amount (after accumulated depreciation and impairment losses) and depreciable amount (cost less residual value), among other terms | IAS 16.6 | **Confirmed (IFRS Foundation)** | `carrying = cost − accumulated` (impairment is outside MVP scope) |
| Depreciable amount is determined after deducting residual value | IAS 16.53 | **Confirmed (IFRS Foundation)** | `max(0, carrying − residual)` |
| No depreciation while residual value ≥ carrying amount; it resumes when residual value falls below carrying amount | IAS 16.54 | **Confirmed (IFRS Foundation)** | floor at 0; info V09 |
| Systematic allocation of depreciable amount over useful life | IAS 16.50 | **Confirmed (IFRS Foundation)** | straight-line by month |
| Depreciation recognised in profit or loss unless included in another asset's carrying amount | IAS 16.48 | **Confirmed (IFRS Foundation)** | (Phase 3: income statement) |
| Depreciation begins when available for use | IAS 16.55 | **Confirmed (IFRS Foundation)** | first month = available-for-use month |
| Residual value and useful life reviewed at least each year-end; expectation changes treated as estimate changes | IAS 16.51 | **Confirmed (IFRS Foundation)** | revision input |
| Useful life is an accounting estimate | IAS 8.32(d) | **Pending** | classification note |
| Effect recognised prospectively in profit or loss | IAS 8.36 | Corroborated (AASB) | no restatement; current and future periods only |
| Related asset's carrying amount adjusted in the period | IAS 8.37 | Corroborated (AASB) | closing carrying amount |
| Applied from the date of the change; useful-life changes affect current and future periods | IAS 8.38 | Corroborated (AASB) | user enters the change date; rate split at that month |
| Disclosure of the nature and amount of an estimate change affecting current or expected future periods; impracticability exception | IAS 8.39–40 | **Pending** | (later phase: report) |
| Prior-period error identification, retrospective correction and related disclosure | IAS 8.41–49 | **Pending** | classification boundary only |
| IFRS 18 effective 1 Jan 2027; IAS 8 retitled *Basis of Preparation of Financial Statements* | IFRS 18 | Confirmed (ifrs.org) | label note only |

These labels are also stored in `src/simulator/references.py`. `tests/test_references.py` fails if any of them is upgraded without evidence.

Official sources checked on 21 Oct 2026: [IAS 16 (2026 issued text)](https://www.ifrs.org/content/dam/ifrs/publications/html-standards/english/2026/issued/ias16.html), [IAS 8 (2026 issued text)](https://www.ifrs.org/content/dam/ifrs/publications/html-standards/english/2026/issued/ias8.html), and [IFRS 18 overview](https://www.ifrs.org/issued-standards/list-of-standards/ifrs-18-presentation-and-disclosure-in-financial-statements/). IAS 16 paragraph references above were checked in the official text. IAS 8 paragraphs 32(d) and 39–49 remain pending; paragraphs 36–38 remain AASB-corroborated with IFRS primary verification pending.

## 3. The calculation

At the date of the change E (always the 1st of a month):

```
carrying amount at E          = cost − accumulated depreciation at E
remaining depreciable amount  = max(0, carrying amount at E − revised residual value)
remaining life (months)       = revised TOTAL life − months elapsed since available for use
depreciation for n months     = remaining depreciable amount × n ÷ remaining life
```

- Months before E use the original estimate; months from E use the revised estimate. Each run of months is a **segment**.
- Accumulated depreciation before E is never recalculated. Opening balances are identical in the baseline and the scenario, and are checked (V13).
- **Baseline** = the same formula with the original estimate throughout. When the opening balances agree with the original estimate, this equals the original straight-line charge.
- If a segment would run past the end of the asset's life, its months are capped there.

## 4. Input conversion at the engine boundary (V22 change)

- Ordinary numeric inputs are accepted, including floats from a user interface (`100000.0`) and text (`"100,000"`). They are converted **once**, at the boundary, to `Decimal`.
- Floats are converted through their shortest exact text (`repr`): 1234.56 becomes `Decimal("1234.56")`, never the binary approximation.
- No float reaches the calculation engine. `test_no_float_anywhere_in_engine_output` walks the whole result to prove it.
- Rejected inputs:
  - **V22:** non-numbers, NaN, infinity, and fractional months.
  - **V23:** amounts with more than 2 decimal places. Amounts must be in cents so that the rounding policy below can reconcile exactly.
- **No input-rounding rule.** Excess decimals are rejected and never silently rounded, so the float artefact 0.1 + 0.2 = 0.30000000000000004 raises V23. Internal calculations keep full precision; only posted amounts are rounded, as set out in section 5.

## 5. Rounding policy (decision 7, Phase 3 condition 2)

1. The engine calculates with exact fractions; 58,500 ÷ 54 is held as 3250/3.
2. Each journal entry (one per segment) is rounded **half-up to 2 decimals**. Ledger balances are sums of posted entries, so they are always in cents.
3. Each period's charge is re-derived from the **posted** carrying amount: (posted carrying amount − residual) × months ÷ remaining months. A cent left over by rounding is therefore spread across the remaining life, not accumulated.
4. In the final period, months = remaining months, so the charge equals the whole remaining depreciable amount. That amount is a difference of two cent amounts and needs no rounding. **The asset therefore closes at exactly its residual value.**

**Proof for T23** (residual revised to 20,000; opening carrying amount 73,000; 84 months left):

- The exact annual charge is 53,000 ÷ 7 = 7,571.428571…, posted as 7,571.43.
- After k years the ledger is ahead of the exact path by k × (7,571.43 − 53,000/7) = **k/700**: 0.0014 after year 1, 0.0086 after year 6.
- In year 7, the remaining months are 12 of 12, so the charge is 27,571.42 − 20,000 = 7,571.42.
- Closing carrying amount = **20,000.00** exactly. Total = 73,000 − 20,000 = 53,000.00.

| Year | Posted | Closing carrying amount | Ledger − exact path |
|---|---|---|---|
| 2025 | 7,571.43 | 65,428.57 | 1/700 |
| 2026 | 7,571.43 | 57,857.14 | 2/700 |
| 2027 | 7,571.43 | 50,285.71 | 3/700 |
| 2028 | 7,571.43 | 42,714.28 | 4/700 |
| 2029 | 7,571.43 | 35,142.85 | 5/700 |
| 2030 | 7,571.43 | 27,571.42 | 6/700 |
| 2031 | 7,571.42 | 20,000.00 | 0 |

`simulator/ias16/rounding.py` produces this reconciliation for any schedule. `tests/test_rounding_policy.py` checks the following on five schedules, including awkward amounts and quarterly periods:

- continuity between periods;
- cent-only ledger balances;
- total posted = opening carrying amount − final carrying amount;
- final carrying amount = residual value;
- drift of at most ½ cent per posting, ending at zero.

## 6. Opening accumulated depreciation (decision 4)

- **Entered:** used exactly as entered (`opening_balance_source = "entered"`). If it differs from what the original estimate implies, warning V08 states both figures, the difference and the effect on carrying amount, and says that no correcting entry is generated.
- **Blank:** derived from the original estimate (`opening_balance_source = "calculated"`). Info V20 says the figure is **calculated, not verified against the ledger**.

## 7. Journal entries (J1–J5)

- **J1:** each entry is Dr *Depreciation expense — PPE* / Cr *Accumulated depreciation — PPE*.
- **J2:** one entry per segment, dated at the segment's end. A change on 1 Jul gives two entries, dated 30 Jun and 31 Dec.
- **J3:** no entry for the revision itself and none against retained earnings, because the change is prospective.
- **J4:** no tax entries.
- **J5:** debits must equal credits (V10). A segment with zero depreciation gets no entry.

## 8. Financial statements

Every line has a stated source:

| Line | Source |
|---|---|
| Revenue, other operating expenses, other income, finance costs | User input (same in both scenarios) |
| Depreciation | **Sum of the scenario's journal entries** |
| Operating profit | Revenue − other operating expenses − depreciation |
| Profit before tax | Operating profit + other income − finance costs (calculated separately from operating profit) |
| Accumulated depreciation | Opening + journal credits |
| Asset carrying amount | Cost − accumulated depreciation (**reported separately from total assets**) |
| Total assets | Other assets (input) + carrying amount |
| Total liabilities | User input (unchanged: depreciation is non-cash) |
| Closing equity | Opening equity + profit before tax (no tax, dividends or OCI) |

**No plug, ever.** The statements are built from the inputs as given and then checked:

- **V11:** assets = liabilities + equity, exactly, in each scenario.
- **V12, line by line:** each derived line is recomputed and compared with the engine and the journals.
- **V12, between scenarios:** every difference must be explained by depreciation alone.

If any check fails, the statements, impact table and ratios are withheld and the error shows both sides and the difference. Depreciation and journal entries stay available, because they were validated on their own.

If the imbalance equals your opening-balance override (the T19 case), the V11 message says so. Opening equity was probably prepared on the implied balance rather than on your ledger figure.

### Opening statement of financial position (separate module: `statements/opening.py`)

Two additional inputs are needed, and the existing opening-equity input is reused:

| Input | Meaning | Worked example |
|---|---|---|
| Opening total assets (**new**) | All assets at the period start, **including this asset** at its opening carrying amount | 409,000 (this asset 73,000 + other assets 336,000) |
| Opening total liabilities (**new**) | All liabilities at the period start | 200,000 |
| Opening equity (existing) | Entered once; used for this check **and** for closing equity | 209,000 |

The checks report problems and never adjust anything:

- **V26:** opening assets must equal opening liabilities + opening equity, exactly.
- **V27:** opening total assets must be at least this asset's opening carrying amount, because the asset is part of them.
- **V28 (info):** if the asset was not yet in use at the period start (as in T21), the engine cannot tell whether its cost was already in opening assets, so V27 is not applied and the user is told so.

How opening and closing figures relate in the worked example:

- Other assets rise from 336,000 to 436,000, an increase of 100,000. That equals revenue 500,000 − other operating expenses 400,000, if those were settled in cash.
- Equity rises from 209,000 to 300,000 by the profit before tax of 91,000.

This roll-forward is shown for understanding only. It is **not** checked, because other balance-sheet movements (capital expenditure, financing) are not collected.

### Result status and partial results (decision 1)

| Status | When | What is released |
|---|---|---|
| **complete** | Every check passed | Everything |
| **partial** | Depreciation passed, a later step failed | Only the sections that passed their own checks, in order: depreciation, then journal entries (V10), then opening position (V26/V27). Each is labelled "validated independently". Everything after the failing step (statements, impact table, ratios) is **withheld**. |
| **failed** | Depreciation inputs invalid | Nothing |

`ImpactResult.summary` quotes every error exactly. A partial result is never reported as a successful scenario: `ok` is `False` and the summary begins "Scenario NOT complete".

## 9. Ratios (all indirect effects)

| Ratio | Formula | Not meaningful when |
|---|---|---|
| Operating profit margin | Operating profit ÷ revenue | Revenue is 0 |
| Return on assets *(simplified)* | PBT ÷ closing total assets | Total assets ≤ 0 |
| Asset turnover *(simplified)* | Revenue ÷ closing total assets | Total assets ≤ 0 (zero revenue gives a valid 0.000×) |
| Liabilities-to-equity *(simplified D/E)* | Total liabilities ÷ closing equity | Equity ≤ 0 |

Ratios are held as exact fractions and displayed half-up: percentages to 2 decimals (changes in percentage points), multiples to 3 decimals. A ratio that is not meaningful shows a reason, never a number (info V25).

## 10. Worked example (SAR)

- **Asset:** cost 100,000; residual 10,000; life 120 months; available 1 Jan 2022.
- **Period:** FY2025; opening accumulated depreciation 27,000.
- **Revision:** revised total life 96 months.

| | Baseline | Revised: change dated 1 Jan | Revised: change dated 1 Jul |
|---|---|---|---|
| Segment 1 | 63,000 × 12 ÷ 84 = 9,000 | 63,000 × 12 ÷ 60 = 12,600 | 63,000 × 6 ÷ 84 = 4,500 |
| Segment 2 | — | — | 58,500 × 6 ÷ 54 = 6,500 |
| 2025 depreciation | 9,000 | 12,600 | 11,000 |
| Closing carrying amount | 64,000 | 60,400 | 62,000 |
| Profit before tax | 91,000 | 87,400 | 89,000 |
| Total assets | 500,000 | 496,400 | 498,000 |
| Closing equity | 300,000 | 296,400 | 298,000 |

The rest-of-entity inputs are: revenue 500,000; other operating expenses 400,000; other assets 436,000; liabilities 200,000; opening equity 209,000.

## 11. Not yet implemented

- The user interface (Phase 4).
- Tax, impairment (IAS 36), daily pro-rata, and other methods are out of the MVP's scope.
