from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .atomgate import apply_atomgate
from .pact_log import append_event, load_events
from .upl_checkout import adjudicate_basket_checkout


MODULE_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = MODULE_ROOT / "data"
LOG_DIR = MODULE_ROOT / "log"
RECEIPTS_DIR = MODULE_ROOT / "receipts"
PACT_LOG_PATH = LOG_DIR / "pact_events.jsonl"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def data_paths() -> tuple[Path, Path, Path]:
    return DATA_DIR / "avatars.json", DATA_DIR / "workcards.json", DATA_DIR / "baskets.json"


def seed_payloads() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    avatars = {
        "avatars": [
            {"avatar_id": "buyer_agent", "namespace": "airmarket", "world": "agentic_marketplace", "role": "buyer"},
            {"avatar_id": "summary_agent", "namespace": "airmarket", "world": "agentic_marketplace", "role": "seller"},
            {"avatar_id": "clause_agent", "namespace": "airmarket", "world": "agentic_marketplace", "role": "seller"},
            {"avatar_id": "vasen_vof", "namespace": "kvk", "world": "nl_business_registry", "role": "principal"},
        ],
        "mandate_links": [
            {
                "link_id": "mandatelink_buyer_vasen_001",
                "source_avatar": "buyer_agent",
                "target_avatar": "vasen_vof",
                "status": "active",
                "principal_depth": 1,
                "principal": {"namespace": "kvk", "world": "nl_business_registry", "avatar": "vasen_vof"},
            },
            {
                "link_id": "mandatelink_summary_vasen_001",
                "source_avatar": "summary_agent",
                "target_avatar": "vasen_vof",
                "status": "active",
                "principal_depth": 1,
                "principal": {"namespace": "kvk", "world": "nl_business_registry", "avatar": "vasen_vof"},
            },
            {
                "link_id": "mandatelink_clause_vasen_001",
                "source_avatar": "clause_agent",
                "target_avatar": "vasen_vof",
                "status": "active",
                "principal_depth": 1,
                "principal": {"namespace": "kvk", "world": "nl_business_registry", "avatar": "vasen_vof"},
            },
        ],
    }
    workcards = {
        "workcards": [
            {
                "workcard_id": "workcard_summary_001",
                "seller_avatar": "summary_agent",
                "task_type": "document_summary",
                "price": {"amount": 0.12, "currency": "EUR"},
                "output_contract": {"format": "markdown", "max_words": 120},
            },
            {
                "workcard_id": "workcard_clause_001",
                "seller_avatar": "clause_agent",
                "task_type": "clause_extraction",
                "price": {"amount": 0.18, "currency": "EUR"},
                "output_contract": {
                    "format": "json",
                    "required_fields": ["clause_id", "summary", "risk_label"],
                },
            },
        ]
    }
    baskets = {"baskets": []}
    return avatars, workcards, baskets


def seed() -> dict[str, Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)
    avatars, workcards, baskets = seed_payloads()
    write_state(avatars, workcards, baskets)
    PACT_LOG_PATH.write_text("", encoding="utf-8")
    append_pact_event(
        event_type="seed_initialized",
        avatar="buyer_agent",
        transition={"type": "seed_initialized"},
        claim="seed_initialized_under_terms",
        status="checked",
        action="no_action",
    )
    return {"avatars": len(avatars["avatars"]), "workcards": len(workcards["workcards"]), "baskets": 0}


def load_state() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    avatars_path, workcards_path, baskets_path = data_paths()
    return load_json(avatars_path), load_json(workcards_path), load_json(baskets_path)


def write_state(avatars: dict[str, Any], workcards: dict[str, Any], baskets: dict[str, Any]) -> None:
    avatars_path, workcards_path, baskets_path = data_paths()
    write_json(avatars_path, avatars)
    write_json(workcards_path, workcards)
    write_json(baskets_path, baskets)


