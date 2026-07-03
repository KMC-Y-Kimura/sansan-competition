const agentOutput = {
  schemaVersion: "1.0.0",
  requestId: "req_20260703_001",
  generatedAt: "2026-07-03T13:00:00+09:00",
  agentTaskType: "REMINDER_GENERATION",
  status: "success",
  course: {
    courseId: "123456789",
    name: "数学I",
    section: "1年A組",
  },
  summary: {
    title: "未提出課題リマインド案",
    shortSummary: "数学Iの課題「二次関数プリント」に未提出者が12名います。",
    teacherActionRequired: true,
    recommendedAction:
      "未提出者に対してClassroomでリマインドを投稿してください。",
  },
  gui: {
    cards: [
      {
        cardId: "card_001",
        type: "metric",
        title: "未提出者数",
        value: "12",
        description: "課題「二次関数プリント」の未提出者数です。",
      },
      {
        cardId: "card_002",
        type: "metric",
        title: "期限まで",
        value: "2日",
        description: "締切は2026-07-05 23:59です。",
      },
      {
        cardId: "card_003",
        type: "metric",
        title: "遅延提出",
        value: "3",
        description: "提出済みですが締切後の提出です。",
      },
    ],
    tables: [
      {
        tableId: "table_001",
        title: "未提出者一覧",
        columns: [
          { key: "studentName", label: "生徒名" },
          { key: "status", label: "状態" },
          { key: "dueDate", label: "締切" },
        ],
        rows: [
          { studentName: "山田太郎", status: "未提出", dueDate: "2026-07-05" },
          { studentName: "佐藤花子", status: "未提出", dueDate: "2026-07-05" },
          { studentName: "鈴木一郎", status: "期限接近", dueDate: "2026-07-05" },
        ],
      },
    ],
    warnings: [
      {
        level: "medium",
        message: "生徒向け投稿には、個別の未提出者名を含めないでください。",
      },
      {
        level: "high",
        message: "Classroom投稿は教師の承認後にのみ実行してください。",
      },
    ],
    editableFields: [
      {
        fieldId: "reminder_title",
        label: "投稿タイトル",
        type: "text",
        value: "課題提出リマインド",
        required: true,
      },
      {
        fieldId: "reminder_body",
        label: "リマインド本文",
        type: "textarea",
        value:
          "課題「二次関数プリント」の提出期限が近づいています。まだ提出していない人は、7月5日までに提出してください。分からないところがある場合は、早めに相談してください。",
        required: true,
      },
    ],
  },
  outputs: {
    markdown: {
      fileName: "math1_submission_report_20260703.md",
      title: "数学I 提出状況レポート",
      content:
        "# 数学I 提出状況レポート\n\n## 概要\n課題「二次関数プリント」に未提出者が12名います。\n\n## 推奨アクション\nClassroomで全体向けのリマインドを投稿してください。",
    },
    pdf: {
      fileName: "math1_submission_report_20260703.pdf",
      title: "数学I 提出状況レポート",
      layout: "report",
      sections: [
        {
          heading: "概要",
          body: "数学Iの課題提出状況をまとめたレポートです。",
        },
      ],
    },
    googleDocument: null,
    classroomReminder: {
      target: {
        courseId: "123456789",
        courseWorkId: "987654321",
      },
      postType: "announcement",
      title: "課題提出リマインド",
      text:
        "課題「二次関数プリント」の提出期限が近づいています。まだ提出していない人は、7月5日までに提出してください。",
      materials: [],
      scheduledTime: null,
      assigneeMode: "ALL_STUDENTS",
      targetStudentIds: [],
      requiresTeacherApproval: true,
    },
  },
  approval: {
    required: true,
    reason: "Classroomへの投稿を行うため、教師の承認が必要です。",
    actions: [
      {
        actionId: "action_001",
        type: "CREATE_CLASSROOM_ANNOUNCEMENT",
        label: "Classroomにリマインドを投稿",
        requiresConfirmation: true,
        payloadRef: "outputs.classroomReminder",
      },
      {
        actionId: "action_002",
        type: "EXPORT_MARKDOWN",
        label: "Markdownとして保存",
        requiresConfirmation: false,
        payloadRef: "outputs.markdown",
      },
      {
        actionId: "action_003",
        type: "EXPORT_PDF",
        label: "PDFとして出力",
        requiresConfirmation: false,
        payloadRef: "outputs.pdf",
      },
    ],
  },
  errors: [],
};

