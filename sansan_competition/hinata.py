from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from .contracts import (
    AgentError,
    AgentOutput,
    Approval,
    ApprovalAction,
    ClassroomReminder,
    Course,
    CourseWork,
    EditableField,
    GuiCard,
    GuiTable,
    GuiTableColumn,
    GuiWarning,
    GoogleDocumentOutput,
    MarkdownOutput,
    PdfOutput,
    Summary,
    StudentSubmission,
    count_states,
    normalize_due_datetime,
    now_jst_iso,
)

TASK_PROMPTS: dict[str, dict[str, str]] = {
    "COURSE_SUMMARY": {
        "purpose": "コース全体の状況を教師向けに要約する。",
        "constraints": "事実と推測を分け、提出状況の数値は必ずデータに基づいて書く。",
    },
    "COURSEWORK_SUMMARY": {
        "purpose": "課題情報を整理し、締切や配布物を見やすくする。",
        "constraints": "締切・満点・公開状態・添付物を過不足なく整理する。",
    },
    "SUBMISSION_ANALYSIS": {
        "purpose": "提出状況を分類し、未提出や遅延提出を可視化する。",
        "constraints": "未提出者一覧は教師向けにのみ出し、生徒向け文面には他者情報を入れない。",
    },
    "REMINDER_GENERATION": {
        "purpose": "未提出者向けのリマインド文を作成する。",
        "constraints": "教師がそのまま編集できるよう本文とメタデータを分離する。",
    },
    "WEEKLY_REPORT": {
        "purpose": "週次の授業運用レポートを生成する。",
        "constraints": "複数課題の傾向を集約し、次に行うべき行動を明記する。",
    },
    "ANNOUNCEMENT_DRAFT": {
        "purpose": "Classroom向けのお知らせ案を作成する。",
        "constraints": "投稿前提の口調にしつつ、教師が最終調整できるようにする。",
    },
    "DOCUMENT_EXPORT": {
        "purpose": "Markdown、PDF、Google Document 用の構造化データを返す。",
        "constraints": "実ファイルは出さず、見出し・表・箇条書きの構造を返す。",
    },
    "RUBRIC_SUPPORT": {
        "purpose": "ルーブリックの補助案を作成する。",
        "constraints": "採点の確定はしない。ルーブリック案・不足点・確認観点を返す。",
    },
    "ERROR_ANALYSIS": {
        "purpose": "API エラーや取得失敗の要因を教師向けに説明する。",
        "constraints": "内部情報を出しすぎず、再試行条件と次の手順を整理する。",
    },
}


@dataclass(frozen=True, slots=True)
class PromptBundle:
    task_type: str
    system: str
    user: str
    constraints: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "taskType": self.task_type,
            "system": self.system,
            "user": self.user,
            "constraints": list(self.constraints),
        }


def build_prompt_bundle(
    *,
    task_type: str,
    course: Course,
    coursework: CourseWork | None = None,
    submissions: Sequence[StudentSubmission] | None = None,
    tone: str = "polite",
    teacher_instruction: str = "",
    extra_notes: str = "",
) -> PromptBundle:
    prompts = TASK_PROMPTS.get(task_type, TASK_PROMPTS["ERROR_ANALYSIS"])
    coursework_title = coursework.title if coursework is not None else "未指定"
    submission_count = len(submissions) if submissions is not None else 0
    user_lines = [
        f"コース: {course.name}",
        f"課題: {coursework_title}",
        f"提出件数: {submission_count}",
        f"口調: {tone}",
    ]
    if teacher_instruction.strip():
        user_lines.append(f"教師の追加指示: {teacher_instruction.strip()}")
    if extra_notes.strip():
        user_lines.append(f"補足: {extra_notes.strip()}")
    return PromptBundle(
        task_type=task_type,
        system=(
            "あなたは Google Classroom 運用支援 AI の hinata です。"
            "自然文だけで返さず、構造化 JSON のための文面を作ってください。"
            "個人情報は必要最小限にし、事実と推測を分けてください。"
        ),
        user="\n".join(user_lines),
        constraints=[prompts["purpose"], prompts["constraints"]],
    )


