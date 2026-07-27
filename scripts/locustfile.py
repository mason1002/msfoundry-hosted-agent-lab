from __future__ import annotations

import random
import time
from pathlib import Path

from locust import User, between, events, task

from agent_ops import hosted_response, load_queries, resolve_context


CONTEXT = resolve_context()
DATASET_PATH = Path("src/agent-framework-agent-basic-responses/tests/queries.jsonl")
QUERIES = [
    row["query"]
    for row in load_queries(DATASET_PATH)
]


class HostedAgentUser(User):
    wait_time = between(1, 3)

    @task
    def single_turn(self) -> None:
        query = random.choice(QUERIES)
        started = time.perf_counter()
        error: Exception | None = None
        response_length = 0
        try:
            result = hosted_response(query, CONTEXT)
            response_length = len(result["response"] or "")
        except Exception as caught:  # noqa: BLE001 - report all request failures to Locust
            error = caught

        events.request.fire(
            request_type="foundry_agent",
            name="responses.create",
            response_time=(time.perf_counter() - started) * 1000,
            response_length=response_length,
            exception=error,
            context={},
        )