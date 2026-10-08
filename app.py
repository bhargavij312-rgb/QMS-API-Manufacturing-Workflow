"""QMS-API-Manufacturing-Workflow

A small teaching prototype that follows ONE fictional API batch through:
raw material -> manufacturing -> in-process check -> deviation -> investigation
-> root cause -> CAPA -> QA review -> batch decision.

It is NOT a validated pharmaceutical QMS. All names, numbers and limits are fictional.
Run with:  streamlit run app.py
"""

import json
from datetime import date
from pathlib import Path

import streamlit as st

import qms_logic as logic

DATA_DIR = Path(__file__).parent / "data"
SAMPLES = {
    "1) Start: in-process check just failed": "sample_case_start.json",
    "2) Fully worked case (for reference)": "sample_case_complete.json",
}

st.set_page_config(page_title="QMS workflow demo - API batch", layout="wide")


# ------------------------------------------------------------------ helpers
def load_case(label):
    """Load a sample into session state. A new case_id gives all widgets fresh keys."""
    with open(DATA_DIR / SAMPLES[label], encoding="utf-8") as f:
        st.session_state["case"] = json.load(f)
    st.session_state["case_id"] = st.session_state.get("case_id", 0) + 1


def _initial(kind, value, options):
    if kind in ("text", "area"):
        return value or ""
    if kind == "select":
        return value if value in options else options[0]
    if kind == "check":
        return bool(value)
    if kind == "number":
        return float(value) if value is not None else 0.0
    if kind == "date":
        try:
            return date.fromisoformat(value)
        except (TypeError, ValueError):
            return date.today()
    raise ValueError(kind)


def bind(kind, label, store, name, prefix, options=None, **kw):
    """Show one widget and write its value back into store[name].

    The widget key includes case_id, so loading a new sample resets every field.
    """
    key = f"{st.session_state['case_id']}:{prefix}:{name}"
    if key not in st.session_state:
        st.session_state[key] = _initial(kind, store.get(name), options)
    if kind == "text":
        value = st.text_input(label, key=key, **kw)
    elif kind == "area":
        value = st.text_area(label, key=key, height=100, **kw)
    elif kind == "select":
        value = st.selectbox(label, options, key=key, **kw)
    elif kind == "check":
        value = st.checkbox(label, key=key, **kw)
    elif kind == "number":
        value = st.number_input(label, key=key, min_value=0.0, step=0.05, format="%.2f", **kw)
    else:  # date
        value = st.date_input(label, key=key, **kw)
    store[name] = value.isoformat() if kind == "date" else value
    return value


def drop_keys(prefix):
    """Forget widget state for a removed row so a re-added row starts empty."""
    full = f"{st.session_state['case_id']}:{prefix}:"
    for k in list(st.session_state.keys()):
        if isinstance(k, str) and k.startswith(full):
            del st.session_state[k]


def not_needed_message():
    st.info(
        "The in-process result is within the limit, so no deviation is needed. "
        "Go to tab 1 and set the result to 0.9 to see the deviation workflow."
    )


# --------------------------------------------------------------------- setup
if "case" not in st.session_state:
    load_case(list(SAMPLES)[0])

with st.sidebar:
    st.header("Case")
    choice = st.selectbox("Sample case", list(SAMPLES), key="sample_choice")
    if st.button("Load / reset this sample"):
        load_case(choice)
        st.rerun()

case = st.session_state["case"]

st.title("QMS workflow demo: one API batch, raw material to batch decision")
st.caption(
    "Teaching prototype, NOT a validated pharmaceutical QMS. "
    "All names, numbers and limits are fictional. No AI is used."
)
summary = st.container()  # filled at the end, once all edits are known

tabs = st.tabs([
    "1 Batch & checks",
    "2 Deviation",
    "3 Investigation & RCA",
    "4 Correction & CAPA",
    "5 QA review & closure",
    "6 Batch decision",
    "7 Beyond the batch",
])

# ------------------------------------------------------------ tab 1: batch
with tabs[0]:
    st.subheader("Batch information")
    left, right = st.columns(2)
    with left:
        bind("text", "Batch number", case["batch"], "batch_no", "batch")
        bind("text", "Product (fictional API)", case["batch"], "product", "batch")
        bind("check", "Manufacturing steps completed", case["batch"],
             "manufacturing_complete", "batch")
    with right:
        st.markdown("**Manufacturing steps (generic)**")
        for n, step in enumerate(case["batch"]["steps"], start=1):
            st.write(f"{n}. {step}")

    st.subheader("Raw material (API starting material)")
    c1, c2, c3 = st.columns(3)
    with c1:
        bind("text", "Material", case["raw_material"], "name", "rm")
        bind("text", "Lot number", case["raw_material"], "lot", "rm")
    with c2:
        bind("text", "Supplier", case["raw_material"], "supplier", "rm")
        bind("check", "Supplier CoA received", case["raw_material"], "coa_received", "rm")
    with c3:
        bind("select", "QC / QA status", case["raw_material"], "qc_status", "rm",
             options=logic.RM_STATUSES)
    if case["raw_material"]["qc_status"] != "Approved":
        st.warning("Material must be approved by QC/QA before it is used in manufacturing.")

    st.subheader("In-process check")
    ip = case["in_process"]
    c1, c2, c3 = st.columns(3)
    with c1:
        bind("text", "Test", ip, "test", "ip")
    with c2:
        bind("number", f"Limit: not more than ({ip['unit']})", ip, "limit_max", "ip")
    with c3:
        bind("number", "Result", ip, "result", "ip")
    if logic.in_process_ok(case):
        st.success("Result is within the limit. The batch can move on.")
    else:
        st.error("Result is OUT of limit. This is a departure from the approved "
                 "instruction, so a deviation must be raised (tab 2).")

