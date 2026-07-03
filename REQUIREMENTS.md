要件定義書
Google Classroom運用支援AIエージェント
1. プロジェクト概要
本プロジェクトでは、Google Classroom APIを利用し、教師側のClassroom運用負担を軽減するAIエージェントを開発する。
教師は日常的に、課題作成、提出状況確認、未提出者へのリマインド、教材共有、連絡文作成、成績確認、フィードバック作成などを行っている。これらの作業は定型的でありながら時間がかかるため、AIエージェントによって補助・自動化することで、教師が授業設計や生徒対応に集中できる環境を作る。
本開発では、GUI班とAI班が分かれて作業する。そのため、AIエージェントがGUI側に返すアウトプット形式、Google Classroomへ投稿する内容、PDF・Markdown・Google Documentとして出力する内容のインターフェースを明確に定義する。
2. 開発目的
本アプリの目的は、教師がGoogle Classroomを運用する際の以下の負担を軽減することである。
課題や連絡文の作成負担を減らす。
提出状況や未提出者の確認負担を減らす。
生徒へのリマインド作成・送信の手間を減らす。
授業資料や課題情報を整理し、PDF・Markdown・Google Documentとして出力できるようにする。
教師がAIの出力を確認・修正したうえでClassroomへ反映できるようにする。
3. 想定ユーザー
主なユーザーは、Google Classroomを利用して授業を運用している教師である。
補助的なユーザーとして、学校管理者、TA、授業補助者を想定する。ただし、初期リリースでは教師を主対象とする。
4. 対象範囲
本アプリが扱う対象は以下とする。
Google Classroomのコース情報取得。
課題情報の取得・整理。
提出状況の取得・整理。
未提出者・期限接近者の抽出。
教師向け要約レポートの生成。
生徒向けリマインド文の生成。
Classroomのお知らせ投稿案の生成。
PDF、Markdown、Google Document形式での出力。
教師による確認後のClassroom投稿。
Google Classroom APIでは、コース、課題、教材、お知らせ、提出物、ルーブリックなどのリソースが扱える。課題や教材、お知らせはClassroom上のストリーム項目として扱われる。(Google for Developers)
5. 初期開発で扱わない範囲
初期開発では以下を対象外とする。
AIによる成績の自動確定。
教師の確認なしでの自動投稿。
生徒の個人情報を外部AIへ無制限に送信する処理。
保護者連絡の自動送信。
学校全体の管理者向け分析ダッシュボード。
Google Classroom以外のLMSとの連携。
完全自動採点。
ただし、将来的な拡張として、ルーブリック補助、提出物の要約、フィードバック文生成、成績入力補助は検討可能とする。
6. システム構成
本システムは以下の構成とする。
GUIフロントエンド。
バックエンドAPI。
AIエージェント処理部。
Google Classroom API連携部。
Google Drive / Google Docs / PDF / Markdown出力部。
認証・権限管理部。
ログ・監査管理部。
GUI班は、教師が操作する画面、AI出力の確認画面、Classroom反映前の承認画面を担当する。
AI班は、Classroom APIから取得した情報をもとに、要約、分類、リマインド文生成、レポート生成、出力JSON生成を担当する。
7. 基本的なユーザーフロー
教師がGoogleアカウントでログインする。
アプリが教師のGoogle Classroomコース一覧を取得する。
教師が対象コースを選択する。
アプリが課題、教材、お知らせ、提出状況を取得する。
教師が実行したい操作を選択する。
例として、未提出者リマインド作成、週次レポート作成、課題概要の整理、授業連絡文作成など。
AIエージェントがClassroom情報を分析し、構造化されたアウトプットを生成する。
GUIがAIアウトプットを表示する。
教師が内容を確認・修正する。
教師が出力形式を選択する。
PDF、Markdown、Google Document、Classroomリマインド投稿など。
教師の承認後、指定された形式で出力または投稿する。
8. 主要機能要件
8.1 コース一覧取得機能
教師がアクセス可能なGoogle Classroomのコース一覧を取得する。
取得する情報は以下とする。
courseId。
コース名。
セクション名。
説明。
コース状態。
作成日時。
更新日時。
教師一覧。
生徒数。
Classroom APIでは、リクエストユーザーが閲覧可能なコース一覧を取得できる。(Google for Developers)
8.2 課題一覧取得機能
選択されたコース内の課題を取得する。
取得する情報は以下とする。
courseWorkId。
タイトル。
説明文。
課題種別。
満点。
締切日。
締切時刻。
公開状態。
作成日時。
更新日時。
添付資料。
トピック。
ルーブリック有無。
CourseWorkは教師が生徒に出す課題を表すリソースである。(Google for Developers)
8.3 提出状況取得機能
選択された課題について、生徒ごとの提出状況を取得する。
取得する情報は以下とする。
studentSubmissionId。
studentId。
生徒名。
提出状態。
提出日時。
更新日時。
点数。
添付ファイル。
返却状態。
遅延提出かどうか。
StudentSubmissionはCourseWork作成時に生成される提出物リソースである。(Google for Developers)
8.4 未提出者抽出機能
課題の締切情報と提出状況をもとに、以下の生徒を抽出する。
未提出者。
期限が近いが未提出の生徒。
提出済みだが添付不足の可能性がある生徒。
遅延提出者。
教師は抽出結果を確認し、リマインド対象を手動で選択できる。
8.5 リマインド文生成機能
AIエージェントは、未提出者や期限接近者に向けたリマインド文を生成する。
リマインド文は以下の種類に対応する。
Classroomのお知らせ用。
個別メッセージ風。
全体向け通知。
やさしい口調。
厳しめの口調。
短文。
詳細文。
初期リリースでは、ClassroomのAnnouncementsを利用したコース全体向けリマインドを主対象とする。Classroom APIではコースへのお知らせ作成が可能である。(Google for Developers)
8.6 教師向けレポート生成機能
AIエージェントは、教師向けに以下のレポートを生成する。
課題別提出状況レポート。
未提出者一覧。
期限接近課題一覧。
クラス全体の進捗要約。
授業運用上の注意点。
次に行うべきアクション提案。
レポートは、PDF、Markdown、Google Documentとして出力可能にする。
8.7 Google Document出力機能
AIエージェントの出力をGoogle Documentとして作成する。
出力対象は以下とする。
週次レポート。
課題提出状況レポート。
授業連絡案。
生徒向け説明文。
課題説明文。
Google Document出力時には、タイトル、本文、見出し、表、箇条書きの構造を保持する。
8.8 Markdown出力機能
AIエージェントの出力をMarkdown形式で保存またはコピーできるようにする。
Markdownは、開発時の確認、Git管理、議事録共有、Notion等への貼り付けを想定する。
8.9 PDF出力機能
AIエージェントの出力をPDFとして保存できるようにする。
PDFは、教師間共有、会議資料、記録用として利用する。
PDFには以下を含める。
タイトル。
対象コース名。
作成日時。
対象期間。
概要。
詳細表。
AIによる提案。
注意事項。
8.10 Classroom投稿機能
教師が承認した場合のみ、Classroomへ投稿する。
投稿対象は以下とする。
お知らせ。
課題リマインド。
授業連絡。
教材案内。
初期リリースでは、課題の自動作成よりも、お知らせ投稿とリマインド投稿を優先する。
9. AIエージェントの役割
AIエージェントは、Google Classroom APIから取得した情報を直接GUIに返すのではなく、GUIが扱いやすい構造化データに変換して返す。
AIエージェントの主な役割は以下とする。
Classroom情報の要約。
提出状況の分類。
リマインド対象者の抽出。
教師向けレポートの作成。
Classroom投稿文の作成。
PDF / Markdown / Google Document用本文の作成。
GUI表示用カードデータの作成。
教師が次に取るべき行動の提案。
10. GUI班とAI班のインターフェース設計
10.1 基本方針
AI班は、自然文だけを返さない。
AI班は、必ずJSON形式で構造化されたアウトプットを返す。
GUI班は、AIアウトプットJSONを受け取り、画面表示、編集画面、出力処理、Classroom投稿処理に利用する。
AI出力には、必ず以下を含める。
実行結果の種類。
教師向け要約。
GUI表示用データ。
出力ファイル用データ。
Classroom投稿用データ。
リスク・注意点。
教師の承認が必要な操作。
10.2 AIアウトプット共通JSON形式
AIエージェントは、以下の形式で出力する。
{
      "schemaVersion": "1.0.0",
    "requestId": "req_20260703_001",
    "generatedAt": "2026-07-03T13:00:00+09:00",
    "agentTaskType": "REMINDER_GENERATION",
    "status": "success",
    "course": {
        "courseId": "123456789",
        "name": "数学I",
        "section": "1年A組"
      },
    "summary": {
        "title": "未提出課題リマインド案",
        "shortSummary": "数学Iの課題「二次関数プリント」に未提出者が12名います。",
        "teacherActionRequired": true,
        "recommendedAction": "未提出者に対してClassroomでリマインドを投稿してください。"
      },
    "gui": {
        "cards": [],
        "tables": [],
        "warnings": [],
        "editableFields": []
      },
    "outputs": {
        "markdown": null,
        "pdf": null,
        "googleDocument": null,
        "classroomReminder": null
      },
    "approval": {
        "required": true,
        "reason": "Classroomへの投稿を行うため、教師の承認が必要です。",
        "actions": []
      },
    "errors": []
  }
