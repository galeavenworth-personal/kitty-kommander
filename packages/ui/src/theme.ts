export const theme = {
  bg: "#1a1b26",
  fg: "#c0caf5",
  accent: "#7aa2f7",
  red: "#f7768e",
  green: "#9ece6a",
  yellow: "#e0af68",
  grey: "#565f89",
  dim: "#414868",
} as const;

export type Theme = typeof theme;
