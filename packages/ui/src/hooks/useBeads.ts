import React, { createContext, useContext } from "react";
import type { BeadsFixture, ProjectStats, ReadyItem, Commit } from "../types.js";

export type UseBeadsResult = {
  stats: ProjectStats | null;
  ready: ReadyItem[];
  commits: Commit[];
};

const BeadsContext = createContext<UseBeadsResult | null>(null);

export type BeadsProviderProps = {
  value: BeadsFixture;
  children: React.ReactNode;
};

export function BeadsProvider(props: BeadsProviderProps): React.ReactElement {
  const value: UseBeadsResult = {
    stats: props.value.stats ?? null,
    ready: props.value.ready ?? [],
    commits: props.value.commits ?? [],
  };
  return React.createElement(BeadsContext.Provider, { value }, props.children);
}

export function useBeads(): UseBeadsResult {
  const ctx = useContext(BeadsContext);
  if (ctx === null) {
    return { stats: null, ready: [], commits: [] };
  }
  return ctx;
}
