from __future__ import annotations

import json

import requests

from azure.ai.projects import AIProjectClient

try:
    from .agent_ops import credential, resolve_context
except ImportError:
    from agent_ops import credential, resolve_context


MANAGEMENT_SCOPE = "https://management.azure.com/.default"
APP_INSIGHTS_SCOPE = "https://api.applicationinsights.io/.default"


def app_insights_app_id(subscription_id: str, resource_group: str, token: str) -> str:
    url = (
        f"https://management.azure.com/subscriptions/{subscription_id}"
        f"/resourceGroups/{resource_group}/resources?api-version=2021-04-01"
    )
    response = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=60)
    response.raise_for_status()
    resources = [
        resource
        for resource in response.json().get("value", [])
        if resource.get("type", "").lower() == "microsoft.insights/components"
    ]
    if len(resources) != 1:
        raise RuntimeError(f"Expected one Application Insights resource, found {len(resources)}")
    response = requests.get(
        f"https://management.azure.com{resources[0]['id']}?api-version=2020-02-02",
        headers={"Authorization": f"Bearer {token}"},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["properties"]["AppId"]


def app_insights_query(app_id: str, query: str, token: str) -> dict:
    response = requests.get(
        f"https://api.applicationinsights.io/v1/apps/{app_id}/query",
        headers={"Authorization": f"Bearer {token}"},
        params={"query": query},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def main() -> None:
    context = resolve_context()
    with credential(context.tenant_id) as token_credential, AIProjectClient(
        endpoint=context.project_endpoint,
        credential=token_credential,
        allow_preview=True,
    ) as project:
        sessions = list(project.agents.list_sessions(agent_name=context.agent_name))
        version_sessions = [
            session
            for session in sessions
            if str(dict(dict(session)["version_indicator"]).get("agent_version")) == context.agent_version
        ]
        if not version_sessions:
            raise RuntimeError(f"No sessions were found for {context.agent_name} v{context.agent_version}")
        latest = max(version_sessions, key=lambda item: dict(item).get("created_at", 0))
        session = dict(latest)
        version = str(dict(session["version_indicator"])["agent_version"])
        stream = project.agents.get_session_log_stream(
            agent_name=context.agent_name,
            agent_version=version,
            session_id=session["agent_session_id"],
        )
        log_chunks: list[bytes] = []
        for chunk in stream:
            log_chunks.append(chunk)
            if (
                b"appinsights_configured=" in chunk
                or b"xAgent telemetry bootstrap" in chunk
                or len(log_chunks) >= 10
            ):
                break
        log_text = b"".join(log_chunks).decode("utf-8", errors="replace")

        if not context.subscription_id or not context.resource_group:
            raise RuntimeError("Subscription and resource group must be available from azd.")
        app_id = app_insights_app_id(
            context.subscription_id,
            context.resource_group,
            token_credential.get_token(MANAGEMENT_SCOPE).token,
        )
        ingestion = app_insights_query(
            app_id,
            "union withsource=TableName requests, dependencies, traces, customEvents "
            "| where timestamp > ago(24h) | summarize Rows=count() by TableName",
            token_credential.get_token(APP_INSIGHTS_SCOPE).token,
        )
        genai = app_insights_query(
            app_id,
            "dependencies | where timestamp > ago(24h) "
            "| extend Operation=tostring(customDimensions['gen_ai.operation.name']), "
            "Agent=tostring(customDimensions['gen_ai.agent.name']), "
            "InputTokens=tolong(customDimensions['gen_ai.usage.input_tokens']), "
            "OutputTokens=tolong(customDimensions['gen_ai.usage.output_tokens']) "
            "| where isnotempty(Operation) "
            "| summarize Spans=count(), InputTokens=sum(InputTokens), "
            "OutputTokens=sum(OutputTokens) by Operation, Agent",
            token_credential.get_token(APP_INSIGHTS_SCOPE).token,
        )

    configured = (
        'appinsights_configured=True' in log_text
        or 'xAgent telemetry bootstrap: appinsights=True' in log_text
    )
    print(f"Agent: {context.agent_name} v{version}")
    print(f"Application Insights configured in container: {configured}")
    print(json.dumps(ingestion, indent=2))
    print(json.dumps(genai, indent=2))
    if not configured:
        raise SystemExit(2)


if __name__ == "__main__":
    main()