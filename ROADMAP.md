# 🗺️ Roadmap & Known Issues

## 🚧 Current Limitations

### 1. Legacy Office File Support
- **Issue**: Old binary formats (`.doc`, `.ppt`) are currently **rejected** with a warning message.
- **Reason**: Python support for these proprietary formats is limited without heavyweight dependencies (like LibreOffice or .NET interop).
- **Workaround**: Users must save files as modern `.docx` or `.pptx` before uploading.

### 2. Vision Model Dependency
- **State**: The "High-Yield" vision pipeline is currently optimized for **Groq + Llama 4 Scout**.
- **Limitation**: While flexible, strict vision prompting is tuned for Llama 4. Other providers (OpenAI GPT-4o, Claude 3.5 Sonnet) are supported via the generic API but haven't been tuned with the same specific "Vision extraction protocols".

### 3. Local Hardware Requirements
- **State**: "Local AI" mode requires a substantial GPU.
- **Requirement**: NVIDIA GPU with 8GB+ VRAM recommended for decent performance with quantization. CPU-only mode is theoretically possible but practically unusable for dataset generation.

## 🚀 Future Improvements (Community Calls)

### 🔹 1. Native Legacy Converters
**Goal**: Integrate a Dockerized microservice (using LibreOffice headless) to automatically convert `.doc`/`.ppt` to modern formats on upload, removing the manual user step.

### 🔹 2. Multi-Provider Vision Support
**Goal**: Abstract the "Vision Protocol" prompts to work equally well with:
- OpenAI GPT-4o
- Anthropic Claude 3.5 Sonnet
- Gemini 1.5 Pro
- Local LLaVA models (via Ollama)

### 🔹 3. Direct HuggingFace Integration
**Goal**: Add a "Push to Hub" button to upload generated `.jsonl` datasets directly to a HuggingFace repository.

### 🔹 4. RAG "Chat with Data"
**Goal**: Before generating a dataset, allow users to "chat" with their ingested documents to verify the extraction quality and context window retrieval.

### 🔹 5. Advanced Chunking Strategies
**Goal**: Move beyond "Semantic Chunking" to support:
- Markdown-aware splitting
- Table-preserving chunks
- Sliding window overlaps