def build_agent_output(
    task_type: str,
    *,
    request_id: str,
    course: Course,
    coursework: CourseWork | None = None,
    submissions: Sequence[StudentSubmission] | None = None,
    tone: str = "polite",
    teacher_instruction: str = "",
    extra_notes: str = "",
    **kwargs: Any,
) -> AgentOutput:
    if task_type == "COURSE_SUMMARY":
        if coursework is None or submissions is None:
            return build_error_analysis_output(
                request_id=request_id,
                course=course,
                title="入力不足のためコース要約を生成できませんでした",
                short_summary="COURSE_SUMMARY に必要な課題情報または提出情報が不足しています。",
                recommended_action="coursework と submissions を渡して再実行してください。",
                error_code="INVALID_AGENT_OUTPUT",
                error_message="COURSE_SUMMARY requires coursework and submissions.",
            )
        return build_course_summary_output(
            request_id=request_id,
            course=course,
            coursework=coursework,
            submissions=list(submissions),
        )
    if task_type == "COURSEWORK_SUMMARY":
        if coursework is None:
            return build_error_analysis_output(
                request_id=request_id,
                course=course,
                title="入力不足のため課題要約を生成できませんでした",
                short_summary="COURSEWORK_SUMMARY に必要な課題情報が不足しています。",
                recommended_action="coursework を渡して再実行してください。",
                error_code="INVALID_AGENT_OUTPUT",
                error_message="COURSEWORK_SUMMARY requires coursework.",
            )
        return build_coursework_summary_output(
            request_id=request_id,
            course=course,
            coursework=coursework,
        )
    if task_type == "SUBMISSION_ANALYSIS":
        if coursework is None or submissions is None:
            return build_error_analysis_output(
                request_id=request_id,
                course=course,
                title="入力不足のため提出分析を生成できませんでした",
                short_summary="SUBMISSION_ANALYSIS に必要な入力が不足しています。",
                recommended_action="coursework と submissions を渡して再実行してください。",
                error_code="INVALID_AGENT_OUTPUT",
                error_message="SUBMISSION_ANALYSIS requires coursework and submissions.",
            )
        return build_submission_analysis_output(
            request_id=request_id,
            course=course,
            coursework=coursework,
            submissions=list(submissions),
        )
    if task_type == "REMINDER_GENERATION":
        if coursework is None or submissions is None:
            return build_error_analysis_output(
                request_id=request_id,
                course=course,
                title="入力不足のためリマインドを生成できませんでした",
                short_summary="REMINDER_GENERATION に必要な入力が不足しています。",
                recommended_action="coursework と submissions を渡して再実行してください。",
                error_code="INVALID_AGENT_OUTPUT",
                error_message="REMINDER_GENERATION requires coursework and submissions.",
            )
        return build_reminder_generation_output(
            request_id=request_id,
            course=course,
            coursework=coursework,
            submissions=list(submissions),
            tone=tone,
            teacher_instruction=teacher_instruction,
        )
    if task_type == "WEEKLY_REPORT":
        if coursework is None or submissions is None:
            return build_error_analysis_output(
                request_id=request_id,
                course=course,
                title="入力不足のため週次レポートを生成できませんでした",
                short_summary="WEEKLY_REPORT に必要な入力が不足しています。",
                recommended_action="coursework と submissions を渡して再実行してください。",
                error_code="INVALID_AGENT_OUTPUT",
                error_message="WEEKLY_REPORT requires coursework and submissions.",
            )
        return build_weekly_report_output(
            request_id=request_id,
            course=course,
            courseworks=[coursework],
            submissions_by_coursework={coursework.course_work_id: list(submissions)},
            tone=tone,
            teacher_instruction=teacher_instruction,
        )
    if task_type == "ANNOUNCEMENT_DRAFT":
        return build_announcement_draft_output(
            request_id=request_id,
            course=course,
            coursework=coursework,
            tone=tone,
            teacher_instruction=teacher_instruction,
            extra_notes=extra_notes,
        )
    if task_type == "DOCUMENT_EXPORT":
        if coursework is None or submissions is None:
            return build_error_analysis_output(
                request_id=request_id,
                course=course,
                title="入力不足のため文書出力を生成できませんでした",
                short_summary="DOCUMENT_EXPORT に必要な入力が不足しています。",
                recommended_action="coursework と submissions を渡して再実行してください。",
                error_code="INVALID_AGENT_OUTPUT",
                error_message="DOCUMENT_EXPORT requires coursework and submissions.",
            )
        return build_document_export_output(
            request_id=request_id,
            course=course,
            coursework=coursework,
            submissions=list(submissions),
        )
    if task_type == "RUBRIC_SUPPORT":
        return build_rubric_support_output(
            request_id=request_id,
            course=course,
            coursework=coursework,
            extra_notes=extra_notes,
        )
    if task_type == "ERROR_ANALYSIS":
        return build_error_analysis_output(
            request_id=request_id,
            course=course,
            title=str(kwargs.get("title", "エラーの解析")),
            short_summary=str(
                kwargs.get(
                    "short_summary",
                    "取得失敗や API エラーの説明を生成しました。",
                )
            ),
            recommended_action=str(kwargs.get("recommended_action", "内容を確認して再実行してください。")),
            error_code=str(kwargs.get("error_code", "AI_GENERATION_FAILED")),
            error_message=str(kwargs.get("error_message", "AI output could not be generated.")),
            recoverable=bool(kwargs.get("recoverable", True)),
        )
    return build_error_analysis_output(
        request_id=request_id,
        course=course,
        title="未対応のタスク種別です",
        short_summary=f"{task_type} は hinata 側で未対応です。",
        recommended_action="ROLE.md と REQUIREMENTS.md を確認して実装を追加してください。",
        error_code="INVALID_AGENT_OUTPUT",
        error_message=f"Unsupported task_type: {task_type}",
        recoverable=False,
    )


