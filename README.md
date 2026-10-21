# Accounting Standards Impact Simulator

An educational Streamlit prototype that demonstrates how a change in an IAS 16 useful-life or residual-value estimate can flow through depreciation, journal entries, financial statements, and selected ratios. It compares a baseline using the original estimate with a scenario using the revised estimate.

This is fictional, illustrative software. It is not accounting, audit, tax, legal, or investment advice and is not a substitute for professional accounting judgment. The appropriate treatment depends on the facts, applicable reporting framework, and jurisdiction. Have a qualified professional review any real-world decision.

## Features

- Four fictional, preloaded examples for exploring complete and partial outcomes.
- Prospective depreciation schedules with the original and revised estimates shown separately.
- Journal entries, opening and closing statement checks, selected financial ratios, and validation messages.
- Partial-result handling: sections that pass their checks remain available; sections affected by failed checks are withheld rather than balanced with an invented amount.
- Markdown and JSON report exports.
- An accounting engine kept separate from the Streamlit interface and display formatting.

Select a sample in the sidebar to load its inputs and update the results. To try different values, use **Scenario Setup** and submit with **Calculate**.

## Sample scenarios

All sample data is fictional and stored in `data/sample_inputs/`.

| Sample | Expected outcome |
|---|---|
| Case A — change on 1 January | Complete; revised-period depreciation of 12,600.00 |
| Case B — change on 1 July | Complete; revised-period depreciation of 11,000.00 |
| T19 — ledger opening balance override | Complete with warning V08; revised-period depreciation of 12,000.00 |
| T14 — unbalanced closing inputs | Partial with V11; depreciation and journal entries are shown, while statements, impact table, and ratios are withheld |

The displayed figures are produced from the selected scenario's inputs. The accounting engine does not plug or silently correct imbalances.

## Requirements

- Python 3.10 or newer
- Packages listed in `requirements.txt`

## Set up and run

### Windows PowerShell

From the project folder, run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

If PowerShell does not allow virtual-environment activation, run the environment's executables directly instead:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\streamlit.exe run app.py
```

### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

Streamlit prints a local URL, usually `http://localhost:8501`. Leave the terminal running while using the app.

## Run the tests

With the virtual environment activated:

```bash
python -m pytest -v
```

On Windows, without activating it:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

The suite includes headless interface tests using Streamlit's `AppTest`, including switching among all four samples and checking their displayed inputs and results.

## Accounting assumptions and limitations

- The prototype covers one asset, the cost model, one component, and straight-line depreciation. It treats the input as a change in accounting estimate; the user must assess whether that classification fits the facts.
- Dates use a monthly convention: availability and estimate-change dates are the first of a month, and reporting periods end on the last day of a month.
- The estimate change is applied prospectively. The model does not restate prior depreciation or post an adjustment to opening retained earnings.
- Amounts are accepted to cents. Calculations retain exact internal precision; posted amounts use the documented half-up rounding and reconciliation policy.
- Opening balances and the accounting equation are checked. The app does not infer missing balances or force an equation to balance.
- Tax, impairment, revaluation, held-for-sale treatment, component accounting, prior-period error correction, and other asset movements are outside the model's scope. Ratios are simplified and use closing rather than average balances.
- User-entered data may be incomplete or incorrect. A successful validation is not assurance that the inputs, accounting classification, or result are appropriate for an entity.

See [accounting methodology](docs/accounting_methodology.md) and [assumptions and limitations](docs/assumptions_and_limitations.md) for the detailed model and controls.

## Standard references

Reference labels distinguish between material checked against the IFRS Foundation's official issued-standard text, material corroborated through an equivalent AASB text, and references still pending verification. AASB corroboration is not presented as IFRS verification. IAS 8.32(d) and IAS 8.39–49 remain pending verification against the official IFRS text; IAS 8.36–38 remain AASB-corroborated, with IFRS primary-text verification pending. See the reference table and source links in [accounting methodology](docs/accounting_methodology.md).

## Project structure

```text
app.py                         Streamlit interface
src/simulator/                 Accounting engine, validation, reporting, and references
data/sample_inputs/            Fictional JSON sample scenarios
docs/                          Methodology, assumptions, test cases, and test results
tests/                         Engine, reporting, validation, and interface tests
requirements.txt               Runtime and test dependencies
```

## Before using with real data

Do not put client records, personal information, credentials, or private exports in the sample-data folder or a public repository. Keep such material outside the repository. The included sample files contain fictional examples. Review the assumptions, reference status, and applicability of the standards before relying on any output.
