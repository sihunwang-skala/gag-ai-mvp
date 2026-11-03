import { useEffect, useState } from "react";
import { api } from "./api";
import Discover from "./views/Discover";
import ProfileView from "./views/ProfileView";
import Coach from "./views/Coach";
import Companion from "./views/Companion";
import ImageLab from "./views/ImageLab";

const TABS = [
  { id: "discover", label: "취향 테스트", icon: "🎯" },
  { id: "profile", label: "내 프로필", icon: "🫧" },
  { id: "coach", label: "반사신경 코치", icon: "⚡" },
  { id: "companion", label: "컴패니언", icon: "💬" },
  { id: "image", label: "밈·이미지", icon: "🖼️" },
] as const;
type Tab = (typeof TABS)[number]["id"];

export default function App() {
  const [tab, setTab] = useState<Tab>("discover");
  const [health, setHealth] = useState<{ mock_mode: boolean; llm_provider: string } | null>(null);
  const [apiDown, setApiDown] = useState(false);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setApiDown(true));
  }, []);

  return (
    <div className="app">
      <header className="top">
        <div className="logo">Gag<span>AI</span></div>
        <div className={"mode " + (health && !health.mock_mode ? "live" : "")}>
          {apiDown ? "백엔드 연결 안 됨" : health ? (health.mock_mode ? "Mock 모드 (API Key 없음)" : `LLM: ${health.llm_provider}`) : "…"}
        </div>
      </header>
      {apiDown && <div className="banner">백엔드(포트 8000)가 꺼져 있어요. README의 실행 방법을 확인하세요.</div>}
      <nav className="tabs" aria-label="메뉴">
        {TABS.map((t) => (
          <button key={t.id} className={tab === t.id ? "on" : ""} onClick={() => setTab(t.id)}>
            <span aria-hidden>{t.icon}</span>
            <b>{t.label}</b>
          </button>
        ))}
      </nav>
      <main>
        {tab === "discover" && <Discover onDone={() => setTab("profile")} />}
        {tab === "profile" && <ProfileView goTest={() => setTab("discover")} />}
        {tab === "coach" && <Coach />}
        {tab === "companion" && <Companion />}
        {tab === "image" && <ImageLab />}
      </main>
      <footer>로그인 없는 로컬 데모 · 입력한 내용은 모델 학습에 사용되지 않아요</footer>
    </div>
  );
}
