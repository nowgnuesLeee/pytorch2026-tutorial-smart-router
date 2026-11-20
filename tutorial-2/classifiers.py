"""분류기 — 질문을 보고 "small"(작은 모델) 또는 "big"(큰 모델)을 고른다.

모든 분류기는 같은 모양이다:  text → "small" | "big"
판정 근거를 함께 보여 주고 싶으면 (결과, 메모) 튜플을 돌려줘도 된다.

    1단계  keyword  키워드
    2단계  score    시그널별 가중치 점수
    3단계  llm      작은 모델에게 판정 맡기기 (실패하면 score로)
           hybrid   점수가 경계 근처일 때만 llm
"""

from __future__ import annotations

import re

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
    for word, size in KEYWORD_RULES:
        if word in text:
            return size, f"rule={word}"
    return DEFAULT, "rule=없음"


# ─────────────────────────────────────────────────────────────
# 2단계 — 점수 분류기
# ─────────────────────────────────────────────────────────────

CODE_WORDS = ["코드", "함수", "클래스", "api", "sql", "에러", "버그", "파이썬", "python", "구현",
              "import", "asyncio", "딕셔너리", "스크립트"]
REASONING_WORDS = ["왜", "단계별", "분석", "비교", "증명", "장단점", "원인"]
TECH_WORDS = ["설계", "아키텍처", "분산", "동시성", "최적화", "보안", "확장", "리팩터링",
              "마이크로서비스", "일관성", "캐시", "메모리"]
SIMPLE_WORDS = ["안녕", "고마워", "뜻", "번역", "몇 시", "오타", "한 줄"]


def _has_any(text: str, words: list[str]) -> bool:
    lowered = text.lower()
    return any(w in lowered for w in words)


def _multi_step(text: str) -> bool:
    numbered = len(re.findall(r"(?m)^\s*\d+[.)]", text)) >= 2
    return numbered or ("먼저" in text and ("다음" in text or "그리고" in text))


# 이름: (가중치, 판정 함수). 음수 가중치는 "쉬움" 쪽 시그널이다.
SIGNALS = {
    "code": (0.35, lambda t: "```" in t or _has_any(t, CODE_WORDS)),
    "reasoning": (0.30, lambda t: _has_any(t, REASONING_WORDS)),
    "technical": (0.30, lambda t: _has_any(t, TECH_WORDS)),
    "long": (0.15, lambda t: len(t) > 200),
    "multi_step": (0.10, _multi_step),
    "simple": (-0.30, lambda t: _has_any(t, SIMPLE_WORDS) or len(t) < 15),
}
THRESHOLD = 0.30  # 이 점수 이상이면 큰 모델


def signals(text: str) -> dict[str, bool]:
    return {name: check(text) for name, (_, check) in SIGNALS.items()}


def difficulty(text: str) -> float:
    # TODO(2-1): signals(text)에서 켜진(True) 시그널의 가중치를 모두 더해 돌려주세요.
    #            가중치는 SIGNALS[name][0] 입니다.
    NotImplemented


def score(text: str):
    s = difficulty(text)
    # TODO(2-2): s가 THRESHOLD 이상이면 "big", 아니면 "small"을 고르고
    #            (결과, f"score={s:+.2f}")를 돌려주세요.
    NotImplemented


# TODO(2-3): `uv run run.py all --no-answer`로 keyword와 비교해 보고,
#            SIGNALS의 가중치·단어 목록과 THRESHOLD를 바꿔 가며 정확도가 어떻게 변하는지 보세요.


# run.py는 이 표에서 이름으로 분류기를 찾는다.
CLASSIFIERS = {
    "keyword": keyword,
    "score": score,
}
