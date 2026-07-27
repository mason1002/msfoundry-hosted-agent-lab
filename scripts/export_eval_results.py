import argparse
import json
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential


def serialize(value):
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if hasattr(value, "__dict__"):
        return {
            key: serialize(item)
            for key, item in vars(value).items()
            if not key.startswith("_")
        }
    if isinstance(value, list):
        return [serialize(item) for item in value]
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-endpoint", required=True)
    parser.add_argument("--eval-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    credential = DefaultAzureCredential()
    project = AIProjectClient(endpoint=args.project_endpoint, credential=credential)
    client = project.get_openai_client()
    items = list(
        client.evals.runs.output_items.list(
            eval_id=args.eval_id,
            run_id=args.run_id,
        )
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps([serialize(item) for item in items], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Exported {len(items)} evaluation output items to {args.output}")


if __name__ == "__main__":
    main()