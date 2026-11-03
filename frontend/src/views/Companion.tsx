import { useEffect, useRef, useState } from "react";
import { api, Msg } from "../api";

export default function Companion() {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [styles, setStyles] = useState<{ id: string; label: string }[]>([]);
  const [style, setStyle] = useState("auto");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [rated, setRated] = useState<Record<number, boolean>>({});
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.messages().then(setMsgs).catch((e) => setErr(e.message));
    api.styles().then((r) => { setStyles(r.options); setStyle(r.current); }).catch(() => {});
  }, []);
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs]);

  async function send() {
    const m = text.trim();
    if (!m || busy) return;
    setText(""); setBusy(true); setErr("");
    setMsgs((x) => [...x, { id: -Date.now(), role: "user", content: m, style }]);
    try {
      const r = await api.chat(m);
      setMsgs((x) => [...x, { id: r.id, role: "assistant", content: r.reply, style: r.style }]);
    } catch (e) { setErr((e as Error).message); }
    setBusy(false);
  }

  return (
    <section className="chat">
      <h1>AI 유머 컴패니언</h1>
      <div className="chips" role="radiogroup" aria-label="유머 스타일">
        {styles.map((s) => (
          <button key={s.id} className={style === s.id ? "on" : ""} onClick={() => { setStyle(s.id); api.setStyle(s.id); }}>{s.label}</button>
        ))}
      </div>
      <div className="log">
        {msgs.length === 0 && <p className="muted">오늘 있었던 일을 편하게 말해보세요. 농담을 요청하지 않아도 대화로 받아줄게요.</p>}
        {msgs.map((m) => (
          <div key={m.id} className={"msg " + m.role}>
            <p>{m.content}</p>
            {m.role === "assistant" && m.id > 0 && !rated[m.id] && (
              <span className="rate">
                <button aria-label="좋아요" onClick={() => { api.feedback("companion", String(m.id), 1); setRated({ ...rated, [m.id]: true }); }}>👍</button>
                <button aria-label="별로예요" onClick={() => { api.feedback("companion", String(m.id), -1); setRated({ ...rated, [m.id]: true }); }}>👎</button>
              </span>
            )}
          </div>
        ))}
        {busy && <div className="msg assistant"><p>…</p></div>}
        <div ref={end} />
      </div>
      {err && <p className="err">{err}</p>}
      <form className="composer" onSubmit={(e) => { e.preventDefault(); send(); }}>
        <input value={text} maxLength={800} onChange={(e) => setText(e.target.value)} placeholder="메시지를 입력하세요" />
        <button className="primary" disabled={busy || !text.trim()}>보내기</button>
      </form>
      <div className="row">
        <button className="link" onClick={async () => { await api.clearChat(); setMsgs([]); }}>대화 기록 지우기</button>
      </div>
      <p className="muted small">특정 실존 인물이나 개그맨의 말투는 흉내 내지 않아요.</p>
    </section>
  );
}
