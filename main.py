from __future__ import annotations

import argparse
import http.server
import json
import socketserver
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import parse_qs, urlparse

from sansan_competition import (
    AgentTaskType,
    Course,
    CourseWork,
    StudentSubmission,
    analyze_submissions,
    build_agent_output,
    build_error_response,
    build_ai_task_input,
    build_reminder_generation_response,
    build_submission_analysis_response,
    normalize_course,
    normalize_coursework,
    normalize_submission_batch,
    validate_agent_output,
)
from sansan_competition.classroom import (
    GoogleClassroomClient,
    build_post_only_client,
    fetch_submission_analysis,
)
from sansan_competition.execution.errors import AgentError, ErrorCode
from sansan_competition.models import JST


ROOT = Path(__file__).resolve().parent
PUBLIC_DIR = ROOT / "public"


class ReusableTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


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


def build_live_request_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def build_course_list_payload(courses: list[Course]) -> dict[str, object]:
    items = sorted(
        (course.to_contract() for course in courses),
        key=lambda item: (
            str(item.get("name") or "").casefold(),
            str(item.get("section") or "").casefold(),
        ),
    )
    return {
        "requestId": build_live_request_id("courses"),
        "generatedAt": datetime.now(JST).isoformat(timespec="seconds"),
        "items": items,
    }


def build_coursework_list_payload(coursework_items: list[CourseWork]) -> dict[str, object]:
    def sort_key(item: CourseWork) -> tuple[int, str, str]:
        due_at = (
            item.due_at.isoformat()
            if item.due_at is not None
            else "9999-12-31T23:59:59+09:00"
        )
        return (0 if item.due_at is not None else 1, due_at, item.title.casefold())

    items = [item.to_contract() for item in sorted(coursework_items, key=sort_key)]
    return {
        "requestId": build_live_request_id("coursework"),
        "generatedAt": datetime.now(JST).isoformat(timespec="seconds"),
        "items": items,
    }


def build_default_reminder_title(course_work: CourseWork) -> str:
    return f"{course_work.title} 提出リマインド"


def build_default_reminder_body(analysis: Any) -> str:
    due_parts = [
        value
        for value in (analysis.course_work.due_date, analysis.course_work.due_time)
        if value
    ]
    due_label = " ".join(due_parts)
    sentences = [f"課題「{analysis.course_work.title}」の提出状況を確認しました。"]
    if due_label:
        sentences.append(
            f"まだ提出していない人は、{due_label} までに提出してください。"
        )
    else:
        sentences.append("まだ提出していない人は、できるだけ早く提出してください。")
    sentences.append("分からない点があれば、早めに相談してください。")
    if analysis.normalization_issues:
        sentences.append("一部データが未取得のため、投稿前に内容を再確認してください。")
    return " ".join(sentences)


def normalize_live_courses(raw_courses: list[dict[str, Any]]) -> list[Course]:
    return [normalize_course(item) for item in raw_courses if isinstance(item, dict)]


def normalize_live_coursework(raw_coursework: list[dict[str, Any]]) -> list[CourseWork]:
    return [
        normalize_coursework(item)
        for item in raw_coursework
        if isinstance(item, dict)
    ]


def resolve_agent_error(exc: Exception, *, fallback_code: str) -> AgentError:
    if isinstance(exc, AgentError):
        return exc

    if isinstance(exc, FileNotFoundError):
        return AgentError(
            ErrorCode.GOOGLE_AUTH_EXPIRED,
            message="OAuth client file が見つかりません。credentials.json を確認してください。",
            detail=str(exc),
        )

    if isinstance(exc, RuntimeError):
        return AgentError(
            ErrorCode.GOOGLE_AUTH_EXPIRED,
            message=str(exc),
            detail=str(exc),
        )

    status = getattr(getattr(exc, "resp", None), "status", None)
    try:
        status_code = int(status)
    except (TypeError, ValueError):
        status_code = None

    mapping = {
        400: ErrorCode.INVALID_AGENT_OUTPUT,
        401: ErrorCode.GOOGLE_AUTH_EXPIRED,
        403: ErrorCode.CLASSROOM_API_PERMISSION_DENIED,
        404: ErrorCode.CLASSROOM_API_NOT_FOUND,
        429: ErrorCode.CLASSROOM_API_RATE_LIMITED,
    }
    return AgentError(mapping.get(status_code, fallback_code), detail=str(exc))


