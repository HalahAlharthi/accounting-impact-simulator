# Test cases

All expected values were calculated by hand (Phase 1 and the derivations in `accounting_methodology.md`). None is produced by the code under test.

- **Base asset** (unless stated): cost 100,000; residual 10,000; life 120 months; available 1 Jan 2022; FY2025; opening accumulated depreciation 27,000.
- **Case A**: revised total life 96 months, change dated 1 Jan 2025.
- **Case B**: the same revision, dated 1 Jul 2025.
- **Rest of entity**: revenue 500,000; other operating expenses 400,000; other income 0; finance costs 0; other assets 436,000; liabilities 200,000; opening equity 209,000.

Results of the latest run are in [test_results.md](test_results.md).

## Approved test cases T01–T27

| ID | Input | Expected | Test function(s) |
|---|---|---|---|
| T01 | Cost 50,000, residual 0, life 60, available 1 Jan 2025 | 10,000 | `test_depreciation::test_t01_zero_residual_value` |
| T02 | No change | 9,000; V21 warning | `test_depreciation::test_t02_residual_above_zero_no_change` |
| T03 | Life 0 | V03 | `test_validation::test_t03_zero_useful_life`, `test_t03b_zero_revised_useful_life` |
| T04 | Residual 120,000 | V02 | `test_validation::test_t04_residual_above_cost`, `test_t04b_revised_residual_above_cost` |
| T05 | Case A | 9,000 / 12,600; carrying amounts 64,000 / 60,400 | `test_depreciation::test_t05_case_a_revision_with_accumulated_depreciation` |
| T06 | Case B | 4,500 + 6,500 = 11,000; carrying amount 62,000 | `test_depreciation::test_t06_mid_period_revision` |
| T07 | Residual revised to 20,000 | 7,571.43 | `test_depreciation::test_t07_residual_revision_rounding` |
| T08 | Case A | Opening balances untouched; not the retrospective 18,000 | `test_depreciation::test_t08_prospective_treatment` |
| T09 | Revised total life 36 | V04 | `test_validation::test_t09_revised_life_already_elapsed` |
| T10 | Revised residual 75,000 | 0; V09 citing IAS 16.54 (confirmed on ifrs.org); no journal entry | `test_depreciation::test_t10_residual_above_carrying_amount`, `test_journal::test_zero_depreciation_segment_gets_no_entry_and_statements_still_reconcile` |
| T10b | Revised residual 73,000 | 0; V09 | `test_depreciation::test_t10b_residual_equal_to_carrying_amount` |
| T11 | Available 1 Jul 2025 | 4,500 | `test_depreciation::test_t11_asset_available_mid_period` |
| T12 | Case A, Case B, T19, T21 entries | Every entry balanced | `test_journal::test_t12_all_entries_balance` |
| T13 | Case A statements | A − L − E = 0 in both scenarios | `test_statements::test_t13_accounting_equation_case_a` |
| T14 | Other assets 435,000 | V11: 499,000 vs 500,000, difference −1,000; equity stays 300,000; no statements or ratios | `test_statements::test_t14_unbalanced_inputs_no_plug` |
| T15 | Equity 0 (baseline) and −3,600 (revised); direct −50,000 | Liabilities-to-equity "not meaningful" with reason | `test_ratios::test_t15_equity_zero_or_negative`, `test_t15_direct_negative_denominator` |
| T16 | Revenue 0 | Margin not meaningful; turnover 0.000×; ROA −1.80% → −2.54% | `test_ratios::test_t16_revenue_zero` |
| T17 | Case B run twice | Identical | `test_depreciation::test_t17_reproducible` |
| T18 | Cost missing | V14 naming "cost" | `test_validation::test_t18_missing_cost` |
| T19 | Opening accumulated depreciation 30,000 | Used as entered; V08 with 30,000 / 27,000 / 3,000; 8,571.43 / 12,000; closing 61,428.57 / 58,000 | `test_depreciation::test_t19_opening_accumulated_depreciation_override` |
| T20 | Case B | Segments 6 + 6 months; 4,500 + 6,500 | `test_depreciation::test_t20_two_rate_segments` |
| T21 | Available 1 Apr 2025; life 60 from 1 Oct | 4,500 + 4,750 = 9,250; baseline 6,750; carrying amount 90,750 | `test_depreciation::test_t21_available_and_revised_in_same_period` |
| T22 | Case B, Jul–Dec | 6,500.00, not 6,499.98 | `test_depreciation::test_t22_full_precision_not_rounded_rate` |
| T23 | T07 asset over 7 years | 6 × 7,571.43 + 7,571.42; closes at 20,000.00; drift k/700 | `test_depreciation::test_t23_full_life_schedule`, `test_rounding_policy::test_t23_year_by_year_hand_figures` |
| T24 | Case A integrity | Journals 9,000 / 12,600 = statement depreciation; accumulated depreciation 36,000 / 39,600; A − L − E = 0; PBT, equity, carrying amount and total assets all −3,600; liabilities and revenue 0 | `test_statements::test_t24_case_a_integrity` |
| T25 | Case B integrity | Entries 4,500 (30 Jun) + 6,500 (31 Dec); operating profit 89,000; total assets 498,000; equity 298,000; A − L − E = 0; changes −2,000 | `test_statements::test_t25_case_b_integrity` |
| T26 | Statement carrying amount set to 64,100 | V12 shows +100 and −100 differences; nothing adjusted | `test_statements::test_t26_statement_inconsistency_reported` |
| T27 | Opening balances identical; accounting equation under the T19 override | (1) Identical opening balances in all cases; V13 guard reports without adjusting. (2) Override with opening equity 209,000: V11, 497,428.57 vs 500,428.57, difference −3,000, message points to the override, no plug. Override with opening equity 206,000: balances (497,428.57 and 494,000). | `test_integrity::test_t27_opening_balances_identical_all_cases`, `test_t27_guard_rejects_different_opening_balances_without_adjusting`; `test_statements::test_t27_override_with_inputs_prepared_on_implied_balance_raises_v11`, `test_t27_override_with_consistent_inputs_balances` |