def build_course_summary_output(
    *,
    request_id: str,
    course: Course,
    coursework: CourseWork,
    submissions: list[StudentSubmission],
) -> AgentOutput:
    counts = count_states(submissions)
    summary = Summary(
        title="課題概要の整理",
        short_summary=(
            f"{course.name} の課題「{coursework.title}」について、"
            f"提出済み {counts['submitted']} 件、未提出 {counts['missing']} 件です。"
        ),
        teacher_action_required=counts["missing"] > 0,
        recommended_action=(
            "未提出者へのリマインドを検討してください。"
            if counts["missing"] > 0
            else "提出状況は安定しています。"
        ),
    )
    gui = {
        "cards": [
            GuiCard(
                card_id="card_submitted",
                type="metric",
                title="提出済み",
                value=str(counts["submitted"]),
                description="提出済みの件数です。",
            ).to_dict(),
            GuiCard(
                card_id="card_missing",
                type="metric",
                title="未提出",
                value=str(counts["missing"]),
                description="未提出の件数です。",
            ).to_dict(),
            GuiCard(
                card_id="card_coursework",
                type="metric",
                title="課題名",
                value=coursework.title,
                description="対象課題です。",
            ).to_dict(),
        ],
        "tables": [],
        "warnings": [],
        "editableFields": [],
    }
    outputs = _build_output_bundle(
        course=course,
        coursework=coursework,
        submissions=submissions,
        counts=counts,
    )
    approval = Approval(
        required=False,
        reason="コース概要の整理のみで、Classroomへの投稿は含みません。",
        actions=[
            ApprovalAction(
                action_id="action_export_markdown",
                type="EXPORT_MARKDOWN",
                label="Markdownとして出力",
                requires_confirmation=False,
                payload_ref="outputs.markdown",
            ),
            ApprovalAction(
                action_id="action_export_pdf",
                type="EXPORT_PDF",
                label="PDFとして出力",
                requires_confirmation=False,
                payload_ref="outputs.pdf",
            ),
        ],
    )
    return _finish_output(
        request_id=request_id,
        task_type="COURSE_SUMMARY",
        course=course,
        summary=summary,
        gui=gui,
        outputs=outputs,
        approval=approval,
    )


def build_coursework_summary_output(
    *,
    request_id: str,
    course: Course,
    coursework: CourseWork,
) -> AgentOutput:
    summary = Summary(
        title="課題情報の整理",
        short_summary=(
            f"{course.name} の課題「{coursework.title}」を整理しました。"
            f"締切は {normalize_due_datetime(coursework.due_date, coursework.due_time)} です。"
        ),
        teacher_action_required=False,
        recommended_action="必要に応じて課題説明や添付資料を確認してください。",
    )
    gui = {
        "cards": [
            GuiCard(
                card_id="card_title",
                type="metric",
                title="課題名",
                value=coursework.title,
                description="対象課題です。",
            ).to_dict(),
            GuiCard(
                card_id="card_due",
                type="metric",
                title="締切",
                value=normalize_due_datetime(coursework.due_date, coursework.due_time),
                description="提出締切です。",
            ).to_dict(),
            GuiCard(
                card_id="card_points",
                type="metric",
                title="満点",
                value="" if coursework.max_points is None else str(coursework.max_points),
                description="課題の満点です。",
            ).to_dict(),
        ],
        "tables": [
            GuiTable(
                table_id="table_coursework",
                title="課題の詳細",
                columns=[
                    GuiTableColumn(key="key", label="項目"),
                    GuiTableColumn(key="value", label="値"),
                ],
                rows=[
                    {"key": "説明", "value": coursework.description or "なし"},
                    {"key": "公開状態", "value": coursework.state or "不明"},
                    {"key": "教材数", "value": str(len(coursework.materials))},
                    {"key": "トピック", "value": coursework.topic_id or "なし"},
                ],
            ).to_dict()
        ],
        "warnings": [],
        "editableFields": [],
    }
    outputs = _build_output_bundle(
        course=course,
        coursework=coursework,
        submissions=[],
        counts={"submitted": 0, "missing": 0, "late": 0},
        include_submission_table=False,
        include_reminder=False,
    )
    return _finish_output(
        request_id=request_id,
        task_type="COURSEWORK_SUMMARY",
        course=course,
        summary=summary,
        gui=gui,
        outputs=outputs,
        approval=Approval(required=False, reason="課題整理のみで投稿は不要です。", actions=[]),
    )