# ----------------------------------------------------------- tab 2: deviation
with tabs[1]:
    if not logic.deviation_required(case):
        not_needed_message()
    else:
        d = case["deviation"]
        st.subheader("Deviation record")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            bind("text", "Deviation ID", d, "id", "dev")
        with c2:
            bind("date", "Date detected", d, "date_detected", "dev")
        with c3:
            bind("text", "Detected by", d, "detected_by", "dev")
        with c4:
            bind("text", "Area / equipment", d, "area", "dev")
        bind("text", "Title", d, "title", "dev")
        bind("area", "What happened?", d, "description", "dev")
        c1, c2 = st.columns(2)
        with c1:
            bind("area", "What was expected?", d, "expected", "dev")
        with c2:
            bind("area", "What was actually observed?", d, "observed", "dev")
        c1, c2 = st.columns([1, 3])
        with c1:
            bind("select", "Classification", d, "classification", "dev",
                 options=logic.CLASSIFICATIONS)
        with c2:
            bind("area", "Why this classification? (follow your company SOP)", d,
                 "classification_rationale", "dev")
        bind("area", "Immediate action / containment", d, "containment", "dev",
             help="What was done at once so the problem cannot spread?")
        if logic.deviation_raised(case):
            st.success("Deviation record is complete. Move on to the investigation.")
        else:
            st.warning("Still missing: text fields and/or a classification.")

# ------------------------------------------------------ tab 3: investigation
with tabs[2]:
    if not logic.deviation_required(case):
        not_needed_message()
    else:
        inv = case["investigation"]
        st.subheader("Investigation checklist: what evidence was checked?")
        for i, item in enumerate(inv["checklist"]):
            c1, c2 = st.columns([2, 3])
            with c1:
                bind("check", item["item"], item, "done", f"chk{i}")
            with c2:
                bind("text", "Finding", item, "finding", f"chk{i}",
                     label_visibility="collapsed", placeholder="What did you find?")

        st.subheader("5 Whys (use as many as you need, at least 3)")
        st.caption("The first obvious cause is rarely the root cause. Keep asking why.")
        whys = inv["five_whys"]
        for i in range(len(whys)):
            key = f"{st.session_state['case_id']}:why:{i}"
            if key not in st.session_state:
                st.session_state[key] = whys[i] or ""
            whys[i] = st.text_input(f"Why {i + 1}?", key=key)

        st.subheader("Root cause")
        bind("area", "Root cause statement", inv, "root_cause", "rca")
        bind("select", "Root cause category", inv, "root_cause_category", "rca",
             options=logic.ROOT_CAUSE_CATEGORIES)

        st.subheader("Impact assessment")
        imp = case["impact"]
        c1, c2 = st.columns(2)
        with c1:
            bind("area", "Impact on this batch / product quality", imp, "product_quality", "imp")
            bind("area", "Impact on equipment / systems", imp, "equipment", "imp")
        with c2:
            bind("area", "Could other batches or products be affected?", imp,
                 "other_batches", "imp")
            bind("area", "Impact on customer / patient", imp, "customer_patient", "imp")

        if logic.root_cause_done(case) and logic.investigation_complete(case):
            st.success("Investigation and root cause are documented.")

# --------------------------------------------------------------- tab 4: CAPA
with tabs[3]:
    if not logic.deviation_required(case):
        not_needed_message()
    else:
        corr = case["correction"]
        st.subheader("Correction: fix THIS batch")
        bind("area", "Correction action", corr, "action", "corr")
        c1, c2 = st.columns(2)
        with c1:
            bind("check", "Retest done", corr, "retest_done", "corr")
        with c2:
            if corr["retest_done"]:
                bind("number", "Retest result", corr, "retest_result", "corr")
        if corr["retest_done"]:
            if logic.retest_ok(case):
                st.success("Retest is within the limit.")
            else:
                st.error("Retest is still outside the limit.")

        st.subheader(f"CAPA plan ({case['capa']['capa_id']})")
        st.caption("Corrective = remove the cause of this problem. "
                   "Preventive = stop similar problems elsewhere.")
        actions = case["capa"]["actions"]
        for i, action in enumerate(actions):
            c1, c2, c3, c4, c5 = st.columns([1.2, 3, 1.5, 1.3, 1.3])
            with c1:
                bind("select", "Type", action, "type", f"capa{i}", options=logic.ACTION_TYPES)
            with c2:
                bind("text", "Action", action, "action", f"capa{i}")
            with c3:
                bind("text", "Owner", action, "owner", f"capa{i}")
            with c4:
                bind("date", "Due", action, "due", f"capa{i}")
            with c5:
                bind("select", "Status", action, "status", f"capa{i}",
                     options=logic.ACTION_STATUSES)
        b1, b2, _ = st.columns([1, 1, 4])
        if b1.button("Add action"):
            actions.append({"type": "Corrective", "action": "", "owner": "",
                            "due": date.today().isoformat(), "status": "Open"})
            st.rerun()
        if b2.button("Remove last action") and actions:
            actions.pop()
            drop_keys(f"capa{len(actions)}")
            st.rerun()

        st.subheader("Effectiveness check")
        eff = case["effectiveness"]
        bind("area", "How and when will we check the fix worked?", eff, "plan", "eff")
        bind("select", "Effectiveness result", eff, "result", "eff",
             options=logic.EFFECTIVENESS_RESULTS)
        st.write(f"**CAPA status:** {logic.capa_status(case)}")

