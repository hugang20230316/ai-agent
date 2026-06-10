#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