def build_submission_analysis_output(
    *,
    request_id: str,
    course: Course,
    coursework: CourseWork,
    submissions: list[StudentSubmission],
) -> AgentOutput:
    counts = count_states(submissions)
    missing_students = _missing_students(submissions)
    summary = Summary(
        title="提出状況分析",
        short_summary=(
            f"{course.name} の課題「{coursework.title}」では、"
            f"提出済み {counts['submitted']} 件、未提出 {counts['missing']} 件、遅延提出 {counts['late']} 件です。"
        ),
        teacher_action_required=counts["missing"] > 0,
        recommended_action=(
            "未提出者の確認とリマインド対象の選定を行ってください。"
            if counts["missing"] > 0
            else "提出状況は安定しています。"
        ),
    )
    gui = {
        "cards": [
            GuiCard(
                card_id="card_submitted",
                type="metric",
                title="提出済み",
                value=str(counts["submitted"]),
                description="提出済み件数です。",
            ).to_dict(),
            GuiCard(
                card_id="card_missing",
                type="metric",
                title="未提出",
                value=str(counts["missing"]),
                description="未提出件数です。",
            ).to_dict(),
            GuiCard(
                card_id="card_late",
                type="metric",
                title="遅延提出",
                value=str(counts["late"]),
                description="遅延提出件数です。",
            ).to_dict(),
        ],
        "tables": [
            GuiTable(
                table_id="table_submission_analysis",
                title="未提出者一覧",
                columns=[
                    GuiTableColumn(key="studentName", label="生徒名"),
                    GuiTableColumn(key="status", label="状態"),
                    GuiTableColumn(key="late", label="遅延"),
                ],
                rows=[
                    {
                        "studentName": submission.student_name,
                        "status": "未提出" if not submission.late else "遅延提出",
                        "late": "はい" if submission.late else "いいえ",
                    }
                    for submission in missing_students
                ],
            ).to_dict()
        ],
        "warnings": [
            GuiWarning(
                level="medium",
                message="個別の生徒名を含むため、共有範囲に注意してください。",
            ).to_dict()
        ]
        if missing_students
        else [],
        "editableFields": [],
    }
    outputs = _build_output_bundle(
        course=course,
        coursework=coursework,
        submissions=submissions,
        counts=counts,
    )
    return _finish_output(
        request_id=request_id,
        task_type="SUBMISSION_ANALYSIS",
        course=course,
        summary=summary,
        gui=gui,
        outputs=outputs,
        approval=Approval(required=False, reason="分析のみで投稿は不要です。", actions=[]),
    )


def build_reminder_generation_output(
    *,
    request_id: str,
    course: Course,
    coursework: CourseWork,
    submissions: list[StudentSubmission],
    tone: str = "polite",
    teacher_instruction: str = "",
) -> AgentOutput:
    counts = count_states(submissions)
    missing_students = _missing_students(submissions)
    due = normalize_due_datetime(coursework.due_date, coursework.due_time)
    reminder_text = _build_reminder_text(
        course_name=course.name,
        coursework_title=coursework.title,
        missing_count=counts["missing"],
        due=due,
        tone=tone,
        teacher_instruction=teacher_instruction,
    )
    summary = Summary(
        title="未提出課題リマインド案",
        short_summary=(
            f"{course.name} の課題「{coursework.title}」に未提出者が {counts['missing']} 名います。"
        ),
        teacher_action_required=True,
        recommended_action="内容を確認し、必要に応じてClassroomへ投稿してください。",
    )
    gui = {
        "cards": [
            GuiCard(
                card_id="card_missing",
                type="metric",
                title="未提出者数",
                value=str(counts["missing"]),
                description=f"課題「{coursework.title}」の未提出者数です。",
            ).to_dict(),
            GuiCard(
                card_id="card_late",
                type="metric",
                title="遅延提出",
                value=str(counts["late"]),
                description="遅延提出として扱われる件数です。",
            ).to_dict(),
        ],
        "tables": [
            GuiTable(
                table_id="table_missing_students",
                title="未提出者一覧",
                columns=[
                    GuiTableColumn(key="studentName", label="生徒名"),
                    GuiTableColumn(key="status", label="状態"),
                    GuiTableColumn(key="dueDate", label="締切"),
                ],
                rows=[
                    {
                        "studentName": submission.student_name,
                        "status": "未提出" if not submission.late else "遅延提出",
                        "dueDate": coursework.due_date,
                    }
                    for submission in missing_students
                ],
            ).to_dict()
        ],
        "warnings": [
            GuiWarning(
                level="medium",
                message="個別の生徒名を含むため、共有範囲に注意してください。",
            ).to_dict()
        ]
        if missing_students
        else [],
        "editableFields": [
            EditableField(
                field_id="reminder_body",
                label="リマインド本文",
                type="textarea",
                value=reminder_text,
                required=True,
            ).to_dict()
        ],
    }
    outputs = _build_output_bundle(
        course=course,
        coursework=coursework,
        submissions=submissions,
        counts=counts,
        reminder_text=reminder_text,
    )
    approval = Approval(
        required=True,
        reason="Classroomへの投稿を行うため、教師の承認が必要です。",
        actions=[
            ApprovalAction(
                action_id="action_create_announcement",
                type="CREATE_CLASSROOM_ANNOUNCEMENT",
                label="Classroomにリマインドを投稿",
                requires_confirmation=True,
                payload_ref="outputs.classroomReminder",
            ),
            ApprovalAction(
                action_id="action_export_markdown",
                type="EXPORT_MARKDOWN",
                label="Markdownとして出力",
                requires_confirmation=False,
                payload_ref="outputs.markdown",
            ),
            ApprovalAction(
                action_id="action_export_pdf",
                type="EXPORT_PDF",
                label="PDFとして出力",
                requires_confirmation=False,
                payload_ref="outputs.pdf",
            ),
        ],
    )
    return _finish_output(
        request_id=request_id,
        task_type="REMINDER_GENERATION",
        course=course,
        summary=summary,
        gui=gui,
        outputs=outputs,
        approval=approval,
    )


