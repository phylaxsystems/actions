import json
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
        build = workflow.split("  publish-manifest-list:", 1)[0]
        self.assertNotIn("systemctl", workflow)
        self.assertNotIn("apt install", workflow)
        self.assertIn("uses: docker/setup-buildx-action@", build)
        self.assertLess(
            build.index("uses: docker/setup-buildx-action@"),
            build.index("uses: docker/build-push-action@"),
        )

    def test_builder_config_is_opt_in_and_amd64_only(self):
        workflow = (ROOT / ".github/workflows/release-docker-ghcr.yaml").read_text()
        self.assertRegex(workflow, r"buildkitd-config-amd64:\n(?:        .*\n)*?        default: ''")
        build, publish = workflow.split("  publish-manifest-list:", 1)
        self.assertIn(
            "buildkitd-config: ${{ matrix.arch == 'amd64' && inputs.buildkitd-config-amd64 || '' }}",
            build,
        )
        self.assertNotIn("inputs.buildkitd-config-amd64", publish)

    def test_optional_base_image_reaches_both_auth_paths(self):
        workflow = (ROOT / ".github/workflows/release-docker-ghcr.yaml").read_text()
        self.assertRegex(workflow, r"base-image:\n(?:        .*\n)*?        default: ''")
        for name in ("Build and push", "Build and push (SSH fallback)"):
            step = workflow.split(f"      - name: {name}\n", 1)[1].split("      - name:", 1)[0]
            self.assertIn(
                "${{ inputs.base-image != '' && format('BASE_IMAGE={0}', inputs.base-image) || '' }}",
                step,
            )

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
        self.assertIn("key: ${{ runner.os }}-${{ matrix.arch }}-${{ inputs.rust-binary-name }}-buildx-${{ github.sha }}", workflow)
        self.assertIn("            ${{ runner.os }}-${{ matrix.arch }}-${{ inputs.rust-binary-name }}-buildx-\n", workflow)
        self.assertNotIn("/tmp/.buildx-cache", workflow)
        self.assertIn("path: ${{ runner.temp }}/.buildx-cache", workflow)
        self.assertEqual(workflow.count("cache-from: type=local,src=${{ runner.temp }}/.buildx-cache"), 2)
        for name in ("Build and push", "Build and push (SSH fallback)"):
            step = workflow.split(f"      - name: {name}\n", 1)[1].split("      - name:", 1)[0]
            self.assertIn("cache-to: type=local,dest=${{ runner.temp }}/.buildx-cache-new,mode=${{ matrix.arch == 'arm64' && 'min' || 'max' }}", step)
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

    def test_guarded_promotion_preserves_sha_and_rejects_stale_runs(self):
        workflow = (ROOT / ".github/workflows/release-docker-ghcr.yaml").read_text()
        self.assertRegex(workflow, r"guard-main-tags:\n(?:        .*\n)*?        default: false")
        publish, promote = workflow.split("  promote-main-tags:\n", 1)
        self.assertNotIn("concurrency:", publish)
        self.assertIn("if: ${{ inputs.guard-main-tags && github.ref == 'refs/heads/main' }}", promote)
        self.assertIn("group: docker-main-promotion-${{ github.repository }}-${{ inputs.rust-binary-name }}", promote)
        self.assertIn("cancel-in-progress: false", promote)
        self.assertIn("needs: [build, publish-manifest-list]", promote)
        self.assertIn("GUARD_MAIN_TAGS: ${{ inputs.guard-main-tags && github.ref == 'refs/heads/main' }}", publish)

        def script(section, name):
            step = section.split(f"      - name: {name}\n", 1)[1].split("      - name:", 1)[0]
            return textwrap.dedent(step.split("        run: |\n", 1)[1])

        image = "ghcr.io/example/project/service"
        publish_script = script(publish, "Create and push manifest list")
        promote_script = script(promote, "Promote current main image")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "docker").write_text('#!/bin/bash\nprintf "%s\\n" "$@" >> "$CALLS"\n')
            (root / "gh").write_text('#!/bin/bash\n[[ "$*" == "api repos/example/project/git/ref/heads/main --jq .object.sha" ]] || exit 9\n[[ "$HEAD_SHA" != error ]] || exit 1\nprintf "%s\\n" "$HEAD_SHA"\n')
            for tool in ("docker", "gh"):
                (root / tool).chmod(0o755)
            calls = root / "calls"
            env = {**os.environ, "PATH": f"{root}:{os.environ['PATH']}", "CALLS": str(calls),
                   "REGISTRY_IMAGE": image, "GITHUB_REPOSITORY": "example/project", "GITHUB_SHA": "new-sha",
                   "DIGEST_AMD64": "sha256:amd64", "DIGEST_ARM64": "sha256:arm64",
                   "DOCKER_METADATA_OUTPUT_JSON": json.dumps({"tags": [f"{image}:{tag}" for tag in ("main", "latest", "sha-new", "new-sha", "1.2.3")]})}
            for guarded in ("true", "false"):
                calls.write_text("")
                subprocess.run(["bash", "-e", "-c", publish_script], env={**env, "GUARD_MAIN_TAGS": guarded}, check=True)
                args = calls.read_text().splitlines()
                for tag in ("sha-new", "new-sha", "1.2.3"):
                    self.assertIn(f"{image}:{tag}", args)
                for tag in ("main", "latest"):
                    self.assertEqual(f"{image}:{tag}" in args, guarded == "false")
                self.assertIn(f"{image}@sha256:amd64", args)
                self.assertIn(f"{image}@sha256:arm64", args)
            for head, version in (("new-sha", "1.2.3"), ("new-sha", ""), ("newer-sha", "1.2.3"), ("error", "1.2.3")):
                with self.subTest(head=head, version=version):
                    calls.write_text("")
                    result = subprocess.run(["bash", "-e", "-c", promote_script], env={**env, "HEAD_SHA": head, "VERSION_TAG": version})
                    self.assertEqual(result.returncode == 0, head != "error")
                    args = calls.read_text().splitlines()
                    self.assertEqual(f"{image}:main" in args, head == "new-sha")
                    self.assertEqual(f"{image}:latest" in args, head == "new-sha" and bool(version))
                    if head != "new-sha":
                        self.assertEqual(args, [])


if __name__ == "__main__":
    unittest.main()
