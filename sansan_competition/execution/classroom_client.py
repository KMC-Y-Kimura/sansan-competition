"""Google Classroom APIクライアント (REQUIREMENTS 8.1-8.3, 8.10, 11.1)。

読み取り(コース/課題/提出状況)は**生データ**を返し、kimuの normalize_* が
正規化する (ROLE 4.2: mocky取得 → kimu正規化)。お知らせ投稿も提供する。

MVPはモック。実APIは同じ ClassroomClient インターフェースで差し替える。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from . import sample_data
from .errors import AgentError, ErrorCode
from .google_auth import AuthProvider, Scopes


@runtime_checkable
class ClassroomClient(Protocol):
    def list_courses(self) -> list[dict]: ...
    def list_course_work(self, course_id: str) -> list[dict]: ...
    def list_submissions(self, course_id: str, course_work_id: str) -> list[dict]: ...
    def create_announcement(
        self,
        course_id: str,
        text: str,
        *,
        materials: list | None = None,
        assignee_mode: str = "ALL_STUDENTS",
        student_ids: list[str] | None = None,
    ) -> dict: ...


class MockClassroomClient:
    """サンプル生データを返すモック。認証スコープも検査する。

    fail_with に ErrorCode を渡すと、読み取りAPIで例外を再現できる。
    """

    def __init__(self, auth: AuthProvider, *, fail_with: str | None = None) -> None:
        self._auth = auth
        self._fail_with = fail_with
        self._announcement_seq = 0

    def _maybe_fail(self) -> None:
        if self._fail_with:
            raise AgentError(self._fail_with)

    def list_courses(self) -> list[dict]:
        self._auth.require_scope(Scopes.COURSES_READONLY)
        self._maybe_fail()
        return [dict(c) for c in sample_data.COURSES]

    def list_course_work(self, course_id: str) -> list[dict]:
        self._auth.require_scope(Scopes.COURSEWORK_READONLY)
        self._maybe_fail()
        works = sample_data.COURSEWORK.get(course_id)
        if works is None:
            raise AgentError(
                ErrorCode.CLASSROOM_API_NOT_FOUND, detail=f"course {course_id}"
            )
        return [dict(w) for w in works]

    def list_submissions(self, course_id: str, course_work_id: str) -> list[dict]:
        self._auth.require_scope(Scopes.SUBMISSIONS_READONLY)
        self._maybe_fail()
        subs = sample_data.SUBMISSIONS.get(course_work_id)
        if subs is None:
            raise AgentError(
                ErrorCode.CLASSROOM_API_NOT_FOUND,
                detail=f"coursework {course_work_id}",
            )
        return [dict(s) for s in subs if s["courseId"] == course_id]

    def create_announcement(
        self,
        course_id: str,
        text: str,
        *,
        materials: list | None = None,
        assignee_mode: str = "ALL_STUDENTS",
        student_ids: list[str] | None = None,
    ) -> dict:
        # 書き込みスコープが必須 (READと分離)
        self._auth.require_scope(Scopes.ANNOUNCEMENTS)
        if not text.strip():
            raise AgentError(
                ErrorCode.CLASSROOM_POST_FAILED, detail="empty announcement text"
            )
        self._announcement_seq += 1
        ann_id = f"ann_{course_id}_{self._announcement_seq:03d}"
        result = {
            "id": ann_id,
            "courseId": course_id,
            "text": text,
            "materials": materials or [],
            "assigneeMode": assignee_mode,
            "state": "PUBLISHED",
            "alternateLink": f"https://classroom.google.com/c/{course_id}/p/{ann_id}",
        }
        if assignee_mode == "INDIVIDUAL_STUDENTS":
            result["individualStudentsOptions"] = {"studentIds": student_ids or []}
        return result
