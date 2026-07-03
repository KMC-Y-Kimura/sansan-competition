"""承認フローの安全性テスト (最重要: 未承認でClassroom投稿しない)。"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from sansan_competition.execution.classroom_client import MockClassroomClient
from sansan_competition.execution.google_auth import (
    MockAuthProvider,
    READ_SCOPES,
    WRITE_SCOPES,
)
from sansan_competition.execution.posting import (
    ActionType,
    OutputExecutor,
    build_post_preview,
)
from sansan_competition.execution.renderers import MockGoogleDocsClient

SAMPLE = (
    Path(__file__).resolve().parent.parent
    / "samples"
    / "reminder_generation_success.json"
)


def _response() -> dict:
    return json.loads(SAMPLE.read_text(encoding="utf-8"))


def _executor(out_dir) -> OutputExecutor:
    auth = MockAuthProvider()
    auth.login(READ_SCOPES + WRITE_SCOPES)
    return OutputExecutor(
        classroom=MockClassroomClient(auth),
        docs=MockGoogleDocsClient(),
        out_dir=out_dir,
    )


class ApprovalGateTests(unittest.TestCase):
    def test_no_approval_no_side_effects(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            results = _executor(tmp).execute(_response(), approved_action_ids=set())
            self.assertTrue(all(r.status == "skipped" for r in results))
            self.assertEqual(list(Path(tmp).iterdir()), [])  # ファイル生成なし

    def test_only_approved_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            results = _executor(tmp).execute(
                _response(), approved_action_ids={"action_export_markdown"}
            )
            by_id = {r.actionId: r for r in results}
            self.assertEqual(by_id["action_export_markdown"].status, "success")
            # Classroom投稿は未承認 → skipped
            self.assertEqual(
                by_id["action_create_classroom_announcement"].status, "skipped"
            )

    def test_approved_announcement_posts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            results = _executor(tmp).execute(
                _response(),
                approved_action_ids={"action_create_classroom_announcement"},
            )
            post = next(
                r
                for r in results
                if r.type == ActionType.CREATE_CLASSROOM_ANNOUNCEMENT
            )
            self.assertEqual(post.status, "success")
            self.assertTrue(post.detail["announcementId"])
            self.assertTrue(
                post.detail["url"].startswith("https://classroom.google.com/")
            )

    def test_error_isolated_per_action(self) -> None:
        response = _response()
        response["outputs"]["classroomReminder"]["target"] = {}  # 投稿だけ壊す
        with tempfile.TemporaryDirectory() as tmp:
            results = _executor(tmp).execute(
                response,
                approved_action_ids={
                    "action_create_classroom_announcement",
                    "action_export_markdown",
                },
            )
            by_id = {r.actionId: r for r in results}
            self.assertEqual(by_id["action_create_classroom_announcement"].status, "error")
            self.assertEqual(by_id["action_export_markdown"].status, "success")

    def test_post_preview_flags_personal_name(self) -> None:
        preview = build_post_preview(
            {
                "target": {"courseId": "1"},
                "text": "山田さん、提出してください。",
                "assigneeMode": "ALL_STUDENTS",
            }
        )
        self.assertEqual(preview["audience"], "コース全員")
        self.assertTrue(preview["warnings"])


if __name__ == "__main__":
    unittest.main()