const courses = [
  {
    courseId: "123456789",
    name: "数学I",
    section: "1年A組",
    studentCount: 36,
    updatedAt: "2026-07-03 12:20",
  },
  {
    courseId: "223456789",
    name: "情報I",
    section: "1年B組",
    studentCount: 34,
    updatedAt: "2026-07-02 16:40",
  },
];

const assignments = [
  {
    courseWorkId: "987654321",
    title: "二次関数プリント",
    dueDate: "2026-07-05",
    dueTime: "23:59",
    turnedIn: 21,
    missing: 12,
    late: 3,
    state: "PUBLISHED",
  },
  {
    courseWorkId: "887654321",
    title: "小テスト復習",
    dueDate: "2026-07-08",
    dueTime: "18:00",
    turnedIn: 29,
    missing: 7,
    late: 0,
    state: "PUBLISHED",
  },
];

const state = {
  isLoggedIn: false,
  view: "login",
  selectedCourseId: courses[0].courseId,
  selectedAssignmentId: assignments[0].courseWorkId,
  editableValues: Object.fromEntries(
    agentOutput.gui.editableFields.map((field) => [field.fieldId, field.value]),
  ),
  selectedOutputs: new Set(["classroom", "markdown"]),
  posted: false,
};

const app = document.querySelector("#app");

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function selectedCourse() {
  return courses.find((course) => course.courseId === state.selectedCourseId);
}

function selectedAssignment() {
  return assignments.find(
    (assignment) => assignment.courseWorkId === state.selectedAssignmentId,
  );
}

function render() {
  app.innerHTML = state.isLoggedIn ? renderShell() : renderLogin();
  bindEvents();
}

function renderLogin() {
  return `
    <main class="login">
      <section class="login-panel">
        <h1>Classroom運用支援</h1>
        <p class="subtle">Google Classroomの提出状況を確認し、AIの提案を教師が編集・承認してから投稿します。</p>
        <ul class="check-list">
          <li>読み取り権限と投稿権限を分けて扱う</li>
          <li>生徒向け投稿には未提出者名を含めない</li>
          <li>Classroom投稿は承認画面を必ず通す</li>
        </ul>
        <button class="button primary" data-action="login">Googleでログイン</button>
      </section>
    </main>
  `;
}

function renderShell() {
  return `
    <div class="layout">
      <aside class="sidebar">
        <div class="brand">
          <span class="brand-mark">C</span>
          <span>Classroom支援</span>
        </div>
        <nav class="nav" aria-label="主画面">
          ${navButton("courses", "コース", "コース選択")}
          ${navButton("dashboard", "概要", "ダッシュボード")}
          ${navButton("assignment", "課題", "課題詳細")}
          ${navButton("review", "AI", "出力確認")}
          ${navButton("exports", "出力", "出力選択")}
          ${navButton("confirm", "承認", "投稿確認")}
        </nav>
      </aside>
      <main class="main">
        <header class="topbar">
          <div>
            <h1>${pageTitle()}</h1>
            <div class="subtle">${escapeHtml(selectedCourse().name)} / ${escapeHtml(selectedCourse().section)}</div>
          </div>
          <button class="button" data-action="logout">ログアウト</button>
        </header>
        <div class="content">
          ${renderView()}
        </div>
      </main>
    </div>
  `;
}

function navButton(view, icon, label) {
  const active = state.view === view ? " active" : "";
  return `<button class="nav-button${active}" data-view="${view}"><span>${icon}</span><span>${label}</span></button>`;
}

function pageTitle() {
  const titles = {
    courses: "コース選択",
    dashboard: "ダッシュボード",
    assignment: "課題詳細",
    review: "AI出力確認",
    exports: "出力選択",
    confirm: "投稿確認",
  };
  return titles[state.view] ?? "コース選択";
}

function renderView() {
  const views = {
    courses: renderCourses,
    dashboard: renderDashboard,
    assignment: renderAssignment,
    review: renderReview,
    exports: renderExports,
    confirm: renderConfirm,
  };
  return (views[state.view] ?? renderCourses)();
}

function renderCourses() {
  return `
    <section class="band">
      <div class="section-heading">
        <h2>担当コース</h2>
        <span class="subtle">モックデータ</span>
      </div>
      <div class="grid cols-2">
        ${courses
          .map(
            (course) => `
              <article class="card">
                <h3>${escapeHtml(course.name)}</h3>
                <p class="subtle">${escapeHtml(course.section)} / ${course.studentCount}名 / 更新 ${escapeHtml(course.updatedAt)}</p>
                <div class="action-row" style="margin-top: 16px">
                  <button class="button primary" data-course="${course.courseId}">このコースを開く</button>
                </div>
              </article>
            `,
          )
          .join("")}
      </div>
    </section>
  `;
}

