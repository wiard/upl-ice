from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .atomgate import ATOMGATE_POLICY, apply_atomgate
from .pact_log import append_event, load_events
from .upl_checkout import adjudicate_checkout


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


def seed_payloads() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    avatars = {
        "avatars": [
            {
                "avatar_id": "agent_A",
                "display_name": "Avatar A",
                "role": "buyer",
            },
            {
                "avatar_id": "agent_B",
                "display_name": "Avatar B",
                "role": "seller",
            },
        ],
        "mandate_links": [
            {
                "link_id": "mandatelink_agent_A_agent_B_001",
                "buyer_avatar": "agent_A",
                "seller_avatar": "agent_B",
                "allowed_workcard_ids": ["workcard_summary_001"],
                "max_price": {
                    "amount": 0.20,
                    "currency": "EUR",
                },
                "status": "active",
            }
        ],
    }

    workcards = {
        "workcards": [
            {
                "workcard_id": "workcard_summary_001",
                "seller_avatar": "agent_B",
                "title": "Bounded summary work",
                "task_type": "document_summary",
                "price": {
                    "amount": 0.12,
                    "currency": "EUR",
                },
                "output_contract": {
                    "format": "markdown",
                    "max_words": 120,
                },
            }
        ]
    }

    orders = {"orders": []}
    return avatars, workcards, orders


def data_paths() -> tuple[Path, Path, Path]:
    return DATA_DIR / "avatars.json", DATA_DIR / "workcards.json", DATA_DIR / "orders.json"


def load_state() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    avatars_path, workcards_path, orders_path = data_paths()
    return load_json(avatars_path), load_json(workcards_path), load_json(orders_path)


def write_state(avatars: dict[str, Any], workcards: dict[str, Any], orders: dict[str, Any]) -> None:
    avatars_path, workcards_path, orders_path = data_paths()
    write_json(avatars_path, avatars)
    write_json(workcards_path, workcards)
    write_json(orders_path, orders)


def next_order_id(orders: dict[str, Any]) -> str:
    count = len(orders["orders"]) + 1
    return f"order_{count:03d}"


def get_avatar(avatars: dict[str, Any], avatar_id: str) -> dict[str, Any]:
    for avatar in avatars["avatars"]:
        if avatar["avatar_id"] == avatar_id:
            return avatar
    raise KeyError(f"Unknown avatar: {avatar_id}")


def get_workcard(workcards: dict[str, Any], workcard_id: str) -> dict[str, Any]:
    for workcard in workcards["workcards"]:
        if workcard["workcard_id"] == workcard_id:
            return workcard
    raise KeyError(f"Unknown workcard: {workcard_id}")


def get_order(orders: dict[str, Any], order_id: str) -> dict[str, Any]:
    for order in orders["orders"]:
        if order["order_id"] == order_id:
            return order
    raise KeyError(f"Unknown order: {order_id}")


def find_mandate_link(avatars: dict[str, Any], buyer_avatar: str, seller_avatar: str) -> dict[str, Any] | None:
    for link in avatars.get("mandate_links", []):
        if link["buyer_avatar"] == buyer_avatar and link["seller_avatar"] == seller_avatar:
            return link
    return None


def seed() -> dict[str, Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)

    avatars, workcards, orders = seed_payloads()
    write_state(avatars, workcards, orders)
    PACT_LOG_PATH.write_text("", encoding="utf-8")
    append_event(PACT_LOG_PATH, {
        "event_id": "event_seed_001",
        "event_type": "seed_initialized",
        "timestamp_utc": utc_now(),
        "payload": {
            "avatars": len(avatars["avatars"]),
            "workcards": len(workcards["workcards"]),
            "orders": len(orders["orders"]),
        },
    })
    return {"avatars": len(avatars["avatars"]), "workcards": len(workcards["workcards"]), "orders": 0}


def list_workcards() -> list[dict[str, Any]]:
    _, workcards, _ = load_state()
    return workcards["workcards"]


