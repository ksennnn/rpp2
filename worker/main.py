import asyncio
import json
from datetime import datetime, timezone
import aio_pika
from sqlalchemy import select
from common.db import Base, engine, Session
from common.models import Account, Operation
from common.messaging import connect, declare_operations, declare_events
from domain import calculate


async def process(data):
    async with Session() as s:
        async with s.begin():
            # Idempotency for redelivered messages
            existing = await s.get(Operation, data["operation_id"])
            if existing:
                # Повторная доставка после сбоя публикации события: повторно публикуем
                # уже зафиксированный результат, чтобы не потерять событие.
                return {
                    "operation_id": existing.operation_id,
                    "type": existing.type,
                    "customer_id": existing.customer_id,
                    "store_id": existing.store_id,
                    "status": existing.status,
                    "points_delta": existing.points_delta,
                    "balance_after": existing.balance_after,
                    "reject_reason": existing.reject_reason,
                    "processed_at": existing.processed_at.isoformat(),
                }

            account = await s.get(Account, data["customer_id"])
            if account is None:
                account = Account(customer_id=data["customer_id"], balance=0)
                s.add(account)
                await s.flush()

            purchase = None
            returned = False
            if data["type"] == "return":
                purchase = await s.scalar(
                    select(Operation)
                    .where(
                        Operation.check_number == data["check_number"],
                        Operation.type == "purchase",
                        Operation.status == "applied",
                    )
                    .with_for_update()
                )
                if purchase:
                    returned = bool(
                        await s.scalar(
                            select(Operation.operation_id).where(
                                Operation.check_number == data["check_number"],
                                Operation.type == "return",
                                Operation.status == "applied",
                            )
                        )
                    )
            elif data["type"] == "purchase":
                purchase = await s.scalar(
                    select(Operation).where(
                        Operation.check_number == data["check_number"],
                        Operation.type == "purchase",
                        Operation.status == "applied",
                    )
                )

            purchase_info = (
                {"customer_id": purchase.customer_id, "points": purchase.points_delta}
                if purchase
                else None
            )

            status, delta, new_balance, reason = calculate(
                data, account.balance, purchase_info, returned
            )
            account.balance = new_balance

            now = datetime.now(timezone.utc)
            rec = Operation(
                operation_id=data["operation_id"],
                type=data["type"],
                customer_id=data["customer_id"],
                store_id=data["store_id"],
                check_number=data["check_number"],
                amount=data.get("amount"),
                points=data.get("points"),
                points_delta=delta,
                balance_after=new_balance,
                status=status,
                reject_reason=reason,
                occurred_at=datetime.fromisoformat(
                    data["occurred_at"].replace("Z", "+00:00")
                ),
                processed_at=now,
            )
            s.add(rec)

            return {
                "operation_id": data["operation_id"],
                "type": data["type"],
                "customer_id": data["customer_id"],
                "store_id": data["store_id"],
                "status": status,
                "points_delta": delta,
                "balance_after": new_balance,
                "reject_reason": reason,
                "processed_at": now.isoformat(),
            }

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    conn = await connect()
    ch = await conn.channel(publisher_confirms=True, prefetch_count=1)

    op_ex, q = await declare_operations(ch)
    event_ex, _ = await declare_events(ch, "notifier.events")
    await declare_events(ch, "analytics.events")

    async with q.iterator() as it:
        async for msg in it:
            async with msg.process(requeue=True):
                data = json.loads(msg.body)
                event = await process(data)
                if event:
                    out = aio_pika.Message(
                        json.dumps(event).encode(),
                        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                        message_id=event["operation_id"],
                        content_type="application/json",
                    )
                    confirmed = await event_ex.publish(out, routing_key="")
                    if confirmed is False:
                        raise RuntimeError("event publish not confirmed")

    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())