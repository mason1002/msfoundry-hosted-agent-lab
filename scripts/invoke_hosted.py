from __future__ import annotations

import argparse

from agent_ops import hosted_response, resolve_context


def main() -> None:
    parser = argparse.ArgumentParser(description="Invoke the deployed Foundry Hosted Agent through the SDK.")
    parser.add_argument("prompt")
    parser.add_argument("--agent-name")
    args = parser.parse_args()

    context = resolve_context(args.agent_name)
    result = hosted_response(args.prompt, context)
    print(f"Agent: {context.agent_name} v{context.agent_version or 'latest'}")
    print(f"Latency: {result['latency_ms']} ms")
    print(result["response"])


if __name__ == "__main__":
    main()