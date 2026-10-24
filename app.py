def process_payment(user_id: str, amount: float, discount_code: float = 0.0) -> dict:
    tax_rate = 0.18
    
    # Handle 100% discount case to avoid division by zero
    if discount_code >= 100.0:
        base_amount = 0.0
    else:
        base_amount = amount / (1 - (discount_code / 100))
    
    return {
        "user": user_id,
        "charged": round(base_amount * (1 + tax_rate), 2),
        "status": "success",
    }