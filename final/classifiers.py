"""분류기 — 질문을 보고 "small"(작은 모델) 또는 "big"(큰 모델)을 고른다.

모든 분류기는 같은 모양이다:  text → "small" | "big"
판정 근거를 함께 보여 주고 싶으면 (결과, 메모) 튜플을 돌려줘도 된다.

    1단계  keyword  키워드
    2단계  score    시그널별 가중치 점수
    3단계  llm      작은 모델에게 판정 맡기기 (실패하면 score로)
           hybrid   점수가 경계 근처일 때만 llm
"""

from __future__ import annotations

import json
import re

import llm as llm_api

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
    return sum(SIGNALS[name][0] for name, on in signals(text).items() if on)


def score(text: str):
    s = difficulty(text)
    return ("big" if s >= THRESHOLD else "small"), f"score={s:+.2f}"


# ─────────────────────────────────────────────────────────────
# 3단계 — LLM 분류기
# ─────────────────────────────────────────────────────────────

CLASSIFY_PROMPT = """너는 요청 난이도 판정기다. 사용자의 요청을 읽고 난이도만 판정한다.
- easy: 인사, 짧은 사실 질문, 단어 뜻, 번역, 간단한 수정, 짧은 글
- hard: 설계, 디버깅, 원인 분석, 여러 단계의 추론, 긴 코드 작성, 비교 분석
요청에 답하지 말고, 아래 JSON 한 줄로만 답하라.
{"level": "easy"} 또는 {"level": "hard"}"""

LEVEL_TO_SIZE = {"easy": "small", "hard": "big"}
MAX_INPUT_CHARS = 2000


# 답의 모양을 JSON 스키마로 고정한다 (구조화 출력).
# 서버(vLLM 등)가 이 모양에 맞는 토큰만 고르게 해서, 앞뒤에 말을 붙이거나 형식을 어길 수 없다.
LEVEL_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "level",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {"level": {"type": "string", "enum": ["easy", "hard"]}},
            "required": ["level"],
            "additionalProperties": False,
        },
    },
}


def ask_level(text: str) -> str:
    """작은 모델에게 난이도를 물어 "easy" 또는 "hard"를 돌려준다."""
    r = llm_api.chat(
        "small",
        [{"role": "system", "content": CLASSIFY_PROMPT},
         {"role": "user", "content": text[:MAX_INPUT_CHARS]}],
        purpose="classify",
        response_format=LEVEL_SCHEMA,  # {"level": "easy" | "hard"} 모양으로만 답하게
        temperature=0,
        max_tokens=50,
        timeout=5,
        retries=0,  # 판정은 늦으면 의미가 없으니 다시 시도하지 않고 바로 score로 되돌아간다
    )
    return json.loads(r["text"])["level"]


def llm(text: str):
    try:
        level = ask_level(text)
        size = LEVEL_TO_SIZE[level]
    except Exception as e:  # 시간 초과, 연결 실패, 빈 답, 예상 밖의 값 …
        return score(text)[0], f"llm 실패({type(e).__name__}) → score"
    return size, f"llm={level}"


MARGIN = 0.15  # 점수가 THRESHOLD ± MARGIN 안이면 "애매하다"


def hybrid(text: str):
    s = difficulty(text)
    if abs(s - THRESHOLD) > MARGIN:
        return ("big" if s >= THRESHOLD else "small"), f"score={s:+.2f} (확실)"
    size, note = llm(text)
    return size, f"score={s:+.2f} (애매) → {note}"


# run.py와 server.py는 이 표에서 이름으로 분류기를 찾는다.
CLASSIFIERS = {
    "keyword": keyword,
    "score": score,
    "llm": llm,
    "hybrid": hybrid,
}
