import { useEffect, useState } from "react";
import { api, DScenario } from "../api";

export default function Discover({ onDone }: { onDone: () => void }) {
  const [items, setItems] = useState<DScenario[]>([]);
  const [i, setI] = useState(0);
  const [picked, setPicked] = useState<string | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.scenarios().then(setItems).catch((e) => setErr(e.message));
  }, []);

  if (err) return <p className="err">{err}</p>;
  if (!items.length) return <p className="muted">불러오는 중…</p>;
  const s = items[i];

  async function choose(type: string) {
    setPicked(type);
    try {
      await api.answer(s.id, type);
    } catch (e) {
      setErr((e as Error).message);
      return;
    }
    setTimeout(() => {
      setPicked(null);
      if (i + 1 >= items.length) onDone();
      else setI(i + 1);
    }, 350);
  }

  return (
    <section>
      <div className="progress" aria-label={`${i + 1}/${items.length}`}>
        {items.map((_, k) => <i key={k} className={k <= i ? "on" : ""} />)}
      </div>
      <h1>이 상황, 어떤 반응이 제일 웃겨요?</h1>
      <p className="situation">{s.situation}</p>
      <div className="options">
        {s.options.map((o) => (
          <button key={o.humor_type} className={"opt " + (picked === o.humor_type ? "picked" : "")} disabled={!!picked} onClick={() => choose(o.humor_type)}>
            {o.text}
          </button>
        ))}
      </div>
      <p className="muted small">가장 웃긴 하나만 고르세요. 다시 하면 이전 선택을 덮어써요.</p>
    </section>
  );
}
