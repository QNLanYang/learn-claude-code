#!/usr/bin/env python3
"""Leader assigns tasks to two workers via asyncio.Queue; collect results."""
from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Task:
    task_id: str
    payload: str


@dataclass(frozen=True)
class Result:
    task_id: str
    worker: str
    output: str


async def worker(name: str, q: asyncio.Queue[Task | None], out: asyncio.Queue[Result]) -> None:
    while True:
        item = await q.get()
        if item is None:
            q.task_done()
            break
        await asyncio.sleep(random.uniform(0.01, 0.05))
        await out.put(Result(task_id=item.task_id, worker=name, output=item.payload.upper()))
        q.task_done()


async def leader(
    tasks: list[Task], w1: asyncio.Queue[Task | None], w2: asyncio.Queue[Task | None]
) -> None:
    for i, t in enumerate(tasks):
        await (w1 if i % 2 == 0 else w2).put(t)
    await w1.put(None)
    await w2.put(None)


async def main() -> None:
    w1_q: asyncio.Queue[Task | None] = asyncio.Queue()
    w2_q: asyncio.Queue[Task | None] = asyncio.Queue()
    results: asyncio.Queue[Result] = asyncio.Queue()

    jobs = [
        Task("a", "alpha"),
        Task("b", "beta"),
        Task("c", "gamma"),
        Task("d", "delta"),
    ]

    leader_task = asyncio.create_task(leader(jobs, w1_q, w2_q))
    w1 = asyncio.create_task(worker("worker-1", w1_q, results))
    w2 = asyncio.create_task(worker("worker-2", w2_q, results))

    await leader_task
    await asyncio.gather(w1, w2)

    collected: list[Result] = []
    while not results.empty():
        collected.append(results.get_nowait())
    collected.sort(key=lambda r: r.task_id)
    for r in collected:
        print(r.task_id, r.worker, "->", r.output)


if __name__ == "__main__":
    asyncio.run(main())
