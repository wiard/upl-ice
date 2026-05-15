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


@dataclass(frozen=True)
class OutputContract:
    format: str
    max_words: int

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "OutputContract":
        return cls(format=str(payload["format"]), max_words=int(payload["max_words"]))

    def to_dict(self) -> dict[str, Any]:
        return {"format": self.format, "max_words": self.max_words}


@dataclass(frozen=True)
class MandateLink:
    link_id: str
    buyer_avatar: str
    seller_avatar: str
    allowed_workcard_ids: list[str]
    max_price: Price
    status: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MandateLink":
        return cls(
            link_id=str(payload["link_id"]),
            buyer_avatar=str(payload["buyer_avatar"]),
            seller_avatar=str(payload["seller_avatar"]),
            allowed_workcard_ids=list(payload["allowed_workcard_ids"]),
            max_price=Price.from_dict(payload["max_price"]),
            status=str(payload["status"]),
        )

