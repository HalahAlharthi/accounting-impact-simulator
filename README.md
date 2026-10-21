# Accounting Standards Impact Simulator

An educational tool that simulates how a change in an accounting estimate flows through depreciation, journal entries, financial statements and ratios. The MVP covers the IAS 16 useful-life case. The full README comes in Phase 6.

**Status: Phase 4 of 6.** The engine is tested; the Streamlit interface is built.

## Run the app

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

The app opens in your browser. Pick a sample scenario in the sidebar and click **Load sample**, or edit the inputs under **Scenario Setup** and click **Calculate**.

## Run the tests

```bash
pytest -v
```

`tests/test_app.py` runs the real app headlessly with Streamlit's `AppTest`. It is skipped if Streamlit is not installed.

## Architecture

```
app.py                         Streamlit UI: inputs and display only, no calculations
src/simulator/reporting/       Presentation tables and report export (formats engine values)
src/simulator/impact.py        run_impact_analysis(inputs, financials, opening) -> complete / partial / failed
src/simulator/ias16/           Depreciation engine (prospective change in estimate), rounding reconciliation
src/simulator/journal/         Journal entries (debit = credit check)
src/simulator/statements/      Opening position check; closing statements built from the journals
src/simulator/ratios/          Ratios with "not meaningful" handling
src/simulator/validation/      Input conversion, input checks, integrity checks (never plug)
src/simulator/references.py    Standard references with verification status
data/sample_inputs/            Four fictional sample scenarios (JSON)
docs/                          Methodology, assumptions, test cases, test results
```

Data flows one way: the UI builds inputs, the engine calculates, the presentation layer formats, and the UI displays. The UI never changes a number.

*Educational use only. Accounting treatment depends on the facts and circumstances.*