10.3 agentTaskType一覧
AIエージェントの処理種別は以下とする。
[
      "COURSE_SUMMARY",
    "COURSEWORK_SUMMARY",
    "SUBMISSION_ANALYSIS",
    "REMINDER_GENERATION",
    "WEEKLY_REPORT",
    "ANNOUNCEMENT_DRAFT",
    "DOCUMENT_EXPORT",
    "RUBRIC_SUPPORT",
    "ERROR_ANALYSIS"
  ]
各意味は以下とする。
COURSE_SUMMARYは、コース全体の概要作成。
COURSEWORK_SUMMARYは、課題情報の整理。
SUBMISSION_ANALYSISは、提出状況分析。
REMINDER_GENERATIONは、リマインド文生成。
WEEKLY_REPORTは、週次レポート生成。
ANNOUNCEMENT_DRAFTは、Classroomお知らせ文の作成。
DOCUMENT_EXPORTは、PDF、Markdown、Google Document用データ生成。
RUBRIC_SUPPORTは、ルーブリック関連の補助。
ERROR_ANALYSISは、APIエラーや取得失敗時の説明。
10.4 GUI表示用データ形式
GUI表示用データは、カード、テーブル、警告、編集可能フィールドに分ける。
{
      "gui": {
        "cards": [
              {
                "cardId": "card_001",
                "type": "metric",
                "title": "未提出者数",
                "value": "12",
                "description": "課題「二次関数プリント」の未提出者数です。"
              }
          ],
        "tables": [
              {
                "tableId": "table_001",
                "title": "未提出者一覧",
                "columns": [
                      {"key": "studentName", "label": "生徒名"},
                    {"key": "status", "label": "状態"},
                    {"key": "dueDate", "label": "締切"}
                  ],
                "rows": [
                      {
                        "studentName": "山田太郎",
                        "status": "未提出",
                        "dueDate": "2026-07-05"
                      }
                  ]
              }
          ],
        "warnings": [
              {
                "level": "medium",
                "message": "個別の生徒名を含むため、共有範囲に注意してください。"
              }
          ],
        "editableFields": [
              {
                "fieldId": "reminder_body",
                "label": "リマインド本文",
                "type": "textarea",
                "value": "課題の提出期限が近づいています。期限までに提出してください。",
                "required": true
              }
          ]
      }
  }