def validate_or_rebuild_contract(
    payload: dict[str, Any],
    *,
    request_id: str,
    agent_task_type: AgentTaskType,
    course: Course | None = None,
) -> dict[str, Any]:
    validation_errors = validate_agent_output(payload)
    if not validation_errors:
        return payload

    return build_error_response(
        request_id,
        agent_task_type,
        title="AIアウトプットJSONの検証に失敗しました",
        short_summary="内部で生成したレスポンスが契約に一致しませんでした。",
        recommended_action="JSON契約とレスポンス生成処理を確認してください。",
        error_code=ErrorCode.INVALID_AGENT_OUTPUT,
        error_message=" / ".join(validation_errors),
        recoverable=False,
        course=course,
    )


def build_contract_error_payload(
    *,
    request_id: str,
    agent_task_type: AgentTaskType,
    error: AgentError,
    title: str,
    short_summary: str,
    recommended_action: str,
    course: Course | None = None,
) -> dict[str, Any]:
    return build_error_response(
        request_id,
        agent_task_type,
        title=title,
        short_summary=short_summary,
        recommended_action=recommended_action,
        error_code=error.code,
        error_message=error.message,
        recoverable=error.recoverable,
        course=course,
    )


class ClassroomPrototypeHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, directory=str(PUBLIC_DIR), **kwargs)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/live/courses":
            self._handle_courses()
            return
        if parsed.path == "/api/live/coursework":
            self._handle_coursework(parsed)
            return
        if parsed.path == "/api/live/submission-analysis":
            self._handle_submission_analysis(parsed)
            return
        if parsed.path == "/api/live/reminder-generation":
            self._handle_reminder_generation(parsed)
            return
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/live/post-reminder":
            self._handle_post_reminder()
            return
        self.send_error(404, "Not Found")

    def _handle_courses(self) -> None:
        request_id = build_live_request_id("courses")
        try:
            client = GoogleClassroomClient.from_oauth()
            payload = build_course_list_payload(
                normalize_live_courses(client.list_courses(course_states=["ACTIVE"]))
            )
            payload["requestId"] = request_id
            self._send_json(200, payload)
        except Exception as exc:
            error = resolve_agent_error(
                exc,
                fallback_code=ErrorCode.CLASSROOM_API_PERMISSION_DENIED,
            )
            self._send_json(
                500,
                {
                    "requestId": request_id,
                    "generatedAt": datetime.now(JST).isoformat(timespec="seconds"),
                    "items": [],
                    "error": error.to_error_item(),
                },
            )

    def _handle_coursework(self, parsed: Any) -> None:
        request_id = build_live_request_id("coursework")
        course_id = self._require_query_value(parsed, "courseId")
        if course_id is None:
            return

        try:
            client = GoogleClassroomClient.from_oauth()
            payload = build_coursework_list_payload(
                normalize_live_coursework(
                    client.list_coursework(
                        course_id,
                        course_work_states=["PUBLISHED"],
                    )
                )
            )
            payload["requestId"] = request_id
            self._send_json(200, payload)
        except Exception as exc:
            error = resolve_agent_error(
                exc,
                fallback_code=ErrorCode.CLASSROOM_API_PERMISSION_DENIED,
            )
            self._send_json(
                500,
                {
                    "requestId": request_id,
                    "generatedAt": datetime.now(JST).isoformat(timespec="seconds"),
                    "items": [],
                    "error": error.to_error_item(),
                },
            )

    def _handle_submission_analysis(self, parsed: Any) -> None:
        request_id = build_live_request_id("submission_analysis")
        course_id = self._require_query_value(parsed, "courseId")
        course_work_id = self._require_query_value(parsed, "courseWorkId")
        if course_id is None or course_work_id is None:
            return

        try:
            client = GoogleClassroomClient.from_oauth()
            analysis = fetch_submission_analysis(
                client,
                course_id=course_id,
                course_work_id=course_work_id,
            )
            payload = validate_or_rebuild_contract(
                build_submission_analysis_response(request_id, analysis),
                request_id=request_id,
                agent_task_type=AgentTaskType.SUBMISSION_ANALYSIS,
                course=analysis.course,
            )
            self._send_json(200, payload)
        except Exception as exc:
            error = resolve_agent_error(
                exc,
                fallback_code=ErrorCode.CLASSROOM_API_PERMISSION_DENIED,
            )
            payload = build_contract_error_payload(
                request_id=request_id,
                agent_task_type=AgentTaskType.SUBMISSION_ANALYSIS,
                error=error,
                title="提出状況の取得に失敗しました",
                short_summary="Google Classroom から提出状況を取得できませんでした。",
                recommended_action="Google OAuth 設定とClassroom権限を確認して再試行してください。",
            )
            self._send_json(200, payload)

    def _handle_reminder_generation(self, parsed: Any) -> None:
        request_id = build_live_request_id("reminder_generation")
        course_id = self._require_query_value(parsed, "courseId")
        course_work_id = self._require_query_value(parsed, "courseWorkId")
        if course_id is None or course_work_id is None:
            return

        try:
            client = GoogleClassroomClient.from_oauth()
            analysis = fetch_submission_analysis(
                client,
                course_id=course_id,
                course_work_id=course_work_id,
            )
            payload = validate_or_rebuild_contract(
                build_reminder_generation_response(
                    request_id,
                    analysis,
                    reminder_title=build_default_reminder_title(analysis.course_work),
                    reminder_body=build_default_reminder_body(analysis),
                ),
                request_id=request_id,
                agent_task_type=AgentTaskType.REMINDER_GENERATION,
                course=analysis.course,
            )
            self._send_json(200, payload)
        except Exception as exc:
            error = resolve_agent_error(
                exc,
                fallback_code=ErrorCode.CLASSROOM_API_PERMISSION_DENIED,
            )
            payload = build_contract_error_payload(
                request_id=request_id,
                agent_task_type=AgentTaskType.REMINDER_GENERATION,
                error=error,
                title="リマインド生成に失敗しました",
                short_summary=(
                    "Google Classroom の事実データを取得できなかったため、"
                    "リマインド案を生成できませんでした。"
                ),
                recommended_action="Google OAuth 設定と対象課題の権限を確認して再試行してください。",
            )
            self._send_json(200, payload)

    def _handle_post_reminder(self) -> None:
        request_id = build_live_request_id("post_reminder")
        try:
            body = self._read_json_body()
            approved = bool(body.get("approved"))
            reminder_output = body.get("classroomReminder")
            if not approved:
                raise AgentError(
                    ErrorCode.CLASSROOM_POST_FAILED,
                    message="教師承認フラグがないため、Classroom 投稿を実行しませんでした。",
                    recoverable=True,
                )
            if not isinstance(reminder_output, dict):
                raise AgentError(
                    ErrorCode.INVALID_AGENT_OUTPUT,
                    message="classroomReminder payload が不正です。",
                    recoverable=False,
                )

            client = build_post_only_client()
            announcement = client.create_announcement_from_output(reminder_output)
            self._send_json(
                200,
                {
                    "requestId": request_id,
                    "generatedAt": datetime.now(JST).isoformat(timespec="seconds"),
                    "status": "success",
                    "announcementId": announcement.get("id"),
                    "alternateLink": announcement.get("alternateLink"),
                },
            )
        except Exception as exc:
            error = resolve_agent_error(exc, fallback_code=ErrorCode.CLASSROOM_POST_FAILED)
            self._send_json(
                500,
                {
                    "requestId": request_id,
                    "generatedAt": datetime.now(JST).isoformat(timespec="seconds"),
                    "status": "error",
                    "error": error.to_error_item(),
                },
            )

    def _require_query_value(self, parsed: Any, key: str) -> str | None:
        values = parse_qs(parsed.query).get(key, [])
        for value in values:
            stripped = value.strip()
            if stripped:
                return stripped

        self._send_json(
            400,
            {
                "requestId": build_live_request_id("request_error"),
                "generatedAt": datetime.now(JST).isoformat(timespec="seconds"),
                "status": "error",
                "error": {
                    "code": ErrorCode.INVALID_AGENT_OUTPUT,
                    "message": f"Query parameter `{key}` is required.",
                    "recoverable": False,
                },
            },
        )
        return None

    def _read_json_body(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length") or "0")
        if content_length <= 0:
            return {}
        raw_body = self.rfile.read(content_length)
        if not raw_body:
            return {}
        payload = json.loads(raw_body.decode("utf-8"))
        if not isinstance(payload, dict):
            raise AgentError(
                ErrorCode.INVALID_AGENT_OUTPUT,
                message="JSON body must be an object.",
                recoverable=False,
            )
        return payload

    def _send_json(self, status_code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def serve_gui(host: str, port: int) -> None:
    with ReusableTCPServer((host, port), ClassroomPrototypeHandler) as server:
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
