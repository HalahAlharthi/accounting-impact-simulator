# Test results

## Current local run

Run on 21 Oct 2026 from the project virtual environment with Python 3.15.1 and pytest 9.1.1:

```text
154 passed, 0 failed, 0 skipped
```

This run includes Streamlit's `AppTest` interface tests, including switching among Case A, Case B, T19 Override, and T14 Partial. The tests compare selected sample inputs and displayed results with the corresponding engine output.

Passing tests show that the implementation reproduces the approved hand-calculated examples and validations. They do not, by themselves, establish that an accounting treatment is appropriate for a real entity. See [accounting methodology](accounting_methodology.md) for reference verification statuses.

## Historical build-sandbox run (superseded)

The following result is retained as historical only. It is superseded by the current local run above.

Run on 21 Oct 2026 with `pytest -v -rs`: 151 tests collected, 150 passed, 1 skipped, exit code 0.

**Skipped:** `tests/test_app.py` (Streamlit's AppTest), because Streamlit could not be installed in the build sandbox. It runs once `pip install -r requirements.txt` has installed Streamlit.

**Environment note:** PyPI was blocked in the build sandbox, so pytest was assembled from its GitHub source (development version 9.0.0.dev0). Re-run locally with a released pytest to confirm.

**App smoke-run:** `app.py` was also executed in the sandbox against a minimal Streamlit stand-in (default sample, T14 sample, form submission), and all assertions passed. This shows the code paths run; it does not show the rendered page.

Passing tests show that the code reproduces the hand-calculated expectations in [test_cases.md](test_cases.md). They do not, on their own, validate the accounting judgments; see [accounting_methodology.md](accounting_methodology.md) for references still pending verification.

```text
============================= test session starts ==============================
platform linux -- Python 3.13.16, pytest-9.0.0.dev0, pluggy-1.6.0 -- /usr/bin/python3
rootdir: /home/claude/accounting-impact-simulator
configfile: pyproject.toml
testpaths: tests
plugins: platformdirs-4.12.3, anyio-4.15.1
collecting ... collected 150 items / 1 skipped

tests/test_coerce.py::test_float_inputs_accepted_and_give_identical_results PASSED [  0%]
tests/test_coerce.py::test_string_inputs_with_thousands_separators_accepted PASSED [  1%]
tests/test_coerce.py::test_no_float_anywhere_in_engine_output PASSED     [  2%]
tests/test_coerce.py::test_float_converted_by_shortest_repr_not_binary_expansion PASSED [  2%]
tests/test_coerce.py::test_v22_rejects_non_numbers PASSED                [  3%]
tests/test_coerce.py::test_v23_rejects_more_than_two_decimals PASSED     [  4%]
tests/test_coerce.py::test_months_must_be_whole PASSED                   [  4%]
tests/test_coerce.py::test_dates_accept_iso_text PASSED                  [  5%]
tests/test_coerce.py::test_blank_string_treated_as_missing PASSED        [  6%]
tests/test_depreciation.py::test_t01_zero_residual_value PASSED          [  6%]
tests/test_depreciation.py::test_t02_residual_above_zero_no_change PASSED [  7%]
tests/test_depreciation.py::test_v21_not_raised_when_depreciation_changes PASSED [  8%]
tests/test_depreciation.py::test_t05_case_a_revision_with_accumulated_depreciation PASSED [  8%]
tests/test_depreciation.py::test_t06_mid_period_revision PASSED          [  9%]
tests/test_depreciation.py::test_t07_residual_revision_rounding PASSED   [ 10%]
tests/test_depreciation.py::test_t08_prospective_treatment PASSED        [ 10%]
tests/test_depreciation.py::test_t10_residual_above_carrying_amount PASSED [ 11%]
tests/test_depreciation.py::test_t10b_residual_equal_to_carrying_amount PASSED [ 12%]
tests/test_depreciation.py::test_t11_asset_available_mid_period PASSED   [ 12%]
tests/test_depreciation.py::test_t17_reproducible PASSED                 [ 13%]
tests/test_depreciation.py::test_t19_opening_accumulated_depreciation_override PASSED [ 14%]
tests/test_depreciation.py::test_t20_two_rate_segments PASSED            [ 14%]
tests/test_depreciation.py::test_t21_available_and_revised_in_same_period PASSED [ 15%]
tests/test_depreciation.py::test_t22_full_precision_not_rounded_rate PASSED [ 16%]
tests/test_depreciation.py::test_t23_full_life_schedule PASSED           [ 16%]
tests/test_depreciation.py::test_schedule_stops_at_end_of_life PASSED    [ 17%]
tests/test_depreciation.py::test_trace_shows_formula_and_numbers PASSED  [ 18%]
tests/test_export.py::test_markdown_report_complete PASSED               [ 18%]
tests/test_export.py::test_markdown_report_partial_states_withheld_sections PASSED [ 19%]
tests/test_export.py::test_json_report PASSED                            [ 20%]
tests/test_integrity.py::test_t27_opening_balances_identical_all_cases PASSED [ 20%]
tests/test_integrity.py::test_t27_guard_rejects_different_opening_balances_without_adjusting PASSED [ 21%]
tests/test_integrity.py::test_arithmetic_check_passes_on_engine_output PASSED [ 22%]
tests/test_integrity.py::test_v12_arithmetic_guard_catches_inconsistent_segment PASSED [ 22%]
tests/test_integrity.py::test_v12_guard_catches_posted_amount_not_matching_exact PASSED [ 23%]
tests/test_journal.py::test_t12_all_entries_balance PASSED               [ 24%]
tests/test_journal.py::test_j1_j2_accounts_dates_and_amounts_case_b PASSED [ 24%]
tests/test_journal.py::test_j3_no_entry_against_retained_earnings PASSED [ 25%]
tests/test_journal.py::test_zero_depreciation_segment_gets_no_entry_and_statements_still_reconcile PASSED [ 26%]
tests/test_journal.py::test_v10_unbalanced_entry_is_reported_not_fixed PASSED [ 26%]
tests/test_monetary_precision.py::test_p1_asset_amounts_with_three_decimals_rejected[cost] PASSED [ 27%]
tests/test_monetary_precision.py::test_p1_asset_amounts_with_three_decimals_rejected[residual_value] PASSED [ 28%]
tests/test_monetary_precision.py::test_p1_asset_amounts_with_three_decimals_rejected[revised_residual_value] PASSED [ 28%]
tests/test_monetary_precision.py::test_p1_asset_amounts_with_three_decimals_rejected[opening_accumulated_depreciation] PASSED [ 29%]
tests/test_monetary_precision.py::test_p2_financial_amounts_with_three_decimals_rejected[revenue] PASSED [ 30%]
tests/test_monetary_precision.py::test_p2_financial_amounts_with_three_decimals_rejected[other_operating_expenses] PASSED [ 30%]
tests/test_monetary_precision.py::test_p2_financial_amounts_with_three_decimals_rejected[other_income] PASSED [ 31%]
tests/test_monetary_precision.py::test_p2_financial_amounts_with_three_decimals_rejected[finance_costs] PASSED [ 32%]
tests/test_monetary_precision.py::test_p2_financial_amounts_with_three_decimals_rejected[other_assets_closing] PASSED [ 32%]
tests/test_monetary_precision.py::test_p2_financial_amounts_with_three_decimals_rejected[total_liabilities_closing] PASSED [ 33%]
tests/test_monetary_precision.py::test_p2_financial_amounts_with_three_decimals_rejected[opening_equity] PASSED [ 34%]
tests/test_monetary_precision.py::test_p3_opening_amounts_with_three_decimals_rejected[opening_total_assets] PASSED [ 34%]
tests/test_monetary_precision.py::test_p3_opening_amounts_with_three_decimals_rejected[opening_total_liabilities] PASSED [ 35%]
tests/test_monetary_precision.py::test_p4_two_decimals_accepted PASSED   [ 36%]
tests/test_monetary_precision.py::test_p5_float_artefact_rejected_not_silently_rounded PASSED [ 36%]
tests/test_monetary_precision.py::test_p6_every_posted_and_reported_amount_has_two_decimals_at_most[case_a] PASSED [ 37%]
tests/test_monetary_precision.py::test_p6_every_posted_and_reported_amount_has_two_decimals_at_most[case_b] PASSED [ 38%]
tests/test_monetary_precision.py::test_p6_every_posted_and_reported_amount_has_two_decimals_at_most[t07] PASSED [ 38%]
tests/test_monetary_precision.py::test_p6_every_posted_and_reported_amount_has_two_decimals_at_most[t21] PASSED [ 39%]
tests/test_monetary_precision.py::test_p7_internal_precision_retained PASSED [ 40%]
tests/test_money_periods.py::test_round_half_up_to_cents PASSED          [ 40%]
tests/test_money_periods.py::test_exact_fraction_division PASSED         [ 41%]
tests/test_money_periods.py::test_month_arithmetic PASSED                [ 42%]
tests/test_opening_and_partial.py::test_o1_opening_position_worked_example PASSED [ 42%]
tests/test_opening_and_partial.py::test_o2_opening_equation_fails PASSED [ 43%]
tests/test_opening_and_partial.py::test_o3_opening_assets_exclude_the_asset PASSED [ 44%]
tests/test_opening_and_partial.py::test_o3b_asset_not_in_use_at_period_start PASSED [ 44%]
tests/test_opening_and_partial.py::test_o4_opening_position_missing PASSED [ 45%]
tests/test_opening_and_partial.py::test_o5_closing_failure_releases_validated_sections_only PASSED [ 46%]
tests/test_opening_and_partial.py::test_o6_journal_failure_withholds_journals PASSED [ 46%]
tests/test_opening_and_partial.py::test_o7_depreciation_failure_releases_nothing PASSED [ 47%]
tests/test_opening_and_partial.py::test_o8_statement_input_failure_is_partial PASSED [ 48%]
tests/test_presentation.py::test_depreciation_table_matches_engine[case_a] PASSED [ 48%]
tests/test_presentation.py::test_depreciation_table_matches_engine[case_b] PASSED [ 49%]
tests/test_presentation.py::test_depreciation_table_matches_engine[t19] PASSED [ 50%]
tests/test_presentation.py::test_impact_and_statements_tables_match_engine[case_a] PASSED [ 50%]
tests/test_presentation.py::test_impact_and_statements_tables_match_engine[case_b] PASSED [ 51%]
tests/test_presentation.py::test_impact_and_statements_tables_match_engine[t19] PASSED [ 52%]
tests/test_presentation.py::test_journal_table_matches_entries[case_a] PASSED [ 52%]
tests/test_presentation.py::test_journal_table_matches_entries[case_b] PASSED [ 53%]
tests/test_presentation.py::test_journal_table_matches_entries[t19] PASSED [ 54%]
tests/test_presentation.py::test_case_a_displayed_ratios PASSED          [ 54%]
tests/test_presentation.py::test_not_meaningful_ratio_shows_no_number PASSED [ 55%]
tests/test_presentation.py::test_key_figures_and_summary_match_engine PASSED [ 56%]
tests/test_presentation.py::test_status_banners_and_section_notes PASSED [ 56%]
tests/test_presentation.py::test_issues_and_references_tables PASSED     [ 57%]
tests/test_ratios.py::test_case_a_ratios PASSED                          [ 58%]
tests/test_ratios.py::test_margin_uses_operating_profit_not_pbt PASSED   [ 58%]
tests/test_ratios.py::test_t15_equity_zero_or_negative PASSED            [ 59%]
tests/test_ratios.py::test_t15_direct_negative_denominator PASSED        [ 60%]
tests/test_ratios.py::test_t16_revenue_zero PASSED                       [ 60%]
tests/test_references.py::test_unverified_references_are_pending PASSED  [ 61%]
tests/test_references.py::test_aasb_corroborated_references_are_not_labelled_confirmed PASSED [ 62%]
tests/test_references.py::test_only_ifrs_org_items_are_confirmed PASSED  [ 62%]
tests/test_rounding_policy.py::test_t23_year_by_year_hand_figures PASSED [ 63%]
tests/test_rounding_policy.py::test_case_b_to_end_of_life PASSED         [ 64%]
tests/test_rounding_policy.py::test_t19_override_to_end_of_life PASSED   [ 64%]
tests/test_rounding_policy.py::test_awkward_amounts_and_mid_year_change PASSED [ 65%]
tests/test_rounding_policy.py::test_awkward_amounts_non_annual_period PASSED [ 66%]
tests/test_scenarios.py::test_four_samples_present PASSED                [ 66%]
tests/test_scenarios.py::test_sample_case_a PASSED                       [ 67%]
tests/test_scenarios.py::test_sample_case_b PASSED                       [ 68%]
tests/test_scenarios.py::test_sample_t19_override_balances_with_warning PASSED [ 68%]
tests/test_scenarios.py::test_sample_t14_is_partial PASSED               [ 69%]
tests/test_statements.py::test_t13_accounting_equation_case_a PASSED     [ 70%]
tests/test_statements.py::test_t24_case_a_integrity PASSED               [ 70%]
tests/test_statements.py::test_carrying_amount_and_total_assets_are_separate_lines PASSED [ 71%]
tests/test_statements.py::test_t25_case_b_integrity PASSED               [ 72%]
tests/test_statements.py::test_t14_unbalanced_inputs_no_plug PASSED      [ 72%]
tests/test_statements.py::test_t26_statement_inconsistency_reported PASSED [ 73%]
tests/test_statements.py::test_t27_override_with_inputs_prepared_on_implied_balance_raises_v11 PASSED [ 74%]
tests/test_statements.py::test_t27_override_with_consistent_inputs_balances PASSED [ 74%]
tests/test_statements.py::test_financial_inputs_missing_or_negative PASSED [ 75%]
tests/test_statements.py::test_financial_inputs_accept_ui_floats PASSED  [ 76%]
tests/test_v24_fields.py::test_v24_negative_rejected[revenue] PASSED     [ 76%]
tests/test_v24_fields.py::test_v24_negative_rejected[other_operating_expenses] PASSED [ 77%]
tests/test_v24_fields.py::test_v24_negative_rejected[finance_costs] PASSED [ 78%]
tests/test_v24_fields.py::test_v24_negative_rejected[other_assets_closing] PASSED [ 78%]
tests/test_v24_fields.py::test_v24_negative_rejected[total_liabilities_closing] PASSED [ 79%]
tests/test_v24_fields.py::test_v24_zero_allowed[revenue] PASSED          [ 80%]
tests/test_v24_fields.py::test_v24_zero_allowed[other_operating_expenses] PASSED [ 80%]
tests/test_v24_fields.py::test_v24_zero_allowed[finance_costs] PASSED    [ 81%]
tests/test_v24_fields.py::test_v24_zero_allowed[other_assets_closing] PASSED [ 82%]
tests/test_v24_fields.py::test_v24_zero_allowed[total_liabilities_closing] PASSED [ 82%]
tests/test_v24_fields.py::test_v24_opening_fields_negative_rejected[opening_total_assets-total_assets] PASSED [ 83%]
tests/test_v24_fields.py::test_v24_opening_fields_negative_rejected[opening_total_liabilities-total_liabilities] PASSED [ 84%]
tests/test_v24_fields.py::test_other_income_may_be_negative PASSED       [ 84%]
tests/test_v24_fields.py::test_opening_equity_may_be_negative PASSED     [ 85%]
tests/test_v24_fields.py::test_every_financial_field_has_a_documented_sign_rule PASSED [ 86%]
tests/test_validation.py::test_t03_zero_useful_life PASSED               [ 86%]
tests/test_validation.py::test_t03b_zero_revised_useful_life PASSED      [ 87%]
tests/test_validation.py::test_t04_residual_above_cost PASSED            [ 88%]
tests/test_validation.py::test_t04b_revised_residual_above_cost PASSED   [ 88%]
tests/test_validation.py::test_t09_revised_life_already_elapsed PASSED   [ 89%]
tests/test_validation.py::test_t18_missing_cost PASSED                   [ 90%]
tests/test_validation.py::test_missing_revision_and_dates PASSED         [ 90%]
tests/test_validation.py::test_v01_cost_not_positive PASSED              [ 91%]
tests/test_validation.py::test_v05_change_date_outside_period PASSED     [ 92%]
tests/test_validation.py::test_v06_period_ends_before_start PASSED       [ 92%]
tests/test_validation.py::test_v06_asset_not_available_during_period PASSED [ 93%]
tests/test_validation.py::test_v07_opening_accumulated_depreciation_above_depreciable_amount PASSED [ 94%]
tests/test_validation.py::test_v07_negative_opening_accumulated_depreciation PASSED [ 94%]
tests/test_validation.py::test_v15_dates_must_follow_monthly_convention PASSED [ 95%]
tests/test_validation.py::test_v16_unsupported_method PASSED             [ 96%]
tests/test_validation.py::test_v17_change_dated_before_available PASSED  [ 96%]
tests/test_validation.py::test_v18_original_life_ended_before_period PASSED [ 97%]
tests/test_validation.py::test_v19_accumulated_depreciation_for_asset_not_yet_in_use PASSED [ 98%]
tests/test_validation.py::test_v20_opening_balance_derived_when_blank_and_labelled_calculated PASSED [ 98%]
tests/test_validation.py::test_entered_opening_balance_is_labelled_entered PASSED [ 99%]
tests/test_validation.py::test_v18_message_says_out_of_scope PASSED      [100%]

=========================== short test summary info ============================
SKIPPED [1] tests/test_app.py:9: could not import 'streamlit.testing.v1': No module named 'streamlit'
======================== 150 passed, 1 skipped in 0.49s ========================
```
