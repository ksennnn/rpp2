import json
from datetime import datetime
from decimal import Decimal
import aio_pika
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import desc, select
from common.db import Base, Session, engine
from common.messaging import connect, declare_operations
from common.models import Account, Operation

app = FastAPI()

connection = None
channel = None
exchange = None

class OperationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation_id: str = Field(min_length=1)
    type: str
    customer_id: str = Field(min_length=1)
    store_id: str = Field(min_length=1)
    check_number: str = Field(min_length=1)
    amount: Decimal | None = None
    points: int | None = None
    occurred_at: datetime

    @field_validator("type")
    @classmethod
    def valid_type(cls, v):
        if v not in {"purchase", "return", "redeem"}:
            raise ValueError("type must be purchase, return or redeem")
        return v

    @field_validator("amount")
    @classmethod
    def valid_amount(cls, v, info):
        if info.data.get("type") in {"purchase", "redeem"} and (v is None or v <= 0):
            raise ValueError("amount must be positive")
        if info.data.get("type") == "return" and v is not None:
            raise ValueError("amount must be absent for return")
        return v

    @field_validator("points")
    @classmethod
    def valid_points(cls, v, info):
        if info.data.get("type") == "redeem" and (v is None or v <= 0):
            raise ValueError("points must be positive")
        if info.data.get("type") != "redeem" and v is not None:
            raise ValueError("points only allowed for redeem")
        return v

    @model_validator(mode="after")
    def required_by_operation_type(self):
        if self.type in {"purchase", "redeem"} and self.amount is None:
            raise ValueError("amount is required for purchase and redeem")
        if self.type == "return" and self.amount is not None:
            raise ValueError("amount must be absent for return")
        if self.type == "redeem" and (self.points is None or self.points <= 0):
            raise ValueError("positive points are required for redeem")
        if self.type != "redeem" and self.points is not None:
            raise ValueError("points are allowed only for redeem")
        return self

@app.on_event("startup")
async def startup():
    global connection, channel, exchange
    connection = await connect()
    channel = await connection.channel(publisher_confirms=True)
    exchange, _ = await declare_operations(channel)

@app.on_event("shutdown")
async def shutdown():
    if connection:
        await connection.close()

@app.get("/health")
async def health():
    try:
        async with Session() as s:
            await s.execute(select(1))
        if not connection or connection.is_closed:
            raise RuntimeError("RabbitMQ unavailable")
        return {"status": "ok"}
    except Exception:
        raise HTTPException(503, "dependency unavailable")

@app.post("/operations", status_code=202)
async def submit(op: OperationIn):
    body = op.model_dump(mode="json")
    try:
        msg = aio_pika.Message(
            json.dumps(body).encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            message_id=op.operation_id,
            content_type="application/json",
        )
        confirmed = await exchange.publish(msg, routing_key="operation", mandatory=True)
        if confirmed is False:
            raise RuntimeError("publisher confirm failed")
    except Exception:
        raise HTTPException(503, "message broker did not confirm publication")
    return {"operation_id": op.operation_id}

@app.get("/operations/{operation_id}")
async def get_operation(operation_id: str):
    async with Session() as s:
        x = await s.get(Operation, operation_id)
        if not x:
            raise HTTPException(404, "operation not processed")
        return {
            "operation_id": x.operation_id,
            "type": x.type,
            "customer_id": x.customer_id,
            "store_id": x.store_id,
            "status": x.status,
            "points_delta": x.points_delta,
            "balance_after": x.balance_after,
            "reject_reason": x.reject_reason,
            "processed_at": x.processed_at.isoformat(),
        }

@app.get("/accounts/{customer_id}")
async def account(customer_id: str):
    async with Session() as s:
        a = await s.get(Account, customer_id)
        if not a:
            raise HTTPException(404, "account not found")
        rows = (
            await s.scalars(
                select(Operation)
                .where(Operation.customer_id == customer_id)
                .order_by(desc(Operation.processed_at))
                .limit(20)
            )
        ).all()
        return {
            "customer_id": customer_id,
            "balance": a.balance,
            "operations": [
                {
                    "operation_id": x.operation_id,
                    "type": x.type,
                    "store_id": x.store_id,
                    "check_number": x.check_number,
                    "amount": str(x.amount) if x.amount is not None else None,
                    "points_delta": x.points_delta,
                    "balance_after": x.balance_after,
                    "status": x.status,
                    "reject_reason": x.reject_reason,
                    "processed_at": x.processed_at.isoformat(),
                }
                for x in rows
            ],
        }