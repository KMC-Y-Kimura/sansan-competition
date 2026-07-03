"""実Google API実装 (REQUIREMENTS 11.1-11.3)。

mockのインターフェースをそのまま満たす実装:
- GoogleAuthProvider  : installed-app方式のOAuth 2.0 (client_secret.json → token.json)
- GoogleClassroomClient: Classroom API。生データ(dict)を返し kimuの normalize_* が消費
- GoogleDocsClient     : Docs API。blocks から実ドキュメントを生成

googleライブラリはメソッド内で遅延importする。未インストールでもモック側は動く。
実ライブ呼び出しには client_secret.json と対象アカウントの同意が必要。
"""

from __future__ import annotations

from typing import Any

from .errors import AgentError, ErrorCode
from .google_auth import Credentials, READ_SCOPES, Scopes, WRITE_SCOPES

DEFAULT_SCOPES = READ_SCOPES + WRITE_SCOPES


# --------------------------------------------------------------- 認証


class GoogleAuthProvider:
    """installed-app方式の実OAuth。

    client_secret.json でブラウザ同意し、token.json にトークンをキャッシュ。
    次回以降は token.json を読み、期限切れは refresh_token で自動更新する。
    """

    def __init__(
        self,
        client_secret_path: str = "client_secret.json",
        token_path: str = "token.json",
        scopes: tuple[str, ...] = DEFAULT_SCOPES,
        email: str = "",
    ) -> None:
        self._client_secret_path = client_secret_path
        self._token_path = token_path
        self._scopes = list(scopes)
        self._email = email
        self._google_creds: Any = None
        self._creds: Credentials | None = None

    def login(self, scopes: tuple[str, ...] | None = None) -> Credentials:
        import os

        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials as GCreds
        from google_auth_oauthlib.flow import InstalledAppFlow

        scope_list = list(scopes) if scopes else self._scopes
        creds = None
        if os.path.exists(self._token_path):
            creds = GCreds.from_authorized_user_file(self._token_path, scope_list)
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as exc:  # リフレッシュ失敗 = 要再ログイン
                raise AgentError(
                    ErrorCode.GOOGLE_AUTH_EXPIRED, detail=f"refresh failed: {exc}"
                ) from exc
        if not creds or not creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file(
                self._client_secret_path, scope_list
            )
            creds = flow.run_local_server(port=0)
            with open(self._token_path, "w", encoding="utf-8") as fh:
                fh.write(creds.to_json())

        self._google_creds = creds
        self._creds = Credentials(
            token=creds.token or "",
            scopes=tuple(creds.scopes or scope_list),
            email=self._email,
            expired=not creds.valid,
        )
        return self._creds

    def credentials(self) -> Credentials:
        if self._creds is None:
            raise AgentError(ErrorCode.GOOGLE_AUTH_EXPIRED, detail="not logged in")
        if self._google_creds is not None and self._google_creds.expired:
            raise AgentError(ErrorCode.GOOGLE_AUTH_EXPIRED, detail="token expired")
        return self._creds

    def require_scope(self, scope: str) -> None:
        creds = self.credentials()
        if not creds.has_scope(scope):
            raise AgentError(
                ErrorCode.CLASSROOM_API_PERMISSION_DENIED,
                detail=f"missing scope: {scope}",
            )

    def google_credentials(self) -> Any:
        """API service構築用の google.oauth2 Credentials を返す。"""
        if self._google_creds is None:
            raise AgentError(ErrorCode.GOOGLE_AUTH_EXPIRED, detail="not logged in")
        return self._google_creds


