import os
import subprocess
import tempfile
import textwrap
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

    def test_full_sha_tags_only_the_combined_manifest(self):
        workflow = (ROOT / ".github/workflows/release-docker-ghcr.yaml").read_text()
        build, publish = workflow.split("  publish-manifest-list:", 1)
        # Both auth paths must push by digest without racing on a shared tag.
        self.assertNotIn("          tags:", build)
        self.assertEqual(
            build.count("outputs: type=image,name=${{ env.REGISTRY_IMAGE }},push-by-digest=true,name-canonical=true,push=true"),
            2,
        )
        # Unconditional: callers that omit version-tag still get a multi-arch SHA.
        self.assertIn("            type=raw,value=${{ github.sha }}\n", publish)
        self.assertIn("needs: build", publish)
        self.assertIn("needs.build.outputs.digest-amd64", publish)
        self.assertIn("needs.build.outputs.digest-arm64", publish)

    def test_cache_export_and_rotation_use_runner_temp(self):
        workflow = (ROOT / ".github/workflows/release-docker-ghcr.yaml").read_text()
        self.assertNotIn("/tmp/.buildx-cache", workflow)
        self.assertIn("path: ${{ runner.temp }}/.buildx-cache", workflow)
        self.assertEqual(workflow.count("cache-from: type=local,src=${{ runner.temp }}/.buildx-cache"), 2)
        self.assertEqual(workflow.count("cache-to: type=local,dest=${{ runner.temp }}/.buildx-cache-new,mode=max"), 2)
        move = workflow.split("      - name: Move cache\n", 1)[1].split("      - name:", 1)[0]
        script = textwrap.dedent(move.split("        run: |\n", 1)[1])
        with tempfile.TemporaryDirectory(prefix="docker cache ") as directory:
            root = Path(directory)
            old = root / ".buildx-cache"
            new = root / ".buildx-cache-new"
            old.mkdir()
            new.mkdir()
            (old / "stale").write_text("old layers")
            (new / "index.json").write_text("new index")
            subprocess.run(["bash", "-e", "-c", script], env={**os.environ, "RUNNER_TEMP": directory}, check=True)
            self.assertEqual((old / "index.json").read_text(), "new index")
            self.assertFalse((old / "stale").exists())
            self.assertFalse(new.exists())


if __name__ == "__main__":
    unittest.main()
