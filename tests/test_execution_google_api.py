"""実Google API実装のオフラインテスト。

実サービスは unittest.mock で差し替え、ネットワーク無しで
生データ整形・エラーマッピング・Docsリクエスト生成を検証する。
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from sansan_competition.execution.errors import AgentError, ErrorCode
from sansan_competition.execution.google_auth import (
    Credentials,
    READ_SCOPES,
    WRITE_SCOPES,
    Scopes,
)
from sansan_competition.execution.google_api import (
    GoogleAuthProvider,
    GoogleClassroomClient,
    GoogleDocsClient,
    _blocks_to_docs_requests,
    _map_http_error,
)


class _FakeResp:
    def __init__(self, status: int) -> None:
        self.status = status


class _FakeHttpError(Exception):
    def __init__(self, status: int) -> None:
        super().__init__(f"http {status}")
        self.resp = _FakeResp(status)


def _authed() -> GoogleAuthProvider:
    """google_credentials不要(サービスを直接差し替える)ため creds だけ用意。"""
    auth = GoogleAuthProvider()
    auth._creds = Credentials(
        token="t", scopes=READ_SCOPES + WRITE_SCOPES, email="teacher@example.com"
    )
    return auth


class AuthProviderLogicTests(unittest.TestCase):
    def test_not_logged_in_raises(self) -> None:
        with self.assertRaises(AgentError) as ctx:
            GoogleAuthProvider().credentials()
        self.assertEqual(ctx.exception.code, ErrorCode.GOOGLE_AUTH_EXPIRED)

    def test_require_scope_checks_granted(self) -> None:
        auth = GoogleAuthProvider()
        auth._creds = Credentials(token="t", scopes=(Scopes.COURSES_READONLY,))
        auth.require_scope(Scopes.COURSES_READONLY)  # OK
        with self.assertRaises(AgentError) as ctx:
            auth.require_scope(Scopes.ANNOUNCEMENTS)
        self.assertEqual(ctx.exception.code, ErrorCode.CLASSROOM_API_PERMISSION_DENIED)


class ErrorMappingTests(unittest.TestCase):
    def test_status_mapping(self) -> None:
        cases = {
            403: ErrorCode.CLASSROOM_API_PERMISSION_DENIED,
            404: ErrorCode.CLASSROOM_API_NOT_FOUND,
            429: ErrorCode.CLASSROOM_API_RATE_LIMITED,
            401: ErrorCode.GOOGLE_AUTH_EXPIRED,
        }
        for status, code in cases.items():
            err = _map_http_error(_FakeHttpError(status), fallback="X")
            self.assertEqual(err.code, code)

    def test_unknown_status_uses_fallback(self) -> None:
        err = _map_http_error(_FakeHttpError(500), fallback=ErrorCode.CLASSROOM_POST_FAILED)
        self.assertEqual(err.code, ErrorCode.CLASSROOM_POST_FAILED)


class ClassroomClientTests(unittest.TestCase):
    def _client_with_service(self) -> tuple[GoogleClassroomClient, MagicMock]:
        svc = MagicMock()
        client = GoogleClassroomClient(_authed())
        client._service = svc
        return client, svc

    def test_list_courses_returns_raw(self) -> None:
        client, svc = self._client_with_service()
        svc.courses.return_value.list.return_value.execute.return_value = {
            "courses": [{"id": "1", "name": "数学I"}]
        }
        courses = client.list_courses()
        self.assertEqual(courses[0]["id"], "1")

    def test_list_submissions_enriches_names_and_turnin(self) -> None:
        client, svc = self._client_with_service()
        courses = svc.courses.return_value
        courses.courseWork.return_value.studentSubmissions.return_value.list.return_value.execute.return_value = {
            "studentSubmissions": [
                {
                    "id": "s1",
                    "userId": "u1",
                    "state": "TURNED_IN",
                    "submissionHistory": [
                        {"stateHistory": {"state": "CREATED", "stateTimestamp": "t0"}},
                        {"stateHistory": {"state": "TURNED_IN", "stateTimestamp": "t1"}},
                    ],
                }
            ]
        }
        courses.students.return_value.list.return_value.execute.return_value = {
            "students": [
                {"userId": "u1", "profile": {"name": {"fullName": "山田太郎"}}}
            ]
        }
        subs = client.list_submissions("c1", "cw1")
        self.assertEqual(subs[0]["studentName"], "山田太郎")
        self.assertEqual(subs[0]["turnInTime"], "t1")
        self.assertEqual(subs[0]["courseId"], "c1")

    def test_create_announcement_individual_students(self) -> None:
        client, svc = self._client_with_service()
        create = svc.courses.return_value.announcements.return_value.create
        create.return_value.execute.return_value = {"id": "ann1"}
        client.create_announcement(
            "c1", "本文", assignee_mode="INDIVIDUAL_STUDENTS", student_ids=["u1"]
        )
        body = create.call_args.kwargs["body"]
        self.assertEqual(body["individualStudentsOptions"]["studentIds"], ["u1"])

    def test_http_error_mapped(self) -> None:
        client, svc = self._client_with_service()
        svc.courses.return_value.list.return_value.execute.side_effect = _FakeHttpError(403)
        with self.assertRaises(AgentError) as ctx:
            client.list_courses()
        self.assertEqual(ctx.exception.code, ErrorCode.CLASSROOM_API_PERMISSION_DENIED)


class DocsClientTests(unittest.TestCase):
    def test_create_document(self) -> None:
        svc = MagicMock()
        svc.documents.return_value.create.return_value.execute.return_value = {
            "documentId": "d1"
        }
        client = GoogleDocsClient(_authed())
        client._service = svc
        result = client.create_document("T", [{"type": "heading1", "text": "見出し"}])
        self.assertEqual(result["documentId"], "d1")
        self.assertTrue(result["url"].endswith("/d1/edit"))
        # batchUpdate が呼ばれている
        self.assertTrue(svc.documents.return_value.batchUpdate.called)

    def test_blocks_to_requests_covers_types(self) -> None:
        requests = _blocks_to_docs_requests(
            [
                {"type": "heading1", "text": "H"},
                {"type": "paragraph", "text": "P"},
                {"type": "bulletList", "items": ["a", "b"]},
                {"type": "table", "columns": ["c1"], "rows": [["r1"]]},
            ]
        )
        kinds = [next(iter(r)) for r in requests]
        self.assertIn("insertText", kinds)
        self.assertIn("createParagraphBullets", kinds)
        # インデックスが単調増加している
        inserts = [r["insertText"]["location"]["index"] for r in requests if "insertText" in r]
        self.assertEqual(inserts, sorted(inserts))


if __name__ == "__main__":
    unittest.main()
