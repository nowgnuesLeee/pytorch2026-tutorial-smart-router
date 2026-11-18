"""분류기 — 질문을 보고 "small"(작은 모델) 또는 "big"(큰 모델)을 고른다.

모든 분류기는 같은 모양이다:  text → "small" | "big"
판정 근거를 함께 보여 주고 싶으면 (결과, 메모) 튜플을 돌려줘도 된다.

    1단계  keyword  키워드
    2단계  score    시그널별 가중치 점수
    3단계  llm      작은 모델에게 판정 맡기기 (실패하면 score로)
           hybrid   점수가 경계 근처일 때만 llm
"""

from __future__ import annotations

# ─────────────────────────────────────────────────────────────
# 1단계 — 키워드 규칙
# ─────────────────────────────────────────────────────────────

# (키워드, 보낼 모델). 위에서부터 확인해 처음 걸리는 규칙을 쓴다.
KEYWORD_RULES = [
    ("설계", "big"),
    ("아키텍처", "big"),
    ("최적화", "big"),
    ("리팩터링", "big"),
    ("디버깅", "big"),
    ("증명", "big"),
    ("비교", "big"),
    ("안녕", "small"),
    ("고마워", "small"),
    ("번역", "small"),
    ("오타", "small"),
    ("뜻", "small"),
]
DEFAULT = "small"


def keyword(text: str):
    # TODO(1-1): KEYWORD_RULES를 위에서부터 보면서, word가 text 안에 있으면
    #            (size, f"rule={word}")를 돌려주세요.
    #            하나도 걸리지 않으면 (DEFAULT, "rule=없음")을 돌려주세요.
    NotImplemented

# TODO(1-2): `uv run run.py keyword --no-answer`로 틀린 질문(❌)을 보고
#            KEYWORD_RULES에 규칙을 더하거나 순서를 바꿔 보세요.


# run.py는 이 표에서 이름으로 분류기를 찾는다.
CLASSIFIERS = {
    "keyword": keyword,
}
