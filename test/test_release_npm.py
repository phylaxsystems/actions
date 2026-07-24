import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ReleaseNpmWorkflowTest(unittest.TestCase):
    def test_step_action_publishes_from_the_calling_workflow(self):
        action_path = ROOT / "release-npm" / "action.yml"

        self.assertTrue(
            action_path.exists(),
            "trusted publishing must run as a step in the caller's workflow",
        )

        action = action_path.read_text()
        self.assertIn("using: composite", action)
        self.assertIn("package-manager-cache: false", action)
        self.assertIn("npm install -g npm@latest", action)
        self.assertIn("npm publish", action)
        self.assertNotIn("NPM_TOKEN", action)
        self.assertNotIn("NODE_AUTH_TOKEN", action)

    def test_reusable_workflow_uses_an_oidc_capable_npm(self):
        workflow = (ROOT / ".github" / "workflows" / "release-npm.yaml").read_text()

        self.assertIn("id-token: write", workflow)
        self.assertIn("package-manager-cache: false", workflow)
        self.assertIn("npm install -g npm@latest", workflow)
        self.assertNotIn("NPM_TOKEN", workflow)
        self.assertNotIn("NODE_AUTH_TOKEN", workflow)


if __name__ == "__main__":
    unittest.main()
