from __future__ import annotations

from agent_ops import resolve_context


def main() -> None:
    context = resolve_context()
    values = {
        "Foundry Project Endpoint": context.project_endpoint,
        "Agent Name": context.agent_name,
        "Agent Version": context.agent_version,
        "Model Deployment": context.model_deployment,
        "Resource Group": context.resource_group,
        "Location": context.location,
    }
    width = max(len(name) for name in values)
    for name, value in values.items():
        print(f"{name:<{width}} : {value or '(not configured)'}")


if __name__ == "__main__":
    main()