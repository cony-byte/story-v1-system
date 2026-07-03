/**
 * OpenRouter 프록시 (Cloudflare Worker)
 * - OpenRouter 키를 서버 secret으로 숨긴다 (브라우저로 안 내려감).
 * - 호출자는 구글 OAuth 액세스 토큰을 Authorization: Bearer 로 보낸다.
 *   프록시가 그 토큰으로 구글 userinfo를 조회해 이메일을 확인하고,
 *   허용 도메인/allowlist에 있는 사람만 통과시킨다.
 * - 모델은 서버에서 강제(고정)한다 → 아무나 비싼 모델을 못 부른다.
 *
 * 환경변수(Cloudflare 대시보드 또는 wrangler secret):
 *   OPENROUTER_KEY   (secret, 필수)  예: sk-or-...
 *   ALLOWED_DOMAIN   (선택, 기본 tain.ai)  이 도메인 이메일 허용
 *   ALLOWED_EMAILS   (선택)  쉼표/공백 구분 추가 허용 이메일
 *   MODEL            (선택, 기본 anthropic/claude-sonnet-5)
 *   ALLOW_ORIGIN     (선택, 기본 https://cony-byte.github.io)  CORS 허용 오리진
 */
const DEFAULTS = {
  MODEL: "anthropic/claude-sonnet-5",
  ALLOWED_DOMAIN: "tain.ai",
  ALLOW_ORIGIN: "https://cony-byte.github.io",
};

export default {
  async fetch(request, env) {
    const allowOrigin = env.ALLOW_ORIGIN || DEFAULTS.ALLOW_ORIGIN;
    const cors = {
      "Access-Control-Allow-Origin": allowOrigin,
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Authorization",
      "Access-Control-Max-Age": "86400",
      Vary: "Origin",
    };
    if (request.method === "OPTIONS") return new Response(null, { headers: cors });
    if (request.method !== "POST") return j({ error: "POST only" }, 405, cors);
    if (!env.OPENROUTER_KEY) return j({ error: "server missing OPENROUTER_KEY" }, 500, cors);

    // 1) 구글 로그인 검증 — 액세스 토큰으로 이메일 확인
    const token = (request.headers.get("Authorization") || "").replace(/^Bearer\s+/i, "").trim();
    if (!token) return j({ error: "missing Google token" }, 401, cors);
    let email = "";
    try {
      const ui = await fetch("https://www.googleapis.com/oauth2/v3/userinfo", {
        headers: { Authorization: "Bearer " + token },
      });
      if (!ui.ok) return j({ error: "google auth check failed" }, 401, cors);
      email = ((await ui.json()).email || "").toLowerCase();
    } catch (e) {
      return j({ error: "auth error" }, 401, cors);
    }
    const domain = (env.ALLOWED_DOMAIN || DEFAULTS.ALLOWED_DOMAIN).toLowerCase();
    const allowlist = (env.ALLOWED_EMAILS || "").toLowerCase().split(/[,\s]+/).filter(Boolean);
    const ok = email && (email.endsWith("@" + domain) || allowlist.includes(email));
    if (!ok) return j({ error: "not authorized: " + (email || "unknown") }, 403, cors);

    // 2) OpenRouter로 전달 — 서버 키 사용 + 모델 강제
    let body = {};
    try { body = await request.json(); } catch (e) {}
    body.model = env.MODEL || DEFAULTS.MODEL; // 모델 고정 (클라이언트 값 무시)
    delete body.stream; // 스트리밍 비활성 (단순화)

    const or = await fetch("https://openrouter.ai/api/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer " + env.OPENROUTER_KEY,
        "HTTP-Referer": allowOrigin,
        "X-Title": "숏폼 기획 대시보드",
      },
      body: JSON.stringify(body),
    });
    const text = await or.text();
    return new Response(text, {
      status: or.status,
      headers: { ...cors, "Content-Type": "application/json" },
    });
  },
};

function j(obj, status, cors) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { ...cors, "Content-Type": "application/json" },
  });
}
