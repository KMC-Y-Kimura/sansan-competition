"""結合テスト: mocky取得 → kimu正規化/分析/生成 → mocky実行 (REQUIREMENTS 20.2)。"""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from scripts import classroom_fetch_analysis as classroom_fetch_analysis_script
from sansan_competition.analysis import analyze_submissions
from sansan_competition.classroom import fetch_submission_analysis, load_classroom_fetch_fixture
from sansan_competition.contract import (
    build_submission_analysis_response,
    build_reminder_generation_response,
    validate_agent_output,
)
from sansan_competition.models import JST
from sansan_competition.normalization import (
    normalize_course,
    normalize_coursework,
    normalize_submission_batch,
)
from sansan_competition.execution.classroom_client import MockClassroomClient
from sansan_competition.execution.google_auth import MockAuthProvider, READ_SCOPES, WRITE_SCOPES
from sansan_competition.execution.posting import OutputExecutor
from sansan_competition.execution.renderers import MockGoogleDocsClient

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "classroom_fetch"


class IntegrationTests(unittest.TestCase):
    def test_full_pipeline(self) -> None:
        auth = MockAuthProvider()
        auth.login(READ_SCOPES + WRITE_SCOPES)
        classroom = MockClassroomClient(auth)

        raw_course = classroom.list_courses()[0]
        raw_work = classroom.list_course_work(raw_course["id"])[0]
        raw_subs = classroom.list_submissions(raw_course["id"], raw_work["id"])

        course = normalize_course(raw_course)
        course_work = normalize_coursework(raw_work)
        submissions, issues = normalize_submission_batch(raw_subs)
        self.assertEqual(issues, [])

        analysis = analyze_submissions(
            course,
            course_work,
            submissions,
            now=datetime(2026, 7, 3, 13, 0, tzinfo=JST),
            normalization_issues=issues,
        )
        self.assertEqual(len(analysis.unsubmitted), 12)

        response = build_reminder_generation_response(
            "req_integration",
            analysis,
            reminder_title="課題提出リマインド",
            reminder_body="まだ提出していない人は提出してください。",
        )
        # kimuの契約バリデータを通ること
        self.assertEqual(validate_agent_output(response), [])

        approved = {a["actionId"] for a in response["approval"]["actions"]}
        with tempfile.TemporaryDirectory() as tmp:
            executor = OutputExecutor(
                classroom=classroom, docs=MockGoogleDocsClient(), out_dir=tmp
            )
            results = executor.execute(response, approved)
            statuses = {r.type: r.status for r in results}
            self.assertEqual(statuses["CREATE_CLASSROOM_ANNOUNCEMENT"], "success")
            self.assertEqual(statuses["EXPORT_PDF"], "success")
            self.assertEqual(statuses["EXPORT_MARKDOWN"], "success")
            # 生成物が存在する
            self.assertTrue(any(Path(tmp).iterdir()))

    def test_live_like_fixture_reaches_submission_analysis_contract(self) -> None:
        fixture = load_classroom_fetch_fixture(FIXTURE_DIR / "live_like_assignment.json")
        analysis = fetch_submission_analysis(
            fixture.build_client(),
            course_id=fixture.course_id,
            course_work_id=fixture.course_work_id,
            now=datetime(2026, 7, 5, 12, 0, tzinfo=JST),
        )

        payload = build_submission_analysis_response("req_fixture_contract", analysis)
        self.assertEqual(validate_agent_output(payload), [])
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["course"]["courseId"], "course_live_math_001")
        self.assertEqual(
            payload["summary"]["shortSummary"],
            "ベクトル課題 3 の未提出者は 2名、遅延提出者は 1名です。",
        )
        late_row = next(
            row
            for row in payload["gui"]["tables"][0]["rows"]
            if row["studentId"] == "student_003"
        )
        self.assertEqual(late_row["studentName"], "上田凛")
        self.assertEqual(late_row["status"], "返却済み（遅延提出）")

    def test_classroom_fetch_analysis_script_replays_fixture_without_oauth(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()

        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exit_code = classroom_fetch_analysis_script.main(
                [
                    "--fixture",
                    str(FIXTURE_DIR / "live_like_assignment.json"),
                    "--request-id",
                    "req_fixture_cli",
                ]
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")

        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["requestId"], "req_fixture_cli")
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["course"]["courseId"], "course_live_math_001")
        self.assertEqual(payload["summary"]["teacherActionRequired"], True)
        self.assertEqual(payload["errors"], [])


if __name__ == "__main__":
    unittest.main()
