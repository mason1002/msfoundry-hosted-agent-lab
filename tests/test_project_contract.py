import re
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = (ROOT / "azure.yaml").read_text(encoding="utf-8")
MAIN = (
    ROOT / "src" / "agent-framework-agent-basic-responses" / "main.py"
).read_text(encoding="utf-8")
DEVUI = (
    ROOT / "src" / "agent-framework-agent-basic-responses" / "devui.py"
).read_text(encoding="utf-8")
GITIGNORE = (ROOT / ".gitignore").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
MACOS_README = (ROOT / "README_macOS.md").read_text(encoding="utf-8")
REFERENCE_MANUAL = (
    ROOT / "docs" / "xAgent_Foundry构建部署与测试参考手册_v1.0.md"
).read_text(encoding="utf-8")
LAB_MANUAL = (
    ROOT / "docs" / "xAgent_Foundry性能安全与Guardrails实验手册_v1.0.md"
).read_text(encoding="utf-8")
SERVICE_ROOT = ROOT / "src" / "agent-framework-agent-basic-responses"
RUNTIME_REQUIREMENTS = (SERVICE_ROOT / "requirements.txt").read_text(encoding="utf-8")
OPTIMIZER_METADATA = (
    SERVICE_ROOT / ".agent_configs" / "baseline" / "metadata.yaml"
).read_text(encoding="utf-8")
OPTIMIZER_INSTRUCTIONS = (
    SERVICE_ROOT / ".agent_configs" / "baseline" / "instructions.md"
).read_text(encoding="utf-8")
OPTIMIZER_RECIPE = (SERVICE_ROOT / "eval-optimize.yaml").read_text(encoding="utf-8")


