export function pct(value: number, digits = 1) {
  return `${(value * 100).toFixed(digits)}%`;
}
export function signed(value: number, digits = 1) {
  return `${value > 0 ? "+" : ""}${value.toFixed(digits)}`;
}

export function teamClass(id: string) {
  return `team-${id.replaceAll("_", "-")}`;
}
