from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .contracts import ALLOWED_AGENT_TASK_TYPES, ALLOWED_STATUSES, SCHEMA_VERSION


@dataclass(frozen=True, slots=True)
class Course:
    course_id: str
    name: str
    section: str
    description: str = ""
    state: str = "ACTIVE"
    teacher_ids: list[str] = field(default_factory=list)
    student_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "courseId": self.course_id,
            "name": self.name,
            "section": self.section,
            "description": self.description,
            "state": self.state,
            "teacherIds": self.teacher_ids,
            "studentCount": self.student_count,
        }


@dataclass(frozen=True, slots=True)
class CourseWork:
    course_work_id: str
    course_id: str
    title: str
    description: str = ""
    work_type: str = "ASSIGNMENT"
    max_points: int | None = None
    due_date: str | None = None
    due_time: str | None = None
    state: str = "PUBLISHED"
    materials: list[dict[str, Any]] = field(default_factory=list)
    topic_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "courseWorkId": self.course_work_id,
            "courseId": self.course_id,
            "title": self.title,
            "description": self.description,
            "workType": self.work_type,
            "maxPoints": self.max_points,
            "dueDate": self.due_date,
            "dueTime": self.due_time,
            "state": self.state,
            "materials": self.materials,
            "topicId": self.topic_id,
        }


@dataclass(frozen=True, slots=True)
class StudentSubmission:
    student_submission_id: str
    course_id: str
    course_work_id: str
    student_id: str
    student_name: str
    state: str
    late: bool
    assigned_grade: float | None = None
    draft_grade: float | None = None
    attachments: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "studentSubmissionId": self.student_submission_id,
            "courseId": self.course_id,
            "courseWorkId": self.course_work_id,
            "studentId": self.student_id,
            "studentName": self.student_name,
            "state": self.state,
            "late": self.late,
            "assignedGrade": self.assigned_grade,
            "draftGrade": self.draft_grade,
            "attachments": self.attachments,
        }


@dataclass(frozen=True, slots=True)
class AgentOutput:
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return self.payload


def build_agent_output(
    agent_task_type: str,
    *,
    request_id: str,
    course: Course,
    coursework: CourseWork | None = None,
    submissions: list[StudentSubmission] | None = None,
    tone: str = "polite",
    teacher_instruction: str = "",
    extra_notes: str = "",
) -> AgentOutput:
    if agent_task_type not in ALLOWED_AGENT_TASK_TYPES:
        raise ValueError(f"unsupported agent task type: {agent_task_type}")

    submissions = submissions or []
    missing_submissions = [
        submission for submission in submissions if submission.state != "TURNED_IN"
    ]
    title = _title_for_task(agent_task_type)
    coursework_title = coursework.title if coursework else "対象課題"
    short_summary = _short_summary(agent_task_type, course, coursework, missing_submissions)
    reminder_text = _reminder_text(coursework_title, coursework, tone, teacher_instruction)

    payload: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "requestId": request_id,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "agentTaskType": agent_task_type,
        "status": "success",
        "course": {
            "courseId": course.course_id,
            "name": course.name,
            "section": course.section,
        },
        "summary": {
            "title": title,
            "shortSummary": short_summary,
            "teacherActionRequired": agent_task_type in _APPROVAL_TASK_TYPES,
            "recommendedAction": "内容を確認し、必要に応じて編集してください。",
        },
        "gui": {
            "cards": _build_cards(coursework, submissions, missing_submissions),
            "tables": _build_tables(coursework, submissions),
            "warnings": [
                {
                    "level": "medium",
                    "message": "生徒向け投稿には、他の生徒の提出状況や氏名を含めないでください。",
                }
            ],
            "editableFields": [
                {
                    "fieldId": "reminder_title",
                    "label": "投稿タイトル",
                    "type": "text",
                    "value": "課題提出リマインド",
                    "required": True,
                },
                {
                    "fieldId": "reminder_body",
                    "label": "リマインド本文",
                    "type": "textarea",
                    "value": reminder_text,
                    "required": True,
                },
            ],
        },
        "outputs": {
            "markdown": _build_markdown(course, coursework, short_summary, extra_notes),
            "pdf": _build_pdf(course, coursework, short_summary),
            "googleDocument": None,
            "classroomReminder": _build_classroom_reminder(
                course, coursework, reminder_text
            ),
        },
        "approval": {
            "required": agent_task_type in _APPROVAL_TASK_TYPES,
            "reason": "Classroomへの投稿を行うため、教師の承認が必要です。",
            "actions": [
                {
                    "actionId": "action_001",
                    "type": "CREATE_CLASSROOM_ANNOUNCEMENT",
                    "label": "Classroomにリマインドを投稿",
                    "requiresConfirmation": True,
                    "payloadRef": "outputs.classroomReminder",
                }
            ],
        },
        "errors": [],
    }
    return AgentOutput(payload)


