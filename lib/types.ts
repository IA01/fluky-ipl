export type Team = { id: string; name: string; abbr: string };

export type ActualRow = {
  team: Team;
  played: number;
  won: number;
  lost: number;
  no_result: number;
  points: number;
  net_run_rate: number;
  position: number;
};

export type ParsedSeason = {
  season: number;
  config: { playoff_format: string; neutral_host: boolean };
  summary: {
    matches: number;
    records: number;
    league_matches: number;
    playoff_matches: number;
    voided_matches: number;
    stages: Record<string, number>;
  };
  validation: { status: string; source_url: string; teams_checked: number; note: string };
  actual_table: ActualRow[];
  matches: Array<Record<string, unknown>>;
};

export type SimulationTeam = {
  team: Team;
  actual_points: number;
  actual_position: number;
  expected_points: number;
  median_points: number;
  expected_position: number;
  luck_index: number;
  playoff_probability: number;
  final_probability: number;
  title_probability: number;
  points_distribution: Record<string, number>;
  position_distribution: Record<string, number>;
  league_end_elo: number;
};

export type SimulationSeason = {
  season: number;
  seed: number;
  simulation_count: number;
  model: {
    elo_scale: number;
    home_advantage: number;
    playoff_format: string;
    no_result_policy: string;
    nrr_policy: string;
  };
  actual_champion: Team;
  champion_title_probability: number;
  fluke_score: number;
  robbery: { team: Team; title_probability: number };
  dominance: { team: Team; elo_gap_to_field: number };
  teams: SimulationTeam[];
  fixtures: Array<Record<string, unknown>>;
};

export const YEARS = Array.from({ length: 19 }, (_, index) => 2008 + index);
