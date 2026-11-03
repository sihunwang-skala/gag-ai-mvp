import { useState } from "react";
import { api, ImageResult } from "../api";

export default function ImageLab() {
  const [file, setFile] = useState<File | null>(null);
  const [caption, setCaption] = useState("");
  const [rights, setRights] = useState(false);
  const [res, setRes] = useState<ImageResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function run() {
    if (!file) return;
    setBusy(true); setErr(""); setRes(null);
    try { setRes(await api.analyzeImage(file, caption, rights)); } catch (e) { setErr((e as Error).message); }
    setBusy(false);
  }

  return (
    <section>
      <h1>밈·이미지 유머 분석</h1>
      <p className="muted">직접 만들었거나 사용 권리가 있는 이미지만 올려주세요. 업로드한 파일은 저장하거나 학습에 쓰지 않아요.</p>
      <input type="file" accept="image/png,image/jpeg,image/webp" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
      {file && <img className="preview" src={URL.createObjectURL(file)} alt="업로드 미리보기" />}
      <input value={caption} maxLength={300} onChange={(e) => setCaption(e.target.value)} placeholder="상황 설명이나 밈 문구 (선택)" />
      <label className="check"><input type="checkbox" checked={rights} onChange={(e) => setRights(e.target.checked)} /> 이 이미지에 대한 사용 권리가 있어요</label>
      <button className="primary" disabled={!file || !rights || busy} onClick={run}>{busy ? "분석 중…" : "유머 맥락 분석"}</button>
      {err && <p className="err">{err}</p>}
      {res && (
        <div className="result">
          <p>{res.analysis}</p>
          {!res.vision_used && <p className="notice">현재 모델/환경에서는 이미지를 직접 보지 못해 설명 문구만으로 추정했어요.</p>}
          {res.suggested_reactions.map((r, i) => <p key={i} className="bubble">“{r}”</p>)}
          <p className="muted small">{res.note}</p>
        </div>
      )}
      <p className="muted small">음성·영상 분석은 후속 단계에서 지원할 예정이에요.</p>
    </section>
  );
}
