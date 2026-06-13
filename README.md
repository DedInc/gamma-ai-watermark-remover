# Gamma Watermark Remover

A local web tool to strip the **"Made with Gamma"** branding from PDF and PowerPoint (`.pptx`) files exported from [gamma.app](https://gamma.app) free accounts.

It runs a **FastAPI** backend that parses the document structure to identify and remove specific watermark elements based on coordinates and object properties.

![Python 3.7+](https://img.shields.io/badge/Python-3.7%2B-blue?logo=python&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-green)
![FastAPI](https://img.shields.io/badge/FastAPI-2.x-009688?logo=fastapi&logoColor=white)

---

## Features

- **PDF:** Scans pages using PyMuPDF (fitz) for images linked to the gamma.app domain located in the bottom-right corner.
- **PPTX:** Uses `python-pptx` to parse the presentation. Since Gamma embeds the watermark in the **Slide Layouts** (masters) rather than individual slides, the script targets the master layouts to remove the branding globally across the presentation.
- **Batch-ready:** Upload multiple files from the web UI.
- **Dark / Light mode:** Toggle between themes; preference is saved locally.
- **Session history:** Track your processed files within a browser session.

---

## Quick Start

Requires **Python 3.7+**.

1. **Clone the repo:**
   ```bash
   git clone https://github.com/DedInc/gamma-ai-watermark-remover.git
   cd gamma-ai-watermark-remover
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the server:**
   ```bash
   python app.py
   ```

4. Open **`http://localhost:8999`** in your browser.

---

## Technical Notes

The detection logic is heuristic-based:

- **PPTX:** Checks `prs.slide_layouts`. If a shape contains a hyperlink to `gamma.app` and is positioned beyond the 70% mark of the slide width/height, it gets deleted.
- **PDF:** Iterates through page objects. If a clickable image points to the Gamma domain, the object is removed from the drawing stream.

> **Note:** If Gamma changes their export coordinates or DOM structure, the coordinate offsets in the processor modules will need to be updated.

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `fastapi` / `uvicorn` | Web server |
| `pymupdf` (fitz) | PDF processing |
| `python-pptx` | PowerPoint manipulation |
| `python-multipart` | File uploads |
| `jinja2` | HTML templating |
| `aiofiles` | Async file serving |

---

## Project Structure

```
├── app.py                   # FastAPI application entry point
├── processors/
│   ├── pdf/
│   │   ├── detector.py      # PDF watermark detection
│   │   └── remover.py       # PDF watermark removal
│   └── pptx/
│       ├── detector.py      # PPTX watermark detection
│       └── remover.py       # PPTX watermark removal
├── utils/
│   ├── file_helpers.py      # File type validation & MIME types
│   └── processors.py        # High-level processor orchestration
├── templates/
│   └── index.html           # Web UI (single-page)
├── uploads/                 # Temporary upload storage
├── outputs/                 # Processed file output
└── test/                    # Analysis & test scripts
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Port already in use | Change the port in `app.py` (line `uvicorn.run(...)`) |
| Large file processing is slow | This is expected for presentations with heavy graphics. The UI will show elapsed time. |
| "No watermark found" on a Gamma file | Gamma may have changed their watermark format. Open an issue with a sample file. |
| Import errors | Make sure you ran `pip install -r requirements.txt` from the project root. |

---

## Disclaimer

This tool is for **educational purposes only**. I am not affiliated with Gamma. Please consider upgrading to their paid tier if you use the software for professional work.
