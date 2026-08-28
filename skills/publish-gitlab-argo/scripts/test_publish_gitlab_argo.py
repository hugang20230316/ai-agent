#!/usr/bin/env python3
from __future__ import annotations

import sys
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import publish_gitlab_argo


class PublishGitLabArgoTests(unittest.TestCase):
    def test_source_ref_cli_overrides_config(self) -> None:
        args = mock.Mock(repo_path="/tmp/project", source_ref="release", scope="default", apps=None)
        connection = mock.Mock(config_path=None, base_url="https://gitlab.example.com")
        locked_source = {
            "sourceRef": "release",
            "sourceCommit": "abc123",
            "sourceBranch": "release",
            "currentBranch": "main",
        }

        with (
            mock.patch.dict(publish_gitlab_argo.PUBLISH_CONFIG, {"sourceRef": "dev"}, clear=True),
            mock.patch.object(publish_gitlab_argo, "resolve_repo_path", return_value=Path("/tmp/project")),
            mock.patch.object(publish_gitlab_argo, "ensure_repo_matches_cwd"),
            mock.patch.object(publish_gitlab_argo, "resolve_locked_source", return_value=locked_source) as resolve_source,
            mock.patch.object(publish_gitlab_argo, "gitlab_connection_info", return_value=connection),
            mock.patch.object(publish_gitlab_argo, "run_git", side_effect=["subject", "message", "origin"]),
            mock.patch.object(
                publish_gitlab_argo,
                "gitlab_latest_release_tag",
                return_value={"latestTag": "v0.1.2-release", "latestTagCommit": "abc123"},
            ),
            mock.patch.object(publish_gitlab_argo, "gitlab_previous_release_tag", return_value=None),
            mock.patch.object(publish_gitlab_argo, "git_changed_files", return_value=[]),
        ):
            plan = publish_gitlab_argo.resolve_publish_plan(args)

        resolve_source.assert_called_once_with(Path("/tmp/project"), "release")
        self.assertEqual(plan["sourceRef"], "release")
        self.assertEqual(plan["sourceRefSource"], "cli")

    def test_default_scope_does_not_imply_source_ref(self) -> None:
        args = mock.Mock(repo_path="/tmp/project", source_ref=None, scope="default")

        with (
            mock.patch.dict(publish_gitlab_argo.PUBLISH_CONFIG, {}, clear=True),
            mock.patch.object(publish_gitlab_argo, "resolve_repo_path", return_value=Path("/tmp/project")),
            mock.patch.object(publish_gitlab_argo, "ensure_repo_matches_cwd"),
            mock.patch.object(publish_gitlab_argo, "gitlab_connection_info") as connection_info,
        ):
            with self.assertRaisesRegex(RuntimeError, "SourceRef"):
                publish_gitlab_argo.resolve_publish_plan(args)

        connection_info.assert_not_called()

    def test_explicit_non_current_source_ref_does_not_switch_branch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_path = Path(directory)
            self._git(repo_path, "init", "-b", "main")
            self._git(repo_path, "config", "user.email", "test@example.com")
            self._git(repo_path, "config", "user.name", "Test User")
            (repo_path / "version.txt").write_text("main\n", encoding="utf-8")
            self._git(repo_path, "add", "version.txt")
            self._git(repo_path, "commit", "-m", "main")
            self._git(repo_path, "branch", "dev")

            source = publish_gitlab_argo.resolve_locked_source(repo_path, "dev")

            self.assertEqual(source["sourceRef"], "dev")
            self.assertEqual(source["sourceBranch"], "dev")
            self.assertEqual(source["currentBranch"], "main")
            self.assertEqual(self._git(repo_path, "branch", "--show-current"), "main")
            self.assertEqual(source["sourceCommit"], self._git(repo_path, "rev-parse", "dev^{commit}"))

    def test_merge_conflict_rejects_head_but_allows_non_current_ref(self) -> None:
        repo_path = Path("/tmp/project")

        def fake_git(_repo_path: Path, *arguments: str) -> str:
            if arguments == ("branch", "--show-current"):
                return "main"
            if arguments == ("diff", "--name-only", "--diff-filter=U"):
                return ""
            if arguments == ("rev-parse", "--verify", "dev^{commit}"):
                return "abc123"
            if arguments == ("rev-parse", "--symbolic-full-name", "dev"):
                return "refs/heads/dev"
            raise AssertionError(arguments)

        with (
            mock.patch.object(publish_gitlab_argo, "git_ref_exists", return_value=True),
            mock.patch.object(publish_gitlab_argo, "run_git", side_effect=fake_git),
        ):
            with self.assertRaisesRegex(RuntimeError, "冲突.*HEAD"):
                publish_gitlab_argo.resolve_locked_source(repo_path, "HEAD")
            source = publish_gitlab_argo.resolve_locked_source(repo_path, "dev")

        self.assertEqual(source["sourceCommit"], "abc123")

    def test_commit_source_ref_does_not_invent_source_branch(self) -> None:
        def fake_git(_repo_path: Path, *arguments: str) -> str:
            if arguments == ("branch", "--show-current"):
                return "main"
            if arguments == ("diff", "--name-only", "--diff-filter=U"):
                return ""
            if arguments == ("rev-parse", "--verify", "abc123^{commit}"):
                return "abc123"
            if arguments == ("rev-parse", "--symbolic-full-name", "abc123"):
                return ""
            raise AssertionError(arguments)

        with (
            mock.patch.object(publish_gitlab_argo, "git_ref_exists", return_value=False),
            mock.patch.object(publish_gitlab_argo, "run_git", side_effect=fake_git),
        ):
            source = publish_gitlab_argo.resolve_locked_source(Path("/tmp/project"), "abc123")

        self.assertEqual(source["sourceBranch"], "")

    def test_tag_must_point_to_locked_source_commit(self) -> None:
        with (
            mock.patch.object(publish_gitlab_argo, "gitlab_tag_commit", return_value="other") as tag_commit,
            mock.patch.object(publish_gitlab_argo, "gitlab_pipeline_status") as pipeline_status,
        ):
            with self.assertRaisesRegex(RuntimeError, "未指向锁定源码提交"):
                publish_gitlab_argo.wait_gitlab_latest_release_tag_passed(
                    mock.Mock(),
                    30,
                    1,
                    publish_gitlab_argo.DEFAULT_RELEASE_TAG_PATTERN,
                    planned_tag="v0.1.2",
                    source_commit="abc123",
                )

        tag_commit.assert_called_once_with(mock.ANY, "v0.1.2")
        pipeline_status.assert_not_called()

    def test_pipeline_gate_stays_on_planned_tag_when_newer_tag_exists(self) -> None:
        connection = mock.Mock()

        with (
            mock.patch.object(publish_gitlab_argo, "gitlab_tag_commit", return_value="abc123"),
            mock.patch.object(publish_gitlab_argo, "gitlab_pipeline_status", return_value={"id": "7", "normalized": "passed"}) as pipeline_status,
            mock.patch.object(publish_gitlab_argo, "gitlab_latest_release_tag") as latest_tag,
        ):
            result = publish_gitlab_argo.wait_gitlab_latest_release_tag_passed(
                connection,
                30,
                1,
                publish_gitlab_argo.DEFAULT_RELEASE_TAG_PATTERN,
                planned_tag="v0.1.2",
                source_commit="abc123",
            )

        latest_tag.assert_not_called()
        pipeline_status.assert_called_once_with(connection, "v0.1.2")
        self.assertEqual(result["latestTag"], "v0.1.2")

    def test_publish_identity_requires_source_tag_and_apps_to_match(self) -> None:
        expected = {
            "sourceRef": "dev",
            "sourceCommit": "abc123",
            "effectiveTag": "v0.1.2",
            "targetApps": ["api-dev", "worker-dev"],
        }

        self.assertEqual(publish_gitlab_argo.publish_identity(dict(expected)), expected)
        for key, value in {
            "sourceRef": "release",
            "sourceCommit": "def456",
            "effectiveTag": "v0.1.3",
            "targetApps": ["api-dev"],
        }.items():
            candidate = dict(expected)
            candidate[key] = value
            self.assertNotEqual(publish_gitlab_argo.publish_identity(candidate), expected, key)

    def test_active_publish_lock_with_different_identity_is_not_reused(self) -> None:
        args = mock.Mock(
            apps=["api-dev"],
            scope="default",
            total_timeout_seconds=30,
            gitlab_wait_timeout_seconds=10,
            sync_timeout_seconds=10,
            what_if=False,
            quiet=True,
            format="json",
        )
        connection = mock.Mock()
        plan = {
            "_connection": connection,
            "repoPath": "/tmp/project",
            "sourceRef": "dev",
            "sourceCommit": "abc123",
            "effectiveTag": "v0.1.2",
            "targetApps": ["api-dev"],
        }

        with tempfile.TemporaryDirectory() as directory:
            state_dir = Path(directory)
            publish_gitlab_argo.write_json_file(
                state_dir / publish_gitlab_argo.LOCK_FILE_NAME,
                {
                    "processId": 999,
                    "sourceRef": "release",
                    "sourceCommit": "def456",
                    "effectiveTag": "v0.1.3",
                    "targetApps": ["worker-dev"],
                    "startedAt": "2026-07-20T00:00:00Z",
                },
            )
            with (
                mock.patch.object(publish_gitlab_argo, "resolve_publish_plan", return_value=plan),
                mock.patch.object(publish_gitlab_argo, "publish_state_directory", return_value=state_dir),
                mock.patch.object(publish_gitlab_argo.os, "kill", return_value=None),
                mock.patch.object(publish_gitlab_argo, "gitlab_create_tag") as create_tag,
            ):
                with self.assertRaisesRegex(RuntimeError, "不一致.*禁止复用"):
                    publish_gitlab_argo.execute_publish(args)

        create_tag.assert_not_called()

    def test_publish_failure_output_includes_locked_identity(self) -> None:
        args = mock.Mock(
            apps=["api-dev"],
            scope="default",
            total_timeout_seconds=30,
            gitlab_wait_timeout_seconds=10,
            sync_timeout_seconds=10,
            what_if=False,
            quiet=True,
            format="json",
        )
        plan = {
            "_connection": mock.Mock(),
            "repoPath": "/tmp/project",
            "sourceRef": "dev",
            "sourceCommit": "abc123",
            "effectiveTag": "v0.1.2",
            "targetApps": ["api-dev"],
            "shouldCreateTag": True,
            "nextTag": "v0.1.2",
            "tagDescription": "release",
            "releaseTagPattern": publish_gitlab_argo.DEFAULT_RELEASE_TAG_PATTERN.pattern,
        }

        with tempfile.TemporaryDirectory() as directory:
            with (
                mock.patch.object(publish_gitlab_argo, "resolve_publish_plan", return_value=plan),
                mock.patch.object(publish_gitlab_argo, "publish_state_directory", return_value=Path(directory)),
                mock.patch.object(publish_gitlab_argo, "gitlab_create_tag", return_value={"action": "created"}),
                mock.patch.object(publish_gitlab_argo, "ensure_gitlab_tag_matches_source", return_value="abc123"),
                mock.patch.object(
                    publish_gitlab_argo,
                    "wait_gitlab_release_gate",
                    side_effect=RuntimeError("pipeline timeout"),
                ),
            ):
                with self.assertRaisesRegex(
                    RuntimeError,
                    "sourceRef=dev sourceCommit=abc123 plannedTag=v0\\.1\\.2; pipeline timeout",
                ):
                    publish_gitlab_argo.execute_publish(args)

    def test_next_tag_keeps_release_suffix(self) -> None:
        self.assertEqual(publish_gitlab_argo.next_tag("v0.0.866-release"), "v0.0.867-release")
        self.assertEqual(publish_gitlab_argo.next_tag("v0.1.21-release"), "v0.1.22-release")

    def test_release_tag_version_prefers_new_minor_family(self) -> None:
        self.assertGreater(publish_gitlab_argo.compare_tag_version("v0.1.21-release", "v0.0.974-release"), 0)

    def test_release_branch_uses_release_tag_pattern(self) -> None:
        pattern = publish_gitlab_argo.release_tag_pattern_for_branch("release")

        self.assertRegex("v0.1.21-release", pattern)
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

    @staticmethod
    def _git(repo_path: Path, *arguments: str) -> str:
        process = subprocess.run(
            ["git", "-C", str(repo_path), *arguments],
            check=True,
            capture_output=True,
            text=True,
        )
        return process.stdout.strip()

    def test_job_gate_timeout_includes_last_observed_jobs(self) -> None:
        args = mock.Mock()
        args.quiet = True
        args.format = "json"
        args.gitlab_poll_interval_seconds = 1
        started_at = datetime(2026, 7, 2, tzinfo=timezone.utc)

        with (
            mock.patch.object(publish_gitlab_argo, "utc_now", side_effect=[started_at, started_at, started_at, started_at + timedelta(seconds=2)]),
            mock.patch.object(publish_gitlab_argo, "gitlab_tag_commit", return_value="abc"),
            mock.patch.object(publish_gitlab_argo, "gitlab_pipeline_status", return_value={"id": "123", "normalized": "running"}),
            mock.patch.object(
                publish_gitlab_argo,
                "gitlab_pipeline_jobs",
                return_value=[
                    {"name": "build-teacherai-services", "status": "running", "stage": "build"},
                    {"name": "build-teacherai-backgroudtasks", "status": "pending", "stage": "build"},
                ],
            ),
            mock.patch.object(publish_gitlab_argo.time, "sleep", return_value=None),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "GitLab job gate 在 1 秒内仍未通过: tag=v0\\.1\\.22-release sourceCommit=abc pipeline=123 build-teacherai-backgroudtasks=running, build-teacherai-services=running",
            ):
                publish_gitlab_argo.wait_gitlab_latest_release_jobs_passed(
                    mock.Mock(),
                    ["build-teacherai-backgroudtasks", "build-teacherai-services"],
                    1,
                    1,
                    publish_gitlab_argo.release_tag_pattern_for_branch("release"),
                    planned_tag="v0.1.22-release",
                    source_commit="abc",
                    args=args,
                )

    def test_job_gate_plays_configured_manual_job_once(self) -> None:
        args = mock.Mock(quiet=True, format="json")
        connection = mock.Mock(project_id="42")

        with (
            mock.patch.object(
                publish_gitlab_argo,
                "gitlab_tag_commit",
                return_value="abc",
            ),
            mock.patch.object(
                publish_gitlab_argo,
                "gitlab_pipeline_status",
                return_value={"id": "7", "normalized": "passed"},
            ),
            mock.patch.object(
                publish_gitlab_argo,
                "gitlab_pipeline_jobs",
                side_effect=[
                    [
                        {"id": 101, "name": "build-worker", "status": "manual", "stage": "build"},
                        {"id": 102, "name": "build-services", "status": "success", "stage": "build"},
                        {"id": 103, "name": "build-other", "status": "manual", "stage": "build"},
                    ],
                    [
                        {"id": 101, "name": "build-worker", "status": "manual", "stage": "build"},
                        {"id": 102, "name": "build-services", "status": "success", "stage": "build"},
                        {"id": 103, "name": "build-other", "status": "manual", "stage": "build"},
                    ],
                    [
                        {"id": 101, "name": "build-worker", "status": "success", "stage": "build"},
                        {"id": 102, "name": "build-services", "status": "success", "stage": "build"},
                    ],
                ],
            ),
            mock.patch.object(publish_gitlab_argo, "gitlab_request") as request,
            mock.patch.object(publish_gitlab_argo.time, "sleep", return_value=None),
        ):
            result = publish_gitlab_argo.wait_gitlab_latest_release_jobs_passed(
                connection,
                ["build-worker", "build-services"],
                30,
                1,
                publish_gitlab_argo.DEFAULT_RELEASE_TAG_PATTERN,
                planned_tag="v0.1.2",
                source_commit="abc",
                auto_play_job_names={"build-worker"},
                args=args,
            )

        request.assert_called_once_with(connection, "POST", "/api/v4/projects/42/jobs/101/play")
        self.assertEqual(result["pipelineStatus"], "jobs-passed")

    def test_job_gate_rejects_unconfigured_manual_job(self) -> None:
        args = mock.Mock(quiet=True, format="json")
        connection = mock.Mock(project_id="42")

        with (
            mock.patch.object(
                publish_gitlab_argo,
                "gitlab_tag_commit",
                return_value="abc",
            ),
            mock.patch.object(
                publish_gitlab_argo,
                "gitlab_pipeline_status",
                return_value={"id": "7", "normalized": "passed"},
            ),
            mock.patch.object(
                publish_gitlab_argo,
                "gitlab_pipeline_jobs",
                return_value=[{"id": 101, "name": "build-worker", "status": "manual", "stage": "build"}],
            ),
            mock.patch.object(publish_gitlab_argo, "gitlab_request") as request,
        ):
            with self.assertRaisesRegex(RuntimeError, "需要手动触发.*build-worker"):
                publish_gitlab_argo.wait_gitlab_latest_release_jobs_passed(
                    connection,
                    ["build-worker"],
                    30,
                    1,
                    publish_gitlab_argo.DEFAULT_RELEASE_TAG_PATTERN,
                    planned_tag="v0.1.2",
                    source_commit="abc",
                    auto_play_job_names=set(),
                    args=args,
                )

        request.assert_not_called()

    def test_job_gate_does_not_play_already_running_job(self) -> None:
        args = mock.Mock(quiet=True, format="json")
        connection = mock.Mock(project_id="42")

        with (
            mock.patch.object(
                publish_gitlab_argo,
                "gitlab_tag_commit",
                return_value="abc",
            ),
            mock.patch.object(
                publish_gitlab_argo,
                "gitlab_pipeline_status",
                return_value={"id": "7", "normalized": "running"},
            ),
            mock.patch.object(
                publish_gitlab_argo,
                "gitlab_pipeline_jobs",
                side_effect=[
                    [{"id": 101, "name": "build-worker", "status": "running", "stage": "build"}],
                    [{"id": 101, "name": "build-worker", "status": "success", "stage": "build"}],
                ],
            ),
            mock.patch.object(publish_gitlab_argo, "gitlab_request") as request,
            mock.patch.object(publish_gitlab_argo.time, "sleep", return_value=None),
        ):
            result = publish_gitlab_argo.wait_gitlab_latest_release_jobs_passed(
                connection,
                ["build-worker"],
                30,
                1,
                publish_gitlab_argo.DEFAULT_RELEASE_TAG_PATTERN,
                planned_tag="v0.1.2",
                source_commit="abc",
                auto_play_job_names={"build-worker"},
                args=args,
            )

        request.assert_not_called()
        self.assertEqual(result["pipelineStatus"], "jobs-passed")

    def test_release_gate_does_not_fallback_for_unconfigured_manual_job(self) -> None:
        args = mock.Mock(
            apps=None,
            resolved_apps=["worker-dev"],
            scope="default",
            gitlab_gate_jobs=None,
            gitlab_poll_interval_seconds=1,
            quiet=True,
            format="json",
        )

        with (
            mock.patch.dict(
                publish_gitlab_argo.PUBLISH_CONFIG,
                {
                    "gitlabGateJobsByApp": {"worker-dev": "build-worker"},
                    "gitlabAutoPlayJobs": [],
                },
                clear=True,
            ),
            mock.patch.object(
                publish_gitlab_argo,
                "gitlab_tag_commit",
                return_value="abc",
            ),
            mock.patch.object(
                publish_gitlab_argo,
                "gitlab_pipeline_status",
                return_value={"id": "7", "normalized": "passed"},
            ),
            mock.patch.object(
                publish_gitlab_argo,
                "gitlab_pipeline_jobs",
                return_value=[{"id": 101, "name": "build-worker", "status": "manual", "stage": "build"}],
            ),
            mock.patch.object(publish_gitlab_argo, "wait_gitlab_latest_release_tag_passed") as fallback,
        ):
            with self.assertRaisesRegex(RuntimeError, "GitLab job gate 失败.*需要手动触发"):
                publish_gitlab_argo.wait_gitlab_release_gate(
                    mock.Mock(),
                    args,
                    30,
                    publish_gitlab_argo.DEFAULT_RELEASE_TAG_PATTERN,
                    planned_tag="v0.1.2",
                    source_commit="abc",
                )

        fallback.assert_not_called()

    def test_release_gate_fails_closed_when_app_job_mapping_is_missing(self) -> None:
        args = mock.Mock(
            apps=None,
            resolved_apps=["worker-dev", "mcp-dev"],
            scope="default",
            gitlab_gate_jobs=None,
            gitlab_poll_interval_seconds=1,
            quiet=True,
            format="json",
        )

        with (
            mock.patch.dict(
                publish_gitlab_argo.PUBLISH_CONFIG,
                {
                    "gitlabGateJobsByApp": {"worker-dev": "build-worker"},
                    "gitlabAutoPlayJobs": ["build-worker"],
                },
                clear=True,
            ),
            mock.patch.object(publish_gitlab_argo, "wait_gitlab_latest_release_tag_passed") as fallback,
        ):
            with self.assertRaisesRegex(RuntimeError, "缺少应用的 GitLab job 映射: mcp-dev"):
                publish_gitlab_argo.wait_gitlab_release_gate(
                    mock.Mock(),
                    args,
                    30,
                    publish_gitlab_argo.DEFAULT_RELEASE_TAG_PATTERN,
                    planned_tag="v0.1.2",
                    source_commit="abc",
                )

        fallback.assert_not_called()

    def test_release_gate_passes_configured_auto_play_jobs_to_job_gate(self) -> None:
        args = mock.Mock(
            apps=None,
            resolved_apps=["worker-dev", "mcp-dev"],
            scope="default",
            gitlab_gate_jobs=None,
            gitlab_poll_interval_seconds=1,
        )
        expected = {"pipelineStatus": "jobs-passed"}

        with (
            mock.patch.dict(
                publish_gitlab_argo.PUBLISH_CONFIG,
                {
                    "gitlabGateJobsByApp": {
                        "worker-dev": "build-worker",
                        "mcp-dev": "build-mcp",
                    },
                    "gitlabAutoPlayJobs": ["build-worker", "build-mcp"],
                },
                clear=True,
            ),
            mock.patch.object(
                publish_gitlab_argo,
                "wait_gitlab_latest_release_jobs_passed",
                return_value=expected,
            ) as wait_jobs,
        ):
            result = publish_gitlab_argo.wait_gitlab_release_gate(
                mock.Mock(),
                args,
                30,
                publish_gitlab_argo.DEFAULT_RELEASE_TAG_PATTERN,
                planned_tag="v0.1.2",
                source_commit="abc",
            )

        self.assertEqual(result, expected)
        self.assertEqual(wait_jobs.call_args.args[1], ["build-mcp", "build-worker"])
        self.assertEqual(wait_jobs.call_args.kwargs["auto_play_job_names"], {"build-worker", "build-mcp"})


if __name__ == "__main__":
    unittest.main()
