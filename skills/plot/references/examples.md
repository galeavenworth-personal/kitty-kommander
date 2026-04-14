# Plot Examples

Copy-pasteable patterns for each chart type. Each shows plotext (quick) and matplotlib/kitty (rich).

---

## Line Plot (Time Series)

### plotext

```bash
python3 -c "
import plotext as plt
import math
x = list(range(50))
y = [math.sin(i * 0.2) for i in x]
plt.plot(x, y)
plt.title('Time Series')
plt.xlabel('Time')
plt.ylabel('Value')
plt.show()
"
```

### matplotlib + kitty

```bash
MPLBACKEND='module://matplotlib-backend-kitty' python3 -c "
import matplotlib.pyplot as plt
import numpy as np
x = np.linspace(0, 10, 200)
plt.plot(x, np.sin(x), label='sin(x)')
plt.plot(x, np.cos(x), label='cos(x)')
plt.title('Time Series')
plt.xlabel('Time')
plt.ylabel('Value')
plt.legend()
plt.tight_layout()
plt.show()
"
```

---

## Scatter Plot (Correlation)

### plotext

```bash
python3 -c "
import plotext as plt
import random
random.seed(42)
x = [random.gauss(0, 1) for _ in range(100)]
y = [xi * 0.8 + random.gauss(0, 0.5) for xi in x]
plt.scatter(x, y)
plt.title('Correlation')
plt.xlabel('X')
plt.ylabel('Y')
plt.show()
"
```

### matplotlib + kitty

```bash
MPLBACKEND='module://matplotlib-backend-kitty' python3 -c "
import matplotlib.pyplot as plt
import numpy as np
rng = np.random.default_rng(42)
x = rng.normal(0, 1, 200)
y = x * 0.8 + rng.normal(0, 0.5, 200)
plt.scatter(x, y, alpha=0.5, s=20)
plt.title('Correlation')
plt.xlabel('X')
plt.ylabel('Y')
plt.tight_layout()
plt.show()
"
```

---

## Bar Chart (Categories)

### plotext

```bash
python3 -c "
import plotext as plt
labels = ['Alpha', 'Beta', 'Gamma', 'Delta', 'Epsilon']
values = [23, 45, 12, 67, 34]
plt.bar(labels, values)
plt.title('Category Comparison')
plt.xlabel('Category')
plt.ylabel('Count')
plt.show()
"
```

### matplotlib + kitty

```bash
MPLBACKEND='module://matplotlib-backend-kitty' python3 -c "
import matplotlib.pyplot as plt
labels = ['Alpha', 'Beta', 'Gamma', 'Delta', 'Epsilon']
values = [23, 45, 12, 67, 34]
plt.bar(labels, values, color='steelblue')
plt.title('Category Comparison')
plt.xlabel('Category')
plt.ylabel('Count')
plt.tight_layout()
plt.show()
"
```

---

## Histogram (Distribution)

### plotext

```bash
python3 -c "
import plotext as plt
import random
random.seed(0)
data = [random.gauss(5, 1.5) for _ in range(500)]
plt.hist(data, bins=20)
plt.title('Distribution')
plt.xlabel('Value')
plt.ylabel('Frequency')
plt.show()
"
```

### matplotlib + kitty

```bash
MPLBACKEND='module://matplotlib-backend-kitty' python3 -c "
import matplotlib.pyplot as plt
import numpy as np
rng = np.random.default_rng(0)
data = rng.normal(5, 1.5, 500)
plt.hist(data, bins=30, edgecolor='white', color='steelblue')
plt.title('Distribution')
plt.xlabel('Value')
plt.ylabel('Frequency')
plt.tight_layout()
plt.show()
"
```

---

## Heatmap (Matrix)

### plotext

```bash
python3 -c "
import plotext as plt
# plotext does not have a native heatmap; fall back to matplotlib for this type
print('Use matplotlib for heatmaps (plotext lacks native heatmap support)')
"
```

### matplotlib + kitty

```bash
MPLBACKEND='module://matplotlib-backend-kitty' python3 -c "
import matplotlib.pyplot as plt
import numpy as np
rng = np.random.default_rng(7)
matrix = rng.random((10, 10))
fig, ax = plt.subplots()
im = ax.imshow(matrix, cmap='viridis', aspect='auto')
plt.colorbar(im, ax=ax)
ax.set_title('Heatmap')
ax.set_xlabel('Column')
ax.set_ylabel('Row')
plt.tight_layout()
plt.show()
"
```

---

## Multi-Subplot Layout

### plotext

```bash
python3 -c "
import plotext as plt
import math
x = list(range(40))
plt.subplots(1, 2)
plt.subplot(1, 1)
plt.plot(x, [math.sin(i * 0.3) for i in x])
plt.title('Sine')
plt.subplot(1, 2)
plt.plot(x, [math.cos(i * 0.3) for i in x])
plt.title('Cosine')
plt.show()
"
```

### matplotlib + kitty

```bash
MPLBACKEND='module://matplotlib-backend-kitty' python3 -c "
import matplotlib.pyplot as plt
import numpy as np
x = np.linspace(0, 4 * np.pi, 200)
fig, axes = plt.subplots(2, 2, figsize=(10, 6))
axes[0, 0].plot(x, np.sin(x));       axes[0, 0].set_title('Sine')
axes[0, 1].plot(x, np.cos(x));       axes[0, 1].set_title('Cosine')
axes[1, 0].plot(x, np.sin(x) ** 2);  axes[1, 0].set_title('Sin^2')
axes[1, 1].plot(x, np.cos(x) ** 2);  axes[1, 1].set_title('Cos^2')
for ax in axes.flat:
    ax.set_xlabel('x')
    ax.set_ylabel('y')
plt.tight_layout()
plt.show()
"
```