def append_pact_event(*, event_type: str, avatar: str, transition: dict[str, Any], claim: str, status: str, action: str) -> None:
    events = load_events(PACT_LOG_PATH)
    event = {
        "event_id": f"evt_{len(events) + 1:04d}",
        "sequence": len(events) + 1,
        "application": "SkyBasket",
        "namespace": "airmarket",
        "world": "agentic_marketplace",
        "avatar": avatar,
        "principal": {
            "namespace": "kvk",
            "world": "nl_business_registry",
            "avatar": "vasen_vof",
        },
        "transition": transition | {"event_type": event_type},
        "upl": {
            "claim": claim,
            "status": status,
        },
        "atomgate": {
            "policy": "pi: Sigma -> Actions",
            "action": action,
            "real_payment_executed": False,
        },
        "timestamp_utc": utc_now(),
    }
    append_event(PACT_LOG_PATH, event)


def list_workcards() -> list[dict[str, Any]]:
    _, workcards, _ = load_state()
    return workcards["workcards"]


def get_avatar(avatars: dict[str, Any], avatar_id: str) -> dict[str, Any]:
    for avatar in avatars["avatars"]:
        if avatar["avatar_id"] == avatar_id:
            return avatar
    raise KeyError(f"Unknown avatar: {avatar_id}")


def get_workcard(workcards: dict[str, Any], workcard_id: str) -> dict[str, Any] | None:
    for workcard in workcards["workcards"]:
        if workcard["workcard_id"] == workcard_id:
            return workcard
    return None


def get_basket(baskets: dict[str, Any], basket_id: str) -> dict[str, Any] | None:
    for basket in baskets["baskets"]:
        if basket["basket_id"] == basket_id:
            return basket
    return None


def create_basket() -> dict[str, Any]:
    avatars, workcards, baskets = load_state()
    if get_basket(baskets, "basket_001") is not None:
        return get_basket(baskets, "basket_001")  # type: ignore[return-value]
    basket = {
        "basket_id": "basket_001",
        "buyer_avatar": "buyer_agent",
        "buyer_mandate": {
            "principal_avatar": "vasen_vof",
            "allowed_task_types": ["document_summary", "clause_extraction"],
            "allowed_sellers": ["summary_agent", "clause_agent"],
            "max_total_price": {"amount": 0.40, "currency": "EUR"},
            "required_principal_depth": 1,
        },
        "items": [
            {
                "workcard_id": "workcard_summary_001",
                "seller_avatar": "summary_agent",
                "task_id": "task_summary_001",
            },
            {
                "workcard_id": "workcard_clause_001",
                "seller_avatar": "clause_agent",
                "task_id": "task_clause_001",
            },
        ],
        "status": "created",
    }
    baskets["baskets"].append(basket)
    write_state(avatars, workcards, baskets)
    append_pact_event(
        event_type="basket_created",
        avatar="buyer_agent",
        transition={"type": "basket_created", "basket_id": "basket_001"},
        claim="basket_001_created_under_terms",
        status="checked",
        action="no_action",
    )
    return basket


def build_proofpack(workcard_id: str) -> dict[str, Any]:
    if workcard_id == "workcard_summary_001":
        return {
            "proofpack_id": "proofpack_workcard_summary_001",
            "result_declared_complete": True,
            "output": {
                "format": "markdown",
                "word_count": 87,
                "content_digest": "digest_summary_001",
            },
        }
    return {
        "proofpack_id": "proofpack_workcard_clause_001",
        "result_declared_complete": True,
        "output": {
            "format": "json",
            "payload": {
                "clause_id": "clause_001",
                "summary": "Payment term summarized.",
                "risk_label": "low",
            },
            "content_digest": "digest_clause_001",
        },
    }


def deliver_all(basket_id: str) -> dict[str, Any]:
    avatars, workcards, baskets = load_state()
    basket = get_basket(baskets, basket_id)
    if basket is None:
        raise KeyError(f"Unknown basket: {basket_id}")
    for item in basket["items"]:
        item["proofpack"] = build_proofpack(item["workcard_id"])
    basket["status"] = "delivered"
    write_state(avatars, workcards, baskets)
    append_pact_event(
        event_type="basket_items_delivered",
        avatar="buyer_agent",
        transition={"type": "basket_items_delivered", "basket_id": basket_id},
        claim=f"{basket_id}_items_delivered_under_terms",
        status="checked",
        action="no_action",
    )
    return basket


