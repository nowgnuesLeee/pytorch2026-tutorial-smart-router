"""LLM 호출 — 토큰 팩토리의 OpenAI 호환 API로 작은 모델과 큰 모델을 부른다.

모든 단계 폴더가 이 파일 하나를 함께 쓴다.
설정은 같은 폴더(저장소 루트)의 .env 파일에서 읽는다 (.env.example을 복사해 채우기).
이미 export한 환경변수가 있으면 그쪽이 우선이다.

직접 실행하면 같은 질문을 두 모델에 보내 비교한다 (도입):
    uv run llm.py "파이썬에서 리스트를 뒤집는 방법은?"
"""

from __future__ import annotations

import os
import sys
import time
from collections import Counter
from pathlib import Path

from openai import OpenAI


def load_env(path: Path) -> None:
    """KEY=VALUE 형식의 .env 파일을 읽어 환경변수로 넣는다 (이미 있는 값은 덮어쓰지 않음)."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


load_env(Path(__file__).resolve().parent / ".env")

BASE_URL = os.environ.get("LLM_BASE_URL", "http://127.0.0.1:8000/v1")
API_KEY = os.environ.get("LLM_API_KEY", "none")

# 분류기가 고르는 값은 "small" 또는 "big" 두 가지뿐이다.
MODELS = {
    "small": os.environ.get("SMALL_MODEL", "small-model"),
    "big": os.environ.get("BIG_MODEL", "big-model"),
}

# 1M 토큰당 USD (입력, 출력). 기본값은 예시일 뿐이니 .env에 토큰 팩토리 가격을 채우세요.
PRICES = {
    "small": (float(os.environ.get("SMALL_PRICE_IN", "0.1")),
              float(os.environ.get("SMALL_PRICE_OUT", "0.4"))),
    "big": (float(os.environ.get("BIG_PRICE_IN", "2.0")),
            float(os.environ.get("BIG_PRICE_OUT", "8.0"))),
}

client = OpenAI(base_url=BASE_URL, api_key=API_KEY, timeout=60)

# 용도별 호출 수와 비용. run.py가 "분류에 LLM을 몇 번 썼나"를 보여 줄 때 쓴다.
CALLS: Counter = Counter()
COSTS: Counter = Counter()


def cost_of(size: str, tokens_in: int, tokens_out: int) -> float:
    price_in, price_out = PRICES[size]
    return (tokens_in * price_in + tokens_out * price_out) / 1_000_000


def chat(size: str, messages: list[dict], purpose: str = "answer",
         retries: int | None = None, **kwargs) -> dict:
    """size("small"/"big") 모델로 대화를 보내고, 답과 토큰·비용·시간을 함께 돌려준다.

    retries를 주면 실패 시 재시도 횟수를 바꾼다 (기본은 openai 라이브러리 기본값 2회).
    """
    c = client if retries is None else client.with_options(max_retries=retries)
    start = time.perf_counter()
    resp = c.chat.completions.create(model=MODELS[size], messages=messages, **kwargs)
    seconds = time.perf_counter() - start

    tokens_in = resp.usage.prompt_tokens if resp.usage else 0
    tokens_out = resp.usage.completion_tokens if resp.usage else 0
    cost = cost_of(size, tokens_in, tokens_out)
    CALLS[purpose] += 1
    COSTS[purpose] += cost
    return {
        "text": resp.choices[0].message.content or "",
        "size": size,
        "model": MODELS[size],
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost": cost,
        "seconds": seconds,
    }


def ask(size: str, question: str, **kwargs) -> dict:
    return chat(size, [{"role": "user", "content": question}], **kwargs)


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "파이썬에서 리스트를 뒤집는 방법은?"
    print(f"[llm] base_url={BASE_URL}")
    print(f"질문: {question}\n")
    for size in ("small", "big"):
        r = ask(size, question)
        print(f"── {size}: {r['model']}  {r['seconds']:.1f}s  "
              f"토큰 {r['tokens_in']}+{r['tokens_out']}  ${r['cost']:.6f}")
        print(r["text"].strip(), "\n")
