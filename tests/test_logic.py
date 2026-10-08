"""Simple tests for qms_logic. Run:  python tests/test_logic.py   (or: pytest)"""

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import qms_logic as logic  # noqa: E402


def load(name):
    with open(ROOT / "data" / name, encoding="utf-8") as f:
        return json.load(f)


def test_complete_case_can_close_and_release():
    case = load("sample_case_complete.json")
    assert logic.deviation_required(case)
    assert logic.closure_blockers(case) == []
    assert logic.deviation_closed(case)
    assert logic.effective_decision(case)[0] == "RELEASE"


def test_capa_can_stay_open_after_closure_and_release():
    case = load("sample_case_complete.json")
    assert logic.capa_status(case) == "Open - actions in progress"


def test_start_case_is_blocked_everywhere():
    case = load("sample_case_start.json")
    assert logic.deviation_required(case)
    assert len(logic.closure_blockers(case)) >= 5
    assert logic.effective_decision(case)[0] == "PENDING"
    current = [r["name"] for r in logic.stage_status(case) if r["state"] == "current"]
    assert current == ["Deviation raised"]


def test_missing_root_cause_blocks_closure():
    case = load("sample_case_complete.json")
    case["investigation"]["root_cause"] = ""
    assert not logic.deviation_closed(case)


def test_qa_not_approved_blocks_closure_and_release():
    case = load("sample_case_complete.json")
    case["qa"]["decision"] = "Pending"
    assert not logic.deviation_closed(case)
    decision, reasons = logic.effective_decision(case)
    assert decision == "HOLD" and any("not closed" in r for r in reasons)


def test_preventive_action_is_required():
    case = load("sample_case_complete.json")
    case["capa"]["actions"] = [a for a in case["capa"]["actions"] if a["type"] != "Preventive"]
    assert not logic.capa_planned(case)
    assert not logic.deviation_closed(case)


def test_failed_retest_blocks_release():
    case = load("sample_case_complete.json")
    case["correction"]["retest_result"] = 0.8
    assert logic.effective_decision(case)[0] == "HOLD"


def test_final_qc_required_for_release():
    case = load("sample_case_complete.json")
    case["release"]["final_qc_passed"] = False
    assert logic.effective_decision(case)[0] == "HOLD"


def test_result_within_limit_needs_no_deviation():
    case = load("sample_case_complete.json")
    case["in_process"]["result"] = 0.3
    assert not logic.deviation_required(case)
    assert logic.closure_blockers(case) == []
    states = {r["name"]: r["state"] for r in logic.stage_status(case)}
    assert states["Deviation raised"] == "na"
    assert logic.capa_status(case) == "Not required"


def test_capa_status_progression():
    case = load("sample_case_complete.json")
    for a in case["capa"]["actions"]:
        a["status"] = "Completed"
    assert logic.capa_status(case) == "Actions done - effectiveness check pending"
    case["effectiveness"]["result"] = "Effective"
    assert logic.capa_status(case) == "Closed - effective"
    case["effectiveness"]["result"] = "Not effective"
    assert logic.capa_status(case) == "Effectiveness failed - reopen CAPA"


def test_reject_and_hold_choices():
    case = load("sample_case_complete.json")
    case["release"]["disposition"] = "Reject"
    assert logic.effective_decision(case)[0] == "REJECT"
    case["release"]["disposition"] = "Hold"
    assert logic.effective_decision(case)[0] == "HOLD"


def test_summary_mentions_key_facts():
    text = logic.build_summary(load("sample_case_complete.json"))
    assert "DEV-2026-007" in text and "Batch decision: RELEASE" in text


def test_data_not_mutated_between_loads():
    a = load("sample_case_complete.json")
    b = copy.deepcopy(a)
    logic.build_summary(a)
    logic.stage_status(a)
    assert a == b


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("ok  ", t.__name__)
    print(f"{len(tests)} tests passed")