function renderDashboard() {
  const assignment = selectedAssignment();
  return `
    <section class="band">
      <div class="grid cols-3">
        ${metricCard("未提出課題", "2", "対応が必要な課題数")}
        ${metricCard("期限接近", "1", "3日以内に締切の課題")}
        ${metricCard("最近のお知らせ", "4", "直近7日間の投稿")}
      </div>
    </section>
    <section class="band">
      <div class="section-heading">
        <h2>最近の課題</h2>
        <button class="button" data-view="assignment">課題詳細へ</button>
      </div>
      ${renderAssignmentTable([assignment])}
    </section>
    <section class="card">
      <h3>AIによる注意点</h3>
      <p>${escapeHtml(agentOutput.summary.shortSummary)}</p>
      <p class="subtle">${escapeHtml(agentOutput.summary.recommendedAction)}</p>
    </section>
  `;
}

function metricCard(title, value, description) {
  return `
    <article class="card metric">
      <h3>${escapeHtml(title)}</h3>
      <div class="metric-value">${escapeHtml(value)}</div>
      <p class="subtle">${escapeHtml(description)}</p>
    </article>
  `;
}

function renderAssignment() {
  return `
    <section class="band">
      <div class="section-heading">
        <h2>課題一覧</h2>
        <button class="button primary" data-action="generate-reminder">リマインド文を生成</button>
      </div>
      ${renderAssignmentTable(assignments)}
    </section>
    <section class="band">
      <div class="section-heading">
        <h2>提出状況</h2>
        <span class="badge warning">未提出者を確認</span>
      </div>
      ${renderAgentTable(agentOutput.gui.tables[0])}
    </section>
  `;
}

