"use client";

import { useRouter } from "next/navigation";

export function SeasonPicker({ current, years }: { current?: number; years: number[] }) {
  const router = useRouter();
  return (
    <label className="season-picker">
      <span>Jump to season</span>
      <select
        aria-label="Choose an IPL season"
        value={current ?? ""}
        onChange={(event) => router.push(`/season/${event.target.value}/`)}
      >
        {!current && <option value="" disabled>Choose year</option>}
        {years.map((year) => <option value={year} key={year}>{year}</option>)}
      </select>
    </label>
  );
}
