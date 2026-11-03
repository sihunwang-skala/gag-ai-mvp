import { useEffect, useState } from "react";
import { api, CScenario, Evaluation } from "../api";

const LABELS: Record<string, string> = { context_fit: "맥락 적절성", naturalness: "자연스러움", creativity: "창의성", offense_risk: "불쾌 가능성" };

export default function Coach() {
  const [list, setList] = useState<CScenario[]>([]);
  const [idx, setIdx] = useState(0);
  const [reply, setReply] = useState("");
  const [res, setRes] = useState<Evaluation | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [lib, setLib] = useState<Awaited<ReturnType<typeof api.library>> | null>(null);
  const [fb, setFb] = useState(false);
  const [mode, setMode] = useState<"reflex" | "library">("reflex");

  useEffect(() => { api.coachScenarios().then(setList).catch((e) => setErr(e.message)); }, []);
  useEffect(() => { if (mode === "library" && !lib) api.library().then(setLib).catch((e) => setErr(e.message)); }, [mode, lib]);

  const s = list[idx];
  async function submit() {
    if (!s || !reply.trim()) return;
    setBusy(true); setErr(""); setFb(false);
    try { setRes(await api.evaluate(s.id, reply)); } catch (e) { setErr((e as Error).message); }
    setBusy(false);
  }
  function next() { setIdx((idx + 1) % list.length); setReply(""); setRes(null); }

  return (
    <section>
      <h1>유머 반사신경 코치</h1>
      <div className="seg">
        <button className={mode === "reflex" ? "on" : ""} onClick={() => setMode("reflex")}>상황 반응 연습</button>
        <button className={mode === "library" ? "on" : ""} onClick={() => setMode("library")}>암기형 농담 라이브러리</button>
      </div>
      {mode === "library" && lib && (
        <div>
          <p className="notice">{lib.note}</p>
          <ul className="jokes">{lib.jokes.map((j) => <li key={j.id}>{j.text}</li>)}</ul>
        </div>
      )}
      {mode === "reflex" && s && (
        <>
          <div className="card">
            <b>{s.title}</b>
            <p className="muted">{s.context}</p>
            <p className="bubble">“{s.partner_line}”</p>
          </div>
          <textarea value={reply} maxLength={500} onChange={(e) => setReply(e.target.value)} placeholder="바로 떠오르는 반응을 자유롭게 써보세요" rows={3} />
          <div className="row">
            <button className="primary" disabled={busy || !reply.trim()} onClick={submit}>{busy ? "분석 중…" : "내 답변 평가받기"}</button>
            <button onClick={next}>다른 상황</button>
          </div>
          {err && <p className="err">{err}</p>}
          {res && (
            <div className="result">
              <p className="notice">{res.disclaimer}</p>
              <ul className="scores">
                {Object.entries(res.scores).map(([k, v]) => (
                  <li key={k} className={k === "offense_risk" && v >= 4 ? "warn" : ""}>
                    <span>{LABELS[k]}</span><div>{[1, 2, 3, 4, 5].map((n) => <i key={n} className={n <= v ? "on" : ""} />)}</div>
                  </li>
                ))}
              </ul>
              {res.memorized_joke_suspected && <p className="notice warn">외워둔 농담과 비슷해 보여요. 상황 속 소재를 직접 써보세요.</p>}
              {res.strengths.map((t, i) => <p key={"s" + i} className="good">👍 {t}</p>)}
              {res.issues.map((t, i) => <p key={"i" + i} className="fix">💡 {t}</p>)}
              <div className="card better">
                <b>이렇게 바꿔볼 수도 있어요</b>
                <p>“{res.improved_reply}”</p>
                <ul>{res.improvement_reasons.map((t, i) => <li key={i}>{t}</li>)}</ul>
              </div>
              <div className="row">
                {fb ? <span className="muted small">피드백 고마워요!</span> : (
                  <>
                    <span className="muted small">이 평가가 도움이 됐나요?</span>
                    <button onClick={() => { api.feedback("coach", String(res.attempt_id), 1); setFb(true); }}>👍</button>
                    <button onClick={() => { api.feedback("coach", String(res.attempt_id), -1); setFb(true); }}>👎</button>
                  </>
                )}
              </div>
              <p className="muted small">평가 방식: {res.source === "mock" ? "규칙 기반(Mock)" : res.source}</p>
            </div>
          )}
        </>
      )}
    </section>
  );
}