def checkout(basket_id: str) -> dict[str, Any]:
    avatars, workcards, baskets = load_state()
    basket = get_basket(baskets, basket_id)
    avatars_by_id = {avatar["avatar_id"]: avatar for avatar in avatars["avatars"]}
    workcards_by_id = {workcard["workcard_id"]: workcard for workcard in workcards["workcards"]}
    result = adjudicate_basket_checkout(
        basket=basket,
        workcards_by_id=workcards_by_id,
        avatars_by_id=avatars_by_id,
        mandate_links=avatars.get("mandate_links", []),
    )
    basket_status = result["basket_status"]
    basket_action = apply_atomgate(basket_status)

    receipt = {
        "application": "SkyBasket",
        "basket_id": basket_id,
        "market_event": "atomic_basket_checkout",
        "basket_status": basket_status,
        "basket_action": basket_action,
        "real_payment_executed": False,
        "item_judgments": [
            {
                "workcard_id": item["workcard_id"],
                "claim": item["claim"],
                "status": item["status"],
            }
            for item in result["item_judgments"]
        ],
        "basket_judgment": {
            "claim": result["basket_claim"],
            "status": basket_status,
            "aggregation_rule": result["basket_reasons"][0],
        },
        "non_claims": [
            "No real payment was executed.",
            "This application-demo does not claim real-world settlement atomicity.",
            "This application-demo only adjudicates a bounded local basket checkout.",
        ],
    }
    receipt_path = RECEIPTS_DIR / f"{basket_id}_basket_receipt.json"
    write_json(receipt_path, receipt)
    append_pact_event(
        event_type="basket_checkout_adjudicated",
        avatar="buyer_agent",
        transition={"type": "basket_checkout", "basket_id": basket_id},
        claim=result["basket_claim"],
        status=basket_status,
        action=basket_action,
    )
    return receipt


def replay() -> dict[str, Any]:
    events = load_events(PACT_LOG_PATH)
    transitions_per_avatar: dict[str, int] = {}
    basket_history: list[dict[str, Any]] = []
    latest_status = None
    latest_action = None
    for event in events:
        avatar = event["avatar"]
        transitions_per_avatar[avatar] = transitions_per_avatar.get(avatar, 0) + 1
        if "basket_id" in event["transition"]:
            basket_history.append(
                {
                    "basket_id": event["transition"]["basket_id"],
                    "event_type": event["transition"]["event_type"],
                    "status": event["upl"]["status"],
                    "action": event["atomgate"]["action"],
                }
            )
            latest_status = event["upl"]["status"]
            latest_action = event["atomgate"]["action"]
    return {
        "event_count": len(events),
        "latest_basket_status": latest_status,
        "latest_basket_action": latest_action,
        "transitions_per_avatar": transitions_per_avatar,
        "basket_history": basket_history,
    }


def print_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print("Usage: python3 -m skybasket <command> [args]", file=sys.stderr)
        return 1
    command = argv[0]

    if command == "seed":
        print_json(seed())
        return 0
    if command == "list-workcards":
        print_json(list_workcards())
        return 0
    if command == "create-basket":
        print_json(create_basket())
        return 0
    if command == "deliver-all":
        if len(argv) != 2:
            print("Usage: python3 -m skybasket deliver-all <basket_id>", file=sys.stderr)
            return 1
        print_json(deliver_all(argv[1]))
        return 0
    if command == "checkout":
        if len(argv) != 2:
            print("Usage: python3 -m skybasket checkout <basket_id>", file=sys.stderr)
            return 1
        print_json(checkout(argv[1]))
        return 0
    if command == "replay":
        print_json(replay())
        return 0

    print(f"Unknown command: {command}", file=sys.stderr)
    return 1
