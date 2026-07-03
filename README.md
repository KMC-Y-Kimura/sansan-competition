# sansan-competition

Google Classroom運用支援AIエージェントのGUIプロトタイプです。

## GUIプロトタイプ

```bash
python3 main.py --port 8000
```

ブラウザで `http://127.0.0.1:8000` を開きます。

現在の実装範囲:

- Googleログイン画面のモック
- コース選択
- ダッシュボード
- 課題詳細と提出状況表示
- AIアウトプットJSONのカード、表、警告、編集フィールド表示
- 出力形式選択
- Classroom投稿前の承認画面

Google OAuth、Classroom API、AI生成処理、実際のPDF/Markdown/Google Document出力は未接続です。

## PR Automation

GitHub Actions based PR automation lives in [`.github/workflows/pr-automation.yml`](.github/workflows/pr-automation.yml).

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
