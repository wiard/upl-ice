from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .basket import aggregate_item_statuses
from .models import Price


@dataclass
class ItemJudgment:
    workcard_id: str
    claim: str
    status: str
    boundary: dict[str, Any]
    witnesses: dict[str, Any]
    reasons: list[str]


def principal_within_boundary(link: dict[str, Any], required_depth: int) -> bool:
    return (
        link.get("status") == "active"
        and int(link.get("principal_depth", 0)) >= required_depth
        and link.get("principal", {}).get("namespace") == "kvk"
    )


def adjudicate_item(
    *,
    basket: dict[str, Any],
    basket_item: dict[str, Any],
    workcard: dict[str, Any] | None,
    seller_avatar: dict[str, Any] | None,
    buyer_avatar: dict[str, Any] | None,
    mandate_link: dict[str, Any] | None,
) -> ItemJudgment:
    workcard_id = basket_item["workcard_id"]
    claim = f"{workcard_id}_delivered_under_terms"
    boundary = {
        "basket_id": basket["basket_id"],
        "workcard_id": workcard_id,
        "buyer_avatar": basket["buyer_avatar"],
        "seller_avatar": basket_item.get("seller_avatar"),
        "principal_required": "vasen_vof@kvk",
        "required_principal_depth": basket["buyer_mandate"]["required_principal_depth"],
        "max_item_price": basket["buyer_mandate"]["max_total_price"],
    }
    witnesses = {
        "basket": basket if basket else None,
        "workcard": workcard,
        "proofpack": basket_item.get("proofpack"),
        "mandate_link": mandate_link,
        "buyer_avatar": buyer_avatar,
        "seller_avatar": seller_avatar,
    }
    reasons: list[str] = []

    if not basket:
        return ItemJudgment(workcard_id, claim, "incomplete", boundary, witnesses, ["missing basket"])
    if workcard is None or buyer_avatar is None or seller_avatar is None:
        return ItemJudgment(workcard_id, claim, "incomplete", boundary, witnesses, ["missing referenced entity"])
    if basket_item.get("proofpack") is None:
        return ItemJudgment(workcard_id, claim, "incomplete", boundary, witnesses, ["missing delivery proofpack"])
    if mandate_link is None:
        return ItemJudgment(workcard_id, claim, "incomplete", boundary, witnesses, ["missing MandateLink"])

    allowed_depth = int(basket["buyer_mandate"]["required_principal_depth"])
    if not principal_within_boundary(mandate_link, allowed_depth):
        return ItemJudgment(workcard_id, claim, "out_of_scope", boundary, witnesses, ["MandateLink outside namespace boundary"])

    allowed_task_types = basket["buyer_mandate"]["allowed_task_types"]
    allowed_sellers = basket["buyer_mandate"]["allowed_sellers"]
    price = Price.from_dict(workcard["price"])
    max_total = Price.from_dict(basket["buyer_mandate"]["max_total_price"])

    if workcard["task_type"] not in allowed_task_types:
        return ItemJudgment(workcard_id, claim, "out_of_scope", boundary, witnesses, ["task type outside buyer mandate"])
    if seller_avatar["avatar_id"] not in allowed_sellers:
        return ItemJudgment(workcard_id, claim, "out_of_scope", boundary, witnesses, ["seller outside buyer mandate"])
    if price.currency != max_total.currency or price.amount > max_total.amount:
        return ItemJudgment(workcard_id, claim, "out_of_scope", boundary, witnesses, ["item price exceeds mandate boundary"])

    proofpack = basket_item["proofpack"]
    output = proofpack.get("output", {})
    contract = workcard["output_contract"]

    if not proofpack.get("result_declared_complete", False):
        return ItemJudgment(workcard_id, claim, "failed", boundary, witnesses, ["delivery not declared complete"])
    if output.get("format") != contract.get("format"):
        return ItemJudgment(workcard_id, claim, "failed", boundary, witnesses, ["output format mismatch"])
    if contract.get("format") == "markdown":
        if int(output.get("word_count", 10**9)) > int(contract.get("max_words", 0)):
            return ItemJudgment(workcard_id, claim, "failed", boundary, witnesses, ["word count exceeds contract"])
    if contract.get("format") == "json":
        payload = output.get("payload")
        if not isinstance(payload, dict):
            return ItemJudgment(workcard_id, claim, "failed", boundary, witnesses, ["json payload missing"])
        missing_fields = [field for field in contract.get("required_fields", []) if field not in payload]
        if missing_fields:
            return ItemJudgment(workcard_id, claim, "failed", boundary, witnesses, [f"missing required fields: {', '.join(missing_fields)}"])

    reasons.append("all required witnesses present and item checks passed")
    return ItemJudgment(workcard_id, claim, "checked", boundary, witnesses, reasons)


def adjudicate_basket_checkout(
    *,
    basket: dict[str, Any] | None,
    workcards_by_id: dict[str, dict[str, Any]],
    avatars_by_id: dict[str, dict[str, Any]],
    mandate_links: list[dict[str, Any]],
) -> dict[str, Any]:
    if basket is None:
        return {
            "basket_claim": "unknown_basket_delivered_under_terms",
            "basket_status": "incomplete",
            "basket_reasons": ["missing basket"],
            "item_judgments": [],
        }

    item_judgments: list[dict[str, Any]] = []
    for item in basket["items"]:
        seller_avatar_id = item["seller_avatar"]
        mandate_link = next(
            (
                link for link in mandate_links
                if link["source_avatar"] == seller_avatar_id and link["target_avatar"] == basket["buyer_mandate"]["principal_avatar"]
            ),
            None,
        )
        judgment = adjudicate_item(
            basket=basket,
            basket_item=item,
            workcard=workcards_by_id.get(item["workcard_id"]),
            seller_avatar=avatars_by_id.get(seller_avatar_id),
            buyer_avatar=avatars_by_id.get(basket["buyer_avatar"]),
            mandate_link=mandate_link,
        )
        item_judgments.append(
            {
                "workcard_id": judgment.workcard_id,
                "claim": judgment.claim,
                "status": judgment.status,
                "boundary": judgment.boundary,
                "witnesses": judgment.witnesses,
                "reasons": judgment.reasons,
            }
        )

    if any(item["status"] == "incomplete" and item["reasons"] == ["missing basket"] for item in item_judgments):
        basket_status = "incomplete"
        aggregation_rule = "missing_basket"
    else:
        total_amount = sum(float(workcards_by_id[item["workcard_id"]]["price"]["amount"]) for item in basket["items"] if item["workcard_id"] in workcards_by_id)
        max_total = Price.from_dict(basket["buyer_mandate"]["max_total_price"])
        if total_amount > max_total.amount:
            basket_status = "out_of_scope"
            aggregation_rule = "basket_total_exceeds_mandate"
        else:
            basket_status, aggregation_rule = aggregate_item_statuses(item_judgments)

    return {
        "basket_claim": f"{basket['basket_id']}_delivered_under_terms",
        "basket_status": basket_status,
        "basket_reasons": [aggregation_rule],
        "item_judgments": item_judgments,
    }
