from __future__ import annotations

import hashlib
import tempfile
import time
import uuid
import zipfile
from pathlib import Path
from typing import Any

import requests
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    AgentEndpointConfig,
    CodeConfiguration,
    CodeDependencyResolution,
    FixedRatioVersionSelectionRule,
    HostedAgentDefinition,
    ProtocolConfiguration,
    ProtocolVersionRecord,
    ResponsesProtocolConfiguration,
    VersionSelector,
)

try:
    from .agent_ops import SERVICE_ROOT, credential, resolve_context
except ImportError:
    from agent_ops import SERVICE_ROOT, credential, resolve_context


MANAGEMENT_SCOPE = "https://management.azure.com/.default"
MONITORING_METRICS_PUBLISHER_ROLE = "3913510d-42f4-4e42-8a64-420c390055eb"
EXCLUDED_NAMES = {
    ".agent_configs",
    ".agentignore",
    ".azdignore",
    ".dockerignore",
    ".env",
    ".env.example",
    ".venv",
    ".venv-devui",
    "Dockerfile",
    "__pycache__",
    "datasets",
    "devui.py",
    "eval.yaml",
    "eval-security.yaml",
    "evaluators",
    "requirements-dev.txt",
    "tests",
}


def arm_get(url: str, token: str) -> dict[str, Any]:
    response = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=60)
    response.raise_for_status()
    return response.json()


def arm_put(url: str, token: str, body: dict[str, Any]) -> dict[str, Any]:
    response = requests.put(
        url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=body,
        timeout=60,
    )
    if response.status_code == 409:
        return {"status": "already_exists"}
    response.raise_for_status()
    return response.json()


def find_app_insights(subscription_id: str, resource_group: str, token: str) -> dict[str, Any]:
    url = (
        f"https://management.azure.com/subscriptions/{subscription_id}"
        f"/resourceGroups/{resource_group}/resources?api-version=2021-04-01"
    )
    resources = [
        resource
        for resource in arm_get(url, token).get("value", [])
        if resource.get("type", "").lower() == "microsoft.insights/components"
    ]
    if len(resources) != 1:
        raise RuntimeError(f"Expected one Application Insights resource, found {len(resources)}")
    return arm_get(f"https://management.azure.com{resources[0]['id']}?api-version=2020-02-02", token)


def ensure_role(scope: str, subscription_id: str, principal_id: str, role_id: str, token: str) -> None:
    assignment_id = uuid.uuid5(uuid.NAMESPACE_URL, f"{scope}:{principal_id}:{role_id}")
    role_definition_id = (
        f"/subscriptions/{subscription_id}/providers/Microsoft.Authorization/roleDefinitions/"
        f"{role_id}"
    )
    arm_put(
        f"https://management.azure.com{scope}/providers/Microsoft.Authorization/roleAssignments/"
        f"{assignment_id}?api-version=2022-04-01",
        token,
        {
            "properties": {
                "roleDefinitionId": role_definition_id,
                "principalId": principal_id,
                "principalType": "ServicePrincipal",
            }
        },
    )


def ensure_telemetry_role(scope: str, subscription_id: str, principal_id: str, token: str) -> None:
    ensure_role(scope, subscription_id, principal_id, MONITORING_METRICS_PUBLISHER_ROLE, token)


def project_principal_id(project_id: str, token: str) -> str:
    project = arm_get(f"https://management.azure.com{project_id}?api-version=2025-06-01", token)
    principal_id = project.get("identity", {}).get("principalId")
    if not principal_id:
        raise RuntimeError("The Foundry Project has no managed identity.")
    return principal_id


def create_code_zip() -> tuple[Path, str]:
    path = Path(tempfile.gettempdir()) / "xagent-hosted-source.zip"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for source in SERVICE_ROOT.rglob("*"):
            relative = source.relative_to(SERVICE_ROOT)
            if not source.is_file() or any(part in EXCLUDED_NAMES for part in relative.parts):
                continue
            archive.write(source, relative)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return path, digest


def wait_for_active(project: AIProjectClient, agent_name: str, version: str) -> None:
    for attempt in range(60):
        details = project.agents.get_version(agent_name=agent_name, agent_version=version)
        status = dict(details).get("status")
        print(f"Version {version}: {status} ({attempt + 1}/60)")
        if status == "active":
            return
        if status == "failed":
            raise RuntimeError(f"Hosted Agent version {version} failed: {dict(details)}")
        time.sleep(10)
    raise TimeoutError(f"Timed out waiting for Hosted Agent version {version}")


