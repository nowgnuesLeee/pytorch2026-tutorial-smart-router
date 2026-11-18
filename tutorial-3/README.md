# 3단계: LLM 분류기

```text
llm     질문 → 작은 모델: {"level": "easy"|"hard"} → small / big
                   └ 실패하면 → score로 되돌아가기
hybrid  점수가 확실하면 → score 결과
        점수가 경계 근처면 → llm에게 묻기
```

1단계 `keyword`와 2단계 `score`는 완성되어 있습니다.

## 판정 요청

`ask_level()`이 `CLASSIFY_PROMPT`와 함께 질문을 작은 모델에 보내고 `"easy"` 또는 `"hard"`를 돌려줍니다. 이 부분은 이미 완성되어 있어요.

작은 모델은 JSON만 달라고 해도 `판정: {"level": "hard"} 입니다!`처럼 앞뒤에 말을 붙이곤 합니다. 그래서 **구조화 출력(structured outputs)**으로 답의 모양을 고정합니다.

- `response_format=LEVEL_SCHEMA`: JSON 스키마를 주면 서버(vLLM 등)가 그 모양에 맞는 토큰만 고릅니다. 답은 `{"level": "easy"}` 또는 `{"level": "hard"}`뿐이라 `json.loads`로 바로 읽습니다.
- `extra_body={"chat_template_kwargs": {"enable_thinking": False}}`: 추론(reasoning) 모델은 답하기 전에 생각하는 데 토큰을 씁니다. 판정에는 생각이 필요 없으니 꺼서 빠르고 싸게 만듭니다. 켜 두면 `max_tokens` 안에서 생각하다 끊겨 답이 비기도 합니다.
- `temperature=0`: 같은 질문에는 늘 같은 판정을 받기 위해서
- `timeout=5`, `retries=0`: 판정이 늦으면 라우터 전체가 늦어지니까

## 실습 3-1: `llm` 만들기

구조화 출력을 써도 서버가 느리거나 죽을 수 있습니다. `ask_level(text)`와 `LEVEL_TO_SIZE[level]`을 `try`로 감싸고, 실패하면 점수 분류기로 되돌아갑니다.

| 상황 | 돌려줄 값 |
| :--- | :--- |
| 예외 (시간 초과, 연결 실패, 빈 답, 예상 밖의 값) | `(score(text)[0], f"llm 실패({type(e).__name__}) → score")` |
| 정상 | `(LEVEL_TO_SIZE[level], f"llm={level}")` |

```bash
uv run run.py llm --no-answer
```

모델 답은 코드가 검사합니다. LLM이 실패해도 라우터는 멈추지 않아야 합니다.

## 실습 3-2: `hybrid` 만들기

점수가 `THRESHOLD`에서 `MARGIN`보다 멀리 있으면 점수로 바로 결정하고, 가까우면 `llm()`에게 묻습니다.

```bash
uv run run.py all --no-answer
```

## 실습 3-3: 비교하기

| 분류기 | 정확도 | 분류용 LLM 호출 | 평균 분류 시간 |
| :--- | :---: | :---: | :---: |
| keyword | | 0 | |
| score | | 0 | |
| llm | | | |
| hybrid | | | |

- `MARGIN`을 0, 0.15, 0.3, 0.5로 바꾸면 정확도와 호출 수가 어떻게 변하나요?
- `hybrid`가 놓치는 질문(22번, 24번)은 왜 놓칠까요? 점수가 "확실"하다고 판단했지만 틀린 경우입니다.
- 답변까지 받아서 비용을 비교해 보세요: `uv run run.py hybrid`

> 정리: LLM 판정은 뜻을 이해하지만 시간과 비용이 듭니다. 그래서 규칙으로 충분한 곳에서는 규칙을 쓰고, 애매할 때만 LLM에게 묻습니다.
