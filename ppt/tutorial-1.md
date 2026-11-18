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
# 1단계: 키워드 분류기
"이 단어가 있으면 이 모델"

---

# 먼저, 같은 질문을 두 모델에게

```bash
uv run llm.py "파이썬에서 hello world를 출력하고 싶어"
uv run llm.py "주문·결제·배송을 마이크로서비스로 나눌 때 데이터 일관성을 지키는 설계를 해줘"
```
품질, 속도, 비용을 비교해 보자

---

## 쉬운 질문에도 큰 모델이 꼭 필요할까?
답은 비슷한데 시간과 돈은 몇 배

---

# 가장 단순한 방법

```text
질문 → "이 단어가 있으면 이 모델" 키워드 → small / big
```
위에서부터 보고, 처음 걸린 규칙 하나로 결정

---

# 키워드

```python
KEYWORD_RULES = [
    ("설계", "big"),
    ("최적화", "big"),
    ("디버깅", "big"),
    ("비교", "big"),
    ...
    ("안녕", "small"),
    ("번역", "small"),
    ("뜻", "small"),
]
DEFAULT = "small"   # 아무것도 안 걸리면
```

---

# 실습 1-1: keyword 만들기

```python
def keyword(text: str):
    # TODO: 규칙을 위에서부터 보고 걸리면 → (size, f"rule={word}")
    #       하나도 안 걸리면 → (DEFAULT, "rule=없음")
```

---

# 구현

```python
def keyword(text: str):
    for word, size in KEYWORD_RULES:
        if word in text:
            return size, f"rule={word}"
    return DEFAULT, "rule=없음"
```

```bash
cd tutorial-1
uv run run.py keyword --no-answer
```

---

# 결과

```text
✅  1 small 안녕? 오늘 기분 어때?                    rule=안녕
✅ 11 big   이 함수가 입력이 커지면 너무 느려져. …    rule=최적화
❌ 17 big   '디버깅'이라는 단어는 어디서 유래했어?   rule=디버깅
❌ 24 small 고마워! 그런데 하나만 더. 서버 여러 …    rule=고마워
── 정확도 17/24 · 분류용 LLM 호출 0회 · 평균 분류 0ms
```
공짜에 0ms, 그런데 7개를 틀렸다

---

# 퀴즈: 어디로 갈까?

> 고마워! 그런데 하나만 더. 서버 여러 대가 같은 캐시를 쓰는데, 데이터 불일치 없이 캐시를 무효화하려면 어떻게 해야 해?

---

## '고마워'만 걸려서 작은 모델로...
'캐시'를 규칙에 넣으면 해결될까?


---

# 실습 1-2: 규칙 고쳐 보기

- 질문을 보고 규칙을 더하거나 순서를 바꿔 보자

```bash
uv run run.py keyword --no-answer
```

---

# 정리

빠르고, 공짜고, 이유가 분명하다

하지만 단어만 볼 뿐 뜻은 모르고,
규칙이 늘수록 서로 부딪친다

---

## 키워드 하나가 아니라 여러 개를 같이 보면?
→ 2단계: 가중치 분류기
