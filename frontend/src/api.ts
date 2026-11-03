// 로그인 없는 로컬 데모: 브라우저에 랜덤 ID를 저장해 X-Demo-User 헤더로 보낸다.
function demoId(): string {
  try {
    let id = localStorage.getItem("gag_demo_id");
    if (!id) {
      id = crypto.randomUUID();
      localStorage.setItem("gag_demo_id", id);
    }
    return id;
  } catch {
    return "session-" + Math.random().toString(36).slice(2, 12);
  }
}
const ID = demoId();

async function req<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { "X-Demo-User": ID, ...(init.headers as Record<string, string>) };
  if (init.body && !(init.body instanceof FormData)) headers["Content-Type"] = "application/json";
  const r = await fetch("/api" + path, { ...init, headers });
  if (!r.ok) {
    let msg = r.statusText;
    try {
      const j = await r.json();
      msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
    } catch { /* ignore */ }
    throw new Error(msg);
  }
  return r.json();
}
const post = <T,>(p: string, body: unknown) => req<T>(p, { method: "POST", body: JSON.stringify(body) });

export type Option = { humor_type: string; text: string };
export type DScenario = { id: string; situation: string; options: Option[] };
export type Profile = { answered: number; vector: Record<string, number>; top_types: string[]; confidence: string; note: string; types: Record<string, string> };
export type CScenario = { id: string; title: string; context: string; partner_line: string };
export type Evaluation = {
  attempt_id: number; scores: { context_fit: number; naturalness: number; creativity: number; offense_risk: number };
  strengths: string[]; issues: string[]; improved_reply: string; improved_style: string; improvement_reasons: string[];
  memorized_joke_suspected: boolean; safety_flags: string[]; disclaimer: string; source: string;
};
export type Msg = { id: number; role: "user" | "assistant"; content: string; style: string };
export type ImageResult = { analysis: string; suggested_reactions: string[]; note: string; source: string; vision_used: boolean };

export const api = {
  health: () => req<{ mock_mode: boolean; llm_provider: string; supports_vision: boolean }>("/health"),
  scenarios: () => req<DScenario[]>("/discovery/scenarios"),
  answer: (scenario_id: string, humor_type: string) => post<Profile>("/discovery/responses", { scenario_id, humor_type }),
  profile: () => req<Profile>("/profile"),
  coachScenarios: () => req<CScenario[]>("/coach/scenarios"),
  library: () => req<{ note: string; jokes: { id: string; text: string; humor_type: string }[] }>("/coach/library"),
  evaluate: (scenario_id: string, reply: string) => post<Evaluation>("/coach/evaluate", { scenario_id, reply }),
  styles: () => req<{ current: string; options: { id: string; label: string }[] }>("/companion/styles"),
  setStyle: (style: string) => req("/companion/style", { method: "PUT", body: JSON.stringify({ style }) }),
  messages: () => req<Msg[]>("/companion/messages"),
  chat: (message: string) => post<{ id: number; reply: string; style: string; source: string }>("/companion/chat", { message }),
  clearChat: () => req("/companion/messages", { method: "DELETE" }),
  feedback: (target_type: string, target_id: string, rating: 1 | -1) => post("/feedback", { target_type, target_id, rating }),
  analyzeImage: (file: File, caption: string, rights: boolean) => {
    const fd = new FormData();
    fd.append("image", file);
    fd.append("caption", caption);
    fd.append("rights_confirmed", String(rights));
    return req<ImageResult>("/multimodal/analyze", { method: "POST", body: fd });
  },
  deleteMe: () => req("/me", { method: "DELETE" }),
};
