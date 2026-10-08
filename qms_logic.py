"""Plain-Python rules for the QMS workflow demo.

There is no Streamlit in this file, so the rules can be tested with plain
Python (see tests/test_logic.py).

IMPORTANT: this is a teaching model. Real companies write these rules in their
own SOPs, and a real QMS is a validated system. Nothing here is regulatory advice.
"""

CLASSIFICATIONS = ["Not yet classified", "Minor", "Major", "Critical"]
ROOT_CAUSE_CATEGORIES = [
    "Not determined",
    "Procedure / batch record",
    "Equipment",
    "Material / supplier",
    "People / training",
    "Environment",
    "Test method / lab",
]
ACTION_TYPES = ["Corrective", "Preventive"]
ACTION_STATUSES = ["Open", "In progress", "Completed"]
EFFECTIVENESS_RESULTS = ["Pending", "Effective", "Not effective"]
QA_DECISIONS = ["Pending", "Approved", "Rejected / send back"]
DISPOSITIONS = ["Pending", "Release", "Hold", "Reject"]
RM_STATUSES = ["Quarantine", "Approved", "Rejected"]


def _filled(value):
    """True if value is a non-empty string."""
    return isinstance(value, str) and value.strip() != ""


# ---------------------------------------------------------------- in-process
def in_process_ok(case):
    ip = case["in_process"]
    return float(ip["result"]) <= float(ip["limit_max"])


def deviation_required(case):
    """A failed in-process check is a departure from the approved limit."""
    return not in_process_ok(case)


# ----------------------------------------------------------------- deviation
def deviation_raised(case):
    d = case["deviation"]
    text_ok = all(
        _filled(d.get(k))
        for k in ("title", "description", "expected", "observed", "containment")
    )
    return text_ok and d.get("classification") in CLASSIFICATIONS[1:]


def investigation_complete(case):
    items = case["investigation"]["checklist"]
    return len(items) > 0 and all(
        i.get("done") and _filled(i.get("finding")) for i in items
    )


def filled_whys(case):
    return [w for w in case["investigation"]["five_whys"] if _filled(w)]


def root_cause_done(case):
    inv = case["investigation"]
    return (
        _filled(inv.get("root_cause"))
        and inv.get("root_cause_category") not in (None, "", "Not determined")
        and len(filled_whys(case)) >= 3
    )


def impact_done(case):
    imp = case["impact"]
    keys = ("product_quality", "other_batches", "equipment", "customer_patient")
    return all(_filled(imp.get(k)) for k in keys)


def _action_ok(action):
    return all(_filled(action.get(k)) for k in ("action", "owner", "due"))


def capa_planned(case):
    actions = case["capa"]["actions"]
    if not actions or not all(_action_ok(a) for a in actions):
        return False
    types = {a.get("type") for a in actions}
    return {"Corrective", "Preventive"} <= types


def qa_approved(case):
    return case["qa"].get("decision") == "Approved"


def closure_blockers(case):
    """Reasons the deviation cannot be closed yet. Empty list = can close."""
    if not deviation_required(case):
        return []
    reasons = []
    if not deviation_raised(case):
        reasons.append(
            "Deviation record incomplete (description, expected vs observed, "
            "classification, containment)"
        )
    if not investigation_complete(case):
        reasons.append("Investigation checklist not finished (each item needs a finding)")
    if not root_cause_done(case):
        reasons.append(
            "Root cause not documented (need root cause, a category, and at least 3 whys)"
        )
    if not impact_done(case):
        reasons.append("Impact assessment incomplete")
    if not capa_planned(case):
        reasons.append(
            "CAPA plan incomplete (need a corrective AND a preventive action, "
            "each with owner and due date)"
        )
    if not qa_approved(case):
        reasons.append("QA has not approved the investigation")
    return reasons


def deviation_closed(case):
    return len(closure_blockers(case)) == 0


def deviation_label(case):
    if not deviation_required(case):
        return "Not needed"
    return "Closed" if deviation_closed(case) else "Open"


# ---------------------------------------------------------------------- CAPA
def capa_status(case):
    """CAPA is tracked separately: it can stay open after the deviation closes."""
    if not deviation_required(case):
        return "Not required"
    if not capa_planned(case):
        return "Not planned yet"
    if case["effectiveness"]["result"] == "Not effective":
        return "Effectiveness failed - reopen CAPA"
    actions = case["capa"]["actions"]
    if not all(a.get("status") == "Completed" for a in actions):
        return "Open - actions in progress"
    if case["effectiveness"]["result"] == "Effective":
        return "Closed - effective"
    return "Actions done - effectiveness check pending"