10.5 Markdown出力形式
Markdown出力は、以下の構造を持つ。
{
      "markdown": {
        "fileName": "math1_submission_report_20260703.md",
        "title": "数学I 提出状況レポート",
        "content": "# 数学I 提出状況レポート\n\n## 概要\n..."
      }
  }
Markdown本文には以下を含める。
タイトル。
概要。
対象コース。
対象課題。
提出状況。
未提出者一覧。
AIによる提案。
注意事項。
10.6 PDF出力形式
PDF出力は、AIが直接PDFバイナリを返すのではなく、PDF生成用の構造化データを返す。
{
      "pdf": {
        "fileName": "math1_submission_report_20260703.pdf",
        "title": "数学I 提出状況レポート",
        "layout": "report",
        "sections": [
              {
                "heading": "概要",
                "body": "数学Iの課題提出状況をまとめたレポートです。"
              },
            {
                "heading": "未提出者一覧",
                "table": {
                      "columns": ["生徒名", "状態", "締切"],
                    "rows": [
                        ["山田太郎", "未提出", "2026-07-05"]
                      ]
                  }
              }
          ]
      }
  }
PDF生成そのものはバックエンドまたはGUI側の出力処理が担当する。
AI班はPDFの内容構造を定義する。
10.7 Google Document出力形式
Google Document出力は、以下の形式とする。
{
      "googleDocument": {
        "title": "数学I 提出状況レポート 2026-07-03",
        "documentType": "report",
        "blocks": [
              {
                "type": "heading1",
                "text": "数学I 提出状況レポート"
              },
            {
                "type": "paragraph",
                "text": "このドキュメントは、Google Classroomの提出状況をもとにAIが作成したレポートです。"
              },
            {
                "type": "heading2",
                "text": "未提出者一覧"
              },
            {
                "type": "table",
                "columns": ["生徒名", "状態", "締切"],
                "rows": [
                      ["山田太郎", "未提出", "2026-07-05"]
                  ]
              }
          ]
      }
  }
