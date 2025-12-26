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

### 2. Usage Guide

#### Step 1: Configure AI Provider
**☁️ Cloud Mode (Fastest)**
1.  Select **Groq**, **OpenAI**, or **Anthropic** from the provider dropdown.
2.  **Enter API Key**: A secure password field will appear. Paste your key here (it is saved locally in your browser).
3.  **Select Model**: The system will auto-populate available models (e.g., `llama-4-scout-17b`).

**🏠 Local Mode (Private)**
1.  Ensure [Ollama](https://ollama.com) is running (`ollama serve`).
2.  Select **Ollama** as the provider.
3.  **Enter Model Tag**: Type the exact name of your local model (e.g., `llama3.2`, `mistral`, `llava`).
4.  **Base URL**: Default is `http://localhost:11434`.

#### Step 2: Upload & Generate
1.  **Upload Files**: Drag & drop PDFs, Images, Excels, or legacy Office files.
2.  **Select Strategy**: Choose **"High-Yield Q&A"** for fine-tuning data or **"Summarization"**.
3.  Click **"Start Processing"**.
4.  Download the resulting `.jsonl` file.

### 3. API Key Security (Cloud Mode)
- **Client-Side Only**: Your API keys (Groq, OpenAI, etc.) are **NEVER** sent to our servers or saved in the backend database.
- **LocalStorage**: They are encrypted and stored locally in your browser's `localStorage`.
- **Control**: You have full control. Clear your browser cache to wipe them instantly.

---

## 🏎️ Recommended Models
FineTuneMe is model-agnostic, but we have tuned the prompts for specific engines.

### ☁️ Cloud (Best Performance)
| Provider | Tested Model | Best For | Notes |
| :--- | :--- | :--- | :--- |
| **Groq** | `llama-4-scout-17b-16e-instruct` | **Everything** | ⚡ **Highly Recommended**. Fastest inference + Native Vision support. |
| **OpenAI** | `gpt-4o` | Complex Logic | Good fallback, but slower and more expensive. |
| **Anthropic** | `claude-3-5-sonnet` | Creative Writing | Excellent prose, but API rate limits can be strict. |

### 🏠 Local (Privacy / Offline)
*Requires [Ollama](https://ollama.com) installed.*

| VRAM | Recommended Model | Use Case |
| :--- | :--- | :--- |
| **< 6GB** | `llama3.2:3b` | Testing / Dev | Too small for high-quality instruction generation. |
| **8GB** | `llama3.1:8b` | Text Only | Good standard model. Fast but no vision. |
| **12GB** | `llama3.2-vision:11b` | **Vision** | Minimum for decent image analysis. |
| **24GB+** | `llama3.3:70b-q4` | **Pro** | Approch state-of-the-art quality locally. |

> **⚠️ Vision Note**: If you upload images while using Groq, the system will **automatically route** the request to `llama-4-scout`, even if you selected a text-only model. This prevents errors and ensures your images are actually analyzed.


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

## 👨‍💻 Developer Guide: "Hacking" the AI

Want to change the models, prompts, or logic? Here are the key files:

| Logic | File Path | What to Change |
| :--- | :--- | :--- |
| **Model Lists** | `src/finetuneme/services/providers.py` | Add new Groq/OpenAI models to `AVAILABLE_MODELS` list. |
| **Prompts** | `src/finetuneme/services/generation.py` | Edit `system_prompt` variables to change how the AI extracts data. |
| **Vision Logic** | `src/finetuneme/services/providers.py` | Modify `GroqProvider.generate` to change how images are attached or routed. |
| **File loaders** | `src/finetuneme/services/loaders.py` | Logic for parsing PDFs, Excels, and PowerPoints. |

---

## 📜 License
MIT License. Build, modify, and distribute properly.
