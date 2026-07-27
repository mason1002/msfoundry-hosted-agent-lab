from __future__ import annotations

import argparse
from typing import Any

import requests

from agent_ops import credential, resolve_context


MANAGEMENT_SCOPE = "https://management.azure.com/.default"


def application_insights_id(subscription_id: str, resource_group: str, token: str) -> str:
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
    return resources[0]["id"]


def put(url: str, token: str, body: dict[str, Any]) -> dict[str, Any]:
    response = requests.put(
        url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=body,
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an Azure Monitor alert for continuous-eval pass rate.")
    parser.add_argument("--agent-name")
    parser.add_argument("--threshold", type=float, default=0.9)
    parser.add_argument("--email")
    args = parser.parse_args()
    if not 0 < args.threshold <= 1:
        raise SystemExit("--threshold must be greater than 0 and at most 1")

    context = resolve_context(args.agent_name)
    required = {
        "subscription": context.subscription_id,
        "resource group": context.resource_group,
        "location": context.location,
        "project ID": context.project_id,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise RuntimeError(f"Missing azd context: {', '.join(missing)}")

    token = credential(context.tenant_id).get_token(MANAGEMENT_SCOPE).token
    app_insights_id = context.application_insights_id or application_insights_id(
        context.subscription_id,
        context.resource_group,
        token,
    )
    base = (
        f"https://management.azure.com/subscriptions/{context.subscription_id}"
        f"/resourceGroups/{context.resource_group}/providers/Microsoft.Insights"
    )
    action_group_ids: list[str] = []
    if args.email:
        action_group_name = f"{context.agent_name}-eval-alerts"
        action_group = put(
            f"{base}/actionGroups/{action_group_name}?api-version=2023-01-01",
            token,
            {
                "location": "Global",
                "properties": {
                    "groupShortName": "AgentEval",
                    "enabled": True,
                    "emailReceivers": [
                        {
                            "name": "EvaluationAlert",
                            "emailAddress": args.email,
                            "useCommonAlertSchema": True,
                        }
                    ],
                },
            },
        )
        action_group_ids.append(action_group["id"])

    query = f'''customEvents
| where name == "gen_ai.evaluation.result"
| extend AgentName = tostring(customDimensions["gen_ai.agent.name"])
| extend ScoreLabel = tostring(customDimensions["gen_ai.evaluation.score.label"])
| where AgentName == "{context.agent_name}"
| summarize PassRate = todouble(countif(ScoreLabel == "pass")) / count()'''
    rule_name = f"{context.agent_name}-eval-pass-rate"
    rule = put(
        f"{base}/scheduledQueryRules/{rule_name}?api-version=2023-12-01",
        token,
        {
            "location": context.location,
            "kind": "LogAlert",
            "tags": {"agent_name": context.agent_name, "category": "evaluation"},
            "properties": {
                "displayName": f"Evaluation pass rate - {context.agent_name}",
                "description": "Alerts when continuous evaluation pass rate falls below the configured threshold.",
                "severity": 3,
                "enabled": True,
                "evaluationFrequency": "PT5M",
                "scopes": [app_insights_id],
                "targetResourceTypes": ["microsoft.insights/components"],
                "windowSize": "PT1H",
                "actions": {"actionGroups": action_group_ids},
                "criteria": {
                    "allOf": [
                        {
                            "query": query,
                            "timeAggregation": "Average",
                            "metricMeasureColumn": "PassRate",
                            "operator": "LessThan",
                            "threshold": args.threshold,
                            "failingPeriods": {
                                "numberOfEvaluationPeriods": 1,
                                "minFailingPeriodsToAlert": 1,
                            },
                        }
                    ]
                },
                "autoMitigate": True,
            },
        },
    )
    print(f"Alert rule: {rule['name']}")
    print(f"Enabled: {rule['properties']['enabled']}")
    print(f"Threshold: {args.threshold:.0%}")
    print(f"Action groups: {len(action_group_ids)}")


if __name__ == "__main__":
    main()