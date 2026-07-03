# 実Google API接続 セットアップ (mocky担当)

モック実装(`Mock*`)を実Google APIへ切り替える手順。MVPはデスクトップ(installed-app)方式。

## 1. Google Cloud側の準備

1. Google Cloud Console でプロジェクトを作成。
2. 以下のAPIを有効化: **Google Classroom API**, **Google Docs API**, **Google Drive API**。
3. OAuth同意画面を構成（ユーザー種別: 内部 または 外部）。テスト段階はテストユーザーに対象教師アカウントを追加。
4. 認証情報 → OAuthクライアントID → アプリの種類 **「デスクトップアプリ」** を作成し、`client_secret.json` をダウンロード。

## 2. 依存インストール

```bash
uv sync --extra google
```

## 3. スコープ

`sansan_competition/execution/google_auth.py` の `READ_SCOPES` / `WRITE_SCOPES` を要求する。
読み取り専用と書き込み(投稿/作成)を分離している (REQUIREMENTS 11.3)。

- 読み取り: courses.readonly / coursework.students.readonly / rosters.readonly / student-submissions.students.readonly
- 書き込み: classroom.announcements / documents / drive.file

## 4. 使い方（モックとの差し替え）

```python
from sansan_competition.execution import (
    GoogleAuthProvider, GoogleClassroomClient, GoogleDocsClient, OutputExecutor,
)

auth = GoogleAuthProvider(
    client_secret_path="client_secret.json",
    token_path="token.json",
)
auth.login()  # 初回のみブラウザで同意 → token.json にキャッシュ

classroom = GoogleClassroomClient(auth)          # MockClassroomClient と同じIF
docs = GoogleDocsClient(auth)                     # MockGoogleDocsClient と同じIF

# 以降は kimu の normalize_* / analyze / build_*_response に接続し、
# OutputExecutor(classroom=classroom, docs=docs, out_dir=...) で承認済みアクションを実行。
```

`demo.py` の `Mock*` を上記に置き換えれば実データで動作する。

## 5. 注意

- `token.json` / `client_secret.json` は**コミットしない**（.gitignore 済み）。
- 初回ログインはローカルサーバ(`run_local_server`)がブラウザを開く。ヘッドレス環境では不可。
- 表を含む Google Document はMVPではタブ区切りテキストで表現する（`_blocks_to_docs_requests`）。
- APIエラーは `_map_http_error` で 403/404/429/401 を対応する `AgentError` コードへ変換する。
