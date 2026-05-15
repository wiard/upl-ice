from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import MandateLink, OutputContract, Price


@dataclass(frozen=True)
class CheckoutResult:
    status: str
    claim: str
    boundary: dict[str, Any]
    witnesses: dict[str, Any]
    trace: list[dict[str, Any]]


def adjudicate_checkout(
    *,
    order: dict[str, Any],
    workcard: dict[str, Any],
    buyer_avatar: dict[str, Any],
    seller_avatar: dict[str, Any],
    mandate_link: dict[str, Any] | None,
) -> CheckoutResult:
    claim = f"{seller_avatar['avatar_id']}_completed_{order['task_id']}"
    output_contract = OutputContract.from_dict(workcard["output_contract"])
    accepted_price = Price.from_dict(order["accepted_price"])

    boundary = {
        "order_id": order["order_id"],
        "task_id": order["task_id"],
        "buyer_avatar": buyer_avatar["avatar_id"],
        "seller_avatar": seller_avatar["avatar_id"],
        "workcard_id": workcard["workcard_id"],
        "price": accepted_price.to_dict(),
        "output_contract": output_contract.to_dict(),
    }

    witnesses = {
        "workcard": {"state": "present", "ref": workcard["workcard_id"]},
        "order": {"state": "present", "ref": order["order_id"]},
        "buyer_avatar": {"state": "present", "ref": buyer_avatar["avatar_id"]},
        "seller_avatar": {"state": "present", "ref": seller_avatar["avatar_id"]},
        "mandate_link": {"state": "missing", "ref": None},
        "proofpack": {"state": "missing", "ref": None},
        "check": {"state": "pending", "ref": "delivery_check_v0_1"},
        "trace": {"state": "present", "ref": "pact_log"},
    }

    trace: list[dict[str, Any]] = []

    if mandate_link is None:
        trace.append({"step": "mandate_link_present", "passed": False, "reason": "missing boundary-sufficient MandateLink"})
        return CheckoutResult(status="incomplete", claim=claim, boundary=boundary, witnesses=witnesses, trace=trace)

    link = MandateLink.from_dict(mandate_link)
    witnesses["mandate_link"] = {"state": "present", "ref": link.link_id}

    workcard_allowed = workcard["workcard_id"] in link.allowed_workcard_ids
    seller_allowed = link.seller_avatar == seller_avatar["avatar_id"]
    buyer_allowed = link.buyer_avatar == buyer_avatar["avatar_id"]
    link_active = link.status == "active"
    price_within_mandate = (
        accepted_price.currency == link.max_price.currency
        and accepted_price.amount <= link.max_price.amount
    )

    trace.append({"step": "mandate_link_present", "passed": True, "link_id": link.link_id})
    trace.append({"step": "buyer_matches_mandate", "passed": buyer_allowed})
    trace.append({"step": "seller_matches_mandate", "passed": seller_allowed})
    trace.append({"step": "workcard_allowed_by_mandate", "passed": workcard_allowed})
    trace.append({"step": "price_within_mandate", "passed": price_within_mandate, "price": accepted_price.to_dict(), "mandate_max_price": link.max_price.to_dict()})
    trace.append({"step": "mandate_link_active", "passed": link_active})

    if not buyer_allowed or not seller_allowed or not workcard_allowed or not price_within_mandate or not link_active:
        return CheckoutResult(status="out_of_scope", claim=claim, boundary=boundary, witnesses=witnesses, trace=trace)

    proofpack = order.get("proofpack")
    if not isinstance(proofpack, dict):
        trace.append({"step": "proofpack_present", "passed": False})
        return CheckoutResult(status="incomplete", claim=claim, boundary=boundary, witnesses=witnesses, trace=trace)

    witnesses["proofpack"] = {"state": "present", "ref": proofpack.get("proofpack_id", "proofpack")}

    result_declared_complete = bool(proofpack.get("result_declared_complete"))
    delivered_output = proofpack.get("output", {})
    format_matches = delivered_output.get("format") == output_contract.format
    word_count_within_contract = int(delivered_output.get("word_count", -1)) <= output_contract.max_words

    trace.append({"step": "proofpack_present", "passed": True})
    trace.append({"step": "result_declared_complete", "passed": result_declared_complete})
    trace.append({"step": "result_format_matches_contract", "passed": format_matches, "expected": output_contract.format, "actual": delivered_output.get("format")})
    trace.append({"step": "result_word_count_within_contract", "passed": word_count_within_contract, "max_words": output_contract.max_words, "actual_word_count": delivered_output.get("word_count")})

    if result_declared_complete and format_matches and word_count_within_contract:
        witnesses["check"] = {"state": "present", "ref": "delivery_check_v0_1"}
        return CheckoutResult(status="checked", claim=claim, boundary=boundary, witnesses=witnesses, trace=trace)

    witnesses["check"] = {"state": "present", "ref": "delivery_check_v0_1"}
    return CheckoutResult(status="failed", claim=claim, boundary=boundary, witnesses=witnesses, trace=trace)
