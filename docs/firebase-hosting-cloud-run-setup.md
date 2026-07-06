# Firebase Hosting + Cloud Run セットアップ

この構成は、次の要件を満たすためのものです。

- Google OAuth の redirect URI を `HTTPS + ドメイン名` にする
- GUI の静的ファイルは Firebase Hosting から配信する
- `/api/live/*` と `/oauth/google/callback` は Python バックエンドで処理する

## 前提

- Firebase project がある
- Firebase Hosting site がある
- `gcloud auth list` に利用アカウントが出る
- `firebase login` 済み

## 現在の推奨構成

- Hosting site: `https://<site-id>.web.app`
- Python backend: Cloud Run service `sansan-competition`
- Hosting rewrites:
  - `/api/**` -> Cloud Run
  - `/oauth/google/callback` -> Cloud Run

`firebase.json` はその前提で追加済みです。

## まず必要なこと

少なくとも次を有効にしてください。

1. Billing を有効化する
2. Cloud Run Admin API を有効化する
3. Cloud Build API を有効化する
4. Artifact Registry API を有効化する
5. Cloud Functions API を有効化する

CLI からまとめて有効化する場合:

```bash
gcloud config set project YOUR_PROJECT_ID
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com cloudfunctions.googleapis.com
```

## デプロイ

この repo には Cloud Run 用の `Dockerfile` と、Firebase Hosting 用の `firebase.json` を追加しています。

デプロイは次で実行できます。

```bash
cd /Users/kimura/Desktop/SP活動/2年/後期/sansan-competition
PROJECT_ID=YOUR_PROJECT_ID ./scripts/deploy_firebase_cloud_run.sh
```

既定値:

- region: `asia-northeast1`
- serviceId: `sansan-competition`

必要なら環境変数で上書きしてください。

```bash
PROJECT_ID=YOUR_PROJECT_ID REGION=asia-northeast1 SERVICE_ID=sansan-competition ./scripts/deploy_firebase_cloud_run.sh
```

### 無料枠を超えにくくする既定値

`scripts/deploy_firebase_cloud_run.sh` は、教師1人が使う低トラフィック前提で次を既定にしています。

- `CPU=1`
- `MEMORY=512Mi`
- `CONCURRENCY=20`
- `MIN_INSTANCES=0`
- `MAX_INSTANCES=1`
- `TIMEOUT=60`

意味は次のとおりです。

- `MIN_INSTANCES=0`: アイドル時に常駐課金を避ける
- `MAX_INSTANCES=1`: service-level / revision-level の両方で横方向に増殖しないようにする
- `CPU=1` / `MEMORY=512Mi`: 必要最小限に寄せる
- `CONCURRENCY=20`: 少人数アクセスでインスタンス数を増やしにくくする
- `--cpu-throttling`: リクエスト非処理時の CPU 消費を抑える
- `--no-cpu-boost`: 起動時の一時的な CPU 上乗せを避ける

必要なら環境変数で上書きできます。

```bash
PROJECT_ID=YOUR_PROJECT_ID MAX_INSTANCES=2 MEMORY=1Gi ./scripts/deploy_firebase_cloud_run.sh
```

## 予算管理

重要なのは、Cloud Billing の `Budget` は通常は「通知」であって「強制停止」ではない、という点です。
そのため、この公開構成は「無料枠を超えにくくする」ことはできますが、「必ず無料枠内に収める」保証はできません。

理由:

- Cloud Run の `max instances` はコスト安全策ですが、一時的に超える場合があります
- Firebase Hosting の通信量はアクセス数に応じて増えます
- Cloud Run の source deploy は Cloud Build / Artifact Registry も使います

厳密に課金ゼロを優先するなら、Cloud Run を使わず各端末でローカル実行する構成に切り替えるべきです。

最低限、次を設定してください。

1. Cloud Billing の `Budgets & alerts` で少額予算を作る
2. 通知閾値を `50% / 90% / 100%` にする
3. 通知先メールに自分を追加する

初期値の実務上の目安:

- まずは `100円` から始める
- 問題なければ `300円` などへ調整する

このプロトでは、予算通知に加えて `MAX_INSTANCES=1` を維持するのが現実的な安全策です。

## OAuth client に登録する redirect URI

Web application OAuth client の Authorized redirect URI に次を追加してください。

```text
https://YOUR_SITE_ID.web.app/oauth/google/callback
```

もし custom domain を Firebase Hosting に接続しているなら、そちらでも構いません。

```text
https://your-domain.example.com/oauth/google/callback
```

## Cloud Run 上で OAuth client JSON を永続化する

Cloud Run コンテナ内に GUI からアップロードした `credentials.json` は、インスタンス再作成で消えます。公開環境では環境変数で持たせてください。

この repo は次のどちらかを読めます。

- `SANSAN_GOOGLE_OAUTH_CLIENT_JSON_B64`
- `SANSAN_GOOGLE_OAUTH_CLIENT_JSON`

実務上は base64 の方が安全です。macOS / Linux なら次で設定できます。

```bash
CLIENT_JSON_B64="$(base64 < /absolute/path/to/client_secret_xxx.json | tr -d '\n')"
gcloud run services update sansan-competition \
  --region asia-northeast1 \
  --update-env-vars "SANSAN_GOOGLE_OAUTH_CLIENT_JSON_B64=${CLIENT_JSON_B64}"
```

この前に、Google Cloud Console 側で Authorized redirect URI に次を追加し、保存後に JSON を再ダウンロードしてください。

```text
https://YOUR_SITE_ID.web.app/oauth/google/callback
```

## 注意

- `http://192.168.x.x:8000/...` のような生 IP + HTTP は Google OAuth の Web application client では使えません
- `https://YOUR_SITE_ID.web.app/oauth/google/callback` を追加しただけでは反映されません。保存後の新しい JSON を使ってください
- `Desktop app` client は同一端末ローカル確認用です
- 別端末ブラウザから使う場合は `Web application` client を使ってください
- OAuth client JSON は repo にコミットしないでください
