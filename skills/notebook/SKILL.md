---
name: notebook
description: This skill should be used when the user asks about Jupyter notebooks, .ipynb files, interactive documents, GoNB (Go kernel), or projection notebooks. Also use when generating structured interactive documents, creating CUE-validated notebooks, launching euporie for terminal notebook editing, or working with the nbformat specification. Activate for "create a notebook", "open notebook", "generate ipynb", "interactive document", "Go notebook" requests.
---

## When to Use This Skill
- Creating new .ipynb notebooks (Go or Python)
- Generating notebooks programmatically from structured data
- Opening notebooks for interactive editing in the terminal
- Validating notebook structure
- Working with GoNB (Go Jupyter kernel)

## Generating Notebooks

Notebooks are JSON files following nbformat v4.5. Generate them directly:

```python
python3 -c "
import json

notebook = {
    'nbformat': 4,
    'nbformat_minor': 5,
    'metadata': {
        'kernelspec': {
            'display_name': 'Go (gonb)',
            'language': 'go',
            'name': 'gonb'
        }
    },
    'cells': [
        {
            'cell_type': 'markdown',
            'metadata': {},
            'source': ['# Title\n', 'Description here.'],
            'id': 'cell-001'
        },
        {
            'cell_type': 'code',
            'metadata': {},
            'source': ['fmt.Println(\"hello\")'],
            'outputs': [],
            'execution_count': None,
            'id': 'cell-002'
        }
    ]
}

with open('output.ipynb', 'w') as f:
    json.dump(notebook, f, indent=1)
print('Wrote output.ipynb')
"
```

### Cell ID Requirements
- 1-64 characters
- Alphanumeric, hyphens, underscores only: `[a-zA-Z0-9_-]`
- Must be unique within the notebook

### Kernel Options
- **Go (GoNB)**: `{'display_name': 'Go (gonb)', 'language': 'go', 'name': 'gonb'}`
- **Python**: `{'display_name': 'Python 3', 'language': 'python', 'name': 'python3'}`

## Interactive Editing (euporie)

Launch a notebook in the terminal TUI:
```bash
euporie notebook path/to/notebook.ipynb
```

euporie supports:
- Full cell execution with kernel connection
- Rich output rendering (images, HTML, LaTeX) via Kitty graphics protocol
- Cell navigation, editing, adding, deleting
- Multiple notebooks in tabs

## GoNB Specifics

GoNB is the Go Jupyter kernel. Key patterns:
- Each cell is compiled and executed (not interpreted)
- Variables, functions, types persist across cells
- Use `!` prefix for shell commands: `!go version`
- Auto-imports: GoNB automatically runs `go get` for new imports
- Supports Go generics, goroutines, modules

### GoNB Display Functions
```go
// Import the display package
import "github.com/janpfeifer/gonb/gonbui"

// Display rich content
gonbui.DisplayHtml("<h1>Hello</h1>")
gonbui.DisplayMarkdown("## Section")
gonbui.DisplayImage(pngBytes)
```

## CUE Validation (when schema available)

Once the CUE schema is created (schema/notebook/notebook.cue), validate with:
```bash
cue vet schema/notebook/notebook.cue notebook.ipynb
```

## Guidelines
- Default kernel to Go (gonb) for actuator project notebooks
- Use Python kernel only when the task requires Python-specific libraries
- Always set cell IDs explicitly — don't let them be auto-generated
- Source arrays should split on newlines: `['line1\n', 'line2\n', 'last line']`
- Set `execution_count` to null and `outputs` to [] for fresh notebooks
- Notebooks render natively on GitHub — use them for documentation that benefits from interactivity
