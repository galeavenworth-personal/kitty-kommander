# nbformat v4.5 JSON Structure Reference

nbformat v4.5 is the current stable Jupyter notebook format. Notebooks are plain JSON files with a `.ipynb` extension.

---

## Top-Level Structure

```json
{
  "nbformat": 4,
  "nbformat_minor": 5,
  "metadata": { ... },
  "cells": [ ... ]
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `nbformat` | integer | yes | Major format version. Must be `4`. |
| `nbformat_minor` | integer | yes | Minor version. Use `5` for cell ID support. |
| `metadata` | object | yes | Notebook-level metadata (kernelspec, language_info, etc.). |
| `cells` | array | yes | Ordered list of cell objects. May be empty. |

---

## Metadata Structure

### Top-Level Metadata Object

```json
{
  "metadata": {
    "kernelspec": { ... },
    "language_info": { ... },
    "title": "Optional notebook title",
    "authors": [{"name": "Author Name"}]
  }
}
```

### kernelspec

```json
{
  "kernelspec": {
    "display_name": "Go (gonb)",
    "language": "go",
    "name": "gonb"
  }
}
```

| Field | Description |
|---|---|
| `display_name` | Human-readable kernel name shown in UI |
| `language` | Programming language identifier (`"go"`, `"python"`, `"julia"`) |
| `name` | Kernel name used to look up the kernel spec on disk (`"gonb"`, `"python3"`) |

Common kernelspec values:

| Kernel | `display_name` | `language` | `name` |
|---|---|---|---|
| GoNB | `"Go (gonb)"` | `"go"` | `"gonb"` |
| Python 3 | `"Python 3"` | `"python"` | `"python3"` |
| Python 3 (ipykernel) | `"Python 3 (ipykernel)"` | `"python"` | `"python3"` |
| Julia | `"Julia 1.9"` | `"julia"` | `"julia-1.9"` |

### language_info

Optional. Populated by the kernel when a notebook is saved after execution. Safe to omit when generating fresh notebooks.

```json
{
  "language_info": {
    "name": "go",
    "version": "1.22.0",
    "file_extension": ".go",
    "mimetype": "text/x-go"
  }
}
```

---

## Cell Types

Every cell shares these base fields:

| Field | Type | Required | Description |
|---|---|---|---|
| `cell_type` | string | yes | `"markdown"`, `"code"`, or `"raw"` |
| `metadata` | object | yes | Cell-level metadata. Use `{}` when empty. |
| `source` | array of strings | yes | Cell content as a list of lines. See pitfalls below. |
| `id` | string | yes (v4.5+) | Unique cell identifier. Required in nbformat 4.5. |

### 1. Markdown Cell

```json
{
  "cell_type": "markdown",
  "id": "cell-md-001",
  "metadata": {},
  "source": [
    "# Heading\n",
    "\n",
    "Paragraph text with **bold** and `code`.\n",
    "\n",
    "- Item one\n",
    "- Item two"
  ]
}
```

Markdown cells have no `outputs` or `execution_count`.

### 2. Code Cell

```json
{
  "cell_type": "code",
  "id": "cell-code-001",
  "metadata": {},
  "source": [
    "import \"fmt\"\n",
    "\n",
    "fmt.Println(\"hello, world\")"
  ],
  "outputs": [],
  "execution_count": null
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `outputs` | array | yes | List of output objects. Empty list for unexecuted cells. |
| `execution_count` | integer or null | yes | Execution counter. `null` for unexecuted cells. |

#### Code Cell Metadata (optional fields)

```json
{
  "metadata": {
    "collapsed": false,
    "scrolled": false,
    "tags": ["parameters", "injected-parameters"],
    "jupyter": {
      "source_hidden": false,
      "outputs_hidden": false
    }
  }
}
```

### 3. Raw Cell

Used to pass content through nbconvert without transformation (e.g., RST, LaTeX).

```json
{
  "cell_type": "raw",
  "id": "cell-raw-001",
  "metadata": {
    "format": "text/restructuredtext"
  },
  "source": [
    ".. note::\n",
    "\n",
    "   This is a reStructuredText note."
  ]
}
```

Raw cells have no `outputs` or `execution_count`.

---

## Output Types

All output objects share a `output_type` field. Code cells may have zero or more outputs.

### stream

Written to stdout or stderr via `print()`, `fmt.Println()`, etc.

```json
{
  "output_type": "stream",
  "name": "stdout",
  "text": [
    "hello, world\n",
    "second line\n"
  ]
}
```

| Field | Values | Description |
|---|---|---|
| `name` | `"stdout"` or `"stderr"` | Which stream |
| `text` | array of strings | Output lines |

### display_data

Rich output not tied to a specific execution (e.g., `IPython.display.display()`).

```json
{
  "output_type": "display_data",
  "metadata": {},
  "data": {
    "text/plain": ["<Figure size 640x480>"],
    "image/png": "<base64-encoded-png-data>",
    "text/html": ["<img src='data:image/png;base64,...' />"]
  }
}
```

`data` is a MIME bundle — keys are MIME types, values are the content (string or array of strings for text, base64 string for binary).

### execute_result

The display representation of the return value of the last expression in a cell (like `Out[N]:` in IPython).

```json
{
  "output_type": "execute_result",
  "execution_count": 3,
  "metadata": {},
  "data": {
    "text/plain": ["42"]
  }
}
```

Identical to `display_data` except it carries `execution_count`.

### error

A traceback from an exception raised during execution.

```json
{
  "output_type": "error",
  "ename": "ZeroDivisionError",
  "evalue": "division by zero",
  "traceback": [
    "\u001b[0;31m---------------------------------------------------------------------------\u001b[0m",
    "\u001b[0;31mZeroDivisionError\u001b[0m  Traceback (most recent call last)",
    "Cell \u001b[0;32mIn[2], line 1\u001b[0m",
    "----> 1 1/0",
    "\u001b[0;31mZeroDivisionError\u001b[0m: division by zero"
  ]
}
```

| Field | Type | Description |
|---|---|---|
| `ename` | string | Exception class name |
| `evalue` | string | Exception message |
| `traceback` | array of strings | ANSI-colored traceback lines |

---

## Cell ID Constraints

Introduced in nbformat 4.5. **Required for all cells.**

- Length: 1 to 64 characters
- Allowed characters: `[a-zA-Z0-9_-]` (alphanumeric, hyphens, underscores)
- Must be **unique within the notebook** — duplicates cause validation errors
- Should be stable across saves (do not regenerate IDs on every write)

Recommended naming patterns:
- Sequential: `cell-001`, `cell-002`
- Semantic: `cell-imports`, `cell-analysis`, `cell-plot`
- UUID prefix: `a1b2c3d4-e5f6` (truncate UUIDs to stay readable)

---

## Common Pitfalls

### source must be an array of strings, not a single string

**Wrong:**
```json
"source": "fmt.Println(\"hello\")"
```

**Correct:**
```json
"source": ["fmt.Println(\"hello\")"]
```

Each string in the array represents a line. Lines except the last should end with `\n`.

**Multi-line example:**
```json
"source": [
  "import \"fmt\"\n",
  "\n",
  "func greet(name string) string {\n",
  "    return fmt.Sprintf(\"Hello, %s!\", name)\n",
  "}"
]
```

The last line has no trailing newline. This is a nbformat convention.

### outputs must be present on code cells

**Wrong** (missing `outputs`):
```json
{
  "cell_type": "code",
  "id": "cell-001",
  "metadata": {},
  "source": ["fmt.Println(\"hello\")"],
  "execution_count": null
}
```

**Correct:**
```json
{
  "cell_type": "code",
  "id": "cell-001",
  "metadata": {},
  "source": ["fmt.Println(\"hello\")"],
  "outputs": [],
  "execution_count": null
}
```

### execution_count must be null, not 0, for unexecuted cells

`0` is a valid execution count (it means the cell was run). Use `null` (JSON null, not the string `"null"`) to signal the cell has never been executed.

### metadata must be an object, not null

**Wrong:**
```json
"metadata": null
```

**Correct:**
```json
"metadata": {}
```

### id is required in nbformat 4.5

If `nbformat_minor` is 5 or higher, every cell must have an `id` field. Notebooks generated without IDs will fail `nbformat.validate()`.

### MIME data values for text types are arrays, not strings

In `display_data` and `execute_result` output objects, text MIME types (`text/plain`, `text/html`) follow the same line-array convention as `source`:

**Wrong:**
```json
"data": {
  "text/plain": "hello"
}
```

**Correct:**
```json
"data": {
  "text/plain": ["hello"]
}
```

Binary MIME types (`image/png`, `image/jpeg`) are base64-encoded strings (not arrays).

---

## Minimal Valid Notebook (Go/GoNB)

```json
{
  "nbformat": 4,
  "nbformat_minor": 5,
  "metadata": {
    "kernelspec": {
      "display_name": "Go (gonb)",
      "language": "go",
      "name": "gonb"
    }
  },
  "cells": [
    {
      "cell_type": "markdown",
      "id": "cell-title",
      "metadata": {},
      "source": ["# Notebook Title\n", "\n", "Description."]
    },
    {
      "cell_type": "code",
      "id": "cell-hello",
      "metadata": {},
      "source": ["import \"fmt\"\n", "\n", "fmt.Println(\"hello\")"],
      "outputs": [],
      "execution_count": null
    }
  ]
}
```

---

## Validation

Use the `nbformat` Python library to validate:

```bash
python3 -c "
import nbformat
with open('notebook.ipynb') as f:
    nb = nbformat.read(f, as_version=4)
nbformat.validate(nb)
print('Valid')
"
```

Or with `jupyter nbconvert` as a lightweight check:

```bash
jupyter nbconvert --to notebook --inplace notebook.ipynb
```

When CUE schema is present in this project:

```bash
cue vet schema/notebook/notebook.cue notebook.ipynb
```
