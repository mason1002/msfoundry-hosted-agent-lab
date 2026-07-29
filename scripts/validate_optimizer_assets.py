from __future__ import annotations

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SERVICE_ROOT = ROOT / "src" / "agent-framework-agent-basic-responses"
RECIPE_PATH = SERVICE_ROOT / "eval-optimize.yaml"


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not row.get("name") or not row.get("query"):
            raise ValueError(f"{path}:{line_number} requires name and query")
        criteria = row.get("criteria", [])
        if not criteria:
            raise ValueError(f"{path}:{line_number} requires task-level criteria")
        for criterion in criteria:
            if not criterion.get("name") or not criterion.get("instruction"):
                raise ValueError(f"{path}:{line_number} has an invalid criterion")
        rows.append(row)
    if len({row["name"] for row in rows}) != len(rows):
        raise ValueError(f"{path} contains duplicate task names")
    return rows


def main() -> None:
    recipe = yaml.safe_load(RECIPE_PATH.read_text(encoding="utf-8"))
    agent = recipe.get("agent", {})
    config_value = agent.get("config")
    if not config_value:
        raise ValueError("agent.config is required")
    config_path = (SERVICE_ROOT / config_value).resolve()
    if not config_path.is_relative_to(SERVICE_ROOT.resolve()):
        raise ValueError("agent.config must resolve inside the service directory")
    if not config_path.is_file():
        raise FileNotFoundError(config_path)

    metadata = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    instruction_file = metadata.get("instruction_file")
    if not instruction_file:
        raise ValueError("Baseline metadata requires instruction_file")
    instruction_path = (config_path.parent / instruction_file).resolve()
    if not instruction_path.is_relative_to(config_path.parent.resolve()):
        raise ValueError("instruction_file must resolve inside the baseline directory")
    if not instruction_path.is_file():
        raise FileNotFoundError(instruction_path)
    baseline_instruction = instruction_path.read_text(encoding="utf-8")
    if "Never invent resource names" not in baseline_instruction:
        raise ValueError("Baseline instructions are missing the no-fabrication rule")

    train_path = (SERVICE_ROOT / recipe["dataset"]["local_uri"]).resolve()
    validation_path = (SERVICE_ROOT / recipe["validation_dataset"]["local_uri"]).resolve()
    for path in (train_path, validation_path):
        if not path.is_relative_to(SERVICE_ROOT.resolve()):
            raise ValueError(f"Dataset must resolve inside the service directory: {path}")
    train = load_jsonl(train_path)
    validation = load_jsonl(validation_path)

    overlap = {row["query"] for row in train} & {row["query"] for row in validation}
    if overlap:
        raise ValueError("Training and validation datasets overlap")
    if not recipe["options"].get("eval_model"):
        raise ValueError("options.eval_model is required")
    if not recipe["options"].get("optimization_model"):
        raise ValueError("options.optimization_model is required")
    if recipe["options"].get("max_candidates", 0) < 1:
        raise ValueError("options.max_candidates must be at least 1")
    if not recipe.get("evaluators"):
        raise ValueError("At least one evaluator is required")

    print(f"Optimizer assets valid: train={len(train)} validation={len(validation)}")
    print(f"Eval model: {recipe['options']['eval_model']}")
    print(f"Optimization model: {recipe['options']['optimization_model']}")


if __name__ == "__main__":
    main()
