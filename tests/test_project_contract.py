import re
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
REFERENCE_MANUAL = (
    ROOT / "docs" / "xAgent_Foundry构建部署与测试参考手册_v1.0.md"
).read_text(encoding="utf-8")
LAB_MANUAL = (
    ROOT / "docs" / "xAgent_Foundry性能安全与Guardrails实验手册_v1.0.md"
).read_text(encoding="utf-8")


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
        self.assertIn("enable_sensitive_data=False", MAIN)

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
        self.assertGreaterEqual(len(links), 11)
        self.assertEqual(set(), links - anchors)
        self.assertGreaterEqual(LAB_MANUAL.count("| 独立前提 |"), 11)
        self.assertGreaterEqual(LAB_MANUAL.count("| 通过标准 |"), 11)

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
        filenames = (
            "foundry-agent-monitor.png",
            "foundry-monitor-settings.png",
            "azure-monitor-genai.png",
            "azure-monitor-eval-alert.png",
        )
        for filename in filenames:
            image = ROOT / "docs" / "images" / filename
            self.assertTrue(image.is_file(), filename)
            self.assertGreater(image.stat().st_size, 10_000, filename)
            self.assertIn(f"images/{filename}", REFERENCE_MANUAL)
            self.assertIn(f"images/{filename}", LAB_MANUAL)

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

    def test_docs_state_hosted_red_team_current_limit(self):
        self.assertIn("Hosted Agent 云端 Red Team 路径尚不受支持", REFERENCE_MANUAL)
        self.assertIn("本地 endpoint", REFERENCE_MANUAL)

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


if __name__ == "__main__":
    unittest.main()
