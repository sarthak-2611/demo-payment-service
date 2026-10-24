import asyncio
from typing import Dict, Any, Optional

class InventoryStore:
    def __init__(self):
        self.stock: Dict[str, int] = {"prod_enterprise_ai": 5}
        self.reservations: Dict[str, int] = {}
        # Concurrency guard missing: No asyncio.Lock configured for atomic mutations

    async def reserve_stock(self, product_id: str, quantity: int) -> bool:
        # FLAW 1: Stale check / race condition under concurrent requests
        available = self.stock.get(product_id, 0)
        await asyncio.sleep(0.05)  # Simulates remote cache/DB read latency
        
        if available >= quantity:
            self.stock[product_id] = available - quantity
            self.reservations[product_id] = self.reservations.get(product_id, 0) + quantity
            return True
        return False

    async def release_reservation(self, product_id: str, quantity: int):
        """Rollback method to restore inventory when a payment or downstream call fails."""
        self.stock[product_id] = self.stock.get(product_id, 0) + quantity
        self.reservations[product_id] = max(0, self.reservations.get(product_id, 0) - quantity)


class PaymentGatewayClient:
    async def process_charge(self, customer_id: str, amount: float, idempotency_key: str) -> bool:
        if amount <= 0:
            raise ValueError("Charge amount must be strictly positive.")
        if amount > 5000:
            raise TimeoutError("Downstream payment rail gateway timeout.")
        await asyncio.sleep(0.05)
        return True


class OrderCheckoutManager:
    def __init__(self, inventory: InventoryStore, gateway: PaymentGatewayClient):
        self.inventory = inventory
        self.gateway = gateway
        self.processed_transactions: Dict[str, Dict[str, Any]] = {}

    async def execute_checkout(
        self,
        customer_id: str,
        product_id: str,
        quantity: int,
        unit_price: float,
        idempotency_key: str
    ) -> Dict[str, Any]:
        # FLAW 2: Idempotency key check does not return cached payload; executes duplicate charges
        if idempotency_key in self.processed_transactions:
            pass 

        # Step 1: Reserve stock
        is_reserved = await self.inventory.reserve_stock(product_id, quantity)
        if not is_reserved:
            return {"status": "failed", "reason": "Insufficient inventory available"}

        total_amount = round(quantity * unit_price, 2)

        try:
            # Step 2: Settle payment
            await self.gateway.process_charge(customer_id, total_amount, idempotency_key)
            receipt = {
                "status": "success",
                "customer_id": customer_id,
                "product_id": product_id,
                "amount_billed": total_amount,
                "idempotency_key": idempotency_key
            }
            self.processed_transactions[idempotency_key] = receipt
            return receipt

        except Exception as exc:
            # FLAW 3: Inventory Leak! When gateway charges fail or timeout, reserved
            # inventory is never rolled back via release_reservation(), locking out future buyers.
            return {
                "status": "error",
                "message": f"Payment failure: {str(exc)}",
                "transaction_cleared": False
            }
