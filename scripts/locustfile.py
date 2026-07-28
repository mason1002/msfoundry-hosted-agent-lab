from __future__ import annotations

import random
import time

from locust import User, between, events, task

from agent_ops import hosted_response, resolve_context


CONTEXT = resolve_context()
QUERIES = [
    "请用两点说明如何验证 Hosted Agent。",
    "请说明本地运行和 Foundry 托管部署的区别。",
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