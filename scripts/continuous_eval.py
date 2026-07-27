from __future__ import annotations

import argparse

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    AzureAIDataSourceConfig,
    EvaluationScheduleTask,
    HourlyRecurrenceSchedule,
    RecurrenceTrigger,
    Schedule,
    TestingCriterionAzureAIEvaluator,
)

from agent_ops import credential, resolve_context


QUALITY_EVALUATORS = ("task_adherence", "intent_resolution", "relevance")
SAFETY_EVALUATORS = ("violence", "self_harm", "sexual", "hate_unfairness", "indirect_attack")


def criterion(name: str, deployment_name: str | None) -> TestingCriterionAzureAIEvaluator:
    arguments = {
        "type": "azure_ai_evaluator",
        "name": name.replace("_", " ").title(),
        "evaluator_name": f"builtin.{name}",
        "data_mapping": {"query": "{{item.query}}", "response": "{{item.response}}"},
    }
    if deployment_name:
        arguments["initialization_parameters"] = {"deployment_name": deployment_name}
    return TestingCriterionAzureAIEvaluator(**arguments)


def main() -> None:
    parser = argparse.ArgumentParser(description="Configure hourly evaluation over recent Hosted Agent traces.")
    parser.add_argument("--agent-name")
    parser.add_argument("--max-traces", type=int, default=100)
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    if args.max_traces < 1 or args.max_traces > 1000:
        raise SystemExit("--max-traces must be between 1 and 1000")

    context = resolve_context(args.agent_name)
    if not context.model_deployment:
        raise RuntimeError("AZURE_AI_MODEL_DEPLOYMENT_NAME is required for quality evaluators.")
    schedule_id = f"{context.agent_name}-continuous-eval"

    with credential(context.tenant_id) as token_credential, AIProjectClient(
        endpoint=context.project_endpoint,
        credential=token_credential,
        allow_preview=True,
    ) as project, project.get_openai_client() as openai_client:
        existing = next(
            (schedule for schedule in project.beta.schedules.list() if schedule.schedule_id == schedule_id),
            None,
        )
        if existing and not args.replace:
            print(f"Schedule already exists: {schedule_id} enabled={existing.enabled}")
            return
        if existing:
            project.beta.schedules.delete(schedule_id)

        evaluation = openai_client.evals.create(
            name=f"Continuous Evaluation - {context.agent_name}",
            data_source_config=AzureAIDataSourceConfig(type="azure_ai_source", scenario="responses"),
            testing_criteria=[
                *(criterion(name, context.model_deployment) for name in QUALITY_EVALUATORS),
                *(criterion(name, None) for name in SAFETY_EVALUATORS),
            ],
        )
        schedule = Schedule(
            display_name=f"Continuous Eval - {context.agent_name}",
            enabled=True,
            trigger=RecurrenceTrigger(interval=1, schedule=HourlyRecurrenceSchedule()),
            task=EvaluationScheduleTask(
                eval_id=evaluation.id,
                eval_run={
                    "data_source": {
                        "type": "azure_ai_traces",
                        "agent_name": context.agent_name,
                        "max_traces": args.max_traces,
                    }
                },
            ),
            properties={"target_default": "true", "target_type": "AzureAITraces"},
        )
        result = project.beta.schedules.create_or_update(schedule_id=schedule_id, schedule=schedule)

    print(f"Agent: {context.agent_name} v{context.agent_version or 'latest'}")
    print(f"Evaluation: {evaluation.id}")
    print(f"Schedule: {result.schedule_id} enabled={result.enabled}")
    print("Trigger: hourly")
    print(f"Max traces per run: {args.max_traces}")


if __name__ == "__main__":
    main()