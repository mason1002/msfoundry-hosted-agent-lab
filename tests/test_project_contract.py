import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = (ROOT / "azure.yaml").read_text(encoding="utf-8")
MAIN = (
    ROOT / "src" / "agent-framework-agent-basic-responses" / "main.py"
).read_text(encoding="utf-8")
GITIGNORE = (ROOT / ".gitignore").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
TRAINING_MANUAL = (
    ROOT / "docs" / "xAgent_Foundry构建部署与测试培训手册_v1.0.md"
).read_text(encoding="utf-8")


class ProjectContractTests(unittest.TestCase):
    def test_manifest_uses_xagent_direct_code_responses_hosting(self):
        self.assertIn("name: xagent-foundry-training", MANIFEST)
        self.assertIn("host: azure.ai.agent", MANIFEST)
        self.assertIn("codeConfiguration:", MANIFEST)
        self.assertIn("entryPoint: main.py", MANIFEST)
        self.assertIn("runtime: python_3_13", MANIFEST)
        self.assertIn("protocol: responses", MANIFEST)

    def test_manifest_declares_supported_training_model(self):
        self.assertIn("name: gpt-5.4-mini", MANIFEST)
        self.assertIn('version: "2026-03-17"', MANIFEST)
        self.assertIn("name: GlobalStandard", MANIFEST)
        self.assertIn("capacity: 10", MANIFEST)

    def test_manifest_declares_hosted_agent_guardrail(self):
        self.assertIn("rai_config:", MANIFEST)
        self.assertIn("rai_policy_name: ${AZURE_AI_RAI_POLICY_ID}", MANIFEST)
        self.assertNotIn("/subscriptions/", MANIFEST)

    def test_agent_uses_identity_and_environment_configuration(self):
        self.assertIn("DefaultAzureCredential()", MAIN)
        self.assertIn('os.environ["FOUNDRY_PROJECT_ENDPOINT"]', MAIN)
        self.assertIn('os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")', MAIN)
        self.assertNotRegex(
            MAIN,
            re.compile(r"(?i)(api[_-]?key|access[_-]?token)\s*=\s*['\"]\S+"),
        )

    def test_local_secrets_and_virtual_environments_are_ignored(self):
        self.assertIn("**/.env", GITIGNORE)
        self.assertIn("**/.venv*/", GITIGNORE)

    def test_training_manual_toc_links_have_explicit_anchors(self):
        links = set(re.findall(r"\]\(#([A-Za-z0-9_-]+)\)", TRAINING_MANUAL))
        anchors = set(re.findall(r'<a id="([A-Za-z0-9_-]+)"></a>', TRAINING_MANUAL))
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


if __name__ == "__main__":
    unittest.main()
