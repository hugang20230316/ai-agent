#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import publish_gitlab_argo


class PublishGitLabArgoTests(unittest.TestCase):
    def test_next_tag_keeps_release_suffix(self) -> None:
        self.assertEqual(publish_gitlab_argo.next_tag("v0.0.866-release"), "v0.0.867-release")

    def test_release_branch_uses_release_tag_pattern(self) -> None:
        pattern = publish_gitlab_argo.release_tag_pattern_for_branch("release")

        self.assertRegex("v0.0.867-release", pattern)
        self.assertNotRegex("v0.0.867", pattern)

    def test_default_branch_uses_default_tag_pattern(self) -> None:
        pattern = publish_gitlab_argo.release_tag_pattern_for_branch("main")

        self.assertRegex("v0.0.867", pattern)
        self.assertNotRegex("v0.0.867-release", pattern)

    def test_changed_files_select_matching_apps(self) -> None:
        apps = publish_gitlab_argo.apps_for_changed_files(
            ["src/Worker/Job.cs", "README.md"],
            {
                "worker-dev": ["src/Worker/"],
                "api-dev": ["src/Api/"],
            },
        )

        self.assertEqual(apps, ["worker-dev"])

    def test_changed_file_matching_normalizes_windows_paths(self) -> None:
        apps = publish_gitlab_argo.apps_for_changed_files(
            [r"src\Worker\Job.cs"],
            {"worker-dev": ["src\\Worker\\"]},
        )

        self.assertEqual(apps, ["worker-dev"])

    def test_configured_publish_repo_paths_read_allowlist(self) -> None:
        with mock.patch.dict(publish_gitlab_argo.PUBLISH_CONFIG, {"repoPath": "/tmp/project-a", "repoPaths": ["/tmp/project-b"]}, clear=True):
            paths = publish_gitlab_argo.configured_publish_repo_paths()

        self.assertEqual(paths, [Path("/tmp/project-a"), Path("/tmp/project-b")])

    def test_unconfigured_repo_is_rejected(self) -> None:
        with mock.patch.dict(publish_gitlab_argo.PUBLISH_CONFIG, {"repoPath": "/tmp/project-a"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "不在发布配置允许列表"):
                publish_gitlab_argo.ensure_publish_repo_allowed(Path("/tmp/project-b"))


if __name__ == "__main__":
    unittest.main()
