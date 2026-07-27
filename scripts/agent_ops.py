from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from azure.ai.projects import AIProjectClient
from azure.identity import AzureDeveloperCliCredential
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
SERVICE_ROOT = ROOT / "src" / "agent-framework-agent-basic-responses"
RESULTS_ROOT = ROOT / ".foundry" / "results"

load_dotenv(SERVICE_ROOT / ".env", override=False)


@dataclass(frozen=True)
class FoundryContext:
    project_endpoint: str
    agent_name: str
    agent_version: str | None
    model_deployment: str | None
    tenant_id: str | None
    subscription_id: str | None
    resource_group: str | None
    location: str | None
    project_id: str | None
    application_insights_id: str | None


def azd_values() -> dict[str, str]:
    completed = subprocess.run(
        ["azd", "env", "get-values", "--cwd", str(ROOT)],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "AZURE_DEV_USER_AGENT": "microsoft_foundry_skill"},
    )
    values: dict[str, str] = {}
    for line in completed.stdout.splitlines():
        key, separator, value = line.partition("=")
        if separator:
            values[key] = value.strip().strip('"')
    return values


def _agent_bindings(values: dict[str, str]) -> list[tuple[str, str | None]]:
    bindings: list[tuple[str, str | None]] = []
    for key, value in values.items():
        if key.startswith("AGENT_") and key.endswith("_NAME") and value:
            prefix = key.removesuffix("_NAME")
            bindings.append((value, values.get(f"{prefix}_VERSION")))
    return bindings


def credential(tenant_id: str | None = None) -> AzureDeveloperCliCredential:
    return AzureDeveloperCliCredential(tenant_id=tenant_id, process_timeout=60)


def resolve_context(agent_name: str | None = None) -> FoundryContext:
    values = azd_values()
    endpoint = (
        os.getenv("FOUNDRY_PROJECT_ENDPOINT")
        or values.get("FOUNDRY_PROJECT_ENDPOINT")
        or values.get("AZURE_AI_PROJECT_ENDPOINT")
    )
    if not endpoint:
        raise RuntimeError("Foundry project endpoint is unavailable. Select an azd environment first.")

    selected_name = agent_name or os.getenv("AGENT_NAME")
    selected_version: str | None = None
    bindings = _agent_bindings(values)
    if not selected_name and len(bindings) == 1:
        selected_name, selected_version = bindings[0]
    elif selected_name:
        selected_version = next((version for name, version in bindings if name == selected_name), None)

    tenant_id = os.getenv("AZURE_TENANT_ID") or values.get("AZURE_TENANT_ID")
    with credential(tenant_id) as token_credential, AIProjectClient(
            endpoint=endpoint,
            credential=token_credential,
            allow_preview=True,
    ) as project:
        if selected_name:
            agent = dict(project.agents.get(agent_name=selected_name))
            latest = dict(agent.get("versions", {})).get("latest", {})
            selected_version = str(latest.get("version")) if latest.get("version") else selected_version
        else:
            agents = list(project.agents.list())
            if len(agents) != 1:
                names = [str(dict(agent).get("name")) for agent in agents]
                raise RuntimeError(f"Set AGENT_NAME because the project contains {len(agents)} agents: {names}")
            agent = dict(agents[0])
            selected_name = str(agent["name"])
            latest = dict(agent.get("versions", {})).get("latest", {})
            selected_version = str(latest.get("version")) if latest.get("version") else None

    return FoundryContext(
        project_endpoint=endpoint,
        agent_name=selected_name,
        agent_version=selected_version,
        model_deployment=os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")
        or values.get("AZURE_AI_MODEL_DEPLOYMENT_NAME"),
        tenant_id=tenant_id,
        subscription_id=values.get("AZURE_SUBSCRIPTION_ID"),
        resource_group=values.get("AZURE_RESOURCE_GROUP"),
        location=values.get("AZURE_LOCATION"),
        project_id=values.get("AZURE_AI_PROJECT_ID"),
        application_insights_id=values.get("APPLICATIONINSIGHTS_RESOURCE_ID"),
    )


def hosted_response(query: str, context: FoundryContext) -> dict[str, Any]:
    started = time.perf_counter()
    with credential(context.tenant_id) as token_credential, AIProjectClient(
        endpoint=context.project_endpoint,
        credential=token_credential,
        allow_preview=True,
    ) as project, project.get_openai_client(agent_name=context.agent_name) as client:
        response = client.responses.create(input=query)
    return {
        "target": "hosted",
        "query": query,
        "response": response.output_text,
        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        "response_id": response.id,
        "usage": response.usage.to_dict() if response.usage else None,
    }


async def _local_responses_async(queries: list[str]) -> list[dict[str, Any]]:
    sys.path.insert(0, str(SERVICE_ROOT))
    from main import create_agent

    responses = []
    async with create_agent() as agent:
        for query in queries:
            started = time.perf_counter()
            try:
                result = await agent.run(query)
                responses.append(
                    {
                        "target": "local",
                        "query": query,
                        "response": result.messages[-1].text,
                        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                        "messages": [message.to_dict() for message in result.messages],
                    }
                )
            except Exception as error:  # noqa: BLE001 - preserve local comparison failures
                responses.append(
                    {
                        "target": "local",
                        "query": query,
                        "error_type": type(error).__name__,
                        "error": str(error),
                    }
                )
    return responses


def local_responses(queries: list[str]) -> list[dict[str, Any]]:
    return asyncio.run(_local_responses_async(queries))


def local_response(query: str) -> dict[str, Any]:
    result = local_responses([query])[0]
    if "error" in result:
        raise RuntimeError(result["error"])
    return result


def load_queries(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def write_result(name: str, payload: Any) -> Path:
    RESULTS_ROOT.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    path = RESULTS_ROOT / f"{name}-{timestamp}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path