# ------------------------------------------------------------- batch decision
def retest_ok(case):
    c = case["correction"]
    limit = float(case["in_process"]["limit_max"])
    return bool(c.get("retest_done")) and float(c.get("retest_result", 999)) <= limit


def release_blockers(case):
    reasons = []
    if deviation_required(case):
        if not deviation_closed(case):
            reasons.append("Deviation is not closed yet")
        if not retest_ok(case):
            reasons.append("Retest after correction is missing or still outside the limit")
    if not case["release"].get("final_qc_passed"):
        reasons.append("Final QC testing of the API is not recorded as passing")
    return reasons


def effective_decision(case):
    """Return (decision, reasons). The app never lets 'Release' through if blocked."""
    choice = case["release"].get("disposition", "Pending")
    blockers = release_blockers(case)
    if choice == "Pending":
        return "PENDING", ["QA has not recorded a batch disposition yet"]
    if choice == "Reject":
        return "REJECT", ["QA rejected the batch"]
    if choice == "Hold":
        return "HOLD", ["QA chose to keep the batch on hold"] + blockers
    # choice == "Release"
    if blockers:
        return "HOLD", ["Release was selected but is blocked:"] + blockers
    return "RELEASE", []


# ------------------------------------------------------------ stage tracker
def stage_status(case):
    """List of {'name', 'state'}; state is done / current / todo / na."""
    required = deviation_required(case)
    decision, _ = effective_decision(case)
    rows = [
        ("Raw material approved", case["raw_material"]["qc_status"] == "Approved", True),
        ("Manufacturing complete", bool(case["batch"]["manufacturing_complete"]), True),
        ("In-process check recorded",
         bool(case["batch"]["manufacturing_complete"])
         and case["in_process"].get("result") is not None, True),
        ("Deviation raised", deviation_raised(case), required),
        ("Investigation", investigation_complete(case), required),
        ("Root cause", root_cause_done(case), required),
        ("Impact assessment", impact_done(case), required),
        ("CAPA planned", capa_planned(case), required),
        ("QA review", qa_approved(case), required),
        ("Deviation closed", deviation_closed(case), required),
        ("Batch decision made", decision in ("RELEASE", "REJECT"), True),
    ]
    result = []
    current_set = False
    for name, done, applicable in rows:
        if not applicable:
            state = "na"
        elif done:
            state = "done"
        elif not current_set:
            state = "current"
            current_set = True
        else:
            state = "todo"
        result.append({"name": name, "state": state})
    return result


# ----------------------------------------------------------------- summary
def build_summary(case):
    """Template-based text summary. No AI involved: it only reuses what was typed."""
    b, ip, d = case["batch"], case["in_process"], case["deviation"]
    inv, imp = case["investigation"], case["impact"]
    decision, _ = effective_decision(case)
    lines = [
        f"Batch {b['batch_no']} - {b['product']}",
        f"In-process check: {ip['test']} = {ip['result']} (limit not more than {ip['limit_max']})",
    ]
    if not deviation_required(case):
        lines.append("Result within limit - no deviation raised.")
    else:
        lines += [
            f"Deviation {d.get('id', '')}: {d.get('title', '')} [{d.get('classification', '')}]",
            f"Expected: {d.get('expected', '')}",
            f"Observed: {d.get('observed', '')}",
            f"Containment: {d.get('containment', '')}",
            f"Root cause ({inv.get('root_cause_category', '')}): {inv.get('root_cause', '')}",
            f"Product impact: {imp.get('product_quality', '')}",
        ]
        for n, a in enumerate(case["capa"]["actions"], start=1):
            lines.append(
                f"CAPA {n} [{a.get('type')}, {a.get('status')}]: {a.get('action')} "
                f"(owner: {a.get('owner')}, due {a.get('due')})"
            )
        lines.append(f"Effectiveness check: {case['effectiveness']['result']}")
        lines.append(f"QA decision: {case['qa'].get('decision')}")
        lines.append(f"Deviation status: {deviation_label(case)}; CAPA status: {capa_status(case)}")
    lines.append(f"Batch decision: {decision}")
    return "\n".join(lines)
