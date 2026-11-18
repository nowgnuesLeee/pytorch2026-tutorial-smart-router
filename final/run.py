"""질문 세트로 분류기 시험하기.

    uv run run.py keyword              # keyword 분류기로 분류하고, 고른 모델로 답까지 받기
    uv run run.py score --no-answer    # 분류만 (모델 답변 호출 안 함)
    uv run run.py all --no-answer      # 등록된 분류기 모두 비교
    uv run run.py score --only 1,5,7   # 일부 질문만

질문 세트: 저장소 루트의 questions.json (QUESTIONS 환경변수로 바꿀 수 있음)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # 루트의 llm.py를 쓰기 위해

import llm  # noqa: E402
from classifiers import CLASSIFIERS  # noqa: E402

HERE = Path(__file__).resolve().parent
QUESTIONS = Path(os.environ.get("QUESTIONS", HERE.parent / "questions.json"))


def load_questions(only: str | None) -> list[dict]:
    items = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    if only:
        wanted = {int(n) for n in only.split(",")}
        items = [q for q in items if q["id"] in wanted]
    return items


def classify(fn, text: str) -> tuple[str, str]:
    result = fn(text)
    size, note = result if isinstance(result, tuple) else (result, "")
    if size not in llm.MODELS:
        raise ValueError(f"분류기가 {size!r}를 돌려줬습니다. 'small' 또는 'big'이어야 합니다.")
    return size, note


def short(text: str, width: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= width else text[: width - 1] + "…"


def run(name: str, questions: list[dict], answer: bool) -> dict:
    fn = CLASSIFIERS[name]
    llm.CALLS.clear()
    llm.COSTS.clear()
    correct = 0
    classify_seconds = 0.0
    big_cost_estimate = 0.0

    print(f"\n=== {name} ===")
    for q in questions:
        start = time.perf_counter()
        size, note = classify(fn, q["q"])
        classify_seconds += time.perf_counter() - start
        ok = size == q["expected"]
        correct += ok

        line = f"{'✅' if ok else '❌'} {q['id']:>2} {size:<5} {short(q['q'], 34):<34} {note}"
        if answer:
            r = llm.ask(size, q["q"])
            # 같은 토큰 수를 큰 모델 가격으로 계산한 값 (실제로는 답 길이가 달라질 수 있는 추정치)
            big_cost_estimate += llm.cost_of("big", r["tokens_in"], r["tokens_out"])
            line += f"\n      {r['seconds']:.1f}s ${r['cost']:.6f} → {short(r['text'], 60)}"
        print(line)

    total = len(questions)
    summary = {
        "name": name,
        "accuracy": f"{correct}/{total}",
        "llm_calls": llm.CALLS["classify"],
        "classify_ms": classify_seconds / max(total, 1) * 1000,
        "cost": llm.COSTS["classify"] + llm.COSTS["answer"],
    }
    print(f"── 정확도 {summary['accuracy']} · 분류용 LLM 호출 {summary['llm_calls']}회 · "
          f"평균 분류 {summary['classify_ms']:.0f}ms")
    if answer:
        print(f"── 비용 ${summary['cost']:.6f} (분류 ${llm.COSTS['classify']:.6f} 포함) · "
              f"전부 큰 모델이었다면 약 ${big_cost_estimate + llm.COSTS['classify']:.6f}")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="질문 세트로 분류기 시험하기")
    parser.add_argument("classifier", choices=[*CLASSIFIERS, "all"])
    parser.add_argument("--no-answer", action="store_true", help="분류만 하고 답변은 받지 않음")
    parser.add_argument("--only", help="질문 id 목록, 예: 1,5,7")
    args = parser.parse_args()

    questions = load_questions(args.only)
    names = list(CLASSIFIERS) if args.classifier == "all" else [args.classifier]
    results = []
    for name in names:
        try:
            results.append(run(name, questions, answer=not args.no_answer))
        except NotImplementedError as e:
            print(f"\n=== {name} ===\n⏳ 아직 구현되지 않았습니다: {e}")

    if len(results) > 1:
        print("\n분류기    정확도   분류용 LLM 호출   평균 분류 시간")
        for s in results:
            print(f"{s['name']:<9} {s['accuracy']:>6}   {s['llm_calls']:>14}   {s['classify_ms']:>10.0f}ms")


if __name__ == "__main__":
    main()
