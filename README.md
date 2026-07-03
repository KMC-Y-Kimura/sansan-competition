# sansan-competition

`kimu` 担当の土台として、Google Classroom の提出状況を正規化し、判定し、GUI 班へ返す構造化 JSON を生成する実装を追加しています。

## PR Automation

GitHub Actions based PR automation lives in `.github/workflows/pr-automation.yml`.

- Trigger: `pull_request_target`
- Loop: auto-fix cache artifacts, rerun validation, post a PR report comment
- Pass condition: `pytest`, CLI sample generation, and shared JSON contract checks all pass
- Merge behavior: by default the workflow stops at a review result; add the `automerge` label to allow squash merge after a green run
- Fork PRs: validation and report comments run, but auto-fix commits are only pushed for same-repository branches

Local dry-run:

```bash
python3 scripts/pr_automation.py --apply-fixes
```

## PR Monitoring

Run the repository monitor with a 5x interval:

```bash
bash scripts/monitor_prs.sh
```

Optional overrides:

- `PR_MONITOR_INTERVAL_SECONDS=300` sets the poll interval.
- `PR_MONITOR_LIMIT=50` sets the maximum number of open PRs to fetch.
- `PR_MONITOR_REPO_DIR=/path/to/repo` sets the repository directory.

## Kimu Scope

## 含めたもの

- `sansan_competition/normalization.py`
  - `Course` / `CourseWork` / `StudentSubmission` の正規化
  - 部分失敗を許容する `normalize_submission_batch`
- `sansan_competition/analysis.py`
  - 未提出
  - 期限接近未提出
  - 遅延提出
  - 添付不足の可能性
  の判定ロジック
- `sansan_competition/contract.py`
  - `schemaVersion=1.0.0` の共通レスポンス組み立て
  - 正常系、部分成功、異常系の返却
  - GUI 向け `summary` / `gui` / `outputs` / `approval` / `errors`
  - 契約検証用のバリデータ
- `sansan_competition/outputs.py`
  - Markdown / PDF / Google Document 用の構造化データ
  - Classroom 投稿 payload
- `schemas/agent-output-v1.0.0.json`
  - GUI 班との契約として渡せる JSON Schema
- `samples/*.json`
  - 正常系と異常系のサンプル JSON

## 設計上の前提

- エラー時も GUI の分岐を減らすため、`gui` / `outputs` / `approval` を空で返す固定形にしています。
- `添付不足の可能性` は、現状では `ASSIGNMENT` で `TURNED_IN` / `RETURNED` だが添付ゼロの場合のヒューリスティックです。実際の提出内容確認は別途必要です。
- `partial_success` を導入し、一部データだけ正規化できたケースを `errors` と `warnings` に残します。

## 実行例

```bash
python3 main.py
```

AI 入力サンプルの確認:

```bash
python3 main.py sample-ai-input-reminder
python3 main.py sample-ai-input-weekly-report
```

部分成功サンプルの確認:

```bash
python3 main.py sample-partial-analysis
python3 main.py sample-partial-reminder
```

## テスト

```bash
python3 -m unittest discover -s tests
```

## Google Classroom / OAuth

このブランチには、CLI ベースの Google OAuth と Classroom API 連携の土台を追加しています。

- `scripts/classroom_oauth_smoke.py`
  - OAuth を通してコース一覧取得を確認
- `scripts/classroom_fetch_analysis.py`
  - Classroom 実データを取得し、`kimu` の共通 JSON 契約へ変換
- `scripts/classroom_post_reminder.py`
  - 承認済みの `classroomReminder` payload を Classroom に投稿
- `sansan_competition/oauth.py`
  - OAuth 認証と Google API service 構築
- `sansan_competition/classroom.py`
  - Classroom 取得、正規化接続、投稿変換

まだ入っていないもの:

- Web GUI 用の Google ログイン画面
- フロントエンドからの OAuth コールバック処理
- Docs / Drive 実出力との結合

`kimu` 担当の正規化・契約・判定ロジックはサンプル入力だけでも進められますが、MVP 全体では OAuth と Classroom 取得は必須です。セットアップ方針と CLI の疎通確認手順は [docs/google-classroom-cli-oauth-setup.md](/Users/kimura/Desktop/SP活動/2年/後期/sansan-competition/docs/google-classroom-cli-oauth-setup.md) にまとめました。

疎通確認だけなら、次でコース一覧取得まで確認できます。

```bash
python3 -m pip install -e '.[google]'
python3 scripts/classroom_oauth_smoke.py
```

ライブ提出分析の例:

```bash
python3 scripts/classroom_fetch_analysis.py --course-id YOUR_COURSE_ID --course-work-id YOUR_COURSEWORK_ID
```

承認済みリマインド投稿の例:

```bash
python3 scripts/classroom_post_reminder.py --input samples/reminder_generation_success.json --approved
```
