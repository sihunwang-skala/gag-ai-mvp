import { useEffect, useState } from "react";
import { api, Profile } from "../api";

function Radar({ p }: { p: Profile }) {
  const keys = Object.keys(p.types);
  const max = Math.max(0.01, ...Object.values(p.vector));
  const R = 90, C = 130;
  const pt = (i: number, r: number) => {
    const a = (Math.PI * 2 * i) / keys.length - Math.PI / 2;
    return [C + Math.cos(a) * r, C + Math.sin(a) * r] as const;
  };
  const poly = keys.map((k, i) => pt(i, (R * p.vector[k]) / max).join(",")).join(" ");
  return (
    <svg viewBox="0 0 260 260" className="radar" role="img" aria-label="유머 취향 레이더 차트">
      {[0.33, 0.66, 1].map((f) => (
        <polygon key={f} points={keys.map((_, i) => pt(i, R * f).join(",")).join(" ")} className="grid" />
      ))}
      <polygon points={poly} className="shape" />
      {keys.map((k, i) => {
        const [x, y] = pt(i, R + 22);
        return <text key={k} x={x} y={y} textAnchor="middle" dominantBaseline="middle">{p.types[k]}</text>;
      })}
    </svg>
  );
}

export default function ProfileView({ goTest }: { goTest: () => void }) {
  const [p, setP] = useState<Profile | null>(null);
  const [msg, setMsg] = useState("");
  const load = () => api.profile().then(setP).catch((e) => setMsg(e.message));
  useEffect(() => { load(); }, []);

  if (!p) return <p className="muted">{msg || "불러오는 중…"}</p>;
  if (p.answered === 0)
    return (
      <section className="center">
        <h1>아직 취향 데이터가 없어요</h1>
        <p className="muted">5개 상황만 고르면 내 유머 프로필이 만들어져요.</p>
        <button className="primary" onClick={goTest}>취향 테스트 시작</button>
      </section>
    );
  const sorted = Object.keys(p.types).sort((a, b) => p.vector[b] - p.vector[a]);
  return (
    <section>
      <h1>내 유머 프로필</h1>
      <p className="lead">
        {p.top_types.map((t) => p.types[t]).join(" + ")} 쪽에 가까워요
        <span className="chip">응답 {p.answered}/5 · 신뢰도 {p.confidence === "low" ? "낮음" : "보통"}</span>
      </p>
      <Radar p={p} />
      <ul className="bars">
        {sorted.map((k) => (
          <li key={k}>
            <span>{p.types[k]}</span>
            <div><i style={{ width: `${Math.round(p.vector[k] * 100)}%` }} /></div>
            <em>{Math.round(p.vector[k] * 100)}%</em>
          </li>
        ))}
      </ul>
      <p className="muted small">{p.note}</p>
      <div className="row">
        <button onClick={goTest}>다시 테스트</button>
        <button
          className="danger"
          onClick={async () => {
            if (!confirm("이 브라우저의 모든 데모 데이터(설문·코치 기록·대화·피드백)를 삭제할까요?")) return;
            await api.deleteMe();
            setMsg("삭제했어요.");
            load();
          }}
        >내 데이터 모두 삭제</button>
      </div>
      {msg && <p className="muted small">{msg}</p>}
    </section>
  );
}
