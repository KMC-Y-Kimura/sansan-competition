"""mocky担当の実行層。

kimuの契約(`sansan_competition.contract` / `outputs`)が生成した AIアウトプットJSON の
`outputs.*` と `approval.actions` を、実ファイル・実投稿へ変換する。

- Google OAuth 認証 (google_auth)
- Google Classroom API クライアント (classroom_client)
- Markdown/PDF/Google Document の実出力 (renderers)
- 教師承認ゲートと Classroom 投稿 (posting)
"""

from .errors import AgentError, ErrorCode
from .google_auth import (
    Credentials,
    MockAuthProvider,
    READ_SCOPES,
    Scopes,
    WRITE_SCOPES,
)
from .classroom_client import ClassroomClient, MockClassroomClient
from .renderers import (
    MockGoogleDocsClient,
    render_google_document,
    render_markdown,
    render_pdf,
)
from .posting import (
    ActionType,
    ExecutionResult,
    OutputExecutor,
    build_post_preview,
    post_classroom_reminder,
)

__all__ = [
    "AgentError",
    "ErrorCode",
    "Credentials",
    "MockAuthProvider",
    "READ_SCOPES",
    "WRITE_SCOPES",
    "Scopes",
    "ClassroomClient",
    "MockClassroomClient",
    "MockGoogleDocsClient",
    "render_google_document",
    "render_markdown",
    "render_pdf",
    "ActionType",
    "ExecutionResult",
    "OutputExecutor",
    "build_post_preview",
    "post_classroom_reminder",
]
