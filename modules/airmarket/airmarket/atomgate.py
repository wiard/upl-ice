from __future__ import annotations


STATUSES = (
    "unsupported",
    "bounded",
    "incomplete",
    "pending_check",
    "checked",
    "failed",
    "contradicted",
    "inconclusive",
    "out_of_scope",
)

ATOMGATE_POLICY = {
    "unsupported": "no_action",
    "bounded": "human_approval_required",
    "incomplete": "blocked_missing_witnesses",
    "pending_check": "hold_pending_check",
    "checked": "mock_payment_release_allowed",
    "failed": "mock_payment_denied",
    "contradicted": "mock_payment_denied_contradicted",
    "inconclusive": "mock_payment_hold",
    "out_of_scope": "mock_payment_denied_out_of_scope",
}


def apply_atomgate(status: str) -> str:
    if status not in ATOMGATE_POLICY:
        raise KeyError(f"Unknown status: {status}")
    return ATOMGATE_POLICY[status]
