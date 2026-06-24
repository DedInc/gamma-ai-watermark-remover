# Gamma Watermark Remover

A local web tool to strip the **"Made with Gamma"** branding from files exported from [gamma.app](https://gamma.app) free accounts — including PDF, PowerPoint (`.pptx`), Apple Keynote (`.key`), and PNG slide ZIP exports.

It runs a **FastAPI** backend that parses the document structure to identify and remove specific watermark elements based on coordinates and object properties.

![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-green)
![FastAPI](https://img.shields.io/badge/FastAPI-2.x-009688?logo=fastapi&logoColor=white)

---

## Features

- **PDF:** Scans pages using PyMuPDF (fitz) for images linked to the gamma.app domain located in the bottom-right corner.
- **PPTX:** Uses `python-pptx` to parse the presentation. Since Gamma embeds the watermark in the **Slide Layouts** (masters) rather than individual slides, the script targets the master layouts to remove the branding globally.
- **Keynote (.key):** macOS only. Uses AppleScript to drive the Keynote app — converts `.key` → `.pptx`, cleans watermarks, then converts back to `.key`. Requires Keynote to be installed. *Tip:* Keeping the Keynote app open in the background before starting the conversion is highly recommended; it speeds up the conversion process significantly and prevents potential macOS permission prompt blocks or startup timeout issues.
- **PNG ZIP / Folder:** Processes ZIP archives (or extracted folders) of Gamma's PNG slide exports. Uses per-row background colour sampling to seamlessly paint over the bottom-right watermark badge on every slide image.
- **Batch-ready:** Upload multiple files at once from the web UI.
- **Dark / Light mode:** Toggle between themes; preference is saved locally.
- **Session history:** Track your processed files within a browser session.

---

## Quick Start

Requires **Python 3.9+**.

1. **Clone the repo:**
   ```bash
   git clone https://github.com/DedInc/gamma-ai-watermark-remover.git
   cd gamma-ai-watermark-remover
   ```

2. **Create a virtual environment and install dependencies:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
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

- **PPTX / Keynote:** Checks `prs.slide_layouts`. If a shape contains a hyperlink to `gamma.app` and is positioned beyond the 70% mark of the slide width/height, it gets deleted.
- **PDF:** Iterates through page objects. If a clickable image points to the Gamma domain, the object is removed from the drawing stream.
- **PNG exports:** The watermark occupies the bottom-right ~22% × 10% of each slide image. The remover samples the background colour row-by-row to the left of the watermark region and fills it in, producing a seamless patch.
- **Google Slides exports:** Gamma exports Google Slides-compatible files as `.pptx`. Upload the downloaded `.pptx` directly — it is already supported.

> **Note:** If Gamma changes their export coordinates or DOM structure, the coordinate offsets in the processor modules will need to be updated.

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `fastapi` / `uvicorn` | Web server |
| `pymupdf` (fitz) | PDF processing |
| `python-pptx` | PowerPoint manipulation |
| `Pillow` | PNG image processing |
| `python-multipart` | File uploads |
| `jinja2` | HTML templating |

---

## Project Structure

```
├── app.py                      # FastAPI application entry point
├── processors/
│   ├── pdf/
│   │   ├── detector.py         # PDF watermark detection
│   │   └── remover.py          # PDF watermark removal
│   ├── pptx/
│   │   ├── detector.py         # PPTX watermark detection
│   │   └── remover.py          # PPTX watermark removal
│   ├── png/
│   │   └── remover.py          # PNG slide watermark removal (PIL)
│   └── keynote/
│       └── converter.py        # Keynote ↔ PPTX via AppleScript (macOS)
├── utils/
│   ├── file_helpers.py         # File type validation & MIME types
│   └── processors.py           # High-level processor orchestration
├── templates/
│   └── index.html              # Web UI (single-page)
├── uploads/                    # Temporary upload storage
├── outputs/                    # Processed file output
└── test/                       # Analysis & test scripts
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Port already in use | Change the port in `app.py` (line `uvicorn.run(...)`) |
| Large file processing is slow | This is expected for presentations with heavy graphics. The UI will show elapsed time. |
| "No watermark found" on a Gamma file | Gamma may have changed their watermark format. Open an issue with a sample file. |
| Import errors | Make sure you ran `pip install -r requirements.txt` inside your activated virtual environment. |
| Keynote (.key) not processing | Apple Keynote must be installed on your Mac. Make sure the Keynote app is already open/running in the background for a seamless and much faster conversion. |
| PNG ZIP — "No PNG files found" | Ensure the ZIP contains PNG files directly or inside a folder. Nested ZIPs are not supported. |

### 🔧 Fixing a Broken Virtual Environment

If your `.venv` becomes corrupted or you see unexpected import errors after updating Python, recreate it from scratch:

```bash
# 1. Remove the broken venv
rm -rf .venv

# 2. Create a fresh virtual environment
python3 -m venv .venv

# 3. Activate it
source .venv/bin/activate   # macOS / Linux
# .venv\Scripts\activate    # Windows

# 4. Re-install all dependencies
pip install -r requirements.txt

# 5. Start the server
python app.py
```

> **Tip:** If `python3 -m venv` fails because the `venv` module is missing (common on some minimal Linux installs), run `sudo apt install python3-venv` first, then retry.

---

## Disclaimer

This tool is for **educational purposes only**. I am not affiliated with Gamma. Please consider upgrading to their paid tier if you use the software for professional work.
