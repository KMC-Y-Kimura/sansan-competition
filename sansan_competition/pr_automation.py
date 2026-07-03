from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

ALLOWED_AGENT_TASK_TYPES = {
    "COURSE_SUMMARY",
    "COURSEWORK_SUMMARY",
    "SUBMISSION_ANALYSIS",
    "REMINDER_GENERATION",
    "WEEKLY_REPORT",
    "ANNOUNCEMENT_DRAFT",
    "DOCUMENT_EXPORT",
    "RUBRIC_SUPPORT",
    "ERROR_ANALYSIS",
}

COMMON_TOP_LEVEL_KEYS = {
    "schemaVersion",
    "requestId",
    "generatedAt",
    "agentTaskType",
    "status",
    "course",
    "summary",
    "gui",
    "outputs",
    "approval",
    "errors",
}
COMMON_GUI_KEYS = {"cards", "tables", "warnings", "editableFields"}
COMMON_OUTPUT_KEYS = {"markdown", "pdf", "googleDocument", "classroomReminder"}
COMMON_APPROVAL_KEYS = {"required", "reason", "actions"}
CACHE_DIR_NAME = "__pycache__"
CACHE_SUFFIXES = {".pyc", ".pyo"}
COMMENT_MARKER = "<!-- pr-automation-report -->"


@dataclass(frozen=True, slots=True)
class Course:
    course_id: str
    name: str
    section: str = ""
    description: str = ""
    state: str = ""
    teacher_ids: list[str] | None = None
    student_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "courseId": self.course_id,
            "name": self.name,
            "section": self.section,
            "description": self.description,
            "state": self.state,
            "teacherIds": list(self.teacher_ids or []),
            "studentCount": self.student_count,
        }


@dataclass(frozen=True, slots=True)
class CourseWork:
    course_work_id: str
    course_id: str
    title: str
    description: str = ""
    work_type: str = ""
    max_points: int | float | None = None
    due_date: str = ""
    due_time: str = ""
    state: str = ""
    materials: list[dict[str, Any]] | None = None
    topic_id: str = ""

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
            "materials": list(self.materials or []),
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
    late: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "studentSubmissionId": self.student_submission_id,
            "courseId": self.course_id,
            "courseWorkId": self.course_work_id,
            "studentId": self.student_id,
            "studentName": self.student_name,
            "state": self.state,
            "late": self.late,
        }


@dataclass(frozen=True, slots=True)
class Summary:
    title: str
    short_summary: str
    teacher_action_required: bool
    recommended_action: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "shortSummary": self.short_summary,
            "teacherActionRequired": self.teacher_action_required,
            "recommendedAction": self.recommended_action,
        }


@dataclass(frozen=True, slots=True)
class Approval:
    required: bool
    reason: str
    actions: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "required": self.required,
            "reason": self.reason,
            "actions": list(self.actions),
        }


@dataclass(frozen=True, slots=True)
class AgentError:
    code: str
    message: str
    recoverable: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "recoverable": self.recoverable,
        }


@dataclass(frozen=True, slots=True)
class AgentOutput:
    request_id: str
    generated_at: str
    agent_task_type: str
    status: str
    summary: Summary
    course: Course
    gui: dict[str, Any]
    outputs: dict[str, Any]
    approval: Approval
    errors: list[AgentError]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": "1.0.0",
            "requestId": self.request_id,
            "generatedAt": self.generated_at,
            "agentTaskType": self.agent_task_type,
            "status": self.status,
            "course": self.course.to_dict(),
            "summary": self.summary.to_dict(),
            "gui": self.gui,
            "outputs": self.outputs,
            "approval": self.approval.to_dict(),
            "errors": [error.to_dict() for error in self.errors],
        }


@dataclass(frozen=True, slots=True)
class CheckResult:
    name: str
    passed: bool
    details: list[str]


@dataclass(frozen=True, slots=True)
class AutomationReport:
    fixes_applied: list[str]
    checks: list[CheckResult]

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)

    def to_markdown(self) -> str:
        lines = [
            COMMENT_MARKER,
            "# PR Automation Report",
            "",
            f"- Overall: {'PASS' if self.passed else 'FAIL'}",
        ]
        if self.fixes_applied:
            lines.extend(["- Auto fixes:", *[f"  - {item}" for item in self.fixes_applied]])
        else:
            lines.append("- Auto fixes: none")
        lines.extend(["", "## Checks"])
        for check in self.checks:
            status = "PASS" if check.passed else "FAIL"
            lines.append(f"- {check.name}: {status}")
            for detail in check.details:
                lines.append(f"  - {detail}")
        lines.append("")
        return "\n".join(lines)


def build_sample_context() -> tuple[Course, CourseWork, list[StudentSubmission]]:
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
        course_id="123456789",
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
            course_id="123456789",
            course_work_id="987654321",
            student_id="student_1",
            student_name="山田太郎",
            state="NEW",
            late=False,
        ),
        StudentSubmission(
            student_submission_id="sub_2",
            course_id="123456789",
            course_work_id="987654321",
            student_id="student_2",
            student_name="佐藤花子",
            state="TURNED_IN",
            late=False,
        ),
    ]
    return course, coursework, submissions


