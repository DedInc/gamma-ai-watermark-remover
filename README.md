# Gamma Watermark Remover

A local web tool to strip the "Made with Gamma" branding from PDF and PowerPoint (.pptx) files exported from gamma.app free accounts. 

It runs a FastAPI backend that parses the document structure to identify and remove specific watermark elements based on coordinates and object properties.

## Functionality

*   **PDF:** Scans pages using PyMuPDF (fitz) for images linked to the gamma.app domain located in the bottom-right corner.
*   **PPTX:** Uses `python-pptx` to parse the presentation. Since Gamma embeds the watermark in the **Slide Layouts** (masters) rather than individual slides, the script targets the master layouts to remove the branding globally across the presentation.

## Setup

Requires Python 3.7+.

1. Clone the repo:
   ```bash
   git clone https://github.com/username/gamma-watermark-remover.git
   cd gamma-watermark-remover
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the server:
   ```bash
   python app.py
   ```
   
4. Go to `http://localhost:8000` in your browser.

## Technical Notes

The detection logic is heuristic-based:

*   **PPTX:** Checks `prs.slide_layouts`. If a shape contains a hyperlink to `gamma.app` and is positioned beyond the 70% mark of the slide width/height, it gets deleted.
*   **PDF:** Iterates through page objects. If a clickable image points to the Gamma domain, the object is removed from the drawing stream.

If Gamma changes their export coordinates or DOM structure, the coordinate offsets in `utils.py` (or wherever logic resides) will need to be updated.

## Dependencies

*   `fastapi` / `uvicorn` - Web server
*   `pymupdf` - PDF processing
*   `python-pptx` - PowerPoint manipulation
*   `python-multipart` - For file uploads

## Disclaimer

This tool is for educational purposes only. I am not affiliated with Gamma. Please consider upgrading to their paid tier if you use the software for professional work.
