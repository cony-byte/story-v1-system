// Val.town HTTP val — OpenRouter 프록시 (구글 로그인 검증 후 서버 키로 대신 호출)
// 설정: Val.town → 이 val → Environment Variables 에 아래 추가
//   OPENROUTER_KEY  (필수)  sk-or-...
//   (선택) ALLOWED_DOMAIN=tain.ai · ALLOWED_EMAILS=a@x.com,b@y.com · MODEL=anthropic/claude-sonnet-5 · ALLOW_ORIGIN=https://cony-byte.github.io
const DEFAULTS = {
  MODEL: "anthropic/claude-sonnet-5",
  ALLOWED_DOMAIN: "tain.ai",
  ALLOW_ORIGIN: "https://cony-byte.github.io",
};

export default async function (req: Request): Promise<Response> {
  const env = (k: string) => Deno.env.get(k) || "";
  const allowOrigin = env("ALLOW_ORIGIN") || DEFAULTS.ALLOW_ORIGIN;
  const cors: Record<string, string> = {
    "Access-Control-Allow-Origin": allowOrigin,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Max-Age": "86400",
    "Vary": "Origin",
  };
  const j = (o: unknown, s: number) =>
    new Response(JSON.stringify(o), { status: s, headers: { ...cors, "Content-Type": "application/json" } });

  if (req.method === "OPTIONS") return new Response(null, { headers: cors });
  if (req.method !== "POST") return j({ error: "POST only" }, 405);

  const key = env("OPENROUTER_KEY");
  if (!key) return j({ error: "server missing OPENROUTER_KEY" }, 500);

  // 1) 구글 로그인 검증
  const token = (req.headers.get("Authorization") || "").replace(/^Bearer\s+/i, "").trim();
  if (!token) return j({ error: "missing Google token" }, 401);
  let email = "";
  try {
    const ui = await fetch("https://www.googleapis.com/drive/v3/about?fields=user(emailAddress)", {
      headers: { Authorization: "Bearer " + token },
    });
    if (!ui.ok) return j({ error: "google auth check failed" }, 401);
    email = ((((await ui.json()) as any).user||{}).emailAddress || "").toLowerCase();
  } catch {
    return j({ error: "auth error" }, 401);
  }
  const domain = (env("ALLOWED_DOMAIN") || DEFAULTS.ALLOWED_DOMAIN).toLowerCase();
  const allow = (env("ALLOWED_EMAILS") || "").toLowerCase().split(/[,\s]+/).filter(Boolean);
  if (!(email && (email.endsWith("@" + domain) || allow.includes(email))))
    return j({ error: "not authorized: " + (email || "unknown") }, 403);

  // 2) OpenRouter로 전달 — 서버 키 + 모델 강제
  let body: any = {};
  try { body = await req.json(); } catch {}
  body.model = env("MODEL") || DEFAULTS.MODEL;
  delete body.stream;

  const or = await fetch("https://openrouter.ai/api/v1/chat/completions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: "Bearer " + key,
      "HTTP-Referer": allowOrigin,
      "X-Title": "숏폼 기획 대시보드",
    },
    body: JSON.stringify(body),
  });
  const text = await or.text();
  return new Response(text, { status: or.status, headers: { ...cors, "Content-Type": "application/json" } });
}