def build_agent_output(
    task_type: str,
    *,
    request_id: str,
    course: Course,
    coursework: CourseWork | None = None,
    submissions: Sequence[StudentSubmission] | None = None,
    tone: str = "polite",
    teacher_instruction: str = "",
    extra_notes: str = "",
    **kwargs: Any,
) -> AgentOutput:
    summary = Summary(
        title=f"{task_type} summary",
        short_summary=f"Generated output for {task_type}.",
        teacher_action_required=task_type != "COURSE_SUMMARY",
        recommended_action="Review and proceed.",
    )
    gui = {"cards": [], "tables": [], "warnings": [], "editableFields": []}
    outputs = {
        "markdown": None,
        "pdf": None,
        "googleDocument": None,
        "classroomReminder": None,
    }
    approval = Approval(required=False, reason="No approval required for this generated sample.", actions=[])
    errors: list[AgentError] = []

    if task_type == "REMINDER_GENERATION":
        outputs["classroomReminder"] = {
            "target": {"courseId": course.course_id},
            "postType": "announcement",
            "title": "課題提出リマインド",
            "text": "提出をお願いします。",
            "materials": [],
            "scheduledTime": None,
            "assigneeMode": "ALL_STUDENTS",
            "targetStudentIds": [],
            "requiresTeacherApproval": True,
        }
        approval = Approval(
            required=True,
            reason="Classroomへの投稿を行うため、教師の承認が必要です。",
            actions=[
                {
                    "actionId": "action_create_announcement",
                    "type": "CREATE_CLASSROOM_ANNOUNCEMENT",
                    "label": "Classroomにリマインドを投稿",
                    "requiresConfirmation": True,
                    "payloadRef": "outputs.classroomReminder",
                }
            ],
        )
    elif task_type == "COURSE_SUMMARY":
        outputs.update(
            {
                "markdown": {"content": "summary"},
                "pdf": {"content": "summary"},
                "googleDocument": {"content": "summary"},
            }
        )
    elif task_type == "ERROR_ANALYSIS":
        errors = [
            AgentError(
                code=str(kwargs.get("error_code", "AI_GENERATION_FAILED")),
                message=str(kwargs.get("error_message", "AI output could not be generated.")),
                recoverable=bool(kwargs.get("recoverable", True)),
            )
        ]
        return AgentOutput(
            request_id=request_id,
            generated_at="2026-07-03T13:00:00+09:00",
            agent_task_type=task_type,
            status="error",
            course=course,
            summary=summary,
            gui=gui,
            outputs=outputs,
            approval=approval,
            errors=errors,
        )

    return AgentOutput(
        request_id=request_id,
        generated_at="2026-07-03T13:00:00+09:00",
        agent_task_type=task_type,
        status="success",
        course=course,
        summary=summary,
        gui=gui,
        outputs=outputs,
        approval=approval,
        errors=errors,
    )


def validate_agent_output_dict(payload: dict[str, Any]) -> list[str]:
    missing = COMMON_TOP_LEVEL_KEYS - payload.keys()
    errors: list[str] = []
    if missing:
        errors.append("missing required top-level keys: " + ", ".join(sorted(missing)))
        return errors
    if payload.get("schemaVersion") != "1.0.0":
        errors.append("unsupported schemaVersion")
    if payload.get("agentTaskType") not in ALLOWED_AGENT_TASK_TYPES:
        errors.append("unsupported agentTaskType")
    if payload.get("status") not in {"success", "error"}:
        errors.append("unsupported status")
    if not isinstance(payload.get("course"), dict):
        errors.append("course must be an object")
    if not isinstance(payload.get("gui"), dict):
        errors.append("gui must be an object")
    if not isinstance(payload.get("outputs"), dict):
        errors.append("outputs must be an object")
    if not isinstance(payload.get("approval"), dict):
        errors.append("approval must be an object")
    if not isinstance(payload.get("errors"), list):
        errors.append("errors must be an array")
    elif payload.get("status") == "error" and not payload["errors"]:
        errors.append("errors must be non-empty when status is error")
    return errors


def collect_cache_artifacts(repo_root: Path) -> list[Path]:
    artifacts: list[Path] = []
    for path in repo_root.rglob("*"):
        if ".git" in path.parts:
            continue
        if path.name == CACHE_DIR_NAME and path.is_dir():
            artifacts.append(path)
            continue
        if path.is_file() and path.suffix in {".pyc", ".pyo"}:
            artifacts.append(path)
    return sorted(artifacts)


def remove_cache_artifacts(paths: Sequence[Path]) -> list[str]:
    removed: list[str] = []
    for path in paths:
        if not path.exists():
            continue
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        removed.append(str(path))
    return removed


