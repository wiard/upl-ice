from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
CONFIGS = ROOT / "configs"
WITNESSES = ROOT / "witnesses"
RESULTS = ROOT / "results"

CLAIM_ID = "K_agent_handoff_payment_release"
CLAIM_TEXT = (
    "Agent A may delegate bounded task S to Agent B and release mock payment P only if mandate, budget, "
    "policy, quote, result, and trace conditions are checked under boundary B."
)
JUDGMENT_FORM = (
    "Gamma_WARP-P1 ⊢ K_agent_handoff_payment_release @ B_demo_WARP_01 "
    "⇐ W_demo_WARP_01 : sigma"
)

PAYMENT_ACTION_MAP = {
    "checked": "mock_payment_release_allowed",
    "bounded": "human_approval_required",
    "pending_check": "mock_payment_hold",
    "incomplete": "deny",
    "unsupported": "deny",
    "failed": "deny",
    "contradicted": "deny",
    "inconclusive": "hold_or_deny",
    "out_of_scope": "deny",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_json(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def witness_record(witness_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    record = {
        "witness_id": witness_id,
        "created_at_utc": utc_now(),
        "payload": payload,
    }
    record["content_hash"] = sha256_json(record)
    return record


def summarize_local_text(content: str) -> str:
    return "This is a bounded local demo result produced by agent_B."


def choose_status(*, boundary: dict[str, Any], quote_ok: bool, agent_ok: bool, capability_ok: bool, task_allowed: bool,
                  task_forbidden: bool, mandate_ok: bool, result_ok: bool, witnesses_present: bool) -> str:
    if boundary["real_payment"] is True or boundary["payment_mode"] != "mock_ledger_only" or boundary["network_access"] != "forbidden":
        return "contradicted" if boundary["real_payment"] is True else "out_of_scope"
    if not witnesses_present:
        return "incomplete"
    if not mandate_ok:
        return "unsupported"
    if task_forbidden:
        return "contradicted"
    if not task_allowed or not agent_ok or not capability_ok or not quote_ok:
        return "failed"
    if not result_ok:
        return "pending_check"
    return "checked"


def main() -> None:
    boundary = load_json(CONFIGS / "boundary.json")
    policy = load_json(CONFIGS / "policy.json")
    agents = load_json(CONFIGS / "agents.json")
    mandate = load_json(CONFIGS / "mandate.json")

    WITNESSES.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)

    trace_lines = ["demo_WARP_01 start"]

    agent_registry = {agent["agent_id"]: agent for agent in agents["agents"]}
    from_agent = agent_registry.get("agent_A")
    to_agent = agent_registry.get("agent_B")

    task = {
        "task_id": "task_demo_bounded_analysis",
        "task_type": "bounded_analysis",
        "content": "Summarize a harmless local demo string in one sentence.",
        "expected_result_type": "short_text",
    }

    result_text = summarize_local_text(task["content"])
    result_ok = bool(result_text) and len(result_text) <= 300

    mandate_ok = bool(mandate.get("mandate_id")) and mandate.get("payment_mode") == "mock_ledger_only"
    allowed_agents = set(boundary["allowed_agents"])
    allowed_tasks = set(boundary["allowed_task_types"])
    forbidden_tasks = set(boundary["forbidden_task_types"])

    agent_ok = bool(to_agent) and to_agent["agent_id"] in allowed_agents
    capability_ok = bool(to_agent) and task["task_type"] in set(to_agent.get("capabilities", []))
    task_allowed = task["task_type"] in allowed_tasks and mandate["allowed_task_type"] == task["task_type"]
    task_forbidden = task["task_type"] in forbidden_tasks

    quote = to_agent["price_quote"]
    quote_ok = (
        quote["currency"] == boundary["currency"]
        and quote["amount"] <= boundary["max_single_payment"]
        and quote["amount"] <= boundary["max_total_budget"]
        and quote["amount"] <= mandate["single_payment_limit"]
        and quote["amount"] <= mandate["budget_limit"]
    )

    witness_payloads = {
        "mandate.json": witness_record("W_mandate", {
            "mandate_id": mandate["mandate_id"],
            "allowed_task_type": mandate["allowed_task_type"],
            "budget_limit": mandate["budget_limit"],
            "single_payment_limit": mandate["single_payment_limit"],
            "payment_mode": mandate["payment_mode"],
            "signature": mandate["signature"],
        }),
        "route.json": witness_record("W_route", {
            "from_agent": from_agent["agent_id"],
            "to_agent": to_agent["agent_id"],
            "task_type": task["task_type"],
            "allowed_to_delegate": from_agent["allowed_to_delegate"],
            "agent_registry_entry": to_agent,
            "capability_match": capability_ok,
        }),
        "quote.json": witness_record("W_quote", {
            "quote_id": quote["quote_id"],
            "amount": quote["amount"],
            "currency": quote["currency"],
            "max_single_payment": boundary["max_single_payment"],
            "max_total_budget": boundary["max_total_budget"],
            "within_budget": quote_ok,
        }),
        "contract.json": witness_record("W_contract", {
            "required_output_type": task["expected_result_type"],
            "result_constraints": {
                "max_characters": 300,
                "must_be_present": True,
            },
            "forbidden_actions": boundary["forbidden_task_types"],
            "payment_release_condition": "status == checked",
        }),
        "check.json": witness_record("W_check", {
            "policy_id": policy["policy_id"],
            "rules": [
                {"rule_id": "R1_mandate_required", "pass": mandate_ok},
                {"rule_id": "R2_budget_limit", "pass": quote_ok},
                {"rule_id": "R3_allowed_agent", "pass": agent_ok},
                {"rule_id": "R4_allowed_task", "pass": task_allowed and not task_forbidden and capability_ok},
                {"rule_id": "R5_result_required", "pass": result_ok},
                {"rule_id": "R6_trace_required", "pass": True},
                {"rule_id": "R7_mock_only", "pass": boundary["payment_mode"] == "mock_ledger_only" and boundary["real_payment"] is False},
            ],
            "result_text": result_text,
        }),
        "ruleout.json": witness_record("W_ruleout", {
            "no_real_payment": boundary["real_payment"] is False,
            "no_network": boundary["network_access"] == "forbidden",
            "no_credentials": True,
            "no_forbidden_task": not task_forbidden,
            "no_over_budget_quote": quote_ok,
            "no_unapproved_agent": agent_ok,
            "no_missing_result": result_ok,
        }),
    }

    for filename, payload in witness_payloads.items():
        write_json(WITNESSES / filename, payload)

    required_witness_paths = [
        WITNESSES / "mandate.json",
        WITNESSES / "route.json",
        WITNESSES / "quote.json",
        WITNESSES / "contract.json",
        WITNESSES / "check.json",
        WITNESSES / "ruleout.json",
    ]
    witnesses_present = all(path.exists() for path in required_witness_paths)

    status = choose_status(
        boundary=boundary,
        quote_ok=quote_ok,
        agent_ok=agent_ok,
        capability_ok=capability_ok,
        task_allowed=task_allowed,
        task_forbidden=task_forbidden,
        mandate_ok=mandate_ok,
        result_ok=result_ok,
        witnesses_present=witnesses_present,
    )
    payment_action = PAYMENT_ACTION_MAP[status]

    judgment = {
        "upl_namespace": "UPL-WARP",
        "profile": "WARP-P1",
        "claim_id": CLAIM_ID,
        "claim": CLAIM_TEXT,
        "boundary_id": boundary["boundary_id"],
        "judgment_form": JUDGMENT_FORM,
        "witnesses": {
            "mandate": "witnesses/mandate.json",
            "route": "witnesses/route.json",
            "quote": "witnesses/quote.json",
            "contract": "witnesses/contract.json",
            "check": "witnesses/check.json",
            "ruleout": "witnesses/ruleout.json"
        },
        "status": status,
        "payment_action": payment_action,
        "allowed_claims": [
            "agent_A may delegate the bounded local task to agent_B under B",
            "mock payment may be released if status is checked",
            "the run produced a warranted local mock ledger event"
        ],
        "forbidden_claims": [
            "real payment was made",
            "agent_B is generally trustworthy",
            "the user authorized future payments",
            "the result is legally or financially valid",
            "the claim generalizes beyond B",
            "UPL-WARP is a payment processor"
        ]
    }

    mock_ledger = {
        "ledger_type": "mock_only",
        "real_payment": False,
        "entries": [
            {
                "entry_id": "ledger_demo_001",
                "from": "local_demo_user_mock_balance",
                "to": "agent_B_mock_balance",
                "amount": quote["amount"],
                "currency": quote["currency"],
                "payment_action": "released" if payment_action == "mock_payment_release_allowed" else payment_action,
                "linked_judgment": "results/judgment.json"
            }
        ]
    }

    summary = {
        "claim_id": CLAIM_ID,
        "status": status,
        "payment_action": payment_action,
        "from_agent": from_agent["agent_id"],
        "to_agent": to_agent["agent_id"],
        "task_type": task["task_type"],
        "quote_amount": quote["amount"],
        "quote_currency": quote["currency"],
    }

    trace_lines.extend([
        f"status={status}",
        f"payment_action={payment_action}",
        f"agent_ok={agent_ok}",
        f"capability_ok={capability_ok}",
        f"quote_ok={quote_ok}",
        f"result_ok={result_ok}",
    ])

    write_json(RESULTS / "judgment.json", judgment)
    write_json(RESULTS / "mock_ledger.json", mock_ledger)
    write_json(RESULTS / "summary.json", summary)
    (RESULTS / "trace.log").write_text("\n".join(trace_lines) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