function renderAssignmentTable(items) {
  return `
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>課題</th>
            <th>締切</th>
            <th>提出済み</th>
            <th>未提出</th>
            <th>遅延</th>
            <th>状態</th>
          </tr>
        </thead>
        <tbody>
          ${items
            .map(
              (item) => `
                <tr>
                  <td>${escapeHtml(item.title)}</td>
                  <td>${escapeHtml(item.dueDate)} ${escapeHtml(item.dueTime)}</td>
                  <td><span class="badge success">${item.turnedIn}</span></td>
                  <td><span class="badge danger">${item.missing}</span></td>
                  <td><span class="badge warning">${item.late}</span></td>
                  <td>${escapeHtml(item.state)}</td>
                </tr>
              `,
            )
            .join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderReview() {
  return `
    <section class="band">
      <div class="section-heading">
        <h2>${escapeHtml(agentOutput.summary.title)}</h2>
        <span class="badge">${escapeHtml(agentOutput.schemaVersion)}</span>
      </div>
      <div class="grid cols-3">
        ${agentOutput.gui.cards
          .map((card) => metricCard(card.title, card.value, card.description))
          .join("")}
      </div>
    </section>
    <section class="split">
      <div class="card">
        <h3>編集</h3>
        <div class="grid" style="margin-top: 14px">
          ${agentOutput.gui.editableFields.map(renderEditableField).join("")}
        </div>
      </div>
      <div class="card">
        <h3>警告</h3>
        <div class="warning-list" style="margin-top: 14px">
          ${agentOutput.gui.warnings
            .map(
              (warning) =>
                `<div class="warning-item">${escapeHtml(warning.message)}</div>`,
            )
            .join("")}
        </div>
      </div>
    </section>
    <section class="band">
      <div class="section-heading">
        <h2>${escapeHtml(agentOutput.gui.tables[0].title)}</h2>
      </div>
      ${renderAgentTable(agentOutput.gui.tables[0])}
    </section>
  `;
}

function renderEditableField(field) {
  const value = state.editableValues[field.fieldId] ?? "";
  if (field.type === "textarea") {
    return `
      <div class="field">
        <label for="${field.fieldId}">${escapeHtml(field.label)}</label>
        <textarea id="${field.fieldId}" data-field="${field.fieldId}" ${field.required ? "required" : ""}>${escapeHtml(value)}</textarea>
      </div>
    `;
  }
  return `
    <div class="field">
      <label for="${field.fieldId}">${escapeHtml(field.label)}</label>
      <input id="${field.fieldId}" data-field="${field.fieldId}" value="${escapeHtml(value)}" ${field.required ? "required" : ""} />
    </div>
  `;
}

function renderAgentTable(table) {
  return `
    <div class="table-wrap">
      <table>
        <thead>
          <tr>${table.columns.map((column) => `<th>${escapeHtml(column.label)}</th>`).join("")}</tr>
        </thead>
        <tbody>
          ${table.rows
            .map(
              (row) => `
                <tr>
                  ${table.columns
                    .map((column) => `<td>${escapeHtml(row[column.key] ?? "")}</td>`)
                    .join("")}
                </tr>
              `,
            )
            .join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderExports() {
  const options = [
    ["classroom", "Classroomリマインド", "承認後にお知らせとして投稿"],
    ["markdown", "Markdown", "議事録や共有用に保存"],
    ["pdf", "PDF", "会議資料や記録用に出力"],
  ];
  return `
    <section class="band">
      <div class="section-heading">
        <h2>出力形式</h2>
        <button class="button primary" data-view="confirm">確認へ進む</button>
      </div>
      <div class="grid cols-3">
        ${options
          .map(
            ([key, title, description]) => `
              <label class="card">
                <input type="checkbox" data-output="${key}" ${state.selectedOutputs.has(key) ? "checked" : ""} />
                <h3 style="margin-top: 12px">${title}</h3>
                <p class="subtle">${description}</p>
              </label>
            `,
          )
          .join("")}
      </div>
    </section>
    <section class="card">
      <h3>Markdownプレビュー</h3>
      <pre class="output-preview">${escapeHtml(agentOutput.outputs.markdown.content)}</pre>
    </section>
  `;
}

function renderConfirm() {
  const title = state.editableValues.reminder_title;
  const body = state.editableValues.reminder_body;
  return `
    <section class="band">
      <div class="section-heading">
        <h2>Classroom投稿前確認</h2>
        <span class="badge danger">教師承認が必要</span>
      </div>
      <div class="grid cols-2">
        <article class="card">
          <h3>投稿先</h3>
          <p>${escapeHtml(selectedCourse().name)} / ${escapeHtml(selectedCourse().section)}</p>
          <p class="subtle">課題: ${escapeHtml(selectedAssignment().title)}</p>
        </article>
        <article class="card">
          <h3>公開範囲</h3>
          <p>コース全体</p>
          <p class="subtle">個別生徒名は投稿本文に含めない設定です。</p>
        </article>
      </div>
    </section>
    <section class="card">
      <h3>${escapeHtml(title)}</h3>
      <p>${escapeHtml(body)}</p>
    </section>
    <section class="warning-list">
      <div class="warning-item">${escapeHtml(agentOutput.approval.reason)}</div>
    </section>
    <section class="action-row">
      <button class="button primary" data-action="approve-post" ${state.posted ? "disabled" : ""}>投稿する</button>
      <button class="button" data-view="review">文面を修正</button>
      ${state.posted ? '<span class="badge success">投稿済みとして記録しました</span>' : ""}
    </section>
  `;
}

function bindEvents() {
  document.querySelectorAll("[data-action='login']").forEach((button) => {
    button.addEventListener("click", () => {
      state.isLoggedIn = true;
      state.view = "courses";
      render();
    });
  });

  document.querySelectorAll("[data-action='logout']").forEach((button) => {
    button.addEventListener("click", () => {
      state.isLoggedIn = false;
      state.view = "login";
      render();
    });
  });

  document.querySelectorAll("[data-view]").forEach((button) => {
    button.addEventListener("click", () => {
      state.view = button.dataset.view;
      render();
    });
  });

  document.querySelectorAll("[data-course]").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedCourseId = button.dataset.course;
      state.view = "dashboard";
      render();
    });
  });

  document.querySelectorAll("[data-action='generate-reminder']").forEach((button) => {
    button.addEventListener("click", () => {
      state.view = "review";
      render();
    });
  });

  document.querySelectorAll("[data-field]").forEach((field) => {
    field.addEventListener("input", () => {
      state.editableValues[field.dataset.field] = field.value;
    });
  });

  document.querySelectorAll("[data-output]").forEach((checkbox) => {
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) {
        state.selectedOutputs.add(checkbox.dataset.output);
      } else {
        state.selectedOutputs.delete(checkbox.dataset.output);
      }
    });
  });

  document.querySelectorAll("[data-action='approve-post']").forEach((button) => {
    button.addEventListener("click", () => {
      state.posted = true;
      render();
    });
  });
}

render();
