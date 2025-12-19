# 💧✨ Gamma AI Watermark Remover ✨💧

<div align="center">
  <img src="https://img.shields.io/badge/Python-3.7+-blue.svg?style=flat-square&logo=python&logoColor=white" alt="Python Version">
  <img src="https://img.shields.io/badge/FastAPI-brightgreen.svg?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/PyMuPDF-orange.svg?style=flat-square&logo=python&logoColor=white" alt="PyMuPDF">
  <img src="https://img.shields.io/badge/python--pptx-yellow.svg?style=flat-square&logo=python&logoColor=white" alt="python-pptx">
  <img src="https://img.shields.io/badge/Uvicorn-red.svg?style=flat-square&logo=python&logoColor=white" alt="Uvicorn">
</div>

<div align="center">
  <p> ⚠️ <b>Educational Purposes Only</b> ⚠️ </p>
</div>

---

## 🌟 What is Gamma AI Watermark Remover?

A specialized web application designed to remove **gamma.app** watermarks from **PDF** and **PowerPoint (.pptx)** files. This tool specifically targets Gamma AI's branding elements that appear in documents exported from their free tier, helping you create clean, professional-looking presentations.

## 🤔 Why do you need it?

Gamma AI is a fantastic presentation tool, but the watermarks in the free version can be problematic for professional and educational use:

* **Professional Presentations:** Remove distracting branding for business meetings and formal presentations
* **Educational Materials:** Create clean study materials and academic presentations  
* **Portfolio Work:** Present your content without third-party branding
* **Document Clarity:** Improve focus and readability by removing visual distractions

## ⚙️ How does it work?

The application uses an intelligent detection and removal system for both supported formats:

### PDF Documents
1. **Analysis:** Parses PDF documents page by page using PyMuPDF (fitz)
2. **Targeted Detection:** Identifies gamma.app watermarks by analyzing images positioned in the bottom-right corner and links pointing to gamma.app domain
3. **Smart Removal:** Removes detected watermarks while preserving document integrity

### PowerPoint (.pptx) Presentations
1. **Structure Analysis:** Parses the presentation structure using `python-pptx`, examining both individual slides and **Slide Layouts**
2. **Layout-Level Detection:** Gamma often embeds watermarks in the slide layouts rather than individual slides. The tool detects these by checking for:
   - Images in the bottom-right corner (position > 70%)
   - Associated hyperlinks pointing to `gamma.app`
3. **Clean Output:** Removes the specific watermark elements from the layouts, which instantly cleans all slides using that layout

## 🚀 Installation & Setup

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt --upgrade
   ```
   *Key dependencies: FastAPI, PyMuPDF, python-pptx*

2. **Start the Server:**
   ```bash
   python app.py
   ```

3. **Access the Web Interface:**
   Open your browser and navigate to: `http://localhost:8000`

4. **Upload and Process:**
   - Click "Choose PDF or PowerPoint File" to select your Gamma AI document
   - Click "Remove Watermark" to process the file
   - Download the clean document automatically

---

## 📝 Version History

### v2.3.0
- **Added PowerPoint Support:** Full support for removing watermarks from `.pptx` files
- **Advanced Layout Detection:** Smart algorithm to handle watermarks embedded in slide master layouts
- **Unified Interface:** Drag-and-drop support for both PDF and PPTX formats

---

<div align="center">
  <p>✨ <b>Enjoy your clean, professional documents!</b> ✨</p>
</div>