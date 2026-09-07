import type { Team } from "@/lib/types";
import { pct, teamClass } from "@/lib/format";

export function ProbabilityBar({ team, value, max = 1 }: { team: Team; value: number; max?: number }) {
  return (
    <div className="prob-row">
      <div><i className={teamClass(team.id)} /> <b>{team.abbr}</b><span>{team.name}</span></div>
      <div className="prob-track"><i className={teamClass(team.id)} style={{ width: `${Math.max(1, value / max * 100)}%` }} /></div>
      <strong>{pct(value)}</strong>
    </div>
  );
}
