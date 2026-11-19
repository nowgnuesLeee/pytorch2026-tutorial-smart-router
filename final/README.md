# 완성본: 분류기 + 라우터 서버

`classifiers.py`에 분류기 네 개(`keyword`, `score`, `llm`, `hybrid`)가 모두 완성되어 있고, `server.py`가 이들을 OpenAI 호환 API 서버로 감쌉니다.

## 분류기 비교

```bash
uv run run.py all --no-answer
```

## 4단계: 라우터 서버로 채팅하기

```bash
uv run server.py                              # http://127.0.0.1:8080, 분류기 hybrid
CLASSIFIER=score PORT=9000 uv run server.py   # 분류기·포트 바꾸기
```

브라우저로 `http://127.0.0.1:8080`을 열면 채팅 페이지가 뜹니다. 답변마다 어느 모델(small/big)로 갔는지, 왜 골랐는지, 토큰 수와 시간이 함께 보입니다.

대화하면 서버 터미널에도 요청마다 이런 줄이 찍힙니다.

```text
[router] big   <큰 모델>   score=+0.65 (확실)  토큰 812+240  1.8s
[router] small <작은 모델> score=-0.30 (확실)  토큰 35+12  0.2s
```

### 서버가 하는 일

1. 대화 전체가 아니라 **마지막 사용자 메시지**만 꺼내 분류합니다 (`last_user_text`).
2. 고른 모델 이름으로 `model` 값을 바꿔 토큰 팩토리에 그대로 전달합니다.
3. 답을 그대로 돌려주면서, 고른 모델과 근거를 함께 담습니다.
   - 응답 헤더: `x-router-size`, `x-router-model`, `x-router-note`(URL 인코딩)
   - 스트리밍이 아닐 때 JSON: `"router": {"size", "model", "note"}`
4. 응답의 `usage`에서 토큰 수를 읽어 로그를 남깁니다. 스트리밍일 때는 `stream_options.include_usage`로 마지막 조각에서 받습니다.

### 직접 시험하기

```bash
# 분류해서 보내기
curl http://127.0.0.1:8080/v1/chat/completions -H 'Content-Type: application/json' \
  -d '{"model": "router", "messages": [{"role": "user", "content": "안녕?"}]}'

# 큰 모델로 직접 보내기 (비교용)
curl http://127.0.0.1:8080/v1/chat/completions -H 'Content-Type: application/json' \
  -d '{"model": "big", "messages": [{"role": "user", "content": "안녕?"}]}'
```

표준 라이브러리 `http.server`만 쓰므로 추가 패키지가 없습니다. 실습용 서버라 인증이나 사용량 제한은 없으니, 외부에 공개하지 마세요.
