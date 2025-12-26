"use client"

import { useState, useEffect } from "react"
import { Upload } from "lucide-react"
import { projectAPI, providerAPI } from "@/lib/api"
import { ftmStorage } from "@/lib/storage"

interface FileUploadProps {
  token?: string
  onSuccess?: (projectId: number) => void
}

// Role options with full system prompts (synced with backend generation.py)
const ROLE_OPTIONS = [
  {
    value: "teacher",
    label: "Teacher",
    description: "Educational, pedagogical approach",
    prompt: "You are an experienced teacher creating educational content.\nYour role is to generate clear, pedagogical questions that help students learn the material.\nFocus on understanding key concepts and practical applications."
  },
  {
    value: "strict_auditor",
    label: "Strict Auditor",
    description: "Critical, compliance-focused",
    prompt: "You are a strict auditor analyzing documents for compliance and accuracy.\nYour role is to generate challenging questions that test deep understanding of the content.\nFocus on critical details, edge cases, and potential issues."
  },
  {
    value: "technical_analyst",
    label: "Technical Analyst",
    description: "Technical deep-dive",
    prompt: "You are a technical analyst breaking down complex information.\nYour role is to generate questions that test technical understanding and implementation details.\nFocus on how things work and technical specifications."
  },
  {
    value: "researcher",
    label: "Researcher",
    description: "Analytical, research-oriented",
    prompt: "You are a researcher extracting insights from documents.\nYour role is to generate analytical questions that explore implications and connections.\nFocus on deeper meanings, relationships, and research applications."
  },
  {
    value: "custom",
    label: "Custom",
    description: "Use your own prompt",
    prompt: ""
  }
]

const SUPPORTED_FILE_TYPES = [
  '.pdf', '.docx', '.xlsx', '.xls', '.csv',
  '.html', '.htm', '.xml', '.txt', '.md', '.markdown',
  '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.c', '.cpp', '.cs',
  '.go', '.rs', '.php', '.rb', '.sql', '.json', '.yaml', '.yml',
  '.pptx', '.ppt', '.doc',
  '.png', '.jpg', '.jpeg', '.webp'
].join(',')

interface Provider {
  name: string
  available: boolean
  requires_api_key: boolean
  models: string[]
}

// Fallback provider list when backend is offline
const FALLBACK_PROVIDERS: Record<string, Provider> = {
  ollama: {
    name: "Ollama",
    available: false,
    requires_api_key: false,
    models: []
  },
  groq: {
    name: "Groq",
    available: true,
    requires_api_key: true,
    models: [
      "meta-llama/llama-4-scout-17b-16e-instruct",
      "llama-3.3-70b-versatile",
      "llama-3.1-8b-instant",
      "mixtral-8x7b-32768"
    ]
  },
  openai: {
    name: "OpenAI",
    available: true,
    requires_api_key: true,
    models: ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]
  },
  anthropic: {
    name: "Anthropic",
    available: true,
    requires_api_key: true,
    models: ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-opus-20240229"]
  }
}

