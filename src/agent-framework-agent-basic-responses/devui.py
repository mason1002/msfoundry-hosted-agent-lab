from agent_framework.devui import serve

from main import create_agent


if __name__ == "__main__":
    serve(
        entities=[create_agent()],
        host="127.0.0.1",
        port=8080,
        auto_open=True,
        auth_enabled=False,
    )