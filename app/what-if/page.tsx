import type { Metadata } from "next";
import { WhatIfMachine } from "@/components/WhatIfMachine";
import { getAnalytics } from "@/lib/data";

export const metadata: Metadata = { title: "What-If Machine" };

export default function WhatIfPage() {
  const data = getAnalytics<Parameters<typeof WhatIfMachine>[0]["data"]>("what_if");
  return (
    <main id="main">
      <section className="page-hero shell short">
        <div className="eyebrow"><span>INTERACTIVE</span> live in your browser</div>
        <h1>Change one game.<br /><em>Rewrite history.</em></h1>
        <p>Pick a season, overturn a result, alter team strength, or stress-test the auction reset. Then watch the table and title odds rebuild.</p>
      </section>
      <section className="machine-band"><div className="shell"><WhatIfMachine data={data} /></div></section>
    </main>
  );
}
