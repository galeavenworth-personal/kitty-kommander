---
name: plot
description: This skill should be used when the user asks to plot data, create charts, visualize data, generate graphs, or display histograms, scatter plots, heatmaps, bar charts, or any data visualization. Also use when the agent needs to visualize data to understand patterns, debug numerical output, or present analysis results. Use even for quick "show me this data" requests.
---

## When to Use This Skill

- User asks for any plot/chart/graph/visualization
- Agent needs to inspect data visually (debugging, analysis)
- Quick data exploration from CLI output

## Backends (in order of preference)

### 1. plotext (Quick CLI plots)

For fast, terminal-native plots from data. No image rendering needed.

```bash
python3 -c "
import plotext as plt
plt.scatter([1,2,3,4], [1,4,9,16])
plt.title('Example')
plt.show()
"
```

Use for: quick exploration, piped data, when speed matters more than beauty.

### 2. matplotlib with Kitty backend (Rich plots)

For publication-quality plots rendered inline via Kitty graphics protocol.
CRITICAL: Always set the backend BEFORE importing matplotlib:

```bash
MPLBACKEND='module://matplotlib-backend-kitty' python3 -c "
import matplotlib.pyplot as plt
import numpy as np
x = np.linspace(0, 10, 100)
plt.plot(x, np.sin(x))
plt.title('Sine Wave')
plt.savefig('/dev/stdout', format='png')
plt.show()
"
```

Use for: rich plots, multiple subplots, custom styling, when visual quality matters.

### 3. gnuplot with Kitty terminal (Interactive)

For interactive, resizable plots.

```bash
gnuplot -e "set terminal kitty; plot sin(x)"
```

Use for: mathematical functions, interactive exploration, when user wants to resize/zoom.

## Guidelines

- Default to plotext for simple requests
- Escalate to matplotlib for multi-series, subplots, or styled plots
- Always include axis labels and titles
- For piped data: parse stdin, detect format (CSV, TSV, whitespace-separated)
- When plotting from files: read the data first, choose appropriate chart type
