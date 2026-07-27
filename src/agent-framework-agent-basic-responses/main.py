# Copyright (c) Microsoft. All rights reserved.

import os

from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from agent_framework_foundry_hosting import ResponsesHostServer
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


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
    server = ResponsesHostServer(create_agent())
    server.run()


if __name__ == "__main__":
    main()
