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
# 2단계: 점수 분류기
여러 시그널을 모두 더해서 판단

---

# 키워드의 문제

처음 걸린 규칙 **하나**로 결정한다

"고마워"가 먼저 걸리면 뒤에 "캐시"가 있어도 끝

---

# 그럼 다 더해 보자

키워드 **하나** 대신, 여러 키워드 **묶음**과 "200자 넘음"과 같은 조건까지 함께 본다
→ 이걸 **시그널**(signal)이라고 부르자

```text
질문 → 시그널마다 켜짐/꺼짐 → 켜진 시그널의 가중치 합 → 경계값 이상이면 big
```

---

# 시그널과 가중치

| 시그널 | 가중치 | 켜지는 조건 |
| :--- | :---: | :--- |
| `code` | +0.35 | 코드 블록, 코드 관련 단어 |
| `reasoning` | +0.30 | "왜", "분석", "비교", "증명" … |
| `technical` | +0.30 | "설계", "아키텍처", "캐시" … |
| `long` | +0.15 | 200자 초과 |
| `multi_step` | +0.10 | 번호 매긴 단계, "먼저 … 다음" |
| `simple` | −0.30 | 인사·번역·뜻 묻기, 15자 미만 |

음수는 "쉬움" 쪽으로 끌어당긴다

---

# 코드로 보면

```python
# 이름: (가중치, 판정 함수)
SIGNALS = {
    "code":       ( 0.35, lambda t: "```" in t or _has_any(t, CODE_WORDS)),
    "reasoning":  ( 0.30, lambda t: _has_any(t, REASONING_WORDS)),
    "technical":  ( 0.30, lambda t: _has_any(t, TECH_WORDS)),
    "long":       ( 0.15, lambda t: len(t) > 200),
    "multi_step": ( 0.10, _multi_step),
    "simple":     (-0.30, lambda t: _has_any(t, SIMPLE_WORDS) or len(t) < 15),
}
THRESHOLD = 0.30  # 이 점수 이상이면 큰 모델

def signals(text: str) -> dict[str, bool]:
    return {name: check(text) for name, (_, check) in SIGNALS.items()}
```

---

# 실습 2-1: difficulty 만들기

```python
def difficulty(text: str) -> float:
    # TODO: signals(text)에서 켜진 시그널의 가중치를 모두 더하기
    #       가중치는 SIGNALS[name][0]
```

`signals(text)` → `{"code": True, "long": False, ...}`

---

# 실습 2-2: score 만들기

```python
THRESHOLD = 0.30

def score(text: str):
    s = difficulty(text)
    # TODO: s >= THRESHOLD 이면 "big", 아니면 "small"
    #       → (결과, f"score={s:+.2f}")
```

---

# 구현

```python
def difficulty(text: str) -> float:
    return sum(SIGNALS[name][0] for name, on in signals(text).items() if on)


def score(text: str):
    s = difficulty(text)
    return ("big" if s >= THRESHOLD else "small"), f"score={s:+.2f}"
```

```bash
cd tutorial-2
uv run run.py all --no-answer     # keyword와 비교
```

---

# 결과

```text
분류기    정확도   분류용 LLM 호출   평균 분류 시간
keyword    17/24                0            0ms
score      20/24                0            0ms
```
여전히 공짜에 0ms, 정확도는 올랐다

---

# 아까 그 퀴즈

> 고마워! 그런데 하나만 더. 서버 여러 대가 같은 캐시를 쓰는데, …

`simple` −0.30 + `technical` +0.30 = **0.00** → 작은 모델 ❌

서로 상쇄돼 버렸다

---

# 퀴즈: 어디로 갈까?

> P와 NP가 같지 않다는 걸 보여줘.

---

## 켜진 시그널이 하나도 없어서 0.00 → 작은 모델 ❌
컴퓨터 과학 최대 난제인데..?

---

# 정리

여러 시그널을 함께 보니 키워드보다 덜 깨진다

그래도 여전히 단어를 셀 뿐, 질문의 뜻은 모른다

---

## 뜻을 아는 건 결국 LLM 아닐까?
→ 3단계: LLM 분류기
