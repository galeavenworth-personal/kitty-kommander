import React, { useEffect, useState } from "react";
import { execFileSync } from "node:child_process";
import { BeadsContext } from "./useBeads.js";
import type { UseBeadsResult } from "./useBeads.js";
import type { ProjectStats, ReadyItem, Commit } from "../types.js";

const EMPTY: UseBeadsResult = { stats: null, ready: [], commits: [] };

// Per-command failure suppression: we log the FIRST failure for each
// command so the operator sees WHICH dependency (bd vs. git vs. both) is
// broken, then suppress subsequent failures of that same command to keep
// the Dashboard quiet during extended outages. A successful invocation
// clears the command's suppression entry, so if `bd` recovers and then
// fails again later, that recurrence surfaces too.
const failureLogged = new Set<string>();

function logFailure(
  command: string,
  args: readonly string[],
  exitCode: number | null,
  stderr: string
): void {
  if (failureLogged.has(command)) return;
  failureLogged.add(command);
  const codeText = exitCode === null ? "?" : String(exitCode);
  const argsJoined = args.join(" ");
  const stderrTrimmed = stderr.trim();
  process.stderr.write(
    `kommander-ui: ${command} ${argsJoined} exited ${codeText}: ${stderrTrimmed}\n`
  );
}

function runCommand(command: string, args: readonly string[]): string | null {
  try {
    const out = execFileSync(command, args as string[], {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"],
    });
    failureLogged.delete(command);
    return out;
  } catch (err) {
    const e = err as { status?: number | null; stderr?: Buffer | string };
    const status = typeof e.status === "number" ? e.status : null;
    const stderr =
      typeof e.stderr === "string"
        ? e.stderr
        : e.stderr !== undefined
          ? e.stderr.toString("utf8")
          : "";
    logFailure(command, args, status, stderr);
    return null;
  }
}

function parseStats(raw: string | null): ProjectStats | null {
  if (raw === null) return null;
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return null;
  }
  if (typeof parsed !== "object" || parsed === null) return null;
  const summary = (parsed as { summary?: unknown }).summary;
  if (typeof summary !== "object" || summary === null) return null;
  const s = summary as Record<string, unknown>;
  const pick = (k: string): number => {
    const v = s[k];
    return typeof v === "number" ? v : 0;
  };
  return {
    total: pick("total_issues"),
    closed: pick("closed_issues"),
    blocked: pick("blocked_issues"),
    in_progress: pick("in_progress_issues"),
    open: pick("open_issues"),
  };
}

function parseReady(raw: string | null): ReadyItem[] {
  if (raw === null) return [];
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return [];
  }
  if (!Array.isArray(parsed)) return [];
  const out: ReadyItem[] = [];
  for (const entry of parsed) {
    if (typeof entry !== "object" || entry === null) continue;
    const e = entry as Record<string, unknown>;
    const id = typeof e["id"] === "string" ? e["id"] : null;
    const title = typeof e["title"] === "string" ? e["title"] : null;
    const priority = typeof e["priority"] === "number" ? e["priority"] : null;
    if (id === null || title === null || priority === null) continue;
    out.push({ id, title, priority });
  }
  return out;
}

function parseCommits(raw: string | null): Commit[] {
  if (raw === null) return [];
  const lines = raw.split("\n");
  const out: Commit[] = [];
  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed.length === 0) continue;
    const space = trimmed.indexOf(" ");
    if (space <= 0) continue;
    const hash = trimmed.slice(0, space);
    const message = trimmed.slice(space + 1);
    out.push({ hash, message });
  }
  return out;
}

function readAll(): UseBeadsResult {
  const statsRaw = runCommand("bd", ["stats", "--format=json"]);
  const readyRaw = runCommand("bd", ["ready", "--format=json"]);
  const commitsRaw = runCommand("git", ["log", "--oneline", "-n", "10"]);
  return {
    stats: parseStats(statsRaw),
    ready: parseReady(readyRaw),
    commits: parseCommits(commitsRaw),
  };
}

export type ProductionBeadsProviderProps = {
  intervalMs: number;
  children: React.ReactNode;
};

export function ProductionBeadsProvider(
  props: ProductionBeadsProviderProps
): React.ReactElement {
  const [state, setState] = useState<UseBeadsResult>(EMPTY);

  useEffect(() => {
    setState(readAll());
    const handle = setInterval(() => {
      setState(readAll());
    }, props.intervalMs);
    return () => {
      clearInterval(handle);
    };
  }, [props.intervalMs]);

  return React.createElement(
    BeadsContext.Provider,
    { value: state },
    props.children
  );
}
