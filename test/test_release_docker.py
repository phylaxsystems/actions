import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ReleaseDockerWorkflowTest(unittest.TestCase):
    def test_native_platforms_and_caller_runner_selection(self):
        workflow = (ROOT / ".github/workflows/release-docker-ghcr.yaml").read_text()
        self.assertNotIn("big-bois-", workflow)
        self.assertIn("runs-on: ${{ matrix.runner }}", workflow)
        self.assertIn("runner: ${{ inputs.runner-amd64 }}", workflow)
        self.assertRegex(workflow, r"runner-amd64:\n(?:        .*\n)*?        default: 'ubuntu-latest'")
        self.assertIn("platform: linux/amd64", workflow)
        self.assertIn("platform: linux/arm64\n            runner: ubuntu-24.04-arm", workflow)
        self.assertIn("platforms: ${{ matrix.platform }}", workflow)
        self.assertIn("needs.build.outputs.digest-amd64", workflow)
        self.assertIn("needs.build.outputs.digest-arm64", workflow)

    def test_uses_provided_docker_daemon(self):
        workflow = (ROOT / ".github/workflows/release-docker-ghcr.yaml").read_text()
        self.assertNotIn("systemctl", workflow)
        self.assertNotIn("apt install", workflow)
        self.assertIn("uses: docker/setup-buildx-action@", workflow)


if __name__ == "__main__":
    unittest.main()
