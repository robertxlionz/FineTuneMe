# 🚀 FineTuneMe V2.0: Universal Dataset Generator

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Next.js](https://img.shields.io/badge/Next.js-14-black)](https://nextjs.org/)
[![Groq Powered](https://img.shields.io/badge/Powered%20by-Groq-orange)](https://groq.com)
[![Llama 4 Certified](https://img.shields.io/badge/Model-Llama%204%20Scout-purple)](https://llama.meta.com/)

**The ultimate tool for turning raw chaos into specialized AI training data.**

---

## 🌟 What is this?
FineTuneMe is a **Sovereign AI Data Pipeline**. It runs locally on your machine (or connects to high-speed cloud APIs) to ingest documents, code, and images, and transforms them into high-quality **Instruction Tuning Datasets** (`.jsonl`) ready for fine-tuning LLMs or importing into RAG systems.

### 🔥 Key Features
- **Universal Loader Engine**: Drag & Drop **PDFs, Word, Excel, PowerPoint, Images, Code, HTML**.
    - *Robustness*: Automatically handles corrupted Excels, legacy files, and scanned PDFs.
- **Vision-First Intelligence**: Uses **Llama 4 Scout** (via Groq) to "see" diagrams, charts, and screenshots, extracting structured data that text-only models miss.
- **Sovereign Execution**:
    - **Cloud Mode**: Blazing fast generation via Groq/OpenAI/Anthropic.
    - **Local Mode**: Full privacy using **Ollama** + Local GPUs (NVIDIA RTX supported).
- **High-Yield Extraction**: Specialized prompt engineering that forces the LLM to extract "Reasoning Traces" and "Chain-of-Thought" analysis, not just surface-level text.

---

## 🛠️ Architecture
- **Frontend**: Next.js 14 + TailwindCSS (Modern, Responsive, Dark Mode)
- **Backend**: FastAPI (Python 3.12)
- **Orchestration**: Asynchronous task queues for parallel processing.
- **Storage**: SQLite (Metadata) + Local File System (Artifacts).

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- (Optional) NVIDIA GPU for Local Mode
- (Optional) Groq API Key for Cloud Mode

### 1. Installation
```powershell
# Clone the repository
git clone https://github.com/your-username/FineTuneMe.git
cd FineTuneMe

# Run the Universal Launcher
start_app.bat
```

The launcher will automatically:
1.  Create a virtual environment (`.venv`).
2.  Install Python dependencies.
3.  Install Frontend dependencies (`npm install`).
4.  Launch the Unified Dashboard.

### 2. Usage
1.  Open **http://localhost:3000**.
2.  **Upload** your raw files (e.g., a folder of PDFs, an Excel sheet, or a screenshot).
3.  Choose your **Strategy** (e.g., "High-Yield Q&A", "Summarization").
4.  Click **"Start Processing"**.
5.  Download your `.jsonl` dataset!

---

## 🧬 Vision Capabilities
FineTuneMe V2 is engineered for the **Multimodal Era**.
- **Images**: Upload direct `.png`/`.jpg` files.
- **Embedded Media**: Automatically extracts images from PDFs and PowerPoints.
- **Intelligence**: Uses `meta-llama/llama-4-scout-17b-16e-instruct` to analyze visual content with strict data extraction protocols.

---

## 🤝 Contributing
We love contributions! Please check [ROADMAP.md](ROADMAP.md) for current limitations and requested features.

### How to help?
- **Legacy Files**: Help us build a better converter for `.doc` and `.ppt`.
- **Chunking**: Implement markdown-aware splitters.
- **Integrations**: Add direct export to HuggingFace.

---

## 📜 License
MIT License. Build, modify, and distribute properly.