**Range note:** "T24–T26" means the three tests **T24, T25 and T26** listed above.

**Opening position** (all tests unless stated): total assets 409,000; liabilities 200,000. 409,000 = 200,000 + 209,000; this asset 73,000; other assets 336,000.

## Opening and closing statement checks (O-series) — `tests/test_opening_and_partial.py`

| ID | Input | Expected | Test |
|---|---|---|---|
| O1 | Worked example | Opening 409,000 = 200,000 + 209,000; asset 73,000, other assets 336,000; status **complete**; all sections released | `test_o1_opening_position_worked_example` |
| O2 | Opening total assets 410,000 | V26, difference 1,000; no plug; status **partial**; released: depreciation, journal entries; withheld: opening position, statements, impact table, ratios; exact error quoted in the summary | `test_o2_opening_equation_fails` |
| O3 | Opening assets 50,000, opening equity −150,000 | Equation balances, but V27: asset 73,000 not covered, shortfall 23,000 | `test_o3_opening_assets_exclude_the_asset` |
| O3b | T21 asset (in use from 1 Apr 2025), opening assets 50,000 | V27 not applied; info V28; V26 still enforced (409,001 → V26) | `test_o3b_asset_not_in_use_at_period_start` |
| O4 | Opening total assets missing | V14 naming `opening_total_assets`; partial | `test_o4_opening_position_missing` |
| T13, T14, T24–T27 | Closing statements | See the table above | `test_statements.py` |

## Partial results after validation failures

| ID | Failure point | Released (labelled "validated independently") | Withheld | Test |
|---|---|---|---|---|
| O5 | Closing V11 (T14 inputs) | Depreciation, journal entries, opening position | Statements, impact table, ratios | `test_o5_closing_failure_releases_validated_sections_only` |
| O2 | Opening V26 | Depreciation, journal entries | Opening position onward | `test_o2_opening_equation_fails` |
| O8 | Statement input V24 | Depreciation, journal entries | Opening position onward | `test_o8_statement_input_failure_is_partial` |
| O6 | Journal V10 (fault injected) | Depreciation | Journal entries onward | `test_o6_journal_failure_withholds_journals` |
| O7 | Depreciation input (T09) | Nothing (status **failed**) | Everything | `test_o7_depreciation_failure_releases_nothing` |

Every partial case also asserts that the result is not reported as successful: `ok` is False, the status is not "complete", and no statements, impact table or ratios are present.

## Monetary precision (P-series) — `tests/test_monetary_precision.py`

| ID | What | Expected |
|---|---|---|
| P1 | Each asset amount (cost, residual, revised residual, opening accumulated depreciation) = 1,000.005 | V23 naming the field; status **failed** (4 tests) |
| P2 | Each of the 7 rest-of-entity amounts = 1,000.005 | V23 naming the field; status **partial**; statements withheld (7 tests) |
| P3 | Each opening amount with 3 decimals | V23 naming the field; opening position withheld (2 tests) |
| P4 | Cost 100,000.01 (2 decimals) | Accepted; 63,000.01 × 12 ÷ 60 = 12,600.002 → posted 12,600.00 |
| P5 | Float artefact 0.1 + 0.2 | V23: rejected, not silently rounded |
| P6 | Case A, Case B, T07, T21 | Every journal line, segment, balance and statement figure has at most 2 decimals; all complete (4 tests) |
| P7 | T07 | Exact value kept as 53,000/7; posted 7,571.43 |

## V24 field rules — `tests/test_v24_fields.py`

| What | Expected |
|---|---|
| Each of revenue, other operating expenses, finance costs, other assets, liabilities = −0.01 | V24 naming the field; partial (5 tests) |
| Each of the same fields = 0 | No V24 (5 tests) |
| Opening total assets / liabilities = −1 | V24 naming the field (2 tests) |
| Other income −5,000 | Allowed; PBT 86,000; complete |
| Opening equity −91,000 | Allowed; complete |
| Rule coverage | Every financial field is classified as non-negative or may-be-negative, never both or neither |

## Additional tests