def place_order(workcard_id: str) -> dict[str, Any]:
    avatars, workcards, orders = load_state()
    workcard = get_workcard(workcards, workcard_id)
    order_id = next_order_id(orders)
    order = {
        "order_id": order_id,
        "task_id": f"task_{order_id}",
        "buyer_avatar": "agent_A",
        "seller_avatar": workcard["seller_avatar"],
        "workcard_id": workcard["workcard_id"],
        "accepted_price": workcard["price"],
        "status": "placed",
    }
    orders["orders"].append(order)
    write_state(avatars, workcards, orders)
    append_event(PACT_LOG_PATH, {
        "event_id": f"event_{order_id}_placed",
        "event_type": "order_placed",
        "timestamp_utc": utc_now(),
        "payload": order,
    })
    return order


def deliver(order_id: str) -> dict[str, Any]:
    avatars, workcards, orders = load_state()
    order = get_order(orders, order_id)
    workcard = get_workcard(workcards, order["workcard_id"])
    proofpack = {
        "proofpack_id": f"proofpack_{order_id}",
        "result_declared_complete": True,
        "output": {
            "format": workcard["output_contract"]["format"],
            "word_count": 87,
            "content_digest": f"digest_{order_id}",
        },
    }
    order["proofpack"] = proofpack
    order["status"] = "delivered"
    write_state(avatars, workcards, orders)
    append_event(PACT_LOG_PATH, {
        "event_id": f"event_{order_id}_delivered",
        "event_type": "work_delivered",
        "timestamp_utc": utc_now(),
        "payload": {
            "order_id": order_id,
            "proofpack_id": proofpack["proofpack_id"],
        },
    })
    return proofpack


def checkout(order_id: str) -> dict[str, Any]:
    avatars, workcards, orders = load_state()
    order = get_order(orders, order_id)
    workcard = get_workcard(workcards, order["workcard_id"])
    buyer_avatar = get_avatar(avatars, order["buyer_avatar"])
    seller_avatar = get_avatar(avatars, order["seller_avatar"])
    mandate_link = find_mandate_link(avatars, order["buyer_avatar"], order["seller_avatar"])

    result = adjudicate_checkout(
        order=order,
        workcard=workcard,
        buyer_avatar=buyer_avatar,
        seller_avatar=seller_avatar,
        mandate_link=mandate_link,
    )
    action = apply_atomgate(result.status)

    receipt = {
        "receipt_id": f"claimreceipt_{order_id}",
        "app": "AirMarket",
        "claim": result.claim,
        "boundary": result.boundary,
        "witnesses": result.witnesses,
        "status": result.status,
        "action": action,
        "non_claims": [
            "No real payment was executed.",
            "AirMarket does not claim legal finality.",
            "AirMarket does not claim settlement finality.",
        ],
    }

    receipt_path = RECEIPTS_DIR / f"{order_id}_claim_receipt.json"
    write_json(receipt_path, receipt)

    append_event(PACT_LOG_PATH, {
        "event_id": f"event_{order_id}_checked",
        "event_type": "checkout_adjudicated",
        "timestamp_utc": utc_now(),
        "payload": {
            "order_id": order_id,
            "status": result.status,
            "action": action,
            "receipt": str(receipt_path.relative_to(MODULE_ROOT)),
        },
    })

    return {
        "order_id": order_id,
        "status": result.status,
        "action": action,
        "receipt_path": str(receipt_path),
        "trace": result.trace,
    }


def replay() -> dict[str, Any]:
    events = load_events(PACT_LOG_PATH)
    history = {
        "event_count": len(events),
        "event_types": [event["event_type"] for event in events],
        "events": events,
    }
    return history


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    if not argv:
        print("Usage: python3 -m airmarket <command> [args]")
        return 1

    command = argv[0]

    if command == "seed":
        _print_json(seed())
        return 0
    if command == "list-workcards":
        _print_json({"workcards": list_workcards()})
        return 0
    if command == "place-order":
        if len(argv) != 2:
            print("Usage: python3 -m airmarket place-order <workcard_id>")
            return 1
        _print_json(place_order(argv[1]))
        return 0
    if command == "deliver":
        if len(argv) != 2:
            print("Usage: python3 -m airmarket deliver <order_id>")
            return 1
        _print_json(deliver(argv[1]))
        return 0
    if command == "checkout":
        if len(argv) != 2:
            print("Usage: python3 -m airmarket checkout <order_id>")
            return 1
        _print_json(checkout(argv[1]))
        return 0
    if command == "replay":
        _print_json(replay())
        return 0

    print(f"Unknown command: {command}")
    return 1
