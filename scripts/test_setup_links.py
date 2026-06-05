#!/usr/bin/env python3
"""Regression tests for setup_links.py."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

import setup_links


class SetupLinksTests(unittest.TestCase):
    def run_main(self, home: Path, *args: str) -> tuple[int, str, str]:
        stdout = StringIO()
        stderr = StringIO()
        argv = ["setup_links.py", *args]
        env = {"HOME": str(home), "PATH": ""}
        with (
            mock.patch.dict(os.environ, env, clear=True),
            mock.patch.object(setup_links.shutil, "which", return_value=None),
            mock.patch.object(sys, "argv", argv),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            code = setup_links.main()
        return code, stdout.getvalue(), stderr.getvalue()

    def test_auto_links_detected_codex_and_backs_up_existing_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            codex = home / ".codex"
            rules = codex / "rules"
            rules.mkdir(parents=True)
            (codex / "AGENTS.md").write_text("old entry\n", encoding="utf-8")
            (rules / "coding-rules.md").write_text("old rule\n", encoding="utf-8")

            code, _, _ = self.run_main(home)

            self.assertEqual(code, 0)
            self.assertTrue((codex / "AGENTS.md").is_symlink())
            self.assertEqual((codex / "AGENTS.md").resolve(strict=False), setup_links.ROOT / "AGENTS.md")
            self.assertTrue((rules / "coding-rules.md").is_symlink())
            self.assertEqual((rules / "coding-rules.md").resolve(strict=False), setup_links.ROOT / "rules" / "coding-rules.md")

            backups = list((codex / ".ai-agent-backups").glob("*/AGENTS.md"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_text(encoding="utf-8"), "old entry\n")
            rule_backups = list((codex / ".ai-agent-backups").glob("*/rules/coding-rules.md"))
            self.assertEqual(len(rule_backups), 1)
            self.assertEqual(rule_backups[0].read_text(encoding="utf-8"), "old rule\n")

    def test_auto_appends_claude_native_reference_with_backup(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            claude = home / ".claude"
            claude.mkdir(parents=True)
            native_entry = claude / "CLAUDE.md"
            native_entry.write_text("local prompt\n", encoding="utf-8")

            code, _, _ = self.run_main(home)

            self.assertEqual(code, 0)
            self.assertEqual(native_entry.read_text(encoding="utf-8"), "local prompt\n@AGENTS.md\n")
            backups = list((claude / ".ai-agent-backups").glob("*/CLAUDE.md"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_text(encoding="utf-8"), "local prompt\n")

    def test_plain_agents_text_does_not_count_as_native_reference(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            claude = home / ".claude"
            claude.mkdir(parents=True)
            native_entry = claude / "CLAUDE.md"
            native_entry.write_text("read AGENTS.md later\n", encoding="utf-8")

            code, _, _ = self.run_main(home)

            self.assertEqual(code, 0)
            self.assertEqual(native_entry.read_text(encoding="utf-8"), "read AGENTS.md later\n@AGENTS.md\n")

    def test_auto_returns_error_when_no_supported_tool_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)

            code, _, stderr = self.run_main(home)

            self.assertEqual(code, 1)
            self.assertIn("no supported agent tool was detected", stderr)

    def test_failed_link_restores_backed_up_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            codex = home / ".codex"
            codex.mkdir(parents=True)
            target = codex / "AGENTS.md"
            target.write_text("old entry\n", encoding="utf-8")
            plan = setup_links.LinkPlan("codex", "entry", setup_links.ROOT / "AGENTS.md", target, False)
            stdout = StringIO()

            with (
                mock.patch.dict(os.environ, {"HOME": str(home)}, clear=True),
                mock.patch.object(setup_links.os, "symlink", side_effect=OSError("boom")),
                redirect_stdout(stdout),
            ):
                code = setup_links.apply_plan([plan], [], [], replace_existing=True)

            self.assertEqual(code, 1)
            self.assertEqual(target.read_text(encoding="utf-8"), "old entry\n")
            self.assertIn("RESTORE:", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