| Area | Test functions |
|---|---|
| Rounding policy, multi-year (condition 2) | `test_rounding_policy::test_case_b_to_end_of_life`, `test_t19_override_to_end_of_life`, `test_awkward_amounts_and_mid_year_change`, `test_awkward_amounts_non_annual_period` |
| Input conversion (V22 change) | `test_coerce::*` (9 tests): floats and text accepted and identical to Decimal; no float in output; V22 and V23 rejections |
| V20 / V21 / V18 wording | `test_validation::test_v20_opening_balance_derived_when_blank_and_labelled_calculated`, `test_entered_opening_balance_is_labelled_entered`, `test_v18_message_says_out_of_scope`; `test_depreciation::test_v21_not_raised_when_depreciation_changes` |
| Journal rules | `test_journal::test_j1_j2_accounts_dates_and_amounts_case_b`, `test_j3_no_entry_against_retained_earnings`, `test_v10_unbalanced_entry_is_reported_not_fixed` |
| Statements | `test_statements::test_carrying_amount_and_total_assets_are_separate_lines`, `test_financial_inputs_missing_or_negative`, `test_financial_inputs_accept_ui_floats` |
| Ratios | `test_ratios::test_case_a_ratios`, `test_margin_uses_operating_profit_not_pbt` |
| Validation codes | `test_validation::test_v01…test_v19…` (one or more per code) |
| Engine guards | `test_integrity::test_arithmetic_check_passes_on_engine_output`, `test_v12_*` |
| Helpers and references | `test_money_periods::*`, `test_references::*` |

## Phase 4: interface, display and export

| Area | What is checked | Tests |
|---|---|---|
| Samples | All four sample files load. Case A → 12,600 (complete); Case B → 11,000 (complete); T19 → 12,000 with V08 (complete); T14 → partial with V11 | `test_scenarios.py` (5) |
| Display = engine | Every depreciation row, impact row, statement line and journal debit shown equals `fmt(engine value)`, for Case A, Case B and T19 | `test_presentation.py::test_*_match_engine` (9) |
| Displayed ratios | 18.20% → 17.48%, −0.72 pp; turnover 1.007×, +0.007×; a not-meaningful ratio shows "Not meaningful" and no number | `test_case_a_displayed_ratios`, `test_not_meaningful_ratio_shows_no_number` |
| Status and labels | Complete → success banner, no notes; partial (T14) → warning banner, depreciation labelled "validated independently", ratios "withheld" with the V11 reason; failed → error banner, no figures | `test_status_banners_and_section_notes` |
| Validation and references tables | Errors listed first; every issue code shown; IAS 16.54 shown as confirmed on ifrs.org | `test_issues_and_references_tables` |
| Export | The Markdown report shows the same rows as the screen; a partial report states 3 sections as **Withheld**; JSON amounts are exact text; withheld sections are null | `test_export.py` (3) |
| Real app (Streamlit `AppTest`) | Default sample runs with no exception, success banner, 12,600.00 metric; loading T14 gives "NOT complete" and "Withheld" notices | `test_app.py` (2), **skipped when Streamlit is not installed** |

## Validation codes

| Code | Severity | Meaning |
|---|---|---|
| V01 | Error | Cost not greater than zero |
| V02 | Error | Residual value (original or revised) outside 0–cost |
| V03 | Error | Useful life (original or revised) not greater than zero |
| V04 | Error | Revised total life not more than the months already elapsed |
| V05 | Error | Change date outside the reporting period |
| V06 | Error | Period ends before it starts, or the asset is not available during the period |
| V07 | Error | Opening accumulated depreciation outside 0 to (cost − residual) |
| V08 | Warning | Opening accumulated depreciation differs from the implied amount; used as entered |
| V09 | Info | Residual value ≥ carrying amount, so depreciation is zero |
| V10 | Error | Journal entry does not balance, or has a negative amount |
| V11 | Error | Accounting equation fails; statements and ratios withheld; no plug |
| V12 | Error | Arithmetic or reconciliation failure (engine, statements, or between scenarios) |
| V13 | Error | Opening balances differ between baseline and revised |
| V14 | Error | Missing input |
| V15 | Error | Date not on the monthly convention |
| V16 | Error | Unsupported method |
| V17 | Error | Change dated before the asset was available |
| V18 | Error | Original life ended before the period (out of MVP scope) |
| V19 | Error | Accumulated depreciation entered for an asset not yet in use |
| V20 | Info | Opening accumulated depreciation **calculated** from the original estimate; not verified against the ledger |
| V21 | Warning | The revision produces no change in depreciation for the period |
| V22 | Error | Not a number, NaN, infinity, or fractional months |
| V23 | Error | Amount with more than 2 decimal places |
| V24 | Error | Negative value in a field that must not be negative (see the field rules in `assumptions_and_limitations.md`) |
| V25 | Info | A ratio is not meaningful (reason given; no number shown) |
| V26 | Error | Opening assets ≠ opening liabilities + opening equity |
| V27 | Error | Opening total assets less than this asset's opening carrying amount |
| V28 | Info | Asset not in use at the period start; V27 not applied |