export default function FileUpload({ token, onSuccess }: FileUploadProps) {
  const [file, setFile] = useState<File | null>(null)
  const [role, setRole] = useState("teacher")
  const [customPrompt, setCustomPrompt] = useState("")
  const [provider, setProvider] = useState("ollama")
  const [apiKey, setApiKey] = useState("")
  const [model, setModel] = useState("")
  const [format, setFormat] = useState("sharegpt")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [dragActive, setDragActive] = useState(false)

  // Provider state
  const [providers, setProviders] = useState<Record<string, Provider>>({})
  const [availableModels, setAvailableModels] = useState<string[]>([])
  const [loadingProviders, setLoadingProviders] = useState(true)
  const [backendError, setBackendError] = useState(false)

  // Load providers on mount
  useEffect(() => {
    loadProviders()
  }, [])

  // V2.0: Load saved settings from localStorage on mount
  useEffect(() => {
    const saved = ftmStorage.getAll()
    console.log("[FineTuneMe] Loading saved settings:", saved)

    // Only restore non-empty values
    if (saved.provider) setProvider(saved.provider)
    if (saved.role) setRole(saved.role)
    if (saved.format) setFormat(saved.format)

    // Load API key based on provider (with backward compatibility)
    if (saved.groqApiKey) {
      setApiKey(saved.groqApiKey)
    } else if (saved.apiKey) {
      setApiKey(saved.apiKey) // Legacy fallback
    }

    // AUTO-MIGRATION: Upgrade Llama 3.1 -> 3.3
    if (saved.model) {
      const migratedModel = saved.model.replace('llama-3.1-70b-versatile', 'llama-3.3-70b-versatile')
      if (migratedModel !== saved.model) {
        console.log(`[FineTuneMe] Auto-migrating model: ${saved.model} → ${migratedModel}`)
        ftmStorage.set('MODEL', migratedModel)
        setModel(migratedModel)
      } else {
        setModel(saved.model)
      }
    }
  }, [])

  // Update API key when provider changes
  useEffect(() => {
    const saved = ftmStorage.getAll()

    // Load the correct API key for the current provider
    switch (provider) {
      case 'groq':
        setApiKey(saved.groqApiKey || saved.apiKey || '') // Legacy fallback
        break
      case 'openai':
        setApiKey(saved.openaiApiKey || '')
        break
      case 'anthropic':
        setApiKey(saved.anthropicApiKey || '')
        break
      default:
        setApiKey('')
    }
  }, [provider])

  // Update available models when provider changes
  useEffect(() => {
    if (providers[provider]) {
      setAvailableModels(providers[provider].models)

      // Check if we have a saved model for this provider
      const savedModel = ftmStorage.get('MODEL')

      // AUTO-MIGRATION: If saved model is old 3.1, upgrade to 3.3
      const migratedModel = savedModel.replace('llama-3.1-70b-versatile', 'llama-3.3-70b-versatile')

      // Set model: prioritize migrated saved model > first available
      if (migratedModel && providers[provider].models.includes(migratedModel)) {
        if (migratedModel !== savedModel) {
          console.log(`[FineTuneMe] Auto-migrating saved model: ${savedModel} → ${migratedModel}`)
          ftmStorage.set('MODEL', migratedModel)
        }
        setModel(migratedModel)
      } else if (savedModel && providers[provider].models.includes(savedModel)) {
        setModel(savedModel)
      } else if (providers[provider].models.length > 0) {
        // Default to first model (which should be 3.3)
        setModel(providers[provider].models[0])
      }
    }
  }, [provider, providers])

  // V2.0: Auto-save provider on change
  useEffect(() => {
    if (provider) {
      console.log("[FineTuneMe] Saving provider:", provider)
      ftmStorage.set('PROVIDER', provider)
    }
  }, [provider])

  // V2.0: Auto-save role on change
  useEffect(() => {
    if (role) {
      ftmStorage.set('ROLE', role)
    }
  }, [role])

  // V2.0: Auto-save format on change
  useEffect(() => {
    if (format) {
      ftmStorage.set('FORMAT', format)
    }
  }, [format])

  // V2.0: Auto-save model on change
  useEffect(() => {
    if (model) {
      ftmStorage.set('MODEL', model)
    }
  }, [model])

  const loadProviders = async (retryCount = 0) => {
    setLoadingProviders(true)
    setBackendError(false)
    setError("")

    try {
      const data = await providerAPI.getProviders()
      setProviders(data)
      setLoadingProviders(false)
      setBackendError(false)

      // Set default provider (prefer Ollama if available, then saved provider)
      const savedProvider = ftmStorage.get('PROVIDER')
      if (savedProvider && data[savedProvider]?.available) {
        setProvider(savedProvider)
      } else if (data.ollama?.available) {
        setProvider("ollama")
      } else if (data.groq?.available) {
        setProvider("groq")
      } else if (data.openai?.available) {
        setProvider("openai")
      } else if (data.anthropic?.available) {
        setProvider("anthropic")
      }
    } catch (err) {
      // Silent failure - expected when backend is offline

      // Retry once before showing error
      if (retryCount < 1) {
        setTimeout(() => loadProviders(retryCount + 1), 1000)
        return
      }

      setBackendError(true)
      setLoadingProviders(false)

      // Use fallback providers so users can still use cloud providers with API keys
      setProviders(FALLBACK_PROVIDERS)

      // Default to saved provider or Groq
      const savedProvider = ftmStorage.get('PROVIDER')
      if (savedProvider && FALLBACK_PROVIDERS[savedProvider]) {
        setProvider(savedProvider)
      } else {
        setProvider("groq")
      }
    }
  }

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true)
    } else if (e.type === "dragleave") {
      setDragActive(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileChange(e.dataTransfer.files[0])
    }
  }

  const handleFileChange = (selectedFile: File) => {
    setError("")

    // Check file extension
    const fileExt = '.' + selectedFile.name.split('.').pop()?.toLowerCase()
    const supportedExtensions = SUPPORTED_FILE_TYPES.split(',')

    if (!supportedExtensions.includes(fileExt)) {
      setError(`Unsupported file type: ${fileExt}. Supported types: Images (.png, .jpg), PDF, Word, PowerPoint, Excel, CSV, HTML, Markdown, Code files`)
      return
    }

    if (selectedFile.size > 100 * 1024 * 1024) {
      setError("File size must not exceed 100MB")
      return
    }

    setFile(selectedFile)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")

    if (!file) {
      setError("Please select a file")
      return
    }

    // Validate API key for cloud providers
    const currentProvider = providers[provider]
    if (currentProvider?.requires_api_key && !apiKey) {
      setError(`API key is required for ${currentProvider.name}`)
      return
    }

    if (!model) {
      setError("Please select a model")
      return
    }

    setLoading(true)

    try {
      const formData = new FormData()
      formData.append("file", file)
      formData.append("role", role)
      formData.append("dataset_format", format)
      formData.append("provider_type", provider)
      formData.append("model_name", model)

      if (currentProvider?.requires_api_key && apiKey) {
        formData.append("api_key", apiKey)
      }

      if (role === "custom" && customPrompt) {
        formData.append("custom_prompt", customPrompt)
      }

      const project = await projectAPI.createProject(formData)

      if (onSuccess) {
        onSuccess(project.id)
      }

      // Reset form
      setFile(null)
      setRole("teacher")
      setCustomPrompt("")
      // Don't clear API key - keep it saved for next use
    } catch (err: any) {
      setError(err.response?.data?.detail || "Upload failed. Please try again.")
    } finally {
      setLoading(false)
    }
  }

  const getFileTypeDescription = () => {
    return "Images (.png, .jpg), PDF, Word (.docx), PowerPoint (.pptx), Excel (.xlsx), HTML, Markdown, Code files"
  }

  const currentProvider = providers[provider]
  const requiresApiKey = currentProvider?.requires_api_key || false

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Error Messages */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800/50 text-red-600 dark:text-red-400 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      {/* File Upload Area */}
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${dragActive
          ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
          : "border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500"
          }`}
        onClick={() => document.getElementById("file-input")?.click()}
      >
        <Upload className="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500" />
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
          {file ? file.name : "Drop your file here or click to browse"}
        </p>
        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
          Supported: {getFileTypeDescription()}
        </p>
        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">Maximum size: 100MB</p>
        <input
          id="file-input"
          type="file"
          accept={SUPPORTED_FILE_TYPES}
          onChange={(e) => e.target.files && handleFileChange(e.target.files[0])}
          className="hidden"
        />
      </div>

      {/* Provider Selection */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            AI Provider
          </label>
          {backendError && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 text-xs font-medium rounded-full">
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Cloud-Only Mode
            </span>
          )}
        </div>
        {loadingProviders ? (
          <div className="text-sm text-gray-500 dark:text-gray-400">Loading providers...</div>
        ) : (
          <select
            value={provider}
            onChange={(e) => setProvider(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
          >
            {Object.entries(providers).map(([key, info]) => (
              <option key={key} value={key} disabled={!info.available}>
                {info.name} {!info.available && "(Not available)"}
                {info.requires_api_key && " - Requires API Key"}
              </option>
            ))}
          </select>
        )}
        <div className="mt-1 flex items-start gap-2">
          <p className="text-xs text-gray-500 dark:text-gray-400 flex-1">
            {currentProvider?.requires_api_key
              ? "Cloud provider - requires API key"
              : "Local provider - runs on your machine"}
          </p>
          {backendError && (
            <button
              type="button"
              onClick={() => loadProviders(0)}
              disabled={loadingProviders}
              className="text-xs text-blue-600 dark:text-blue-400 hover:underline disabled:opacity-50"
            >
              {loadingProviders ? "Checking..." : "Reconnect"}
            </button>
          )}
        </div>
      </div>

      {/* API Key Input (for cloud providers) */}
      {requiresApiKey && (
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            API Key
          </label>

          {apiKey ? (
            // Show indicator when key is already saved
            <div className="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800/50 rounded-md">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <svg className="w-4 h-4 text-green-600 dark:text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span className="text-sm text-green-700 dark:text-green-300 font-medium">
                    Using saved {currentProvider.name} API key
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => setApiKey('')}
                  className="text-xs text-green-600 dark:text-green-400 hover:text-green-700 dark:hover:text-green-300 font-medium underline"
                >
                  Change
                </button>
              </div>
              <p className="mt-1 text-xs text-green-600 dark:text-green-400">
                Manage all API keys in Settings
              </p>
            </div>
          ) : (
            // Show input when no key is saved
            <>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => {
                  const newKey = e.target.value
                  setApiKey(newKey)
                  // V2.0: Save API key to localStorage immediately (provider-specific)
                  switch (provider) {
                    case 'groq':
                      ftmStorage.set('GROQ_API_KEY', newKey)
                      ftmStorage.set('API_KEY', newKey) // Legacy backward compatibility
                      break
                    case 'openai':
                      ftmStorage.set('OPENAI_API_KEY', newKey)
                      break
                    case 'anthropic':
                      ftmStorage.set('ANTHROPIC_API_KEY', newKey)
                      break
                  }
                }}
                placeholder={`Enter your ${currentProvider.name} API key`}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500"
              />
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                Your API key is stored locally in your browser and will be remembered
              </p>
            </>
          )}
        </div>
      )}

      {/* Model Selection */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Model
        </label>
        <select
          value={model}
          onChange={(e) => setModel(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 disabled:opacity-50"
          disabled={availableModels.length === 0}
        >
          {availableModels.length === 0 ? (
            <option>No models available</option>
          ) : (
            availableModels.map((modelName) => (
              <option key={modelName} value={modelName}>
                {modelName}
              </option>
            ))
          )}
        </select>
        {provider === "ollama" && availableModels.length === 0 && (
          <p className="mt-1 text-xs text-red-500 dark:text-red-400">
            No Ollama models detected. Please install a model with: ollama pull llama3.1
          </p>
        )}
      </div>

      {/* Role Selection */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Generation Role</label>
        <select
          value={role}
          onChange={(e) => setRole(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
        >
          {ROLE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label} - {option.description}
            </option>
          ))}
        </select>

        {/* Display the actual system prompt for selected role */}
        {role !== "custom" && (
          <div className="mt-3 p-3 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-md">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wide">System Prompt</span>
            </div>
            <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-line font-mono leading-relaxed">
              {ROLE_OPTIONS.find(opt => opt.value === role)?.prompt}
            </p>
          </div>
        )}
      </div>

      {/* Custom Prompt */}
      {role === "custom" && (
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Custom System Prompt</label>
          <textarea
            value={customPrompt}
            onChange={(e) => setCustomPrompt(e.target.value)}
            rows={4}
            placeholder="Enter your custom system prompt..."
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500"
          />
        </div>
      )}

      {/* Dataset Format */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Output Format</label>
        <div className="flex flex-wrap gap-4">
          <label className="flex items-center">
            <input
              type="radio"
              value="sharegpt"
              checked={format === "sharegpt"}
              onChange={(e) => setFormat(e.target.value)}
              className="mr-2"
            />
            <span className="text-gray-700 dark:text-gray-300">ShareGPT</span>
          </label>
          <label className="flex items-center">
            <input
              type="radio"
              value="alpaca"
              checked={format === "alpaca"}
              onChange={(e) => setFormat(e.target.value)}
              className="mr-2"
            />
            <span className="text-gray-700 dark:text-gray-300">Alpaca</span>
          </label>
          <label className="flex items-center">
            <input
              type="radio"
              value="jsonl"
              checked={format === "jsonl"}
              onChange={(e) => setFormat(e.target.value)}
              className="mr-2"
            />
            <span className="text-gray-700 dark:text-gray-300">JSONL</span>
          </label>
        </div>
      </div>

      {/* Submit Button */}
      <button
        type="submit"
        disabled={loading || !file || !model || (requiresApiKey && !apiKey)}
        className="w-full flex justify-center py-3 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {loading ? "Processing..." : "Generate Dataset"}
      </button>
    </form>
  )
}