# --------------------------------------------------------------- tab 5: QA
with tabs[4]:
    if not logic.deviation_required(case):
        not_needed_message()
    else:
        qa = case["qa"]
        st.subheader("QA review")
        c1, c2 = st.columns(2)
        with c1:
            bind("text", "QA reviewer", qa, "reviewer", "qa")
        with c2:
            bind("select", "QA decision on the investigation", qa, "decision", "qa",
                 options=logic.QA_DECISIONS)
        bind("area", "QA comments", qa, "comments", "qa")

        st.subheader("Can the deviation be closed?")
        blockers = logic.closure_blockers(case)
        if blockers:
            st.error("Not yet. Missing:")
            for reason in blockers:
                st.write(f"- {reason}")
        else:
            st.success("Deviation can be closed. The CAPA is tracked separately and may "
                       "stay open until its effectiveness check is done.")

        st.subheader("Case summary (template text, no AI)")
        st.code(logic.build_summary(case), language="text")

# ---------------------------------------------------------- tab 6: decision
with tabs[5]:
    st.subheader("Batch decision")
    rel = case["release"]
    bind("check", "Final QC testing of the API meets specification (fictional)", rel,
         "final_qc_passed", "rel")
    bind("select", "QA batch disposition", rel, "disposition", "rel",
         options=logic.DISPOSITIONS)
    bind("area", "QA comments", rel, "comments", "rel")

    decision, reasons = logic.effective_decision(case)
    if decision == "RELEASE":
        st.success("BATCH DECISION: RELEASE")
    elif decision == "REJECT":
        st.error("BATCH DECISION: REJECT")
    else:
        st.warning(f"BATCH DECISION: {decision}")
    for reason in reasons:
        st.write(f"- {reason}")
    st.caption("In real life the quality unit decides release. Here the app only "
               "blocks a release that its simple rules do not support.")

# ------------------------------------------------------- tab 7: beyond batch
with tabs[6]:
    st.subheader("What happens after the batch leaves the plant?")
    with st.expander("Complaint"):
        st.write("A report that something is wrong with the product, for example the "
                 "customer says our API powder is clumpy. It is logged, investigated and "
                 "traced to the batch number, which leads back to records like DEV-2026-007.")
    with st.expander("Adverse event"):
        st.write("A medical event in a patient who took a medicine. It is handled mainly "
                 "by pharmacovigilance at the drug company. If it points to a quality "
                 "problem, it feeds back into complaint and deviation investigations.")
    with st.expander("Recall"):
        st.write("Pulling product back from the market. It depends on the health risk and "
                 "on whether other shipped batches share the same cause.")
    with st.expander("Supplier quality"):
        st.write("If the root cause had been the starting material, the supplier would be "
                 "asked to investigate too. Suppliers are qualified, audited and covered by "
                 "a quality agreement.")
    st.info("This demo is a learning tool. It does not cover change control, audit "
            "trails, electronic signatures, user roles or validation.")

# ------------------------------------------------- top summary and sidebar
with summary:
    decision, _ = logic.effective_decision(case)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Batch", case["batch"]["batch_no"])
    m2.metric("Deviation", logic.deviation_label(case))
    m3.metric("CAPA", logic.capa_status(case))
    m4.metric("Batch decision", decision)

with st.sidebar:
    st.divider()
    st.subheader("Workflow progress")
    icons = {"done": "✅", "current": "👉", "todo": "⬜", "na": "➖"}
    for row in logic.stage_status(case):
        st.write(f"{icons[row['state']]} {row['name']}")
    st.divider()
    st.download_button(
        "Download case as JSON",
        data=json.dumps(case, indent=2),
        file_name=f"{case['batch']['batch_no']}_case.json",
        mime="application/json",
    )
    if st.button("Save a copy to data/saved_case.json"):
        try:
            with open(DATA_DIR / "saved_case.json", "w", encoding="utf-8") as f:
                json.dump(case, f, indent=2)
            st.success("Saved.")
        except OSError as err:
            st.error(f"Could not save: {err}")
