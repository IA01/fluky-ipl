import type { Metadata } from "next";
import { MatchExplorer } from "@/components/MatchExplorer";
import { getAnalytics } from "@/lib/data";

export const metadata: Metadata = { title: "Famous IPL finals" };

export default function MatchesPage() {
  const data = getAnalytics<{ method: string; matches: Parameters<typeof MatchExplorer>[0]["matches"] }>("famous_matches");
  return (
    <main id="main">
      <section className="page-hero shell short">
        <div className="eyebrow"><span>10 FINALS</span> ball-by-ball win probability</div>
        <h1>The moment<br /><em>everything turned.</em></h1>
        <p>Scrub through ten famous IPL finals. Each delivery updates the balance between score, equation, wickets, venue par and pre-match strength.</p>
      </section>
      <section className="interactive-band"><div className="shell"><MatchExplorer matches={data.matches} /></div></section>
      <section className="methods-teaser shell">
        <div><div className="eyebrow"><span>READ THIS</span> What the line means</div><h2>A lens, not an oracle.</h2></div>
        <p>{data.method} It is designed to expose turning points consistently, not to recreate a bookmaker’s historical in-play market.</p>
      </section>
    </main>
  );
}
