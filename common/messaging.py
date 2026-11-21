import os
import aio_pika

URL = os.getenv("RABBITMQ_URL", "amqp://loyalty:loyalty@rabbitmq:5672/")

async def connect():
    return await aio_pika.connect_robust(URL)

async def declare_operations(channel):
    ex = await channel.declare_exchange("loyalty", aio_pika.ExchangeType.DIRECT, durable=True)
    q = await channel.declare_queue("operations", durable=True, arguments={"x-queue-type": "quorum"})
    await q.bind(ex, routing_key="operation")
    return ex, q

async def declare_events(channel, queue_name):
    ex = await channel.declare_exchange("loyalty.events", aio_pika.ExchangeType.FANOUT, durable=True)
    q = await channel.declare_queue(queue_name, durable=True, arguments={"x-queue-type": "quorum"})
    await q.bind(ex)
    return ex, q