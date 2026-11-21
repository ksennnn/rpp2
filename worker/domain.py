from decimal import Decimal, ROUND_DOWN

def calculate(op, balance, purchase_points=None, returned=False):
    """Pure domain function: no database or broker dependencies."""
    reason = None
    delta = 0

    if op["type"] == "purchase":
        if purchase_points is not None:
            reason = "duplicate_purchase"
        else:
            delta = int(
                (Decimal(str(op["amount"])) * Decimal("0.05")).to_integral_value(rounding=ROUND_DOWN)
            )
    elif op["type"] == "return":
        if purchase_points is None:
            reason = "purchase_not_found"
        elif op["customer_id"] != purchase_points["customer_id"]:
            reason = "customer_mismatch"
        elif returned:
            reason = "already_returned"
        else:
            delta = -purchase_points["points"]
    elif op["type"] == "redeem":
        # 30% cap is floored to a whole point.
        if int(Decimal(str(op["amount"])) * Decimal("0.30")) < int(op["points"]):
            reason = "limit_exceeded"
        elif int(op["points"]) > balance:
            reason = "insufficient_balance"
        else:
            delta = -int(op["points"])

    if reason:
        return "rejected", 0, balance, reason
    return "applied", delta, balance + delta, None
