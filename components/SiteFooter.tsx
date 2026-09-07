import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="shell">
      <Link className="wordmark" href="/">HOW FLUKY<span>?</span></Link>
      <p>Cricsheet ball-by-ball data · 10,000 replays per season<br />Open methods. Fixed seeds. Numbers before narratives.</p>
      <span>2008—2026</span>
    </footer>
  );
}
