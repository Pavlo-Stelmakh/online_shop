from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

MONEY_QUANT = Decimal("0.01")


class MoneyValidationError(ValueError):
    """Raised when a money input cannot be safely accepted."""


def parse_money(value: Any, *, field_name: str = "price") -> Decimal:
    """Parse and validate a money input as Decimal with at most 2 decimal places."""
    if isinstance(value, str):
        value = value.strip()
        if value == "":
            raise MoneyValidationError(f"{field_name} is required")

    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise MoneyValidationError(f"{field_name} must be a valid decimal amount") from None

    if not amount.is_finite():
        raise MoneyValidationError(f"{field_name} must be a finite decimal amount")

    if amount < 0:
        raise MoneyValidationError(f"{field_name} must be greater than or equal to 0")

    if amount.as_tuple().exponent < -2:
        raise MoneyValidationError(f"{field_name} must not have more than 2 decimal places")

    return amount.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def parse_positive_money(value: Any, *, field_name: str = "price") -> Decimal:
    amount = parse_money(value, field_name=field_name)

    if amount <= 0:
        raise MoneyValidationError(f"{field_name} must be greater than 0")

    return amount


def money_to_float(value: Decimal) -> float:
    return float(value)


def format_money(value: Any) -> str:
    amount = Decimal(str(value)).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    return f"{amount:.2f}"
