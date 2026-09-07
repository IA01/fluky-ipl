import fs from "node:fs";
import path from "node:path";
import type { ParsedSeason, SimulationSeason } from "./types";

function readJson<T>(relativePath: string): T {
  return JSON.parse(fs.readFileSync(path.join(process.cwd(), relativePath), "utf8")) as T;
}
export function getSeason(year: number) {
  return {
    parsed: readJson<ParsedSeason>(`data/parsed/seasons/${year}.json`),
    simulation: readJson<SimulationSeason>(`data/simulations/${year}.json`),
  };
}

export function getAnalytics<T = Record<string, unknown>>(name: string): T {
  return readJson<T>(`data/analytics/${name}.json`);
}

export function getRating<T = Record<string, unknown>>(name: string): T {
  return readJson<T>(`data/ratings/${name}.json`);
}
