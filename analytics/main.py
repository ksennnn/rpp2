import asyncio
import json
from collections import defaultdict
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from common.messaging import connect, declare_events

connection = None
received = 0
stores = {}

def blank():
    return {
        "accepted_purchase": 0,
        "accepted_return": 0,
        "accepted_redeem": 0,
        "rejected": 0,
        "points_accrued": 0,
        "points_returned": 0,
        "points_redeemed": 0,
    }

async def consume():
    global received
    ch = await connection.channel()
    _, q = await declare_events(ch, "analytics.events")
    async with q.iterator() as it:
        async for msg in it:
            async with msg.process():
                e = json.loads(msg.body)
                received += 1
                st = stores.setdefault(e["store_id"], blank())
                if e["status"] == "rejected":
                    st["rejected"] += 1
                else:
                    st["accepted_" + e["type"]] += 1
                    if e["type"] == "purchase":
                        st["points_accrued"] += max(0, e["points_delta"])
                    elif e["type"] == "return":
                        st["points_returned"] += abs(e["points_delta"])
                    elif e["type"] == "redeem":
                        st["points_redeemed"] += abs(e["points_delta"])

@asynccontextmanager
async def lifespan(app):
    global connection
    connection = await connect()
    task = asyncio.create_task(consume())
    yield
    task.cancel()
    await connection.close()

app = FastAPI()

@app.get("/stores")
async def all_stores():
    return [{"store_id": k, **v} for k, v in sorted(stores.items())]

@app.get("/stores/{store_id}")
async def one_store(store_id: str):
    if store_id not in stores:
        raise HTTPException(404, "store has no events")
    return {"store_id": store_id, **stores[store_id]}

@app.get("/stats")
async def stats():
    return {"received_events": received}