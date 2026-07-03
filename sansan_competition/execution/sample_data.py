"""モックClassroom用の生データ (Google Classroom API風)。

kimuの `normalize_course` / `normalize_coursework` / `normalize_submission_batch` が
そのまま消費できる生JSON形状にする。エイリアス経路(id, courseState, teachers,
dueDate/dueTimeオブジェクト, userId)も含めて正規化を実際に通せるようにしている。
"""

from __future__ import annotations

# コース (Google APIは courseId ではなく id / courseState を返す)
COURSES: list[dict] = [
    {
        "id": "123456789",
        "name": "数学I",
        "section": "1年A組",
        "description": "高校1年 数学I",
        "courseState": "ACTIVE",
        "teachers": [{"userId": "teacher_001"}],
        "studentCount": 30,
    },
    {
        "id": "223456789",
        "name": "英語コミュニケーションI",
        "section": "1年A組",
        "description": "高校1年 英語",
        "courseState": "ACTIVE",
        "teachers": [{"userId": "teacher_001"}],
        "studentCount": 30,
    },
]

COURSEWORK: dict[str, list[dict]] = {
    "123456789": [
        {
            "id": "987654321",
            "courseId": "123456789",
            "title": "二次関数プリント",
            "description": "教科書p.42-45の問題を解く。",
            "workType": "ASSIGNMENT",
            "maxPoints": 100,
            "dueDate": {"year": 2026, "month": 7, "day": 5},
            "dueTime": {"hours": 23, "minutes": 59},
            "state": "PUBLISHED",
        },
        {
            "id": "987654322",
            "courseId": "123456789",
            "title": "因数分解 小テスト",
            "description": "範囲: 因数分解全般。",
            "workType": "SHORT_ANSWER_QUESTION",
            "maxPoints": 20,
            "dueDate": {"year": 2026, "month": 6, "day": 28},
            "dueTime": {"hours": 23, "minutes": 59},
            "state": "PUBLISHED",
        },
    ]
}


def _build_submissions() -> dict[str, list[dict]]:
    """二次関数プリント(987654321)に未提出12名を含む30名分を生成。"""
    subs: list[dict] = []
    for i in range(1, 31):
        # 18名提出済み、12名未提出。提出済みのうち2名は遅延。
        if i <= 18:
            state = "TURNED_IN"
            late = i in (17, 18)
            submission_time = "2026-07-05T20:00:00+09:00"
        else:
            state = "NEW"
            late = False
            submission_time = None
        raw = {
            "id": f"sub_{i:03d}",
            "courseId": "123456789",
            "courseWorkId": "987654321",
            "userId": f"student_{i:03d}",
            "studentName": f"生徒{i:02d}",
            "state": state,
            "late": late,
            "attachments": [],
        }
        if submission_time:
            raw["submissionTime"] = submission_time
        subs.append(raw)
    return {"987654321": subs}


SUBMISSIONS: dict[str, list[dict]] = _build_submissions()