Google Documentの実作成処理は、Google Docs APIまたはGoogle Drive連携部が担当する。
AI班はDocumentの構造を返す。
10.8 Classroomリマインド出力形式
Classroom投稿用データは、教師の承認後にのみ利用する。
{
      "classroomReminder": {
        "target": {
              "courseId": "123456789",
            "courseWorkId": "987654321"
          },
        "postType": "announcement",
        "title": "課題提出リマインド",
        "text": "課題「二次関数プリント」の提出期限が近づいています。まだ提出していない人は、7月5日までに提出してください。",
        "materials": [],
        "scheduledTime": null,
        "assigneeMode": "ALL_STUDENTS",
        "targetStudentIds": [],
        "requiresTeacherApproval": true
      }
  }
postTypeは初期リリースではannouncementを基本とする。
将来的には、courseWork、courseWorkMaterialにも対応する。
Classroom APIでは、Announcementsを作成できる。(Google for Developers)
10.9 承認アクション形式
教師の承認が必要な操作は、approval.actionsに格納する。
{
      "approval": {
        "required": true,
        "reason": "Classroomへ投稿する操作が含まれています。",
        "actions": [
              {
                "actionId": "action_001",
                "type": "CREATE_CLASSROOM_ANNOUNCEMENT",
                "label": "Classroomにリマインドを投稿",
                "requiresConfirmation": true,
                "payloadRef": "outputs.classroomReminder"
              },
            {
                "actionId": "action_002",
                "type": "EXPORT_PDF",
                "label": "PDFとして出力",
                "requiresConfirmation": false,
                "payloadRef": "outputs.pdf"
              }
          ]
      }
  }
11. API連携要件
11.1 Google Classroom API
Google Classroom APIを利用して以下を行う。
コース一覧の取得。
課題一覧の取得。
教材一覧の取得。
お知らせ一覧の取得。
提出状況の取得。
お知らせの作成。
ルーブリック情報の取得・作成補助。
Google Classroom APIは、クラス、名簿、招待、課題、提出物などを管理するAPIである。(Google for Developers)
11.2 Google Docs / Drive連携
Google Documentを作成する場合、Google Docs APIまたはGoogle Drive APIとの連携を行う。
必要な機能は以下とする。
新規ドキュメント作成。
タイトル設定。
本文挿入。
見出し挿入。
表挿入。
共有設定。
URL取得。
11.3 認証
Google OAuth 2.0を利用する。
教師が明示的にログインし、必要なスコープを許可する。
必要最小限の権限のみを要求する。
投稿や作成を行うスコープは、読み取り専用スコープと分離する。
12. 非機能要件
12.1 セキュリティ
生徒の個人情報を扱うため、以下を必須とする。
OAuthトークンを安全に保存する。
不要な個人情報をAIに渡さない。
AIに渡す前に必要に応じて生徒IDを仮名化する。
ログに個人情報を残しすぎない。
教師の承認なしにClassroomへ投稿しない。
権限エラー時には、詳細な内部情報をGUIに表示しない。
12.2 プライバシー
AI処理に渡すデータは、目的に必要な範囲に限定する。
未提出者リマインド作成では、必要に応じて生徒名を使わず人数のみで文章を生成する。
個別名を含むレポートは、教師向け出力として扱う。
生徒向け投稿には、他の生徒の提出状況が分からないようにする。
12.3 操作安全性
Classroomに投稿する前に必ず確認画面を表示する。
投稿前に以下を教師が確認できるようにする。
投稿先コース。
投稿本文。
対象課題。
対象生徒。
公開範囲。
投稿予定時刻。
教師が編集できる状態で表示する。
12.4 可用性
Google APIが失敗した場合でも、GUIはエラーメッセージを表示し、再試行できるようにする。
一部データが取得できない場合は、取得できた範囲でAI処理を行う。
12.5 保守性
GUI班とAI班の結合度を下げるため、AI出力形式はschemaVersionで管理する。
破壊的変更を行う場合は、schemaVersionを更新する。
GUI側は未知のフィールドを無視できるようにする。
AI側は必須フィールドを欠落させない。
13. エラー設計
AIエージェントは、エラー時もJSON形式で返す。
{
      "schemaVersion": "1.0.0",
    "requestId": "req_20260703_002",
    "generatedAt": "2026-07-03T13:10:00+09:00",
    "agentTaskType": "SUBMISSION_ANALYSIS",
    "status": "error",
    "summary": {
        "title": "提出状況の取得に失敗しました",
        "shortSummary": "Google Classroom APIから提出状況を取得できませんでした。",
        "teacherActionRequired": true,
        "recommendedAction": "Googleアカウントの権限を確認し、再度実行してください。"
      },
    "errors": [
        {
              "code": "CLASSROOM_API_PERMISSION_DENIED",
            "message": "提出状況を取得する権限がありません。",
            "recoverable": true
          }
      ]
  }
