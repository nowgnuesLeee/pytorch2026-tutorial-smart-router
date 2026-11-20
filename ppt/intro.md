---
marp: true
---
# 나만의 작고 소중한 스마트 LLM 라우터 만들기
이승원(래블업)

---

# 목차
1. AI 시대를 대비하는 방법
2. 튜토리얼
3. Continuum Router & Hub

---

# AI 시대를 대비하는 방법

---

<style scoped>img { display: block; margin: 0 auto; }</style>

![h:500](./t-800.png)
너 이리와서 프롬프트 까봐

---

<img src="good-prompt.png">
꿀팁: 인사를 잘하자

---

## 하지만 수많은 자원이 소모된다
<img src="./thanks.png">
샘 올트만도 인정한 꿀팁

---

# Smart LLM Router

---

# LLM Router

<img src="./smart-router.svg" width="100%">
여러 모델을 하나의 endpoint로

---

# Smart LLM Router

<img src="./smart-llm-router.svg" width="100%">
사용자의 질문에 대해서 적절한 모델을 선택

---

# Smart LLM Router

liteLLM, RouteLLM, vLLM, Continuum Router


---

# 분류기를 간단히 구현해보자

---

# 오늘의 튜토리얼
1. 키워드 기반 분류
2. 가중치 기반 분류
3. LLM 분류
4. 채팅 페이지에서 확인

---

<style scoped>section { text-align: center; } img { display: block; margin: 0 auto; }</style>

![h:420](./qr.jpg)

https://github.com/nowgnuesLeee/pytorch2026-tutorial-smart-router

---


LLM_BASE_URL=https://api.console.lablup.ai/v1
LLM_API_KEY=

SMALL_MODEL=google/gemma-4-26b
BIG_MODEL=deepseek-ai/DeepSeek-V4.1-Flash