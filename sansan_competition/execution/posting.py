"""教師承認フロー・Classroom投稿・承認済みアクション実行
(REQUIREMENTS 8.10, 10.8, 10.9, 12.3, 15.7, 23章)。

安全性の核心: 教師が明示的に承認(approved_action_ids)したアクションのみ実行する。
特にClassroom投稿は、承認セットに無ければ絶対に実行しない。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .classroom_client import ClassroomClient
from .errors import AgentError, ErrorCode
from .renderers import (
    GoogleDocsClient,
    render_google_document,
    render_markdown,
    render_pdf,
)


class ActionType:
    CREATE_CLASSROOM_ANNOUNCEMENT = "CREATE_CLASSROOM_ANNOUNCEMENT"
    EXPORT_MARKDOWN = "EXPORT_MARKDOWN"
    EXPORT_PDF = "EXPORT_PDF"
    EXPORT_GOOGLE_DOCUMENT = "EXPORT_GOOGLE_DOCUMENT"


def _resolve_payload(agent_output: dict, ref: str | None) -> Any:
    """"outputs.classroomReminder" のような参照をたどって値を返す。"""
    if not ref:
        return None
    node: Any = agent_output
    for key in ref.split("."):
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    return node


# ------------------------------------------------------------ Classroom投稿


def post_classroom_reminder(payload: dict | None, client: ClassroomClient) -> dict:
    """classroomReminderペイロードをClassroomへ投稿し、結果メタを返す。

    承認ゲート(OutputExecutor)経由でのみ呼ばれる前提。
    """
    if not isinstance(payload, dict):
        raise AgentError(
            ErrorCode.CLASSROOM_POST_FAILED, detail="classroomReminder payload missing"
        )
    target = payload.get("target") or {}
    course_id = target.get("courseId")
    if not course_id:
        raise AgentError(
            ErrorCode.CLASSROOM_POST_FAILED, detail="target.courseId missing"
        )
    post_type = payload.get("postType", "announcement")
    if post_type != "announcement":
        # MVPはannouncementのみ対応 (10.8)
        raise AgentError(
            ErrorCode.CLASSROOM_POST_FAILED,
            detail=f"unsupported postType: {post_type}",
        )
    result = client.create_announcement(
        course_id,
        payload.get("text", ""),
        materials=payload.get("materials", []),
        assignee_mode=payload.get("assigneeMode", "ALL_STUDENTS"),
        student_ids=payload.get("targetStudentIds", []),
    )
    return {
        "format": "classroomReminder",
        "postType": post_type,
        "courseId": course_id,
        "announcementId": result.get("id"),
        "url": result.get("alternateLink"),
    }


# ---------------------------------------------------------- 投稿確認画面(15.7)


def build_post_preview(payload: dict | None) -> dict:
    """教師が「投稿する」を押す前に確認する項目を組み立てる (12.3, 15.7)。"""
    payload = payload or {}
    target = payload.get("target") or {}
    assignee_mode = payload.get("assigneeMode", "ALL_STUDENTS")
    target_students = payload.get("targetStudentIds") or []
    warnings: list[str] = []
    if assignee_mode == "ALL_STUDENTS":
        audience = "コース全員"
    else:
        audience = f"指定生徒 {len(target_students)}名"
    # 生徒向け投稿に個人名を含めない (12.2)
    if any(kw in payload.get("text", "") for kw in ("さん", "君", "氏")):
        warnings.append(
            "本文に個人名が含まれる可能性があります。生徒向け投稿では個人名を避けてください。"
        )
    return {
        "courseId": target.get("courseId"),
        "courseWorkId": target.get("courseWorkId"),
        "postType": payload.get("postType", "announcement"),
        "title": payload.get("title", ""),
        "text": payload.get("text", ""),
        "audience": audience,
        "scheduledTime": payload.get("scheduledTime"),
        "warnings": warnings,
    }


# ------------------------------------------------------- 承認済みアクション実行


@dataclass
class ExecutionResult:
    actionId: str
    type: str
    status: str  # "success" | "skipped" | "error"
    detail: dict | None = None
    error: dict | None = None


@dataclass
class OutputExecutor:
    """承認済みアクションを対応する出力/投稿処理へ振り分けて実行する。

    agent_output は kimu の build_*_response が返す辞書 (schemaVersion 1.0.0)。
    """

    classroom: ClassroomClient
    docs: GoogleDocsClient
    out_dir: str | Path = "output"

    def execute(
        self,
        agent_output: dict,
        approved_action_ids: set[str],
    ) -> list[ExecutionResult]:
        actions = (agent_output.get("approval") or {}).get("actions") or []
        results: list[ExecutionResult] = []
        for action in actions:
            action_id = action.get("actionId", "")
            action_type = action.get("type", "")
            if action_id not in approved_action_ids:
                # 未承認は実行しない (投稿・出力ともに教師承認が前提)
                results.append(ExecutionResult(action_id, action_type, "skipped"))
                continue
            results.append(self._run(action, agent_output))
        return results

    def _run(self, action: dict, agent_output: dict) -> ExecutionResult:
        action_id = action.get("actionId", "")
        action_type = action.get("type", "")
        payload = _resolve_payload(agent_output, action.get("payloadRef"))
        try:
            detail = self._dispatch(action_type, payload)
            return ExecutionResult(action_id, action_type, "success", detail)
        except AgentError as exc:
            return ExecutionResult(
                action_id, action_type, "error", error=exc.to_error_item()
            )

    def _dispatch(self, action_type: str, payload) -> dict:
        if action_type == ActionType.EXPORT_MARKDOWN:
            return render_markdown(payload, self.out_dir)
        if action_type == ActionType.EXPORT_PDF:
            return render_pdf(payload, self.out_dir)
        if action_type == ActionType.EXPORT_GOOGLE_DOCUMENT:
            return render_google_document(payload, self.docs)
        if action_type == ActionType.CREATE_CLASSROOM_ANNOUNCEMENT:
            return post_classroom_reminder(payload, self.classroom)
        raise AgentError(
            ErrorCode.INVALID_AGENT_OUTPUT,
            detail=f"unknown action type: {action_type}",
        )
