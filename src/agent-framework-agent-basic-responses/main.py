# Copyright (c) Microsoft. All rights reserved.

import logging
import os

from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from agent_framework.observability import enable_instrumentation
from agent_framework_foundry_hosting import ResponsesHostServer
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import trace
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger("xagent")
logger.setLevel(logging.INFO)


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
    if connection_string:
        os.environ.pop("APPLICATIONINSIGHTS_CONNECTION_STRING", None)
        configure_azure_monitor(
            connection_string=connection_string,
            credential=ManagedIdentityCredential(),
            enable_live_metrics=False,
        )
    enable_instrumentation(enable_sensitive_data=False)
    print(
        "xAgent telemetry bootstrap: "
        f"appinsights={bool(connection_string)} "
        f"aad={bool(os.getenv('APPLICATIONINSIGHTS_AUTHENTICATION_STRING'))} "
        f"otel_disabled={os.getenv('OTEL_SDK_DISABLED', '(unset)')} "
        f"provider={type(trace.get_tracer_provider()).__name__}",
        flush=True,
    )
    logger.info(
        "Telemetry configured: appinsights=%s aad=%s sensitive_data=false",
        bool(connection_string),
        bool(os.getenv("APPLICATIONINSIGHTS_AUTHENTICATION_STRING")),
    )
    with trace.get_tracer("xagent.startup").start_as_current_span("xagent.startup"):
        pass
    provider = trace.get_tracer_provider()
    if hasattr(provider, "force_flush"):
        provider.force_flush(timeout_millis=10000)
    server = ResponsesHostServer(create_agent())
    server.run()


if __name__ == "__main__":
    main()
