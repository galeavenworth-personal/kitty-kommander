import React from "react";
import { Box, Text, ListItem } from "../adapters/index.js";
import { useBeads } from "../hooks/useBeads.js";
import { theme } from "../theme.js";

function percentComplete(total: number, closed: number): number {
  if (total <= 0) return 0;
  return Math.round((closed / total) * 100);
}

const BAR_WIDTH = 20;

function renderBar(pct: number): string {
  const filled = Math.round((pct / 100) * BAR_WIDTH);
  const empty = BAR_WIDTH - filled;
  return "#".repeat(filled) + "-".repeat(empty);
}

export function Sidebar(): React.ReactElement {
  const { stats, ready, commits } = useBeads();

  const total = stats?.total ?? 0;
  const closed = stats?.closed ?? 0;
  const blocked = stats?.blocked ?? 0;
  const wip = stats?.in_progress ?? 0;
  const pct = percentComplete(total, closed);

  return (
    <Box flexDirection="column" padding={1}>
      <Box flexDirection="column" marginBottom={1}>
        <Text bold color={theme.accent}>PROJECT HEALTH</Text>
        <Text testId="health-bar" className="health-bar">
          {`[${renderBar(pct)}] ${pct}% complete`}
        </Text>
        <Text dimColor color={theme.grey}>
          {`${closed} closed  ${blocked} blocked  ${wip} wip`}
        </Text>
      </Box>

      <Box flexDirection="column" marginBottom={1}>
        <Text bold color={theme.accent}>READY QUEUE</Text>
        {ready.length === 0 ? (
          <Text dimColor color={theme.grey}>No work items</Text>
        ) : (
          <Box flexDirection="column" className="ready-queue">
            {ready.map((item) => (
              <ListItem
                key={item.id}
                className="ready-queue-item"
                testId={`ready-${item.id}`}
              >
                {`P${item.priority} ${item.title}`}
              </ListItem>
            ))}
          </Box>
        )}
      </Box>

      <Box flexDirection="column">
        <Text bold color={theme.accent}>RECENT COMMITS</Text>
        {commits.length === 0 ? (
          <Text dimColor color={theme.grey}>No commits yet</Text>
        ) : (
          <Box flexDirection="column" className="commit-list">
            {commits.map((c) => (
              <Text key={c.hash} color={theme.fg}>
                {`${c.hash} ${c.message}`}
              </Text>
            ))}
          </Box>
        )}
      </Box>
    </Box>
  );
}