def validate_agent_output_dict(payload: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if payload.get("schemaVersion") != SCHEMA_VERSION:
        issues.append("schemaVersion must be 1.0.0")
    if payload.get("agentTaskType") not in ALLOWED_AGENT_TASK_TYPES:
        issues.append("agentTaskType is not allowed")
    if payload.get("status") not in ALLOWED_STATUSES:
        issues.append("status is not allowed")
    summary = payload.get("summary")
    if isinstance(summary, dict):
        for key in (
            "title",
            "shortSummary",
            "teacherActionRequired",
            "recommendedAction",
        ):
            if key not in summary:
                issues.append(f"summary missing key: {key}")
    elif summary is not None:
        issues.append("summary must be an object")
    return issues


_APPROVAL_TASK_TYPES = {"REMINDER_GENERATION", "ANNOUNCEMENT_DRAFT"}


def _title_for_task(agent_task_type: str) -> str:
    titles = {
        "COURSE_SUMMARY": "コース概要",
        "COURSEWORK_SUMMARY": "課題概要",
        "SUBMISSION_ANALYSIS": "提出状況分析",
        "REMINDER_GENERATION": "未提出課題リマインド案",
        "WEEKLY_REPORT": "週次レポート",
        "ANNOUNCEMENT_DRAFT": "お知らせ文案",
        "DOCUMENT_EXPORT": "出力用ドキュメント",
        "RUBRIC_SUPPORT": "ルーブリック補助",
        "ERROR_ANALYSIS": "エラー分析",
    }
    return titles[agent_task_type]


def _short_summary(
    agent_task_type: str,
    course: Course,
    coursework: CourseWork | None,
    missing_submissions: list[StudentSubmission],
) -> str:
    if coursework:
        return (
            f"{course.name}の課題「{coursework.title}」に"
            f"未提出または確認が必要な提出物が{len(missing_submissions)}件あります。"
        )
    return f"{course.name}の{_title_for_task(agent_task_type)}を作成しました。"


def _reminder_text(
    coursework_title: str,
    coursework: CourseWork | None,
    tone: str,
    teacher_instruction: str,
) -> str:
    due = ""
    if coursework and coursework.due_date:
        due = f"{coursework.due_date}"
        if coursework.due_time:
            due = f"{due} {coursework.due_time}"
    suffix = "分からないところがある場合は、早めに相談してください。"
    if teacher_instruction:
        suffix = f"{suffix} {teacher_instruction}"
    if tone == "strict":
        return f"課題「{coursework_title}」を期限{due}までに必ず提出してください。"
    return f"課題「{coursework_title}」の提出期限が近づいています。{due}までに提出してください。{suffix}"


def _build_cards(
    coursework: CourseWork | None,
    submissions: list[StudentSubmission],
    missing_submissions: list[StudentSubmission],
) -> list[dict[str, Any]]:
    return [
        {
            "cardId": "card_missing",
            "type": "metric",
            "title": "未提出者数",
            "value": str(len(missing_submissions)),
            "description": "提出状況から抽出した未提出または確認が必要な件数です。",
        },
        {
            "cardId": "card_total",
            "type": "metric",
            "title": "提出物数",
            "value": str(len(submissions)),
            "description": "取得済みの提出物数です。",
        },
        {
            "cardId": "card_due",
            "type": "metric",
            "title": "締切",
            "value": coursework.due_date if coursework and coursework.due_date else "未設定",
            "description": "対象課題の締切日です。",
        },
    ]


def _build_tables(
    coursework: CourseWork | None,
    submissions: list[StudentSubmission],
) -> list[dict[str, Any]]:
    return [
        {
            "tableId": "table_submissions",
            "title": "提出状況一覧",
            "columns": [
                {"key": "studentName", "label": "生徒名"},
                {"key": "status", "label": "状態"},
                {"key": "dueDate", "label": "締切"},
            ],
            "rows": [
                {
                    "studentName": submission.student_name,
                    "status": submission.state,
                    "dueDate": coursework.due_date if coursework else "",
                }
                for submission in submissions
            ],
        }
    ]


def _build_markdown(
    course: Course,
    coursework: CourseWork | None,
    short_summary: str,
    extra_notes: str,
) -> dict[str, str]:
    title = f"{course.name} 提出状況レポート"
    target = coursework.title if coursework else "コース全体"
    return {
        "fileName": "classroom_report.md",
        "title": title,
        "content": (
            f"# {title}\n\n"
            f"## 概要\n{short_summary}\n\n"
            f"## 対象\n{target}\n\n"
            f"## 注意事項\n{extra_notes or '教師が内容を確認してから利用してください。'}"
        ),
    }


def _build_pdf(
    course: Course,
    coursework: CourseWork | None,
    short_summary: str,
) -> dict[str, Any]:
    return {
        "fileName": "classroom_report.pdf",
        "title": f"{course.name} 提出状況レポート",
        "layout": "report",
        "sections": [
            {"heading": "概要", "body": short_summary},
            {"heading": "対象課題", "body": coursework.title if coursework else "未指定"},
        ],
    }


def _build_classroom_reminder(
    course: Course,
    coursework: CourseWork | None,
    reminder_text: str,
) -> dict[str, Any]:
    return {
        "target": {
            "courseId": course.course_id,
            "courseWorkId": coursework.course_work_id if coursework else None,
        },
        "postType": "announcement",
        "title": "課題提出リマインド",
        "text": reminder_text,
        "materials": [],
        "scheduledTime": None,
        "assigneeMode": "ALL_STUDENTS",
        "targetStudentIds": [],
        "requiresTeacherApproval": True,
    }
