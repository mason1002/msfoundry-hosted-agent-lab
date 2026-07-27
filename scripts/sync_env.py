from __future__ import annotations

from agent_ops import SERVICE_ROOT, azd_values


ALLOWED_KEYS = (
    "FOUNDRY_PROJECT_ENDPOINT",
    "AZURE_AI_MODEL_DEPLOYMENT_NAME",
    "AZURE_TENANT_ID",
)


def main() -> None:
    values = azd_values()
    lines = []
    for key in ALLOWED_KEYS:
        value = values.get(key)
        if value:
            escaped = value.replace('"', '\\"')
            lines.append(f'{key}="{escaped}"')
    if len(lines) < 2:
        raise RuntimeError("The selected azd environment does not contain the Foundry endpoint and model deployment.")
    target = SERVICE_ROOT / ".env"
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {target} with {len(lines)} non-secret settings.")


if __name__ == "__main__":
    main()