def build_weekly_report_output(
    *,
    request_id: str,
    course: Course,
    courseworks: Sequence[CourseWork],
    submissions_by_coursework: dict[str, Sequence[StudentSubmission]],
    tone: str = "polite",
    teacher_instruction: str = "",
) -> AgentOutput:
    totals = {"submitted": 0, "missing": 0, "late": 0}
    coursework_rows: list[dict[str, Any]] = []
    for coursework in courseworks:
        submissions = list(submissions_by_coursework.get(coursework.course_work_id, []))
        counts = count_states(submissions)
        for key in totals:
            totals[key] += counts[key]
        coursework_rows.append(
            {
                "courseWorkTitle": coursework.title,
                "submitted": counts["submitted"],
                "missing": counts["missing"],
                "late": counts["late"],
            }
        )
    summary = Summary(
        title="週次レポート",
        short_summary=(
            f"{course.name} の週次レポートです。"
            f"提出済み {totals['submitted']} 件、未提出 {totals['missing']} 件です。"
        ),
        teacher_action_required=totals["missing"] > 0,
        recommended_action="未提出の多い課題を優先してリマインドしてください。",
    )
    gui = {
        "cards": [
            GuiCard(
                card_id="card_weekly_submitted",
                type="metric",
                title="提出済み合計",
                value=str(totals["submitted"]),
                description="週次の提出済み件数です。",
            ).to_dict(),
            GuiCard(
                card_id="card_weekly_missing",
                type="metric",
                title="未提出合計",
                value=str(totals["missing"]),
                description="週次の未提出件数です。",
            ).to_dict(),
        ],
        "tables": [
            GuiTable(
                table_id="table_weekly_report",
                title="課題別集計",
                columns=[
                    GuiTableColumn(key="courseWorkTitle", label="課題"),
                    GuiTableColumn(key="submitted", label="提出済み"),
                    GuiTableColumn(key="missing", label="未提出"),
                    GuiTableColumn(key="late", label="遅延提出"),
                ],
                rows=coursework_rows,
            ).to_dict()
        ],
        "warnings": [],
        "editableFields": [],
    }
    outputs = _build_output_bundle(
        course=course,
        coursework=courseworks[0] if courseworks else None,
        submissions=[
            submission
            for coursework in courseworks
            for submission in submissions_by_coursework.get(coursework.course_work_id, [])
        ],
        counts=totals,
        reminder_text=None,
        report_title=f"{course.name} 週次レポート",
        report_intro=teacher_instruction or "週次の提出状況をまとめたレポートです。",
        include_classroom_reminder=False,
        include_submission_table=False,
    )
    return _finish_output(
        request_id=request_id,
        task_type="WEEKLY_REPORT",
        course=course,
        summary=summary,
        gui=gui,
        outputs=outputs,
        approval=Approval(required=False, reason="週次レポートの生成のみです。", actions=[]),
    )


def build_announcement_draft_output(
    *,
    request_id: str,
    course: Course,
    coursework: CourseWork | None = None,
    tone: str = "polite",
    teacher_instruction: str = "",
    extra_notes: str = "",
) -> AgentOutput:
    title = coursework.title if coursework is not None else "Classroom お知らせ"
    announcement_text = _build_announcement_text(
        course_name=course.name,
        title=title,
        tone=tone,
        teacher_instruction=teacher_instruction,
        extra_notes=extra_notes,
    )
    summary = Summary(
        title="Classroomお知らせ案",
        short_summary=f"{course.name} 向けの Classroom お知らせ案を作成しました。",
        teacher_action_required=True,
        recommended_action="内容を確認し、必要なら編集してから投稿してください。",
    )
    gui = {
        "cards": [
            GuiCard(
                card_id="card_announcement_title",
                type="metric",
                title="件名",
                value=title,
                description="お知らせの件名です。",
            ).to_dict(),
        ],
        "tables": [],
        "warnings": [],
        "editableFields": [
            EditableField(
                field_id="announcement_body",
                label="お知らせ本文",
                type="textarea",
                value=announcement_text,
                required=True,
            ).to_dict(),
        ],
    }
    outputs = {
        "markdown": MarkdownOutput(
            file_name="announcement.md",
            title=title,
            content=f"# {title}\n\n{announcement_text}\n",
        ).to_dict(),
        "pdf": None,
        "googleDocument": None,
        "classroomReminder": ClassroomReminder(
            target={"courseId": course.course_id, "courseWorkId": coursework.course_work_id if coursework else None},
            post_type="announcement",
            title=title,
            text=announcement_text,
            requires_teacher_approval=False,
        ).to_dict(),
    }
    approval = Approval(
        required=False,
        reason="お知らせ案の生成のみで、投稿は教師確認後に別操作で行います。",
        actions=[
            ApprovalAction(
                action_id="action_copy_text",
                type="COPY_ANNOUNCEMENT_TEXT",
                label="本文をコピー",
                requires_confirmation=False,
                payload_ref="outputs.markdown",
            ),
        ],
    )
    return _finish_output(
        request_id=request_id,
        task_type="ANNOUNCEMENT_DRAFT",
        course=course,
        summary=summary,
        gui=gui,
        outputs=outputs,
        approval=approval,
    )


