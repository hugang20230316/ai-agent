#!/usr/bin/env python3
"""Focused tests for timer_manager safety behavior."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import timer_manager


class TimerManagerTests(unittest.TestCase):
    def launchd_job(self, visible: bool = True, scope: str = "user") -> timer_manager.TimerJob:
        return timer_manager.TimerJob(
            id=timer_manager.stable_id("launchd", scope, "com.example.codex-test"),
            native_id="com.example.codex-test",
            name="Codex Test",
            platform="macos",
            backend="launchd",
            scope=scope,
            category="ai-workflow" if visible else "system-or-app",
            visible_by_default=visible,
            filter_reasons=["strong-term:codex"] if visible else [],
            tags=["codex"] if visible else [],
            source="/tmp/com.example.codex-test.plist",
            enabled=True,
            loaded=True,
            running=False,
            pid=None,
            trigger=timer_manager.TimerTrigger(type="interval", interval_seconds=60),
            action=timer_manager.TimerAction(command="/usr/bin/true"),
            logs=timer_manager.TimerLogs(),
            health=timer_manager.TimerHealth(),
            capabilities=timer_manager.TimerCapabilities(
                can_delete=True,
                can_start=True,
                can_stop=True,
                can_restart=True,
                can_enable=True,
                can_disable=True,
            ),
        )

    def test_unload_uses_delete_capability(self) -> None:
        timer_manager.require_capability(self.launchd_job(), "unload")

    def test_non_ai_write_requires_override(self) -> None:
        with self.assertRaisesRegex(timer_manager.TimerError, "--allow-non-ai"):
            timer_manager.require_capability(self.launchd_job(visible=False), "start")

    def test_system_write_requires_override(self) -> None:
        with self.assertRaisesRegex(timer_manager.TimerError, "--allow-system"):
            timer_manager.require_capability(self.launchd_job(scope="system"), "start")

    def test_windows_system_create_is_refused(self) -> None:
        definition = {
            "native_id": r"\Microsoft\Windows\Example",
            "trigger": {"type": "manual"},
            "action": {"command": "cmd.exe", "args": ["/c", "echo", "codex"]},
        }
        with self.assertRaisesRegex(timer_manager.TimerError, "system-scope"):
            timer_manager.create_windows_task(definition, apply=False, allow_non_ai=True)

    def test_windows_user_create_preview_builds_schtasks(self) -> None:
        definition = {
            "native_id": r"\Codex\ObsidianSync",
            "trigger": {"type": "interval", "interval_seconds": 300},
            "action": {"command": "python", "args": ["-m", "codex.timer"]},
        }

        preview = timer_manager.create_windows_task(definition, apply=False, allow_non_ai=False)

        self.assertTrue(preview["dry_run"])
        self.assertEqual(preview["id"], r"windows-task-scheduler:user:\Codex\ObsidianSync")
        self.assertEqual(preview["command"][:5], ["schtasks", "/Create", "/TN", r"\Codex\ObsidianSync", "/TR"])
        self.assertEqual(preview["command"][5], "python -m codex.timer")
        self.assertIn("/SC", preview["command"])
        self.assertIn("MINUTE", preview["command"])

    def test_windows_control_splits_task_path_and_name(self) -> None:
        calls: list[str] = []
        job = timer_manager.TimerJob(
            id=timer_manager.stable_id("windows-task-scheduler", "user", r"\Codex\ObsidianSync"),
            native_id=r"\Codex\ObsidianSync",
            name="Obsidian Sync",
            platform="windows",
            backend="windows-task-scheduler",
            scope="user",
            category="ai-workflow",
            visible_by_default=True,
            filter_reasons=["strong-term:codex"],
            tags=["codex"],
            source=r"\Codex\\",
            enabled=True,
            loaded=True,
            running=False,
            pid=None,
            trigger=timer_manager.TimerTrigger(type="scheduled-task"),
            action=timer_manager.TimerAction(command="python"),
            logs=timer_manager.TimerLogs(),
            health=timer_manager.TimerHealth(),
            capabilities=timer_manager.TimerCapabilities(can_start=True),
        )

        def fake_powershell_json(command: str):
            calls.append(command)
            return {"ok": True}

        with mock.patch.object(timer_manager, "powershell_json", side_effect=fake_powershell_json):
            result = timer_manager.windows_control(job, "start", allow_system=False, allow_non_ai=False)

        self.assertEqual(result["returncode"], 0)
        self.assertIn("Start-ScheduledTask", calls[0])
        self.assertIn("ObsidianSync", calls[0])
        self.assertIn(r"\\Codex\\", calls[0])

    def test_windows_list_filters_to_ai_workflow_by_default(self) -> None:
        sample_tasks = [
            {
                "TaskName": "ObsidianSync",
                "TaskPath": r"\Codex\\",
                "State": "Ready",
                "Actions": "python -m codex.timer",
                "Triggers": "Daily",
            },
            {
                "TaskName": "GoogleUpdateTaskMachineUA",
                "TaskPath": r"\Microsoft\Windows\\",
                "State": "Ready",
                "Actions": "GoogleUpdate.exe",
                "Triggers": "Hourly",
            },
        ]

        with mock.patch.object(timer_manager, "powershell_json", return_value=sample_tasks):
            default_jobs = timer_manager.windows_list_tasks(include_all=False)
            all_jobs = timer_manager.windows_list_tasks(include_all=True)

        self.assertEqual([job.native_id for job in default_jobs], [r"\Codex\\ObsidianSync"])
        self.assertEqual(len(all_jobs), 2)
        self.assertEqual(all_jobs[1].scope, "system")

    def test_cli_aliases_normalize_launch_commands(self) -> None:
        with mock.patch.object(timer_manager, "control_job", return_value={"ok": True}) as control:
            exit_code = timer_manager.main(["lunch", "timer-id"])

        self.assertEqual(exit_code, 0)
        control.assert_called_once_with("timer-id", "launch", False, False, False)

        with mock.patch.object(timer_manager, "control_job", return_value={"ok": True}) as control:
            exit_code = timer_manager.main(["执行", "timer-id"])

        self.assertEqual(exit_code, 0)
        control.assert_called_once_with("timer-id", "launch", False, False, False)

    def test_launchd_create_preview_requires_ai_evidence(self) -> None:
        definition = {
            "id": "com.example.backup",
            "backend": "launchd",
            "scope": "user",
            "trigger": {"type": "interval", "interval_seconds": 60},
            "action": {"command": "/usr/bin/true"},
        }
        with tempfile.NamedTemporaryFile("w", delete=False) as handle:
            path = Path(handle.name)
            handle.write(__import__("json").dumps(definition))
        try:
            with self.assertRaisesRegex(timer_manager.TimerError, "--allow-non-ai"):
                timer_manager.create_job(str(path), apply=False, allow_non_ai=False)
        finally:
            path.unlink(missing_ok=True)

    def test_system_launch_agents_path_is_system_scope(self) -> None:
        paths = dict(timer_manager.launchd_paths())
        self.assertEqual(paths[Path("/Library/LaunchAgents")], "system")

    def test_start_does_not_enable_launchd_job(self) -> None:
        calls: list[list[str]] = []

        def fake_run_command(args: list[str], timeout: int = 20):
            calls.append(args)
            return timer_manager.subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

        job = self.launchd_job()
        job.loaded = True
        with mock.patch.object(timer_manager, "run_command", side_effect=fake_run_command):
            timer_manager.launchd_control(job, "start", allow_system=False, allow_non_ai=False)

        self.assertNotIn("enable", [part for call in calls for part in call])
        self.assertIn("kickstart", [part for call in calls for part in call])


if __name__ == "__main__":
    unittest.main()