def run_command(args: Sequence[str], *, repo_root: Path) -> tuple[int, str]:
    completed = subprocess.run(
        list(args),
        cwd=repo_root,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        check=False,
    )
    output = completed.stdout.strip()
    if completed.stderr.strip():
        output = f"{output}\n{completed.stderr.strip()}".strip()
    return completed.returncode, output


def run_pytest(repo_root: Path) -> CheckResult:
    returncode, output = run_command([sys.executable, "-m", "pytest", "-q"], repo_root=repo_root)
    if returncode != 0 and "No module named pytest" in output:
        returncode, output = run_command(["pytest", "-q"], repo_root=repo_root)
    return CheckResult(name="pytest", passed=returncode == 0, details=[output or "pytest completed without output"])


def run_cli_contract_checks(repo_root: Path) -> CheckResult:
    details: list[str] = []
    passed = True
    for command in (
        ["scripts/review_implementation_agent.py", "--help"],
        ["scripts/pr_automation.py", "--help"],
    ):
        returncode, output = run_command([sys.executable, *command], repo_root=repo_root)
        command_name = " ".join(command)
        if returncode != 0:
            passed = False
            details.append(f"{command_name}: command failed")
            if output:
                details.append(output)
            continue
        if "usage:" not in output.lower():
            passed = False
            details.append(f"{command_name}: help output missing usage text")
        else:
            details.append(f"{command_name}: help output valid")
    return CheckResult(name="cli-contract", passed=passed, details=details)


def validate_common_contract(payload: dict[str, Any]) -> list[str]:
    issues = validate_agent_output_dict(payload)
    missing_top_level = COMMON_TOP_LEVEL_KEYS - payload.keys()
    if missing_top_level:
        issues.append("missing common top-level keys: " + ", ".join(sorted(missing_top_level)))
    course = payload.get("course")
    if not isinstance(course, dict):
        issues.append("course must be an object")
    gui = payload.get("gui")
    if not isinstance(gui, dict):
        issues.append("gui must be an object")
    elif COMMON_GUI_KEYS - gui.keys():
        issues.append("gui missing keys: " + ", ".join(sorted(COMMON_GUI_KEYS - gui.keys())))
    outputs = payload.get("outputs")
    if not isinstance(outputs, dict):
        issues.append("outputs must be an object")
    elif COMMON_OUTPUT_KEYS - outputs.keys():
        issues.append("outputs missing keys: " + ", ".join(sorted(COMMON_OUTPUT_KEYS - outputs.keys())))
    approval = payload.get("approval")
    if not isinstance(approval, dict):
        issues.append("approval must be an object")
    elif COMMON_APPROVAL_KEYS - approval.keys():
        issues.append("approval missing keys: " + ", ".join(sorted(COMMON_APPROVAL_KEYS - approval.keys())))
    errors = payload.get("errors")
    if not isinstance(errors, list):
        issues.append("errors must be an array")
    return issues


def run_agent_task_contract_checks() -> CheckResult:
    course, coursework, submissions = build_sample_context()
    details: list[str] = []
    passed = True
    for task_type in sorted(ALLOWED_AGENT_TASK_TYPES):
        payload = build_agent_output(
            task_type,
            request_id=f"req_{task_type.lower()}",
            course=course,
            coursework=coursework,
            submissions=submissions,
            tone="polite",
            teacher_instruction="必要があれば補足してください。",
            extra_notes="自動レビュー用のサンプルです。",
        ).to_dict()
        issues = validate_common_contract(payload)
        if issues:
            passed = False
            details.append(f"{task_type}: " + "; ".join(issues))
        else:
            details.append(f"{task_type}: contract valid")
    return CheckResult(name="agent-contract", passed=passed, details=details)


def run_repo_hygiene_check(repo_root: Path) -> CheckResult:
    artifacts = collect_cache_artifacts(repo_root)
    if not artifacts:
        return CheckResult(name="repo-hygiene", passed=True, details=["no cache artifacts detected"])
    return CheckResult(
        name="repo-hygiene",
        passed=False,
        details=[f"remove cache artifact: {path}" for path in artifacts],
    )


def build_report(repo_root: Path, *, apply_fixes: bool) -> AutomationReport:
    fixes_applied: list[str] = []
    if apply_fixes:
        cache_artifacts = collect_cache_artifacts(repo_root)
        removed = remove_cache_artifacts(cache_artifacts)
        fixes_applied.extend(f"removed {path}" for path in removed)
    checks = [
        run_repo_hygiene_check(repo_root),
        run_pytest(repo_root),
        run_cli_contract_checks(repo_root),
        run_agent_task_contract_checks(),
    ]
    return AutomationReport(fixes_applied=fixes_applied, checks=checks)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="pr-automation")
    parser.add_argument("--apply-fixes", action="store_true")
    parser.add_argument("--report-path", default="")
    parser.add_argument("--repo-root", default=".")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    report = build_report(repo_root, apply_fixes=args.apply_fixes)
    markdown = report.to_markdown()
    if args.report_path:
        report_path = Path(args.report_path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(markdown, encoding="utf-8")
    print(markdown)
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
