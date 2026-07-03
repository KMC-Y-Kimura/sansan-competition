from __future__ import annotations

import argparse
import functools
import http.server
import json
import socketserver
from datetime import datetime
from pathlib import Path
from typing import Sequence

from sansan_competition import (
    AgentTaskType,
    Course,
    CourseWork,
    StudentSubmission,
    analyze_submissions,
    build_agent_output,
    build_ai_task_input,
    build_reminder_generation_response,
    build_submission_analysis_response,
    normalize_course,
    normalize_coursework,
    normalize_submission_batch,
)
from sansan_competition.models import JST


ROOT = Path(__file__).resolve().parent
PUBLIC_DIR = ROOT / "public"


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


def build_sample_analysis():
    course = normalize_course(
        {
            "id": "123456789",
            "name": "数学I",
            "section": "1年A組",
            "description": "二次関数の基礎",
            "teacherIds": ["teacher_001"],
            "studentCount": 3,
        }
    )
    course_work = normalize_coursework(
        {
            "id": "987654321",
            "courseId": "123456789",
            "title": "二次関数プリント",
            "description": "配布プリントを解いて提出",
            "workType": "ASSIGNMENT",
            "dueDate": "2026-07-05",
            "dueTime": "23:59",
        }
    )
    submissions, issues = normalize_submission_batch(
        [
            {
                "id": "sub_001",
                "courseId": "123456789",
                "courseWorkId": "987654321",
                "studentId": "student_001",
                "studentName": "山田太郎",
                "state": "NEW",
            },
            {
                "id": "sub_002",
                "courseId": "123456789",
                "courseWorkId": "987654321",
                "studentId": "student_002",
                "studentName": "佐藤花子",
                "state": "TURNED_IN",
                "submissionTime": "2026-07-05T20:15:00+09:00",
                "attachments": [{"driveFile": {"id": "file_001"}}],
            },
            {
                "id": "sub_003",
                "courseId": "123456789",
                "courseWorkId": "987654321",
                "studentId": "student_003",
                "studentName": "鈴木一郎",
                "state": "TURNED_IN",
                "submissionTime": "2026-07-06T00:30:00+09:00",
                "late": True,
            },
        ]
    )

    analysis = analyze_submissions(
        course,
        course_work,
        submissions,
        now=datetime(2026, 7, 3, 13, 0, tzinfo=JST),
        normalization_issues=issues,
    )
    return course, course_work, analysis


def build_partial_sample_analysis():
    course = normalize_course(
        {
            "id": "123456789",
            "name": "数学I",
            "section": "1年A組",
            "description": "二次関数の基礎",
            "teacherIds": ["teacher_001"],
            "studentCount": 4,
        }
    )
    course_work = normalize_coursework(
        {
            "id": "987654321",
            "courseId": "123456789",
            "title": "二次関数プリント",
            "description": "配布プリントを解いて提出",
            "workType": "ASSIGNMENT",
            "dueDate": "2026-07-05",
            "dueTime": "23:59",
        }
    )
    submissions, issues = normalize_submission_batch(
        [
            {
                "id": "sub_001",
                "courseId": "123456789",
                "courseWorkId": "987654321",
                "studentId": "student_001",
                "studentName": "山田太郎",
                "state": "NEW",
            },
            {
                "id": "sub_002",
                "courseId": "123456789",
                "courseWorkId": "987654321",
                "studentId": "student_002",
                "studentName": "佐藤花子",
                "state": "TURNED_IN",
                "submissionTime": "2026-07-05T20:15:00+09:00",
                "attachments": [{"driveFile": {"id": "file_001"}}],
            },
            {
                "id": "sub_003",
                "courseWorkId": "987654321",
                "studentId": "student_003",
                "studentName": "鈴木一郎",
                "state": "TURNED_IN",
            },
            {
                "id": "sub_004",
                "courseId": "123456789",
                "courseWorkId": "987654321",
                "studentId": "student_004",
                "studentName": "高橋未来",
                "state": "TURNED_IN",
                "submissionTime": "2026-07-06T00:30:00+09:00",
                "late": True,
            },
        ]
    )

    analysis = analyze_submissions(
        course,
        course_work,
        submissions,
        now=datetime(2026, 7, 3, 13, 0, tzinfo=JST),
        normalization_issues=issues,
    )
    return course, course_work, analysis


