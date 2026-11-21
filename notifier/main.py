import asyncio
import json
import os
import random
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
import aio_pika
from common.messaging import connect, declare_events

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("notifier")

UNSUB = set(filter(None, os.getenv("UNSUBSCRIBED", "").split(",")))
MIN = int(os.getenv("MIN_DELAY_MS", "200"))
MAX = int(os.getenv("MAX_DELAY_MS", "1500"))

notifications = []
received = 0
sent = 0
connection = None


async def consume():
    global received, sent
    ch = await connection.channel()
    _, q = await declare_events(ch, "notifier.events")
    async with q.iterator() as it:
        async for msg in it:
            async with msg.process():
                e = json.loads(msg.body)
                received += 1
                cid = e["customer_id"]
                if cid in UNSUB:
                    continue
                if e["status"] != "applied":
                    body = f"Операция отклонена: {e['reject_reason']}"
                elif e["points_delta"] >= 0:
                    body = f"Начислено {e['points_delta']} баллов, баланс {e['balance_after']}"
                else:
                    body = f"Списано {abs(e['points_delta'])} баллов, баланс {e['balance_after']}"
                await asyncio.sleep(random.randint(MIN, MAX) / 1000)
                item = {
                    "customer_id": cid,
                    "operation_id": e["operation_id"],
                    "message": body,
                    "created_at": e["processed_at"],
                }
                notifications.append(item)
                sent += 1
                log.info("%s", item)

@asynccontextmanager
async def lifespan(app):
    global connection
    connection = await connect()
    task = asyncio.create_task(consume())
    yield
    task.cancel()
    await connection.close()

app = FastAPI()

@app.get("/notifications")
async def get_notifications(customer_id: str):
    return [n for n in notifications if n["customer_id"] == customer_id]

@app.get("/stats")
async def stats():
    return {"received_events": received, "sent_notifications": sent}

@app.get("/health")
async def health():
    return {"status": "ok"}