class ProjectContractTests(unittest.TestCase):
    def test_manifest_uses_xagent_direct_code_responses_hosting(self):
        self.assertIn("name: xagent-foundry-lab", MANIFEST)
        self.assertIn("host: azure.ai.agent", MANIFEST)
        self.assertIn("codeConfiguration:", MANIFEST)
        self.assertIn("entryPoint: main.py", MANIFEST)
        self.assertIn("runtime: python_3_13", MANIFEST)
        self.assertIn("protocol: responses", MANIFEST)

    def test_manifest_declares_supported_lab_model(self):
        self.assertIn("name: gpt-5.4-mini", MANIFEST)
        self.assertIn('version: "2026-03-17"', MANIFEST)
        self.assertIn("name: GlobalStandard", MANIFEST)
        self.assertIn("capacity: 10", MANIFEST)

    def test_manifest_declares_hosted_agent_guardrail(self):
        self.assertIn("rai_config:", MANIFEST)
        self.assertIn("rai_policy_name: ${AZURE_AI_RAI_POLICY_ID}", MANIFEST)
        self.assertNotIn("/subscriptions/", MANIFEST)

    def test_agent_uses_identity_and_environment_configuration(self):
        self.assertIn("def create_agent() -> Agent:", MAIN)
        self.assertIn("DefaultAzureCredential()", MAIN)
        self.assertIn('os.environ["FOUNDRY_PROJECT_ENDPOINT"]', MAIN)
        self.assertIn('os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")', MAIN)
        self.assertNotRegex(
            MAIN,
            re.compile(r"(?i)(api[_-]?key|access[_-]?token)\s*=\s*['\"]\S+"),
        )
        self.assertIn('OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"] = "false"', MAIN)
        self.assertGreaterEqual(MAIN.count('os.getenv("XAGENT_APPLICATIONINSIGHTS_CONNECTION_STRING")'), 2)
        self.assertIn('os.environ.pop("APPLICATIONINSIGHTS_CONNECTION_STRING", None)', MAIN)
        self.assertEqual(1, MAIN.count("configure_azure_monitor("))
        self.assertIn("credential=ManagedIdentityCredential()", MAIN)
        self.assertIn("span_processors=[FoundryIdentitySpanProcessor()]", MAIN)
        self.assertIn("configure_observability=configure_hosted_observability", MAIN)
        self.assertIn("create_span_hook=ResponsesOpenTelemetryHook()", MAIN)

    def test_devui_reuses_the_hosted_agent_factory(self):
        self.assertIn("from main import create_agent", DEVUI)
        self.assertIn("serve(", DEVUI)
        self.assertIn("entities=[create_agent()]", DEVUI)
        self.assertIn('host="127.0.0.1"', DEVUI)
        self.assertIn("auth_enabled=False", DEVUI)

        service_root = ROOT / "src" / "agent-framework-agent-basic-responses"
        for ignore_file in (".azdignore", ".agentignore"):
            ignore_rules = (service_root / ignore_file).read_text(encoding="utf-8")
            self.assertIn("devui.py", ignore_rules)
            self.assertIn("requirements-dev.txt", ignore_rules)

    def test_hosted_agent_is_optimizer_ready(self):
        self.assertIn("azure-ai-agentserver-optimization==1.0.0b1", RUNTIME_REQUIREMENTS)
        self.assertIn("from azure.ai.agentserver.optimization import load_config", MAIN)
        self.assertIn("OPTIMIZATION_CONFIG_DIR = Path(__file__).resolve().parent", MAIN)
        self.assertIn("load_config(config_dir=OPTIMIZATION_CONFIG_DIR)", MAIN)
        self.assertIn("optimization_config.model", MAIN)
        self.assertIn("optimization_config.compose_instructions()", MAIN)
        self.assertIn("model: gpt-5.4-mini", OPTIMIZER_METADATA)
        self.assertIn("instruction_file: instructions.md", OPTIMIZER_METADATA)
        self.assertIn("Never invent resource names", OPTIMIZER_INSTRUCTIONS)
        self.assertIn("config: .agent_configs/baseline/metadata.yaml", OPTIMIZER_RECIPE)
        self.assertIn("name: xagent-foundry-lab", OPTIMIZER_RECIPE)
        self.assertIn("validation_dataset:", OPTIMIZER_RECIPE)
        self.assertIn("optimization_model:", OPTIMIZER_RECIPE)
        self.assertIn('<a id="agent-optimizer"></a>', REFERENCE_MANUAL)
        self.assertIn('<a id="agent-optimizer"></a>', LAB_MANUAL)
        self.assertIn("azd ai agent optimize --config eval-optimize.yaml", REFERENCE_MANUAL)
        self.assertIn("azd ai agent optimize --config eval-optimize.yaml", LAB_MANUAL)

    def test_optimizer_assets_are_valid(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "validate_optimizer_assets.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_local_secrets_and_virtual_environments_are_ignored(self):
        self.assertIn("**/.env", GITIGNORE)
        self.assertIn("**/.venv*/", GITIGNORE)

    def test_reference_manual_toc_links_have_explicit_anchors(self):
        links = set(re.findall(r"\]\(#([A-Za-z0-9_-]+)\)", REFERENCE_MANUAL))
        anchors = set(re.findall(r'<a id="([A-Za-z0-9_-]+)"></a>', REFERENCE_MANUAL))
        self.assertGreaterEqual(len(links), 12)
        self.assertEqual(set(), links - anchors)

    def test_lab_manual_methods_are_independent_and_linked(self):
        links = set(re.findall(r"\]\(#([A-Za-z0-9_-]+)\)", LAB_MANUAL))
        anchors = set(re.findall(r'<a id="([A-Za-z0-9_-]+)"></a>', LAB_MANUAL))
        self.assertGreaterEqual(len(links), 10)
        self.assertEqual(set(), links - anchors)
        self.assertGreaterEqual(LAB_MANUAL.count("| 独立前提 |"), 10)
        self.assertGreaterEqual(LAB_MANUAL.count("| 通过标准 |"), 10)

    def test_optimizer_evidence_belongs_to_lab_manual(self):
        evidence_files = (
            "foundry-optimizer-run-succeeded.png",
            "foundry-optimizer-candidate-2-changes.png",
        )
        for filename in evidence_files:
            image = ROOT / "docs" / "images" / filename
            self.assertTrue(image.is_file(), filename)
            self.assertGreater(image.stat().st_size, 10_000, filename)
            self.assertIn(f"images/{filename}", LAB_MANUAL)
            self.assertNotIn(f"images/{filename}", REFERENCE_MANUAL)

        self.assertIn(
            "xAgent_Foundry性能安全与Guardrails实验手册_v1.0.md#agent-optimizer",
            REFERENCE_MANUAL,
        )
        self.assertNotIn("score `0.897`", REFERENCE_MANUAL)
        self.assertIn("candidate_2 标记为 best candidate", LAB_MANUAL)
        self.assertIn("score `0.897`", LAB_MANUAL)

    def test_all_local_markdown_links_resolve(self):
        for markdown_path in (ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))):
            if "端到端验证报告" in markdown_path.name:
                continue
            text = markdown_path.read_text(encoding="utf-8")
            for target in re.findall(r"!?\[[^]]*\]\(([^)]+)\)", text):
                if target.startswith(("http://", "https://", "#")):
                    continue
                relative_target = target.split("#", 1)[0]
                resolved = (markdown_path.parent / relative_target).resolve()
                self.assertTrue(resolved.is_file(), f"{markdown_path.name}: {target}")

    def test_platform_monitoring_evidence_exists_and_is_linked(self):
        lab_filenames = (
            "foundry-monitor-v16.png",
            "foundry-traces-v16.png",
            "foundry-conversations-v16.png",
            "foundry-sessions-v16.png",
            "azure-monitor-genai.png",
            "foundry-guardrail-assignment.png",
            "foundry-playground-guardrail-block-v16.png",
            "locust-v16-statistics.png",
            "azure-monitor-eval-alert.png",
        )
        for filename in lab_filenames:
            image = ROOT / "docs" / "images" / filename
            self.assertTrue(image.is_file(), filename)
            self.assertGreater(image.stat().st_size, 10_000, filename)
            self.assertIn(f"images/{filename}", LAB_MANUAL)
            self.assertNotIn(f"images/{filename}", REFERENCE_MANUAL)

        main_only = "devui-agent-behavior.png"
        self.assertIn(f"images/{main_only}", REFERENCE_MANUAL)
        self.assertGreater((ROOT / "docs" / "images" / main_only).stat().st_size, 10_000)

    def test_readme_document_navigation_targets_exist(self):
        links = re.findall(r"\]\((docs/[^)]+)\)", README)
        self.assertGreaterEqual(len(links), 14)
        for link in links:
            target, _, anchor = link.partition("#")
            target_path = ROOT / target
            self.assertTrue(target_path.is_file(), target)
            if anchor:
                target_text = target_path.read_text(encoding="utf-8")
                self.assertIn(f'<a id="{anchor}"></a>', target_text)

    def test_readme_macos_lab_flow_is_safe_and_reproducible(self):
        macos_section = MACOS_README.split("## macOS 快速开始", 1)[1].split(
            "## 获取自己的训练环境", 1
        )[0]

        ordered_steps = [
            'az account set --subscription "<实验订阅名称或 ID>"',
            'export AZURE_TENANT_ID="$(az account show --query tenantId --output tsv)"',
            'azd auth login --tenant-id "$AZURE_TENANT_ID"',
            'azd auth token --tenant-id "$AZURE_TENANT_ID" >/dev/null',
            "azd extension install azure.ai.agents --no-prompt",
            'azd env new "$LAB_ENV_NAME"',
            "azd provision --preview --no-prompt",
            "azd provision --no-prompt",
            'export FOUNDRY_PROJECT_ENDPOINT="$(azd env get-value FOUNDRY_PROJECT_ENDPOINT)"',
            "azd env get-value AI_PROJECT_DEPLOYMENTS",
            "azd ai agent run --no-client",
            "azd env set AZURE_AI_MODEL_DEPLOYMENT_NAME",
            "azd env set AZURE_AI_RAI_POLICY_ID",
            "azd deploy --no-prompt",
            "azd ai agent show --output json",
            "azd ai agent invoke --new-session",
            "azd ai agent monitor --tail 100",
            'azd ai agent invoke \\\n  --session-id "<错误输出中的 Session ID>"',
        ]
        offsets = [macos_section.index(step) for step in ordered_steps]
        self.assertEqual(sorted(offsets), offsets)

        self.assertNotIn("azd provision --no-state", macos_section)
        self.assertNotIn("azd down --purge --force", MACOS_README)
        self.assertNotIn("pwsh", MACOS_README)
        self.assertNotIn("powershell", MACOS_README.lower())
        self.assertNotIn(".ps1", MACOS_README.lower())
        self.assertNotIn("render_reference_docs.py", MACOS_README)
        self.assertIn("isinstance(data, str)", macos_section)
        self.assertIn(
            ': "${AZURE_AI_MODEL_DEPLOYMENT_NAME:?当前 azd 环境没有模型部署}"',
            macos_section,
        )
        self.assertIn(
            'assert model, "Hosted Agent 的模型部署名称为空"',
            macos_section,
        )
        monitor_offset = macos_section.index("azd ai agent monitor --tail 100")
        token_preflight_offset = macos_section.index(
            'azd auth token --tenant-id "$AZURE_TENANT_ID" >/dev/null',
            monitor_offset,
        )
        monitor_retry_offset = macos_section.index(
            "azd ai agent monitor --tail 100",
            monitor_offset + 1,
        )
        self.assertLess(monitor_offset, token_preflight_offset)
        self.assertLess(token_preflight_offset, monitor_retry_offset)
        self.assertIn("az deployment group what-if", macos_section)
        self.assertIn(
            "--config src/agent-framework-agent-basic-responses/eval-security.yaml",
            macos_section,
        )

    def test_docs_assume_an_existing_local_maf_agent(self):
        self.assertIn("已有可运行并完成本地验证", README)
        self.assertIn("不要求把现有 Agent 重写成 xAgent", README)
        self.assertIn("### 2.1 接入前提", REFERENCE_MANUAL)
        self.assertIn("ResponsesHostServer(agent)", REFERENCE_MANUAL)
        self.assertIn("自定义业务 Golden Dataset", REFERENCE_MANUAL)

    def test_docs_do_not_require_responses_host_server_for_all_hosted_agents(self):
        self.assertIn("不是 Foundry 的唯一实现", REFERENCE_MANUAL)
        self.assertIn("Responses + Invocations", REFERENCE_MANUAL)
        self.assertIn("代码实现必须与 `azure.yaml` 声明的协议和版本一致", REFERENCE_MANUAL)

    def test_cross_platform_operations_are_python_first(self):
        required = (
            "agent_ops.py",
            "invoke_hosted.py",
            "compare_agent.py",
            "send_traffic.py",
            "locustfile.py",
            "continuous_eval.py",
            "configure_eval_alert.py",
            "verify_monitoring.py",
            "sync_env.py",
            "show_context.py",
            "connect_observability.py",
        )
        scripts = ROOT / "scripts"
        for filename in required:
            self.assertTrue((scripts / filename).is_file(), filename)
        self.assertTrue((scripts / "run_ops.sh").is_file())
        self.assertTrue((scripts / "run_ops.cmd").is_file())

    def test_docs_do_not_include_unsupported_red_teaming(self):
        for document in (REFERENCE_MANUAL, LAB_MANUAL):
            self.assertNotRegex(document, re.compile(r"(?i)red[ -]?team"))

    def test_local_dependency_groups_are_separate(self):
        service = ROOT / "src" / "agent-framework-agent-basic-responses"
        dev = (service / "requirements-dev.txt").read_text(encoding="utf-8")
        ops = (ROOT / "requirements-ops.txt").read_text(encoding="utf-8")
        load = (ROOT / "requirements-load.txt").read_text(encoding="utf-8")
        self.assertIn("agent-framework-devui", dev)
        self.assertNotIn("locust", dev)
        self.assertNotIn("locust", ops)
        self.assertNotIn("agent-framework-devui", ops)
        self.assertIn("locust", load)

    def test_deployment_has_smoke_test_and_rollback(self):
        deploy = (ROOT / "scripts" / "deploy_existing_agent.py").read_text(encoding="utf-8")
        self.assertIn("def smoke_test(", deploy)
        self.assertIn("Rolled back endpoint", deploy)
        self.assertNotIn('    ".agent_configs",', deploy)
        self.assertIn('    "eval-optimize.yaml",', deploy)
        self.assertIn("OPTIMIZATION_CONFIG_SUFFIXES", deploy)
        self.assertIn("source.is_symlink()", deploy)
        ensure_role = deploy.split("def ensure_role(", 1)[1].split(
            "def ensure_telemetry_role(", 1
        )[0]
        self.assertIn("arm_put(", ensure_role)


if __name__ == "__main__":
    unittest.main()
