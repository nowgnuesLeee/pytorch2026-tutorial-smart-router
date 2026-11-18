---
marp: true
style: |
  pre {
    position: relative;
    background: #1e1e2e;
    color: #cdd6f4;
    border: none;
    border-radius: 12px;
    padding: 2.4em 1.4em 1.2em;
    font-size: 0.7em;
    line-height: 1.5;
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.25);
  }
  pre::before {
    content: "";
    position: absolute;
    top: 0.9em;
    left: 1.2em;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: #ff5f56;
    box-shadow: 20px 0 #ffbd2e, 40px 0 #27c93f;
  }
  pre code { color: inherit; background: none; }
  .hljs-keyword, .hljs-built_in { color: #cba6f7; }
  .hljs-string { color: #a6e3a1; }
  .hljs-number, .hljs-literal { color: #fab387; }
  .hljs-comment { color: #7f849c; font-style: italic; }
  .hljs-title, .hljs-section { color: #89b4fa; }
  .hljs-params, .hljs-attr { color: #f5e0dc; }
  .hljs-meta { color: #f9e2af; }
  .hljs-subst, .hljs-variable { color: #f38ba8; }
---
# 3단계: LLM 분류기
작은 모델에게 판정을 맡기자

---

# 아이디어

```text
질문 → 작은 모델: {"level": "easy" | "hard"} → small / big
```
뜻은 LLM이 제일 잘 안다

---

# 판정 프롬프트

```text
너는 요청 난이도 판정기다. 사용자의 요청을 읽고 난이도만 판정한다.
- easy: 인사, 짧은 사실 질문, 단어 뜻, 번역, 간단한 수정, 짧은 글
- hard: 설계, 디버깅, 원인 분석, 여러 단계의 추론, 긴 코드 작성, 비교 분석
요청에 답하지 말고, 아래 JSON 한 줄로만 답하라.
{"level": "easy"} 또는 {"level": "hard"}
```

---

# 그런데 LLM은 말을 잘 안 듣는다

```text
판정: {"level": "hard"} 입니다!
```

JSON만 달라고 해도 앞뒤에 말을 붙이곤 한다

---

# 구조화 출력: 답의 모양을 고정하기

```python
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
```

---

## 서버가 스키마에 맞는 토큰만 고르게 한다
말을 덧붙이거나 형식을 어길 수가 없다

---

# 판정 요청

```python
def ask_level(text: str) -> str:
    r = llm_api.chat(
        "small",
        [{"role": "system", "content": CLASSIFY_PROMPT},
         {"role": "user", "content": text[:MAX_INPUT_CHARS]}],
        purpose="classify",
        response_format=LEVEL_SCHEMA,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        temperature=0,
        max_tokens=50,
        timeout=5,
        retries=0,
    )
    return json.loads(r["text"])["level"]
```

---

# 판정 요청 설정

| 설정 | 이유 |
| :--- | :--- |
| `response_format` | `{"level": "easy" \| "hard"}` 모양으로만 답하게 |
| `enable_thinking: False` | 추론 모델이 답 전에 생각하느라 토큰과 시간을 쓰지 않게 |
| `temperature=0` | 같은 질문에는 늘 같은 판정 |
| `timeout=5` | 판정이 늦으면 라우터 전체가 늦어진다 |
| `retries=0` | 늦은 판정은 의미 없으니 바로 포기 |

---

# 생각을 끄면

| 설정 | 시간 | 출력 토큰 | 결과 |
| :--- | ---: | ---: | :--- |
| 생각 켜짐, `max_tokens=300` | 2.2s | 300 | 생각하다 잘려서 빈 답 ❌ |
| 생각 켜짐, `max_tokens=1500` | 5.6s | 748 | `{"level": "hard"}` |
| 생각 꺼짐 | **0.3s** | **10** | `{"level": "hard"}` ✅ |

---

# 실습 3-1: llm 만들기

그래도 서버가 느리거나 죽을 수 있다
LLM이 실패해도 라우터는 멈추면 안 된다

| 상황 | 돌려줄 값 |
| :--- | :--- |
| 예외 (시간 초과, 연결 실패, 빈 답, 예상 밖의 값) | `score`로 되돌아가기 |
| 정상 | `LEVEL_TO_SIZE[level]` |

---

# 구현

```python
def llm(text: str):
    try:
        level = ask_level(text)
        size = LEVEL_TO_SIZE[level]
    except Exception as e:
        return score(text)[0], f"llm 실패({type(e).__name__}) → score"
    return size, f"llm={level}"
```

```bash
cd tutorial-3
uv run run.py llm --no-answer
```

---

## 정확해졌는데... 질문마다 LLM을 한 번씩 부른다
분류하는 데도 시간과 토큰이 든다

---

# hybrid: 애매할 때만 묻자

```text
점수 계산 (2단계 score)
 ├─ 경계값에서 멀다 (확실)  → 점수로 바로 결정        LLM 호출 0번
 └─ 경계값 근처 (애매)      → 작은 모델에게 판정
                               └─ 실패하면 → 점수로 되돌아가기
```

어려운 판단만 LLM에게

---

# 실습 3-2: hybrid 만들기

```python
MARGIN = 0.15   # THRESHOLD ± MARGIN 안이면 "애매하다"

def hybrid(text: str):
    s = difficulty(text)
    # TODO: abs(s - THRESHOLD) > MARGIN 이면 점수로 바로 결정
    #       아니면 llm(text)에게 묻기
```

---

# 구현

```python
def hybrid(text: str):
    s = difficulty(text)
    if abs(s - THRESHOLD) > MARGIN:
        return ("big" if s >= THRESHOLD else "small"), f"score={s:+.2f} (확실)"
    size, note = llm(text)
    return size, f"score={s:+.2f} (애매) → {note}"
```

```bash
uv run run.py all --no-answer
```

---

# 실습 3-3: 비교하기

| 분류기 | 정확도 | 분류용 LLM 호출 | 평균 분류 시간 |
| :--- | :---: | :---: | :---: |
| keyword | 17/24 | 0 | 0ms |
| score | 20/24 | 0 | 0ms |
| llm | | | |
| hybrid | | | |

---

# 실습 3-3: 조절해 보기

- `MARGIN`을 0, 0.15, 0.3, 0.5로 바꾸면 정확도와 호출 수는?
- hybrid가 놓치는 질문은 왜 놓칠까?
  - 점수가 "확실"하다고 했는데 틀린 경우
- 답변까지 받아서 비용 비교: `uv run run.py hybrid`

---

# 정리

LLM 판정은 뜻을 이해하지만
시간과 비용이 든다
형식은 구조화 출력으로 고정한다

규칙으로 충분한 곳에서는 규칙을,
애매할 때만 LLM에게

---

## 분류기는 다 만들었다. 이제 진짜로 써 보자
→ 4단계: 라우터 서버