def build_document_export_output(
    *,
    request_id: str,
    course: Course,
    coursework: CourseWork,
    submissions: list[StudentSubmission],
) -> AgentOutput:
    counts = count_states(submissions)
    summary = Summary(
        title="文書出力用データ",
        short_summary=(
            f"{course.name} の課題「{coursework.title}」について、"
            "Markdown / PDF / Google Document 用の構造化データを生成しました。"
        ),
        teacher_action_required=False,
        recommended_action="必要な出力形式を選んで利用してください。",
    )
    gui = {
        "cards": [
            GuiCard(
                card_id="card_export_formats",
                type="metric",
                title="出力形式",
                value="Markdown / PDF / Google Document",
                description="出力可能な形式です。",
            ).to_dict(),
        ],
        "tables": [],
        "warnings": [],
        "editableFields": [],
    }
    outputs = _build_output_bundle(
        course=course,
        coursework=coursework,
        submissions=submissions,
        counts=counts,
        include_classroom_reminder=False,
    )
    return _finish_output(
        request_id=request_id,
        task_type="DOCUMENT_EXPORT",
        course=course,
        summary=summary,
        gui=gui,
        outputs=outputs,
        approval=Approval(required=False, reason="文書出力のみで投稿は不要です。", actions=[]),
    )


def build_rubric_support_output(
    *,
    request_id: str,
    course: Course,
    coursework: CourseWork | None = None,
    extra_notes: str = "",
) -> AgentOutput:
    title = coursework.title if coursework is not None else "ルーブリック補助"
    summary = Summary(
        title="ルーブリック補助案",
        short_summary=f"{course.name} 向けのルーブリック補助案を作成しました。",
        teacher_action_required=True,
        recommended_action="ルーブリックの観点と配点を確認してください。",
    )
    gui = {
        "cards": [
            GuiCard(
                card_id="card_rubric_title",
                type="metric",
                title="対象",
                value=title,
                description="ルーブリック補助の対象です。",
            ).to_dict(),
        ],
        "tables": [
            GuiTable(
                table_id="table_rubric_support",
                title="確認観点",
                columns=[
                    GuiTableColumn(key="item", label="項目"),
                    GuiTableColumn(key="note", label="メモ"),
                ],
                rows=[
                    {"item": "観点の明確さ", "note": "評価基準が曖昧でないか"},
                    {"item": "配点合計", "note": "満点と配点の整合性を確認"},
                    {"item": "コメント方針", "note": "教師の手直しを前提にする"},
                ],
            ).to_dict()
        ],
        "warnings": [
            GuiWarning(
                level="low",
                message="ルーブリックの自動確定は行いません。",
            ).to_dict()
        ],
        "editableFields": [
            EditableField(
                field_id="rubric_notes",
                label="補足メモ",
                type="textarea",
                value=extra_notes or "必要に応じて教師が配点と観点を調整してください。",
                required=False,
            ).to_dict()
        ],
    }
    outputs = {
        "markdown": MarkdownOutput(
            file_name="rubric_support.md",
            title=title,
            content="\n".join(
                [
                    f"# {title}",
                    "",
                    "## 確認観点",
                    "- 観点の明確さ",
                    "- 配点合計",
                    "- コメント方針",
                ]
            ),
        ).to_dict(),
        "pdf": None,
        "googleDocument": None,
        "classroomReminder": None,
    }
    return _finish_output(
        request_id=request_id,
        task_type="RUBRIC_SUPPORT",
        course=course,
        summary=summary,
        gui=gui,
        outputs=outputs,
        approval=Approval(required=False, reason="補助案の提示のみです。", actions=[]),
    )


def build_error_analysis_output(
    *,
    request_id: str,
    course: Course,
    task_type: str = "ERROR_ANALYSIS",
    title: str,
    short_summary: str,
    recommended_action: str,
    error_code: str,
    error_message: str,
    recoverable: bool = True,
) -> AgentOutput:
    return _finish_output(
        request_id=request_id,
        task_type=task_type,
        course=course,
        summary=Summary(
            title=title,
            short_summary=short_summary,
            teacher_action_required=True,
            recommended_action=recommended_action,
        ),
        gui={
            "cards": [
                GuiCard(
                    card_id="card_error",
                    type="metric",
                    title="エラーコード",
                    value=error_code,
                    description="取得失敗や生成失敗の識別子です。",
                ).to_dict()
            ],
            "tables": [],
            "warnings": [
                GuiWarning(
                    level="high" if not recoverable else "medium",
                    message=error_message,
                ).to_dict()
            ],
            "editableFields": [],
        },
        outputs={
            "markdown": None,
            "pdf": None,
            "googleDocument": None,
            "classroomReminder": None,
        },
        approval=Approval(required=False, reason="エラー解析のみです。", actions=[]),
        errors=[AgentError(code=error_code, message=error_message, recoverable=recoverable)],
    )