def _map_http_error(exc: Exception, *, fallback: str) -> AgentError:
    """googleapiclient の HttpError 等を AgentError へ変換する。"""
    status = getattr(getattr(exc, "resp", None), "status", None)
    try:
        status = int(status)
    except (TypeError, ValueError):
        status = None
    mapping = {
        400: ErrorCode.INVALID_AGENT_OUTPUT,
        401: ErrorCode.GOOGLE_AUTH_EXPIRED,
        403: ErrorCode.CLASSROOM_API_PERMISSION_DENIED,
        404: ErrorCode.CLASSROOM_API_NOT_FOUND,
        429: ErrorCode.CLASSROOM_API_RATE_LIMITED,
    }
    code = mapping.get(status, fallback)
    return AgentError(code, detail=f"HTTP {status}: {exc}")


# ------------------------------------------------------------ Classroom


class GoogleClassroomClient:
    """Classroom API クライアント。読み取りは生データ(dict)を返す。"""

    def __init__(self, auth: GoogleAuthProvider, *, roster_names: bool = True) -> None:
        self._auth = auth
        self._roster_names = roster_names
        self._service: Any = None

    def _svc(self) -> Any:
        if self._service is None:
            from googleapiclient.discovery import build

            self._service = build(
                "classroom",
                "v1",
                credentials=self._auth.google_credentials(),
                cache_discovery=False,
            )
        return self._service

    def list_courses(self) -> list[dict]:
        self._auth.require_scope(Scopes.COURSES_READONLY)
        return self._collect(
            lambda **p: self._svc().courses().list(**p),
            "courses",
            {"courseStates": ["ACTIVE"]},
        )

    def list_course_work(self, course_id: str) -> list[dict]:
        self._auth.require_scope(Scopes.COURSEWORK_READONLY)
        return self._collect(
            lambda **p: self._svc().courses().courseWork().list(**p),
            "courseWork",
            {"courseId": course_id},
        )

    def list_submissions(self, course_id: str, course_work_id: str) -> list[dict]:
        self._auth.require_scope(Scopes.SUBMISSIONS_READONLY)
        subs = self._collect(
            lambda **p: self._svc().courses().courseWork().studentSubmissions().list(**p),
            "studentSubmissions",
            {"courseId": course_id, "courseWorkId": course_work_id},
        )
        names = self._student_names(course_id) if self._roster_names else {}
        for sub in subs:
            sub["courseId"] = course_id
            sub["courseWorkId"] = course_work_id
            uid = sub.get("userId", "")
            if uid in names:
                sub["studentName"] = names[uid]
            turn_in = _turn_in_time(sub)
            if turn_in:
                sub["turnInTime"] = turn_in
        return subs

    def create_announcement(
        self,
        course_id: str,
        text: str,
        *,
        materials: list | None = None,
        assignee_mode: str = "ALL_STUDENTS",
        student_ids: list[str] | None = None,
    ) -> dict:
        self._auth.require_scope(Scopes.ANNOUNCEMENTS)
        if not text.strip():
            raise AgentError(
                ErrorCode.CLASSROOM_POST_FAILED, detail="empty announcement text"
            )
        body: dict = {
            "text": text,
            "assigneeMode": assignee_mode,
            "materials": materials or [],
        }
        if assignee_mode == "INDIVIDUAL_STUDENTS":
            body["individualStudentsOptions"] = {"studentIds": student_ids or []}
        try:
            return (
                self._svc()
                .courses()
                .announcements()
                .create(courseId=course_id, body=body)
                .execute()
            )
        except Exception as exc:
            raise _map_http_error(exc, fallback=ErrorCode.CLASSROOM_POST_FAILED) from exc

    def _student_names(self, course_id: str) -> dict[str, str]:
        try:
            students = self._collect(
                lambda **p: self._svc().courses().students().list(**p),
                "students",
                {"courseId": course_id},
            )
        except AgentError:
            # 名簿が取れなくてもリマインドは人数ベースで作れる (12.2)
            return {}
        names: dict[str, str] = {}
        for student in students:
            uid = student.get("userId", "")
            full = (student.get("profile") or {}).get("name", {}).get("fullName", "")
            if uid and full:
                names[uid] = full
        return names

    def _collect(self, method, key: str, params: dict) -> list[dict]:
        """ページネーションをたどって全件を集める。"""
        items: list[dict] = []
        page_token: str | None = None
        while True:
            call_params = dict(params)
            if page_token:
                call_params["pageToken"] = page_token
            try:
                resp = method(**call_params).execute()
            except AgentError:
                raise
            except Exception as exc:
                raise _map_http_error(
                    exc, fallback=ErrorCode.CLASSROOM_API_NOT_FOUND
                ) from exc
            items.extend(resp.get(key, []) or [])
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
        return items


