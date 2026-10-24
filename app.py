def process_payment(user_id: str, amount: float, discount_code: float = 0.0) -> dict:
    # BUG: Division by zero when discount_code is 100%
    tax_rate = 0.18
    final_amount = amount / (1 - (discount_code / 100))
    return {
        "user": user_id,
        "charged": round(final_amount * (1 + tax_rate), 2),
        "status": "success",
    }