def build_error_output(
    *,
    request_id: str,
    task_type: str,
    title: str,
    short_summary: str,
    recommended_action: str,
    error_code: str,
    error_message: str,
    recoverable: bool,
) -> AgentOutput:
    return build_error_analysis_output(
        request_id=request_id,
        course=Course(course_id="", name=""),
        task_type=task_type,
        title=title,
        short_summary=short_summary,
        recommended_action=recommended_action,
        error_code=error_code,
        error_message=error_message,
        recoverable=recoverable,
    )


def _finish_output(
    *,
    request_id: str,
    task_type: str,
    course: Course,
    summary: Summary,
    gui: dict[str, Any] | None,
    outputs: dict[str, Any] | None,
    approval: Approval,
    errors: list[AgentError] | None = None,
) -> AgentOutput:
    return AgentOutput(
        request_id=request_id,
        generated_at=now_jst_iso(),
        agent_task_type=task_type,  # type: ignore[arg-type]
        status="error" if errors else "success",
        course=course,
        summary=summary,
        gui=gui,
        outputs=outputs,
        approval=approval,
        errors=errors or [],
    )


def _build_output_bundle(
    *,
    course: Course,
    coursework: CourseWork | None,
    submissions: list[StudentSubmission],
    counts: dict[str, int],
    reminder_text: str | None = None,
    report_title: str | None = None,
    report_intro: str | None = None,
    include_classroom_reminder: bool = True,
    include_submission_table: bool = True,
    include_reminder: bool = True,
) -> dict[str, Any]:
    markdown = _build_markdown_output(
        course=course,
        coursework=coursework,
        submissions=submissions,
        counts=counts,
        reminder_text=reminder_text if include_reminder else None,
        report_title=report_title,
        report_intro=report_intro,
        include_submission_table=include_submission_table,
    )
    pdf = _build_pdf_output(
        course=course,
        coursework=coursework,
        submissions=submissions,
        counts=counts,
        reminder_text=reminder_text if include_reminder else None,
        report_title=report_title,
        report_intro=report_intro,
        include_submission_table=include_submission_table,
    )
    google_document = _build_google_document_output(
        course=course,
        coursework=coursework,
        submissions=submissions,
        counts=counts,
        reminder_text=reminder_text if include_reminder else None,
        report_title=report_title,
        report_intro=report_intro,
        include_submission_table=include_submission_table,
    )
    classroom_reminder = None
    if include_classroom_reminder and coursework is not None and reminder_text is not None:
        classroom_reminder = ClassroomReminder(
            target={"courseId": course.course_id, "courseWorkId": coursework.course_work_id},
            post_type="announcement",
            title="課題提出リマインド",
            text=reminder_text,
        ).to_dict()
    return {
        "markdown": markdown.to_dict() if markdown is not None else None,
        "pdf": pdf.to_dict() if pdf is not None else None,
        "googleDocument": google_document.to_dict() if google_document is not None else None,
        "classroomReminder": classroom_reminder,
    }


def _build_markdown_output(
    *,
    course: Course,
    coursework: CourseWork | None,
    submissions: list[StudentSubmission],
    counts: dict[str, int],
    reminder_text: str | None = None,
    report_title: str | None = None,
    report_intro: str | None = None,
    include_submission_table: bool = True,
) -> MarkdownOutput:
    title = report_title or f"{course.name} {coursework.title if coursework is not None else 'レポート'}"
    lines = [
        f"# {title}",
        "",
        "## 概要",
        f"- 提出済み: {counts['submitted']}",
        f"- 未提出: {counts['missing']}",
        f"- 遅延提出: {counts['late']}",
    ]
    if report_intro:
        lines.extend(["", report_intro])
    if coursework is not None:
        lines.extend(
            [
                "",
                "## 対象課題",
                f"- 課題名: {coursework.title}",
                f"- 締切: {normalize_due_datetime(coursework.due_date, coursework.due_time)}",
                f"- 満点: {'' if coursework.max_points is None else coursework.max_points}",
            ]
        )
    if include_submission_table:
        lines.extend(["", "## 未提出者一覧"])
        missing = _missing_students(submissions)
        if missing:
            for submission in missing:
                lines.append(f"- {submission.student_name} / {'遅延提出' if submission.late else '未提出'}")
        else:
            lines.append("- 該当なし")
    if reminder_text:
        lines.extend(["", "## リマインド案", reminder_text])
    lines.extend(
        [
            "",
            "## 注意事項",
            "- 本文は教師確認後にのみClassroomへ投稿してください。",
        ]
    )
    return MarkdownOutput(
        file_name="report.md",
        title=title,
        content="\n".join(lines),
    )


