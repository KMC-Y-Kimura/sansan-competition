"""mocky実行層のデモ (オフライン・モック)。

kimuの契約(正規化→分析→レスポンス生成)と、mockyの実行(認証→取得→承認→出力/投稿)を
一連で通す。実行: uv run python -m sansan_competition.execution.demo
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..analysis import analyze_submissions
from ..contract import build_reminder_generation_response, validate_agent_output
from ..models import JST
from ..normalization import (
    normalize_course,
    normalize_coursework,
    normalize_submission_batch,
)
from .classroom_client import MockClassroomClient
from .google_auth import MockAuthProvider, READ_SCOPES, WRITE_SCOPES
from .posting import OutputExecutor, build_post_preview
from .renderers import MockGoogleDocsClient

OUT_DIR = Path(__file__).resolve().parent.parent.parent / "output"


def main() -> None:
    # 1. ログイン (READ + WRITE)
    auth = MockAuthProvider(email="teacher@example.com")
    creds = auth.login(READ_SCOPES + WRITE_SCOPES)
    print(f"[auth] logged in: {creds.email} token={creds.masked_token()}")

    # 2. Classroom生データ取得 (mocky) → 正規化 (kimu)
    classroom = MockClassroomClient(auth)
    raw_course = classroom.list_courses()[0]
    raw_work = classroom.list_course_work(raw_course["id"])[0]
    raw_subs = classroom.list_submissions(raw_course["id"], raw_work["id"])

    course = normalize_course(raw_course)
    course_work = normalize_coursework(raw_work)
    submissions, issues = normalize_submission_batch(raw_subs)
    print(f"[classroom] course={course.name} work={course_work.title}")

    # 3. 分析 → リマインド応答生成 (kimu)
    analysis = analyze_submissions(
        course,
        course_work,
        submissions,
        now=datetime(2026, 7, 3, 13, 0, tzinfo=JST),
        normalization_issues=issues,
    )
    print(f"[analysis] 未提出{len(analysis.unsubmitted)}名 / 遅延{len(analysis.late_submissions)}名")

    response = build_reminder_generation_response(
        "req_20260703_demo_reminder",
        analysis,
        reminder_title="課題提出リマインド",
        reminder_body=(
            "課題「二次関数プリント」の提出期限が近づいています。"
            "まだ提出していない人は、7月5日までに提出してください。"
        ),
    )
    schema_errors = validate_agent_output(response)
    print(f"[contract] validate_agent_output errors={schema_errors}")

    # 4. 投稿確認画面(15.7)
    preview = build_post_preview(response["outputs"]["classroomReminder"])
    print("[preview] 投稿先:", preview["courseId"], "/ 対象:", preview["audience"])
    if preview["warnings"]:
        print("[preview] warnings:", preview["warnings"])

    # 5. 教師承認 → 実行 (mocky)
    approved = {a["actionId"] for a in response["approval"]["actions"]}
    print(f"[approval] 承認: {sorted(approved)}")

    executor = OutputExecutor(
        classroom=classroom, docs=MockGoogleDocsClient(), out_dir=OUT_DIR
    )
    results = executor.execute(response, approved)
    print("[execute] 結果:")
    for r in results:
        line = f"  - {r.actionId} {r.type}: {r.status}"
        if r.detail:
            line += f" -> {r.detail.get('path') or r.detail.get('url')}"
        if r.error:
            line += f" !! {r.error}"
        print(line)


if __name__ == "__main__":
    main()