主なエラーコードは以下とする。
CLASSROOM_API_PERMISSION_DENIED。
CLASSROOM_API_NOT_FOUND。
CLASSROOM_API_RATE_LIMITED。
GOOGLE_AUTH_EXPIRED。
AI_GENERATION_FAILED。
INVALID_AGENT_OUTPUT。
DOCUMENT_EXPORT_FAILED。
PDF_EXPORT_FAILED。
CLASSROOM_POST_FAILED。
14. データモデル
14.1 Course
{
      "courseId": "string",
    "name": "string",
    "section": "string",
    "description": "string",
    "state": "string",
    "teacherIds": ["string"],
    "studentCount": 0
  }
14.2 CourseWork
{
      "courseWorkId": "string",
    "courseId": "string",
    "title": "string",
    "description": "string",
    "workType": "string",
    "maxPoints": 100,
    "dueDate": "2026-07-05",
    "dueTime": "23:59",
    "state": "PUBLISHED",
    "materials": [],
    "topicId": "string"
  }
14.3 StudentSubmission
{
      "studentSubmissionId": "string",
    "courseId": "string",
    "courseWorkId": "string",
    "studentId": "string",
    "studentName": "string",
    "state": "TURNED_IN",
    "late": false,
    "assignedGrade": null,
    "draftGrade": null,
    "attachments": []
  }
14.4 ReminderDraft
{
      "title": "string",
    "body": "string",
    "tone": "polite",
    "target": "all_students",
    "courseId": "string",
    "courseWorkId": "string",
    "requiresApproval": true
  }
