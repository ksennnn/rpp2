import argparse
import asyncio
import random
import time
import math
import json
import httpx

def percentile(values, p):
    if not values:
        return 0
    values = sorted(values)
    index = math.ceil(len(values) * p) - 1
    index = max(0, min(index, len(values) - 1))
    return round(values[index], 2)

async def run_load(client, url, mode, clients, rate, duration, day, metrics=None):
    stop_time = time.monotonic() + duration

    async def send_request():
        start = time.perf_counter()
        try:
            response = await client.get(
                url + "/search",
                params={"origin": "AAA", "destination": "AAB", "date": day}
            )
            response.raise_for_status()
            failed = False
        except Exception:
            failed = True
        elapsed = (time.perf_counter() - start) * 1000
        if metrics is not None:
            metrics["requests"] += 1
            metrics["latencies"].append(elapsed)
            if failed:
                metrics["errors"] += 1

    if mode == "closed":
        async def worker():
            while time.monotonic() < stop_time:
                await send_request()
        await asyncio.gather(*[worker() for _ in range(clients)])
    else:
        tasks = []
        while time.monotonic() < stop_time:
            tasks.append(asyncio.create_task(send_request()))
            interval = random.expovariate(rate)
            await asyncio.sleep(interval)
        if tasks:
            await asyncio.gather(*tasks)

async def monitor_health(client, url, duration, values):
    stop_time = time.monotonic() + duration
    while time.monotonic() < stop_time:
        start = time.perf_counter()
        try:
            response = await client.get(url + "/health")
            response.raise_for_status()
            elapsed = (time.perf_counter() - start) * 1000
            values.append(elapsed)
        except Exception:
            pass
        elapsed = time.perf_counter() - start
        await asyncio.sleep(max(0, 0.1 - elapsed))

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--mode", choices=["closed", "open"], default="open")
    parser.add_argument("--clients", type=int, default=10)
    parser.add_argument("--rate", type=float, default=5)
    parser.add_argument("--duration", type=int, default=60)
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--date", default="2026-11-09")
    args = parser.parse_args()

    limits = httpx.Limits(max_connections=500, max_keepalive_connections=200)

    async with httpx.AsyncClient(timeout=args.timeout, limits=limits) as client:
        print("Начало прогрева...")
        await run_load(client, args.url, args.mode, args.clients, args.rate, args.warmup, args.date)
        print("Прогрев завершён.")
        print("Начало измерения...")

        metrics = {"requests": 0, "errors": 0, "latencies": []}
        health_values = []

        health_task = asyncio.create_task(
            monitor_health(client, args.url, args.duration, health_values)
        )
        await run_load(client, args.url, args.mode, args.clients, args.rate, args.duration, args.date, metrics)
        await health_task

    requests_count = metrics["requests"]
    errors = metrics["errors"]
    latencies = metrics["latencies"]

    result = {
        "mode": args.mode,
        "requests": requests_count,
        "rps": round(requests_count / args.duration, 2),
        "p50_ms": percentile(latencies, 0.50),
        "p95_ms": percentile(latencies, 0.95),
        "p99_ms": percentile(latencies, 0.99),
        "max_ms": round(max(latencies, default=0), 2),
        "errors_percent": round(errors / max(requests_count, 1) * 100, 2),
        "health_p95_ms": percentile(health_values, 0.95)
    }

    print("\nРЕЗУЛЬТАТЫ НАГРУЗОЧНОГО ТЕСТИРОВАНИЯ")
    print(json.dumps(result, indent=4, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())