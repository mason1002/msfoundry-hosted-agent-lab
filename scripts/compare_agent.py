from __future__ import annotations

import argparse
from pathlib import Path

from agent_ops import hosted_response, load_queries, local_responses, resolve_context, write_result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one dataset against local and/or hosted xAgent.")
    parser.add_argument("--target", choices=("local", "hosted", "both"), default="both")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("src/agent-framework-agent-basic-responses/tests/queries.jsonl"),
    )
    parser.add_argument("--limit", type=int)
    parser.add_argument("--agent-name")
    args = parser.parse_args()

    rows = load_queries(args.dataset)
    if args.limit:
        rows = rows[: args.limit]
    context = resolve_context(args.agent_name) if args.target in ("hosted", "both") else None
    local_results = (
        local_responses([row["query"] for row in rows])
        if args.target in ("local", "both")
        else []
    )
    results = []
    failures = 0
    for index, row in enumerate(rows, 1):
        query = row["query"]
        print(f"[{index}/{len(rows)}] {query}")
        item = {"query": query, "expected_behavior": row.get("expected_behavior")}
        if args.target in ("local", "both"):
            item["local"] = local_results[index - 1]
            if "error" not in item["local"]:
                print(f"  local  {item['local']['latency_ms']} ms")
            else:
                failures += 1
                print(f"  local  ERROR {item['local']['error_type']}")
        if context and args.target in ("hosted", "both"):
            try:
                item["hosted"] = hosted_response(query, context)
                print(f"  hosted {item['hosted']['latency_ms']} ms")
            except Exception as error:  # noqa: BLE001 - Guardrail failures are comparison evidence
                failures += 1
                item["hosted"] = {"error_type": type(error).__name__, "error": str(error)}
                print(f"  hosted ERROR {type(error).__name__}")
        results.append(item)

    path = write_result("agent-comparison", results)
    print(f"Results: {path}")
    print(f"Invocation failures recorded: {failures}")


if __name__ == "__main__":
    main()