15. 画面要件
15.1 ログイン画面
Googleアカウントでログインできる。
必要な権限の説明を表示する。
15.2 コース選択画面
教師が担当しているコース一覧を表示する。
コース名、セクション、生徒数、最終更新日時を表示する。
15.3 ダッシュボード画面
選択したコースの概要を表示する。
表示項目は以下とする。
未提出課題数。
期限接近課題数。
最近の課題。
最近のお知らせ。
AIによる注意点。
15.4 課題詳細画面
課題ごとの提出状況を表示する。
未提出者、提出済み、遅延提出を分類して表示する。
AIにリマインド文生成を依頼できる。
15.5 AI出力確認画面
AIが生成した内容を表示する。
教師が編集できる。
JSONの直接表示は開発者モードのみとする。
通常画面では、カード、表、文章、警告として表示する。
15.6 出力選択画面
以下の出力形式を選択できる。
PDF。
Markdown。
Google Document。
Classroomリマインド。
複数選択も可能とする。
15.7 投稿確認画面
Classroom投稿前に、以下を表示する。
投稿先コース。
投稿種別。
投稿本文。
対象課題。
対象者。
公開範囲。
警告。
教師が「投稿する」を押すまで投稿しない。
16. AI出力の品質要件
AI出力は以下を満たす必要がある。
教師がそのまま使える自然な日本語である。
生徒を責めすぎない表現にする。
個人情報の扱いに注意する。
事実と推測を分ける。
Classroom APIから取得した事実に基づいて作成する。
不明な情報を勝手に補わない。
締切日や課題名を間違えない。
GUI側で編集しやすいよう、本文とメタデータを分離する。
17. AIプロンプト設計要件
AI班は、タスクごとにプロンプトを分ける。
主なプロンプトは以下とする。
課題要約プロンプト。
提出状況分析プロンプト。
未提出者リマインド生成プロンプト。
週次レポート生成プロンプト。
Classroomお知らせ文生成プロンプト。
PDF / Markdown / Google Document構造生成プロンプト。
AIには、必ず以下を渡す。
タスク種別。
対象コース。
対象課題。
提出状況。
出力形式。
口調。
教師の追加指示。
禁止事項。
AIには、不要な個人情報を渡さない。
18. MVP要件
初期開発のMVPでは以下を実装する。
Googleログイン。
コース一覧取得。
課題一覧取得。
提出状況取得。
未提出者一覧表示。
未提出者向けClassroomリマインド文生成。
AI出力のGUI表示。
教師による編集。
Markdown出力。
PDF出力。
Classroomお知らせ投稿。
Google Document出力はMVP後半または次フェーズでも可とする。
19. 優先度
必須
Googleログイン。
コース一覧取得。
課題一覧取得。
提出状況取得。
AIアウトプットJSON形式。
未提出者抽出。
リマインド文生成。
教師承認フロー。
Classroom投稿前確認。
Markdown出力。
重要
PDF出力。
Google Document出力。
週次レポート生成。
ダッシュボード表示。
AI出力編集画面。
後回し
ルーブリック補助。
個別フィードバック文生成。
成績分析。
保護者連絡。
複数Classroom横断分析。
20. テスト要件
20.1 単体テスト
Classroom APIレスポンスのパース。
AI出力JSONのバリデーション。
未提出者抽出ロジック。
Markdown生成。
PDF生成。
Google Document構造生成。
Classroom投稿payload生成。
20.2 結合テスト
コース選択から課題取得まで。
課題取得から提出状況分析まで。
AI出力からGUI表示まで。
GUI編集からPDF出力まで。
GUI編集からClassroom投稿まで。
20.3 受け入れテスト
教師がログインできる。
対象コースを選べる。
課題提出状況を確認できる。
未提出者リマインド文を生成できる。
教師が文面を編集できる。
教師の承認後にClassroomへ投稿できる。
Markdownとして保存できる。
PDFとして保存できる。
21. 受け入れ基準
以下を満たした場合、MVP完了とする。
教師アカウントでログインできる。
Google Classroomのコース一覧を取得できる。
選択したコースの課題一覧を取得できる。
選択した課題の提出状況を取得できる。
未提出者を抽出できる。
AIがリマインド文をJSON形式で返せる。
GUIがAI出力JSONを表示できる。
教師がAI出力を編集できる。
教師の承認なしにClassroom投稿が行われない。
Markdown出力ができる。
PDF出力ができる。
Classroomのお知らせとしてリマインドを投稿できる。
22. 今後の拡張案
提出物の内容要約。
AIによるフィードバック案生成。
ルーブリック作成補助。
ルーブリックに基づく採点補助。
クラス全体の学習状況分析。
学期末レポート生成。
教師ごとの運用傾向分析。
複数コース横断ダッシュボード。
Google Calendarとの連携。
Google Formsとの連携。
23. 開発上の重要ポイント
本プロジェクトで最も重要なのは、AI班とGUI班のインターフェースを曖昧にしないことである。
AI班は、自然文だけでなく、必ず構造化JSONを返す。
GUI班は、そのJSONを画面表示、編集、出力、投稿に使う。
Classroomへ投稿する操作は、必ず教師の承認を必要とする。
AIは判断を補助するが、最終決定者は教師とする。
出力形式は、PDF、Markdown、Google Document、Classroomリマインドの4種類を想定する。
初期開発では、未提出者抽出とリマインド生成を中心に実装する。