def _build_pdf_output(
    *,
    course: Course,
    coursework: CourseWork | None,
    submissions: list[StudentSubmission],
    counts: dict[str, int],
    reminder_text: str | None = None,
    report_title: str | None = None,
    report_intro: str | None = None,
    include_submission_table: bool = True,
) -> PdfOutput:
    title = report_title or f"{course.name} {coursework.title if coursework is not None else 'レポート'}"
    sections: list[dict[str, Any]] = [
        {
            "heading": "概要",
            "body": report_intro
            or f"{course.name} の課題「{coursework.title if coursework is not None else '不明'}」のレポートです。",
        },
        {
            "heading": "提出状況",
            "table": {
                "columns": ["提出済み", "未提出", "遅延提出"],
                "rows": [[str(counts["submitted"]), str(counts["missing"]), str(counts["late"])]],
            },
        },
    ]
    if coursework is not None:
        sections.append(
            {
                "heading": "課題情報",
                "table": {
                    "columns": ["項目", "内容"],
                    "rows": [
                        ["課題名", coursework.title],
                        ["締切", normalize_due_datetime(coursework.due_date, coursework.due_time)],
                        ["満点", "" if coursework.max_points is None else str(coursework.max_points)],
                    ],
                },
            }
        )
    if include_submission_table:
        missing = _missing_students(submissions)
        sections.append(
            {
                "heading": "未提出者一覧",
                "table": {
                    "columns": ["生徒名", "状態", "締切"],
                    "rows": [
                        [
                            submission.student_name,
                            "遅延提出" if submission.late else "未提出",
                            coursework.due_date if coursework is not None else "",
                        ]
                        for submission in missing
                    ],
                },
            }
        )
    if reminder_text:
        sections.append({"heading": "リマインド案", "body": reminder_text})
    return PdfOutput(
        file_name="report.pdf",
        title=title,
        layout="report",
        sections=sections,
    )


def _build_google_document_output(
    *,
    course: Course,
    coursework: CourseWork | None,
    submissions: list[StudentSubmission],
    counts: dict[str, int],
    reminder_text: str | None = None,
    report_title: str | None = None,
    report_intro: str | None = None,
    include_submission_table: bool = True,
) -> GoogleDocumentOutput:
    title = report_title or f"{course.name} {coursework.title if coursework is not None else 'レポート'}"
    blocks: list[dict[str, Any]] = [
        {"type": "heading1", "text": title},
        {
            "type": "paragraph",
            "text": report_intro
            or "このドキュメントは、Google Classroom の情報をもとに AI が作成したレポートです。",
        },
        {"type": "heading2", "text": "提出状況"},
        {
            "type": "table",
            "columns": ["提出済み", "未提出", "遅延提出"],
            "rows": [[str(counts["submitted"]), str(counts["missing"]), str(counts["late"])]],
        },
    ]
    if coursework is not None:
        blocks.extend(
            [
                {"type": "heading2", "text": "課題情報"},
                {
                    "type": "table",
                    "columns": ["項目", "内容"],
                    "rows": [
                        ["課題名", coursework.title],
                        ["締切", normalize_due_datetime(coursework.due_date, coursework.due_time)],
                        ["満点", "" if coursework.max_points is None else str(coursework.max_points)],
                    ],
                },
            ]
        )
    if include_submission_table:
        missing = _missing_students(submissions)
        blocks.extend(
            [
                {"type": "heading2", "text": "未提出者一覧"},
                {
                    "type": "table",
                    "columns": ["生徒名", "状態", "締切"],
                    "rows": [
                        [
                            submission.student_name,
                            "遅延提出" if submission.late else "未提出",
                            coursework.due_date if coursework is not None else "",
                        ]
                        for submission in missing
                    ],
                },
            ]
        )
    if reminder_text:
        blocks.extend(
            [
                {"type": "heading2", "text": "リマインド案"},
                {"type": "paragraph", "text": reminder_text},
            ]
        )
    return GoogleDocumentOutput(
        title=title,
        document_type="report",
        blocks=blocks,
    )


def _build_reminder_text(
    *,
    course_name: str,
    coursework_title: str,
    missing_count: int,
    due: str,
    tone: str,
    teacher_instruction: str,
) -> str:
    base = [
        f"{course_name} の課題「{coursework_title}」についてお知らせします。",
        f"提出期限は {due} です。",
    ]
    if missing_count > 0:
        base.append("まだ提出できていない人は、期限までに提出してください。")
    else:
        base.append("提出状況は良好です。")

    if tone == "strict":
        base.append("期限を過ぎないよう、必ず確認してください。")
    elif tone == "short":
        base = [
            f"{course_name} の課題「{coursework_title}」は {due} が締切です。",
            "未提出の人は早めに提出してください。",
        ]
    else:
        base.append("ご不明点があれば教師へ確認してください。")

    if teacher_instruction.strip():
        base.append(f"補足: {teacher_instruction.strip()}")

    return " ".join(base)


def _build_announcement_text(
    *,
    course_name: str,
    title: str,
    tone: str,
    teacher_instruction: str,
    extra_notes: str,
) -> str:
    if tone == "short":
        text = f"{course_name} のお知らせです。{title} を確認してください。"
    elif tone == "strict":
        text = f"{course_name} のお知らせです。{title} を必ず確認してください。"
    else:
        text = f"{course_name} のお知らせです。{title} に関するご案内です。"
    if teacher_instruction.strip():
        text += f" 補足: {teacher_instruction.strip()}"
    if extra_notes.strip():
        text += f" 備考: {extra_notes.strip()}"
    return text


def _missing_students(submissions: Sequence[StudentSubmission]) -> list[StudentSubmission]:
    return [submission for submission in submissions if submission.state not in {"TURNED_IN", "RETURNED"}]
