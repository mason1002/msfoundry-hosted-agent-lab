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
MACOS_README = (ROOT / "README_macOS.md").read_text(encoding="utf-8")
REFERENCE_MANUAL = (
    ROOT / "docs" / "xAgent_Foundry构建部署与测试参考手册_v1.0.md"
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

    def test_readme_macos_training_flow_is_safe_and_reproducible(self):
        macos_section = MACOS_README.split("## macOS 快速开始", 1)[1].split(
            "## 获取自己的训练环境", 1
        )[0]

        ordered_steps = [
            'az account set --subscription "<讲师提供的订阅名称或 ID>"',
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


if __name__ == "__main__":
    unittest.main()
