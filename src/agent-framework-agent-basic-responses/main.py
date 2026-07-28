# Copyright (c) Microsoft. All rights reserved.

import logging
import os
from contextvars import ContextVar
from typing import Any

from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from agent_framework.observability import enable_instrumentation
from agent_framework_foundry_hosting import ResponsesHostServer
from azure.ai.agentserver.responses import ResponsesServerOptions
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from azure.monitor.opentelemetry import configure_azure_monitor
from dotenv import load_dotenv
from opentelemetry import context, trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, Span, SpanProcessor

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger("xagent")
logger.setLevel(logging.INFO)


class FoundryIdentitySpanProcessor(SpanProcessor):
    def on_start(self, span: Span, parent_context: context.Context | None = None) -> None:
        attributes = {
            "microsoft.foundry.project.id": os.getenv("FOUNDRY_PROJECT_ARM_ID"),
            "gen_ai.agent.name": os.getenv("FOUNDRY_AGENT_NAME"),
            "gen_ai.agent.version": os.getenv("FOUNDRY_AGENT_VERSION"),
            "microsoft.gen_ai.main_agent.name": os.getenv("FOUNDRY_AGENT_NAME"),
            "microsoft.gen_ai.main_agent.id": os.getenv("FOUNDRY_AGENT_ID"),
            "microsoft.gen_ai.main_agent.version": os.getenv("FOUNDRY_AGENT_VERSION"),
        }
        for key, value in attributes.items():
            if value:
                span.set_attribute(key, value)

    def on_end(self, span: ReadableSpan) -> None:
        pass

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True


class ResponsesOpenTelemetryHook:
    def __init__(self) -> None:
        self._span: ContextVar[Span | None] = ContextVar("responses_create_span", default=None)
        self._token: ContextVar[object | None] = ContextVar("responses_create_token", default=None)

    def on_span_start(self, name: str, tags: dict[str, Any]) -> None:
        span = trace.get_tracer("azure.ai.agentserver.responses").start_span(name, attributes=tags)
        token = context.attach(trace.set_span_in_context(span))
        self._span.set(span)
        self._token.set(token)

    def on_span_end(self, name: str, tags: dict[str, Any], error: BaseException | None) -> None:
        span = self._span.get()
        if span is None:
            return
        for key, value in tags.items():
            if value is not None:
                span.set_attribute(key, value)
        if error is not None:
            span.record_exception(error)
            span.set_status(trace.StatusCode.ERROR, str(error))
        span.end()
        token = self._token.get()
        if token is not None:
            context.detach(token)
        provider = trace.get_tracer_provider()
        if hasattr(provider, "force_flush"):
            provider.force_flush(timeout_millis=5000)


def configure_hosted_observability(
    *,
    connection_string: str | None = None,
    log_level: str | None = None,
    enable_sensitive_data: bool = False,
) -> None:
    connection_string = os.getenv("XAGENT_APPLICATIONINSIGHTS_CONNECTION_STRING")
    os.environ.pop("APPLICATIONINSIGHTS_CONNECTION_STRING", None)
    logging.basicConfig(
        level=getattr(logging, (log_level or "INFO").upper()),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    configure_azure_monitor(
        connection_string=connection_string,
        credential=ManagedIdentityCredential(),
        enable_live_metrics=False,
        enable_performance_counters=False,
        resource=Resource.create(
            {"service.name": os.getenv("FOUNDRY_AGENT_NAME", "azure.ai.agentserver")}
        ),
        span_processors=[FoundryIdentitySpanProcessor()],
    )
    enable_instrumentation(enable_sensitive_data=enable_sensitive_data)


def create_agent() -> Agent:
    model_name = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME") or os.getenv("FOUNDRY_MODEL_NAME")
    if not model_name:
        raise RuntimeError(
            "Model deployment name is not configured. Set "
            "AZURE_AI_MODEL_DEPLOYMENT_NAME or FOUNDRY_MODEL_NAME."
        )

    client = FoundryChatClient(
        project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
        model=model_name,
        credential=DefaultAzureCredential(),
    )

    return Agent(
        client=client,
        name="xAgent",
        instructions=(
            "You are xAgent, a concise reference assistant for Microsoft Foundry Agents. "
            "Explain how to build, run locally, deploy as a hosted agent, invoke, test, "
            "evaluate, monitor, version, and clean up an Agent Framework application. "
            "Use short numbered steps when describing a procedure. Distinguish local "
            "execution from hosted deployment, and never invent resource names, endpoints, "
            "test results, or deployment status."
        ),
        # History will be managed by the hosting infrastructure, thus there
        # is no need to store history by the service. Learn more at:
        # https://developers.openai.com/api/reference/resources/responses/methods/create
        default_options={"store": False},
    )


def main():
    connection_string = os.getenv("XAGENT_APPLICATIONINSIGHTS_CONNECTION_STRING")
    os.environ["OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"] = "false"
    print(
        "xAgent telemetry bootstrap: "
        f"appinsights={bool(connection_string)} "
        f"aad={bool(os.getenv('APPLICATIONINSIGHTS_AUTHENTICATION_STRING'))} "
        f"otel_disabled={os.getenv('OTEL_SDK_DISABLED', '(unset)')} "
        "provider=hosted-server",
        flush=True,
    )
    logger.info(
        "Telemetry configured: appinsights=%s aad=%s sensitive_data=false",
        bool(connection_string),
        bool(os.getenv("APPLICATIONINSIGHTS_AUTHENTICATION_STRING")),
    )
    server = ResponsesHostServer(
        create_agent(),
        configure_observability=configure_hosted_observability,
        options=ResponsesServerOptions(create_span_hook=ResponsesOpenTelemetryHook()),
    )
    server.run()


if __name__ == "__main__":
    main()