def _turn_in_time(sub: dict) -> str | None:
    """submissionHistory から最後の TURNED_IN 時刻を取り出す。"""
    for entry in reversed(sub.get("submissionHistory", []) or []):
        state = entry.get("stateHistory")
        if state and state.get("state") == "TURNED_IN":
            return state.get("stateTimestamp")
    return None


# ----------------------------------------------------------- Google Docs


class GoogleDocsClient:
    """Docs API クライアント。blocks から実ドキュメントを生成する。"""

    def __init__(self, auth: GoogleAuthProvider) -> None:
        self._auth = auth
        self._service: Any = None

    def _svc(self) -> Any:
        if self._service is None:
            from googleapiclient.discovery import build

            self._service = build(
                "docs",
                "v1",
                credentials=self._auth.google_credentials(),
                cache_discovery=False,
            )
        return self._service

    def create_document(self, title: str, blocks: list[dict]) -> dict:
        self._auth.require_scope(Scopes.DOCUMENTS)
        try:
            doc = self._svc().documents().create(body={"title": title}).execute()
            doc_id = doc["documentId"]
            requests = _blocks_to_docs_requests(blocks)
            if requests:
                self._svc().documents().batchUpdate(
                    documentId=doc_id, body={"requests": requests}
                ).execute()
        except AgentError:
            raise
        except Exception as exc:
            raise _map_http_error(
                exc, fallback=ErrorCode.DOCUMENT_EXPORT_FAILED
            ) from exc
        return {
            "documentId": doc_id,
            "title": title,
            "url": f"https://docs.google.com/document/d/{doc_id}/edit",
        }


def _blocks_to_docs_requests(blocks: list[dict]) -> list[dict]:
    """blocks を Docs API batchUpdate リクエストへ変換する。

    先頭から実行インデックスを進めながら挿入する。表はMVPではタブ区切り
    テキストで表現する(Docsの表セル挿入はインデックス管理が複雑なため)。
    """
    requests: list[dict] = []
    index = 1  # ドキュメント本文の先頭

    def insert(text: str, *, style: str = "NORMAL_TEXT", bullet: bool = False) -> None:
        nonlocal index
        if not text.endswith("\n"):
            text = text + "\n"
        start = index
        end = start + len(text)
        requests.append(
            {"insertText": {"location": {"index": start}, "text": text}}
        )
        requests.append(
            {
                "updateParagraphStyle": {
                    "range": {"startIndex": start, "endIndex": end},
                    "paragraphStyle": {"namedStyleType": style},
                    "fields": "namedStyleType",
                }
            }
        )
        if bullet:
            requests.append(
                {
                    "createParagraphBullets": {
                        "range": {"startIndex": start, "endIndex": end},
                        "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE",
                    }
                }
            )
        index = end

    for block in blocks:
        if not isinstance(block, dict):
            continue
        btype = block.get("type")
        if btype in ("heading1", "heading2", "heading3"):
            insert(block.get("text", ""), style=f"HEADING_{btype[-1]}")
        elif btype == "paragraph":
            insert(block.get("text", ""))
        elif btype == "bulletList":
            for item in block.get("items", []):
                insert(str(item), bullet=True)
        elif btype == "table":
            columns = block.get("columns", [])
            rows = block.get("rows", [])
            insert("\t".join(str(c) for c in columns))
            for row in rows:
                insert("\t".join(str(c) for c in row))

    return requests
