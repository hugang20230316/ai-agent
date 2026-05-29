#!/usr/bin/env python3
"""Focused tests for timer_manager safety behavior."""

from __future__ import annotations

import tempfile
import unittest
from io import StringIO
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
                can_update=True,
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

    def test_cli_rejects_removed_command_aliases(self) -> None:
        for command in ["run", "lunch", "执行", "开启", "停止", "状态"]:
            with self.subTest(command=command), mock.patch("sys.stderr", StringIO()), self.assertRaises(SystemExit) as raised:
                timer_manager.main([command, "timer-id"])

            self.assertEqual(raised.exception.code, 2)

    def test_cli_control_commands_pass_preview_and_apply_flags(self) -> None:
        for command in ["enable", "disable", "start", "launch", "restart", "stop"]:
            with self.subTest(command=command), mock.patch.object(
                timer_manager,
                "control_job",
                return_value={"ok": True},
            ) as control, mock.patch("sys.stdout", StringIO()):
                exit_code = timer_manager.main([command, "timer-id"])

            self.assertEqual(exit_code, 0)
            control.assert_called_once_with("timer-id", command, False, False, False)

            with self.subTest(command=f"{command} --apply"), mock.patch.object(
                timer_manager,
                "control_job",
                return_value={"ok": True},
            ) as control, mock.patch("sys.stdout", StringIO()):
                exit_code = timer_manager.main([command, "timer-id", "--apply"])

            self.assertEqual(exit_code, 0)
            control.assert_called_once_with("timer-id", command, True, False, False)

    def test_cli_returns_failure_when_backend_returncode_fails(self) -> None:
        with mock.patch.object(
            timer_manager,
            "create_job",
            return_value={"operation": "create", "bootstrap_returncode": 5},
        ), mock.patch("sys.stdout", StringIO()):
            exit_code = timer_manager.main(["create", "--file", "timer.json", "--apply"])

        self.assertEqual(exit_code, 1)

    def test_launchd_crud_preview_and_apply_paths_are_separated(self) -> None:
        definition = {
            "id": "com.example.codex-crud",
            "backend": "launchd",
            "scope": "user",
            "trigger": {"type": "interval", "interval_seconds": 60},
            "action": {"command": "/bin/echo", "args": ["codex"]},
        }
        with tempfile.NamedTemporaryFile("w", delete=False) as handle:
            path = Path(handle.name)
            handle.write(timer_manager.json.dumps(definition))
        try:
            with tempfile.TemporaryDirectory() as directory:
                preview_source = Path(directory) / "com.example.codex-crud.plist"
                with mock.patch.object(timer_manager, "launchd_source_for_label", return_value=preview_source), mock.patch.object(
                    timer_manager,
                    "write_launchd_plist",
                ) as write_plist, mock.patch.object(timer_manager, "run_command") as run_command:
                    preview = timer_manager.create_job(str(path), apply=False, allow_non_ai=False)

                self.assertTrue(preview["dry_run"])
                write_plist.assert_not_called()
                run_command.assert_not_called()

                job = self.launchd_job()
                job.native_id = "com.example.codex-crud"
                job.id = timer_manager.stable_id("launchd", "user", job.native_id)
                job.source = str(preview_source)
                with mock.patch.object(timer_manager, "find_job", return_value=job), mock.patch.object(
                    timer_manager,
                    "launchd_control",
                ) as launchd_control, mock.patch.object(timer_manager, "write_launchd_plist") as write_plist, mock.patch.object(
                    timer_manager,
                    "run_command",
                    return_value=timer_manager.subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
                ) as run_command:
                    update = timer_manager.update_job(job.id, str(path), apply=True, allow_system=False, allow_non_ai=False)

                self.assertFalse(update["dry_run"])
                launchd_control.assert_called_once()
                write_plist.assert_called_once()
                run_command.assert_called_once()

                with mock.patch.object(timer_manager, "find_job", return_value=job), mock.patch.object(
                    timer_manager,
                    "launchd_control",
                ) as launchd_control, mock.patch.object(Path, "unlink") as unlink:
                    delete_preview = timer_manager.delete_job(job.id, confirm=None, allow_system=False, allow_non_ai=False)

                self.assertTrue(delete_preview["dry_run"])
                launchd_control.assert_not_called()
                unlink.assert_not_called()
        finally:
            path.unlink(missing_ok=True)

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

    def test_list_output_defaults_to_chinese_with_description_and_interval(self) -> None:
        job = timer_manager.timer_to_dict(self.launchd_job())
        job["pid"] = 12345
        job["health"]["last_exit_code"] = 0
        job["trigger"]["schedule"] = "every 10800s"
        job["trigger"]["interval_seconds"] = 10800

        output = StringIO()
        with mock.patch("sys.stdout", output), mock.patch.object(
            timer_manager.shutil,
            "get_terminal_size",
            return_value=timer_manager.os.terminal_size((160, 20)),
        ):
            timer_manager.print_result([job], as_json=False)

        lines = output.getvalue().splitlines()
        self.assertIn("标识", lines[0])
        self.assertIn("描述", lines[0])
        self.assertIn("间隔", lines[0])
        self.assertIn("状态", lines[0])
        self.assertIn("启用", lines[0])
        self.assertIn("加载", lines[0])
        self.assertIn("计划", lines[0])
        self.assertIn("PID", lines[0])
        self.assertIn("退出", lines[0])
        self.assertIn("动作", lines[0])
        self.assertIn("来源", lines[0])
        self.assertIn("launchd:user:com.example.codex-test", lines[1])
        self.assertIn("Codex Test", lines[1])
        self.assertIn("3h", lines[1])
        self.assertIn("停止", lines[1])
        self.assertIn("是", lines[1])
        self.assertIn("12345", lines[1])
        self.assertIn("0", lines[1])
        self.assertIn("true", lines[1])

    def test_list_output_can_use_english_headers(self) -> None:
        job = timer_manager.timer_to_dict(self.launchd_job())
        job["trigger"]["interval_seconds"] = 300

        output = StringIO()
        with mock.patch("sys.stdout", output), mock.patch.object(
            timer_manager.shutil,
            "get_terminal_size",
            return_value=timer_manager.os.terminal_size((160, 20)),
        ):
            timer_manager.print_result([job], as_json=False, lang="en")

        lines = output.getvalue().splitlines()
        self.assertIn("ID", lines[0])
        self.assertIn("DESCRIPTION", lines[0])
        self.assertIn("INTERVAL", lines[0])
        self.assertIn("STATE", lines[0])
        self.assertIn("SCHEDULE", lines[0])
        self.assertIn("5m", lines[1])
        self.assertIn("stopped", lines[1])

    def test_narrow_list_output_keeps_pid_and_exit_untruncated(self) -> None:
        job = timer_manager.timer_to_dict(self.launchd_job())
        job["pid"] = 12345
        job["health"]["last_exit_code"] = 0
        job["trigger"]["schedule"] = "every 10800s"

        output = StringIO()
        with mock.patch("sys.stdout", output), mock.patch.object(
            timer_manager.shutil,
            "get_terminal_size",
            return_value=timer_manager.os.terminal_size((80, 20)),
        ):
            timer_manager.print_result([job], as_json=False)

        lines = output.getvalue().splitlines()
        self.assertNotIn("ACTION", lines[0])
        self.assertIn("描述", lines[0])
        self.assertIn("间隔", lines[0])
        self.assertIn("PID", lines[0])
        self.assertIn("退出", lines[0])
        self.assertIn("计划", lines[0])
        self.assertIn("12345", lines[1])
        self.assertIn("0", lines[1])
        self.assertIn("停止", lines[1])
        self.assertLessEqual(max(len(line) for line in lines), 80)

    def test_extreme_pid_and_exit_are_not_truncated(self) -> None:
        job = timer_manager.timer_to_dict(self.launchd_job())
        job["pid"] = 987654321
        job["health"]["last_exit_code"] = -1073741510

        output = StringIO()
        with mock.patch("sys.stdout", output), mock.patch.object(
            timer_manager.shutil,
            "get_terminal_size",
            return_value=timer_manager.os.terminal_size((80, 20)),
        ):
            timer_manager.print_result([job], as_json=False)

        line = output.getvalue().splitlines()[1]
        self.assertIn("987654321", line)
        self.assertIn("-1073741510", line)

    def test_json_list_output_preserves_full_payload(self) -> None:
        job = timer_manager.timer_to_dict(self.launchd_job())

        output = StringIO()
        with mock.patch("sys.stdout", output):
            timer_manager.print_result([job], as_json=True)

        payload = timer_manager.json.loads(output.getvalue())
        self.assertEqual(payload, [job])

    def test_status_output_stays_json(self) -> None:
        job = self.launchd_job()
        output = StringIO()
        with mock.patch.object(timer_manager, "find_job", return_value=job), mock.patch("sys.stdout", output):
            exit_code = timer_manager.main(["status", job.id])

        self.assertEqual(exit_code, 0)
        payload = timer_manager.json.loads(output.getvalue())
        self.assertEqual(payload["id"], job.id)
        self.assertEqual(payload["trigger"]["type"], "interval")


if __name__ == "__main__":
    unittest.main()
