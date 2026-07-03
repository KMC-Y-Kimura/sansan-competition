from __future__ import annotations

import argparse
import functools
import http.server
import json
import socketserver
from pathlib import Path

from sansan_competition import Course, CourseWork, StudentSubmission, build_agent_output


ROOT = Path(__file__).resolve().parent
PUBLIC_DIR = ROOT / "public"


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


def build_sample_payload(agent_task_type: str) -> dict[str, object]:
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
        request_id=f"req_{agent_task_type.lower()}",
        course=course,
        coursework=coursework,
        submissions=submissions,
        tone="polite",
    ).to_dict()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Serve the Google Classroom support GUI prototype."
    )
    parser.add_argument(
        "command",
        choices=["serve", "sample-reminder", "sample-course-summary"],
        default="serve",
        nargs="?",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    if args.command == "sample-reminder":
        print(
            json.dumps(
                build_sample_payload("REMINDER_GENERATION"),
                ensure_ascii=False,
            )
        )
        return

    if args.command == "sample-course-summary":
        print(
            json.dumps(
                build_sample_payload("COURSE_SUMMARY"),
                ensure_ascii=False,
            )
        )
        return

    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler,
        directory=str(PUBLIC_DIR),
    )

    with ReusableTCPServer((args.host, args.port), handler) as server:
        url = f"http://{args.host}:{args.port}"
        print(f"Serving sansan-competition GUI at {url}")
        server.serve_forever()


if __name__ == "__main__":
    main()
