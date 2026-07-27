from __future__ import annotations

try:
    from .agent_ops import credential, resolve_context
    from .deploy_existing_agent import (
        MANAGEMENT_SCOPE,
        MONITORING_METRICS_PUBLISHER_ROLE,
        arm_put,
        ensure_role,
        find_app_insights,
        project_principal_id,
    )
except ImportError:
    from agent_ops import credential, resolve_context
    from deploy_existing_agent import (
        MANAGEMENT_SCOPE,
        MONITORING_METRICS_PUBLISHER_ROLE,
        arm_put,
        ensure_role,
        find_app_insights,
        project_principal_id,
    )


LOG_ANALYTICS_READER_ROLE = "73c42c96-874c-492b-b04d-ab87d138a893"


def main() -> None:
    context = resolve_context()
    if not all((context.subscription_id, context.resource_group, context.project_id)):
        raise RuntimeError("Subscription, resource group, and Foundry project ID must be available from azd.")

    with credential(context.tenant_id) as token_credential:
        token = token_credential.get_token(MANAGEMENT_SCOPE).token
        app_insights = find_app_insights(context.subscription_id, context.resource_group, token)
        project_principal = project_principal_id(context.project_id, token)
        ensure_role(
            app_insights["id"],
            context.subscription_id,
            project_principal,
            MONITORING_METRICS_PUBLISHER_ROLE,
            token,
        )
        ensure_role(
            app_insights["id"],
            context.subscription_id,
            project_principal,
            LOG_ANALYTICS_READER_ROLE,
            token,
        )
        connection_name = app_insights["name"]
        connection = arm_put(
            f"https://management.azure.com{context.project_id}/connections/{connection_name}"
            "?api-version=2025-06-01",
            token,
            {
                "properties": {
                    "authType": "ProjectManagedIdentity",
                    "category": "AppInsights",
                    "target": app_insights["id"],
                    "metadata": {"purpose": "agent-tracing-monitoring"},
                }
            },
        )
    print(f"Connection: {connection.get('name', connection_name)}")
    print("Auth: ProjectManagedIdentity")
    print("Project roles: Monitoring Metrics Publisher, Log Analytics Reader")


if __name__ == "__main__":
    main()