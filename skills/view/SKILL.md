---
name: view
description: This skill should be used when the user or agent needs to view, display, preview, or inspect images (PNG, JPG, GIF, SVG, WebP), PDFs, or documents in the terminal. Also use for comparing images side-by-side, viewing screenshots, inspecting visual test output, or rendering any visual content. Activate for "show me", "look at", "display", "preview", "compare", "inspect" requests involving files.
---

## When to Use This Skill
- Viewing images (screenshots, test output, generated graphics, diagrams)
- Reading PDF documents
- Comparing two or more images side-by-side
- Previewing visual content before committing/shipping
- Inspecting file content that benefits from visual rendering

## Image Viewing (timg)

### Single image
```bash
/usr/bin/timg <file.png>
```

### Side-by-side comparison (grid layout)
```bash
/usr/bin/timg --grid=2x1 before.png after.png
```

### Constrained size
```bash
/usr/bin/timg -g 80x40 <file.png>    # Width x Height in cells
/usr/bin/timg -g 120x60 large-diagram.svg
```

### Multiple images in grid
```bash
/usr/bin/timg --grid=3x2 img1.png img2.png img3.png img4.png img5.png img6.png
```

### Supported formats
PNG, JPEG, GIF (animated), SVG, WebP, BMP, ICO, TIFF, PDF (first page), QOI

## Document Viewing (mcat)

### PDF to readable text
```bash
mcat document.pdf
```
This converts and formats the document for terminal display. Good for agent consumption of PDF content.

### Other document formats
```bash
mcat README.md       # Formatted markdown
mcat data.json       # Syntax-highlighted JSON
mcat report.html     # HTML rendered as text
```

## Guidelines
- For images: default to `/usr/bin/timg` — it uses Kitty graphics protocol for GPU-accelerated rendering. IMPORTANT: Always use `/usr/bin/timg` (the system binary), NOT bare `timg` which resolves to a Python wrapper that shadows it.
- For documents: default to `mcat` — it converts to readable terminal output
- For PDFs where visual layout matters: use `/usr/bin/timg document.pdf` (renders first page as image)
- For image comparison: always use `--grid` flag to show side-by-side
- Specify `-g WxH` when terminal space is constrained or images are very large
- When viewing multiple related images, group them in a grid for easier comparison
