# OpenRouter 프록시 배포 (Cloudflare Workers · 무료)

목적: OpenRouter 키를 **서버 secret**에 숨기고, 팀원은 **구글 로그인만** 하면 AI 초안 생성을 쓰게 한다.
(키는 브라우저로 안 내려감 → 공개 사이트에 키 노출 없음)

## 방법 A — Cloudflare 대시보드 (가장 쉬움, 클릭만)

1. https://dash.cloudflare.com → **Workers & Pages** → **Create** → **Create Worker**
2. 이름 정하고 (예: `story-ai-proxy`) → **Deploy** (기본 코드로 일단 생성)
3. **Edit code** → 기본 코드 전부 지우고 `openrouter-proxy.js` 내용 붙여넣기 → **Deploy**
4. Worker의 **Settings → Variables and Secrets**:
   - **Secret** 추가: 이름 `OPENROUTER_KEY`, 값 = 본인 OpenRouter 키(`sk-or-...`)
   - (선택) 변수 `ALLOWED_DOMAIN` = `tain.ai` (이 도메인 이메일만 허용 · 기본값도 tain.ai)
   - (선택) 변수 `ALLOWED_EMAILS` = 도메인 밖 허용할 이메일들 (쉼표 구분)
   - (선택) 변수 `MODEL` = `anthropic/claude-sonnet-5` (기본값 동일)
   - (선택) 변수 `ALLOW_ORIGIN` = `https://cony-byte.github.io` (기본값 동일)
5. 배포된 주소 확인: `https://story-ai-proxy.<계정>.workers.dev`
6. 이 주소를 앱의 `AI_PROXY_URL`(app-shell.html 상단)에 넣고 push → 끝.

## 방법 B — wrangler (CLI)

```bash
npm i -g wrangler
wrangler login
# 이 파일이 있는 폴더에서
wrangler deploy proxy/openrouter-proxy.js --name story-ai-proxy
wrangler secret put OPENROUTER_KEY --name story-ai-proxy   # 붙여넣기: sk-or-...
# (선택) 변수는 대시보드 또는 wrangler.toml [vars] 로 설정
```

## 동작 / 보안 요약

- 앱 → (구글 액세스 토큰) → **프록시** → 이메일 검증(도메인/allowlist) → OpenRouter(서버 키) → 응답
- 허용 안 된 이메일이면 `403`. 토큰 없으면 `401`.
- 모델은 서버에서 **강제 고정** → 호출자가 비싼 모델로 못 바꿈.
- 남용/한도 걱정되면 OpenRouter에서 그 키에 **월 지출 한도**를 걸어두면 안전.

## 확인

배포 후 앱에서 로그인 → `＋캐릭터`에서 🎲 → 실제 초안이 생성되면 성공.
`403`이면 그 계정 이메일이 `ALLOWED_DOMAIN`/`ALLOWED_EMAILS`에 없는 것.
