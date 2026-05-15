from __future__ import annotations

from typing import Any


def aggregate_item_statuses(item_judgments: list[dict[str, Any]]) -> tuple[str, str]:
    statuses = [item["status"] for item in item_judgments]
    if any(status == "out_of_scope" for status in statuses):
        return "out_of_scope", "contains_out_of_scope_item"
    if any(status == "incomplete" for status in statuses):
        return "incomplete", "contains_incomplete_item"
    if any(status == "failed" for status in statuses):
        return "failed", "contains_failed_item"
    if any(status == "inconclusive" for status in statuses):
        return "inconclusive", "contains_inconclusive_item"
    if any(status == "pending_check" for status in statuses):
        return "pending_check", "contains_pending_item"
    if any(status == "bounded" for status in statuses):
        return "bounded", "contains_bounded_item"
    if any(status == "unsupported" for status in statuses):
        return "unsupported", "contains_unsupported_item"
    if any(status == "contradicted" for status in statuses):
        return "contradicted", "contains_contradicted_item"
    return "checked", "all_items_checked"
