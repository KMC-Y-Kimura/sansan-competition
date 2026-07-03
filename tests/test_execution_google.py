from __future__ import annotations

import unittest

from sansan_competition.execution.errors import AgentError, ErrorCode
from sansan_competition.execution.google_auth import (
    MockAuthProvider,
    READ_SCOPES,
    WRITE_SCOPES,
    Scopes,
)
from sansan_competition.execution.classroom_client import MockClassroomClient
from sansan_competition.normalization import normalize_submission_batch


def _logged_in() -> MockAuthProvider:
    auth = MockAuthProvider()
    auth.login(READ_SCOPES + WRITE_SCOPES)
    return auth


class AuthTests(unittest.TestCase):
    def test_login_scoped_credentials(self) -> None:
        auth = MockAuthProvider(email="t@example.com")
        creds = auth.login(READ_SCOPES)
        self.assertEqual(creds.email, "t@example.com")
        self.assertTrue(creds.has_scope(Scopes.COURSES_READONLY))
        self.assertIn("***", creds.masked_token())

    def test_expired_token_raises(self) -> None:
        auth = MockAuthProvider(simulate_expired=True)
        auth.login(READ_SCOPES)
        with self.assertRaises(AgentError) as ctx:
            auth.credentials()
        self.assertEqual(ctx.exception.code, ErrorCode.GOOGLE_AUTH_EXPIRED)


class ClassroomClientTests(unittest.TestCase):
    def test_missing_scope_denied(self) -> None:
        auth = MockAuthProvider()
        auth.login((Scopes.COURSES_READONLY,))  # coursework/submissionスコープ無し
        client = MockClassroomClient(auth)
        self.assertTrue(client.list_courses())
        with self.assertRaises(AgentError) as ctx:
            client.list_course_work("123456789")
        self.assertEqual(ctx.exception.code, ErrorCode.CLASSROOM_API_PERMISSION_DENIED)

    def test_read_scope_cannot_post(self) -> None:
        auth = MockAuthProvider()
        auth.login(READ_SCOPES)  # 書き込みスコープ無し
        client = MockClassroomClient(auth)
        with self.assertRaises(AgentError) as ctx:
            client.create_announcement("123456789", "本文")
        self.assertEqual(ctx.exception.code, ErrorCode.CLASSROOM_API_PERMISSION_DENIED)

    def test_raw_data_feeds_normalization(self) -> None:
        # mocky取得の生データ → kimu正規化 が通ること (ROLE 4.2)
        client = MockClassroomClient(_logged_in())
        raw_subs = client.list_submissions("123456789", "987654321")
        self.assertEqual(len(raw_subs), 30)
        submissions, issues = normalize_submission_batch(raw_subs)
        self.assertEqual(issues, [])
        unsubmitted = [s for s in submissions if s.state == "NEW"]
        self.assertEqual(len(unsubmitted), 12)

    def test_not_found(self) -> None:
        client = MockClassroomClient(_logged_in())
        with self.assertRaises(AgentError) as ctx:
            client.list_course_work("000")
        self.assertEqual(ctx.exception.code, ErrorCode.CLASSROOM_API_NOT_FOUND)

    def test_simulated_failure(self) -> None:
        client = MockClassroomClient(
            _logged_in(), fail_with=ErrorCode.CLASSROOM_API_RATE_LIMITED
        )
        with self.assertRaises(AgentError) as ctx:
            client.list_courses()
        self.assertEqual(ctx.exception.code, ErrorCode.CLASSROOM_API_RATE_LIMITED)


if __name__ == "__main__":
    unittest.main()
