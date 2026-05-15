from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Price:
    amount: float
    currency: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Price":
        return cls(amount=float(payload["amount"]), currency=str(payload["currency"]))

    def to_dict(self) -> dict[str, Any]:
        return {"amount": self.amount, "currency": self.currency}
