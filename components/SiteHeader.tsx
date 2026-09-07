import Link from "next/link";

const links = [
  ["Seasons", "/#seasons"],
  ["What if?", "/what-if/"],
  ["Greatest", "/greatest/"],
  ["Matches", "/matches/"],
  ["Methods", "/methods/"],
];

export function SiteHeader() {
  return (
    <header className="site-header shell">
      <Link className="wordmark" href="/" aria-label="How Fluky Was the IPL home">
        HOW FLUKY<span>?</span>
      </Link>
      <nav aria-label="Primary navigation">
        {links.map(([label, href]) => <Link href={href} key={href}>{label}</Link>)}
      </nav>
      <div className="live-pill"><i /> 19 seasons</div>
    </header>
  );
}
