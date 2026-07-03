"""実行層のエラー (REQUIREMENTS 13章)。

エラーコードはkimuの契約(`STANDARD_ERROR_CODES`)と共有し、逸脱しないようにする。
権限エラー等の内部詳細はGUIへ出さず、安全なメッセージのみ返す (12.1)。
"""

from __future__ import annotations

from ..contract import STANDARD_ERROR_CODES


class ErrorCode:
    CLASSROOM_API_PERMISSION_DENIED = "CLASSROOM_API_PERMISSION_DENIED"
    CLASSROOM_API_NOT_FOUND = "CLASSROOM_API_NOT_FOUND"
    CLASSROOM_API_RATE_LIMITED = "CLASSROOM_API_RATE_LIMITED"
    GOOGLE_AUTH_EXPIRED = "GOOGLE_AUTH_EXPIRED"
    INVALID_AGENT_OUTPUT = "INVALID_AGENT_OUTPUT"
    DOCUMENT_EXPORT_FAILED = "DOCUMENT_EXPORT_FAILED"
    PDF_EXPORT_FAILED = "PDF_EXPORT_FAILED"
    CLASSROOM_POST_FAILED = "CLASSROOM_POST_FAILED"


# GUIへ返す教師向けメッセージ。内部詳細は含めない (12.1)。
SAFE_MESSAGES = {
    ErrorCode.CLASSROOM_API_PERMISSION_DENIED: "この操作を行う権限がありません。Googleアカウントの権限を確認してください。",
    ErrorCode.CLASSROOM_API_NOT_FOUND: "対象のデータが見つかりませんでした。",
    ErrorCode.CLASSROOM_API_RATE_LIMITED: "アクセスが集中しています。しばらく待って再試行してください。",
    ErrorCode.GOOGLE_AUTH_EXPIRED: "ログインの有効期限が切れました。再度ログインしてください。",
    ErrorCode.INVALID_AGENT_OUTPUT: "AIの出力形式が不正です。",
    ErrorCode.DOCUMENT_EXPORT_FAILED: "Google Documentの作成に失敗しました。",
    ErrorCode.PDF_EXPORT_FAILED: "PDFの出力に失敗しました。",
    ErrorCode.CLASSROOM_POST_FAILED: "Classroomへの投稿に失敗しました。",
}

_UNRECOVERABLE = {ErrorCode.INVALID_AGENT_OUTPUT}

# 契約側の標準コードから逸脱していないことを保証する
assert {
    ErrorCode.CLASSROOM_API_PERMISSION_DENIED,
    ErrorCode.CLASSROOM_API_NOT_FOUND,
    ErrorCode.CLASSROOM_API_RATE_LIMITED,
    ErrorCode.GOOGLE_AUTH_EXPIRED,
    ErrorCode.INVALID_AGENT_OUTPUT,
    ErrorCode.DOCUMENT_EXPORT_FAILED,
    ErrorCode.PDF_EXPORT_FAILED,
    ErrorCode.CLASSROOM_POST_FAILED,
}.issubset(STANDARD_ERROR_CODES)


class AgentError(Exception):
    """JSON化してGUIへ返せるエラー (13章のerrors要素形式)。"""

    def __init__(
        self,
        code: str,
        message: str | None = None,
        recoverable: bool | None = None,
        detail: str | None = None,
    ) -> None:
        self.code = code
        self.message = message or SAFE_MESSAGES.get(code, "エラーが発生しました。")
        if recoverable is None:
            recoverable = code not in _UNRECOVERABLE
        self.recoverable = recoverable
        # detail は内部ログ用。GUIレスポンスへは含めない。
        self.detail = detail
        super().__init__(self.message)

    def to_error_item(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "recoverable": self.recoverable,
        }