def build_gui_sample_payload(agent_task_type: AgentTaskType | str) -> dict[str, object]:
    course = Course(
        course_id="123456789",
        name="数学I",
        section="1年A組",
        description="",
        state="ACTIVE",
        teacher_ids=["teacher_1"],
        student_count=30,
    )
    coursework = CourseWork(
        course_work_id="987654321",
        course_id=course.course_id,
        title="二次関数プリント",
        description="",
        work_type="ASSIGNMENT",
        max_points=100,
        due_date="2026-07-05",
        due_time="23:59",
        state="PUBLISHED",
        materials=[],
        topic_id="topic_1",
    )
    submissions = [
        StudentSubmission(
            student_submission_id="sub_1",
            course_id=course.course_id,
            course_work_id=coursework.course_work_id,
            student_id="student_1",
            student_name="山田太郎",
            state="NEW",
            late=False,
        ),
        StudentSubmission(
            student_submission_id="sub_2",
            course_id=course.course_id,
            course_work_id=coursework.course_work_id,
            student_id="student_2",
            student_name="佐藤花子",
            state="TURNED_IN",
            late=False,
        ),
    ]
    return build_agent_output(
        agent_task_type,
        request_id=f"req_{AgentTaskType(agent_task_type).value.lower()}",
        course=course,
        coursework=coursework,
        submissions=submissions,
        tone="polite",
    ).to_dict()


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Serve the GUI prototype or emit sample contract payloads."
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="serve",
        choices=(
            "serve",
            "demo",
            "sample-reminder",
            "sample-course-summary",
            "sample-ai-input-reminder",
            "sample-ai-input-weekly-report",
            "sample-partial-analysis",
            "sample-partial-reminder",
        ),
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    return parser.parse_args(argv)


def serve_gui(host: str, port: int) -> None:
    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler,
        directory=str(PUBLIC_DIR),
    )
    with ReusableTCPServer((host, port), handler) as server:
        url = f"http://{host}:{port}"
        print(f"Serving sansan-competition GUI at {url}")
        server.serve_forever()


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    course, course_work, analysis = build_sample_analysis()

    if args.command == "serve":
        serve_gui(args.host, args.port)
        return 0

    if args.command == "sample-reminder":
        payload = build_gui_sample_payload(AgentTaskType.REMINDER_GENERATION)
        print(json.dumps(payload, ensure_ascii=False))
        return 0

    if args.command == "sample-course-summary":
        payload = build_gui_sample_payload(AgentTaskType.COURSE_SUMMARY)
        print(json.dumps(payload, ensure_ascii=False))
        return 0

    if args.command == "sample-ai-input-reminder":
        payload = build_ai_task_input(
            AgentTaskType.REMINDER_GENERATION,
            analysis,
            output_formats=["classroomReminder", "markdown"],
            tone="polite",
            teacher_instruction="締切日を必ず明記してください。",
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if args.command == "sample-ai-input-weekly-report":
        payload = build_ai_task_input(
            AgentTaskType.WEEKLY_REPORT,
            analysis,
            output_formats=["markdown", "pdf", "googleDocument"],
            tone="formal",
            teacher_instruction="事実と次のアクションを分けてください。",
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if args.command == "sample-partial-analysis":
        _, _, partial_analysis = build_partial_sample_analysis()
        payload = build_submission_analysis_response(
            "req_20260703_demo_partial_analysis",
            partial_analysis,
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if args.command == "sample-partial-reminder":
        _, _, partial_analysis = build_partial_sample_analysis()
        payload = build_reminder_generation_response(
            "req_20260703_demo_partial_reminder",
            partial_analysis,
            reminder_title="課題提出リマインド",
            reminder_body=(
                "提出データの一部が取得できていません。"
                "確認できた範囲で、まだ提出していない人は7月5日までに提出してください。"
            ),
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if args.command == "demo":
        payload = {
            "submissionAnalysis": build_submission_analysis_response(
                "req_20260703_demo_analysis",
                analysis,
            ),
            "reminderGeneration": build_reminder_generation_response(
                "req_20260703_demo_reminder",
                analysis,
                reminder_title="課題提出リマインド",
                reminder_body=(
                    "課題「二次関数プリント」の提出期限が近づいています。"
                    "まだ提出していない人は、7月5日までに提出してください。"
                ),
            ),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    raise ValueError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
