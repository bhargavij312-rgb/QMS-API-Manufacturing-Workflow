# QMS-API-Manufacturing-Workflow

A small Streamlit demo that follows **one fictional API batch** through a quality-management workflow:

`Raw material → Manufacturing → In-process check → Deviation → Investigation → Root cause → CAPA → QA review → Batch decision`

> **This is a learning prototype, not a validated pharmaceutical QMS.** All names, numbers and limits are fictional. It has no audit trail, electronic signatures, user roles or validation, and it makes no regulatory-compliance claims. No AI is used anywhere (the "case summary" is plain template text).

I built it to understand how the pieces of a QMS connect, as part of a product-understanding exercise.

## The example

Batch **API-2026-014** of a fictional API ("Veridexol"). After the drying step, the in-process loss-on-drying (LOD) test gives **0.9%** against a batch-record limit of **not more than 0.5%** (illustrative numbers). That is a deviation. The app walks through containment, investigation, 5 Whys, root cause, impact assessment, correction, corrective and preventive actions, effectiveness check, QA review, and the batch decision.

## What it demonstrates

- A failed in-process check forces a deviation record (expected vs observed, classification, containment).
- Investigation needs a finding for every checklist item, a root cause and at least three "whys".
- **Correction** (fix this batch) vs **corrective action** (remove the cause) vs **preventive action** (stop it elsewhere).
- A deviation can only be **closed** when the record, investigation, root cause, impact assessment, CAPA plan and QA approval are all present. The app lists what is missing.
- CAPA is tracked separately and can stay open after the deviation closes, until its effectiveness check is done.
- The app will not show **RELEASE** unless the deviation is closed, the retest is within limit, and final QC passes. Otherwise it shows **HOLD**.

## Folder structure

```
QMS-API-Manufacturing-Workflow/
├── app.py                      # Streamlit UI
├── qms_logic.py                # workflow rules (plain Python, testable)
├── data/
│   ├── sample_case_start.json      # story starts at the failed check
│   └── sample_case_complete.json   # fully worked example
├── tests/test_logic.py         # simple tests for the rules
├── requirements.txt
├── .gitignore
└── README.md
```

## Run it (VS Code)

1. Install Python 3.9+ and open this folder in VS Code (`File → Open Folder`).
2. Open a terminal (`Terminal → New Terminal`) and create a virtual environment:
   - Windows: `python -m venv .venv` then `.venv\Scripts\activate`
   - macOS/Linux: `python3 -m venv .venv` then `source .venv/bin/activate`
3. `pip install -r requirements.txt`
4. `streamlit run app.py` (if the command is not found, use `python -m streamlit run app.py`)
5. Your browser opens at `http://localhost:8501`.

Run the tests (no Streamlit needed): `python tests/test_logic.py`

## How to use the demo

1. Pick **"1) Start"** in the sidebar and click *Load / reset this sample*.
2. Tab 1: see the failed in-process check. Tab 2: classify the deviation and add containment.
3. Tab 3: tick each checklist item and write a finding, fill the whys and the root cause.
4. Tab 4: describe the correction, enter the retest result, add corrective and preventive actions.
5. Tab 5: record QA approval and watch the "can it be closed?" list shrink.
6. Tab 6: tick final QC and choose a disposition. Try choosing *Release* too early.

Load **"2) Fully worked case"** to see a finished example.

## Suggested README screenshots

1. Tab 1 with the red out-of-limit message and the sidebar progress tracker.
2. Tab 2 with the completed deviation record.
3. Tab 3 showing the 5 Whys and root cause.
4. Tab 4 showing the CAPA table and the CAPA status.
5. Tab 5 showing the red "Not yet. Missing:" list.
6. Tab 6 showing a blocked release (HOLD) and then a successful RELEASE.

## Limitations and ideas for next steps

- Single user, no login, no roles. Data lives in the browser session (you can download or save JSON).
- No audit trail or e-signatures. A natural next step is a simple event log (who changed what, when).
- Classification rules are free choices, not tied to any real SOP.
- Ideas: SQLite storage, multiple deviations per batch, a trend chart of root-cause categories, change control.

## Upload to GitHub

```bash
git init
git add .
git commit -m "Add QMS API manufacturing workflow demo"
git branch -M main
git remote add origin https://github.com/<your-username>/QMS-API-Manufacturing-Workflow.git
git push -u origin main
```

Create the empty repository on github.com first (no README, since this folder already has one).

**Suggested topics:** `streamlit`, `python`, `quality-management-system`, `pharmaceutical`, `capa`

## Disclaimer

Educational project. Not a GxP system, not validated, not regulatory advice.