def route_version(project: AIProjectClient, agent_name: str, version: str) -> None:
    project.agents.update_details(
        agent_name=agent_name,
        agent_endpoint=AgentEndpointConfig(
            version_selector=VersionSelector(
                version_selection_rules=[
                    FixedRatioVersionSelectionRule(agent_version=version, traffic_percentage=100)
                ]
            ),
            protocol_configuration=ProtocolConfiguration(responses=ResponsesProtocolConfiguration()),
        ),
    )


def smoke_test(project: AIProjectClient, agent_name: str) -> None:
    error: Exception | None = None
    for attempt in range(3):
        try:
            with project.get_openai_client(agent_name=agent_name) as client:
                response = client.responses.create(input="Reply with exactly: READY")
            if response.output_text:
                print(f"Endpoint smoke test passed ({attempt + 1}/3)")
                return
        except Exception as caught:  # noqa: BLE001 - rollback on any readiness failure
            error = caught
        time.sleep(10)
    raise RuntimeError(f"Endpoint smoke test failed: {error}")


def main() -> None:
    context = resolve_context()
    if not all(
        (context.subscription_id, context.resource_group, context.model_deployment, context.project_id)
    ):
        raise RuntimeError("Subscription, resource group, project ID, and model deployment must be available from azd.")

    with credential(context.tenant_id) as token_credential, AIProjectClient(
        endpoint=context.project_endpoint,
        credential=token_credential,
        allow_preview=True,
    ) as project:
        agent_details = dict(project.agents.get(agent_name=context.agent_name))
        endpoint = dict(agent_details.get("agent_endpoint", {}))
        rules = dict(endpoint.get("version_selector", {})).get("version_selection_rules", [])
        original_version = str(rules[0]["agent_version"]) if rules else context.agent_version
        current = dict(project.agents.get_version(context.agent_name, context.agent_version or "latest"))
        principal_id = dict(current.get("instance_identity", {})).get("principal_id")
        rai_config = dict(current.get("definition", {})).get("rai_config")
        if not principal_id:
            raise RuntimeError("The current Hosted Agent version has no instance identity.")

        token = token_credential.get_token(MANAGEMENT_SCOPE).token
        app_insights = find_app_insights(context.subscription_id, context.resource_group, token)
        ensure_telemetry_role(app_insights["id"], context.subscription_id, principal_id, token)
        ensure_telemetry_role(
            app_insights["id"],
            context.subscription_id,
            project_principal_id(context.project_id, token),
            token,
        )
        connection_string = app_insights.get("properties", {}).get("ConnectionString")
        if not connection_string:
            raise RuntimeError("Application Insights connection string is unavailable.")

        code_path, digest = create_code_zip()
        with code_path.open("rb") as code:
            created = project.agents.create_version_from_code(
                agent_name=context.agent_name,
                description="xAgent with AAD-authenticated Application Insights telemetry.",
                definition=HostedAgentDefinition(
                    cpu="0.5",
                    memory="1Gi",
                    code_configuration=CodeConfiguration(
                        runtime="python_3_13",
                        entry_point=["python", "main.py"],
                        dependency_resolution=CodeDependencyResolution.REMOTE_BUILD,
                    ),
                    environment_variables={
                        "AZURE_AI_MODEL_DEPLOYMENT_NAME": context.model_deployment,
                        "XAGENT_APPLICATIONINSIGHTS_CONNECTION_STRING": connection_string,
                        "APPLICATIONINSIGHTS_AUTHENTICATION_STRING": "Authorization=AAD",
                    },
                    protocol_versions=[ProtocolVersionRecord(protocol="responses", version="2.0.0")],
                    rai_config=rai_config,
                ),
                code=code,
                code_zip_sha256=digest,
            )
        version = str(created.version)
        wait_for_active(project, context.agent_name, version)
        route_version(project, context.agent_name, version)
        try:
            smoke_test(project, context.agent_name)
        except Exception:
            if original_version:
                route_version(project, context.agent_name, original_version)
                print(f"Rolled back endpoint to v{original_version}")
            raise

    print(f"Deployed and routed {context.agent_name} v{version}")
    print("Application Insights: AAD authentication enabled; sensitive trace content disabled in code.")


if __name__ == "__main__":
    main()