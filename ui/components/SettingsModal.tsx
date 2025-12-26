"use client"

import { useState, useEffect } from "react"
import { X, Settings, Key, Cpu, Eye, EyeOff, RefreshCw } from "lucide-react"
import { ftmStorage, type FineTuneMeSettings } from "@/lib/storage"
import { api, providerAPI } from "@/lib/api"

interface SettingsModalProps {
  isOpen: boolean
  onClose: () => void
}

interface Provider {
  name: string
  available: boolean
  requires_api_key: boolean
  models: string[]
}

interface HardwareStatus {
  status: string
  version: string
  hardware: {
    tier: "GREEN" | "YELLOW" | "RED"
    gpu_name: string
    compute_capability?: number
    vram_gb?: number
    driver_version?: string
    pytorch_mode?: string
    message: string
    recommendation?: string
  }
  pytorch: {
    installed: boolean
    version?: string
    cuda_available: boolean
    cuda_version?: string
    device_count: number
  }
  providers: {
    [key: string]: {
      available: boolean
      status: string
      warning?: string
    }
  }
}

export default function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const [activeTab, setActiveTab] = useState<"general" | "secrets" | "hardware">("general")
  const [settings, setSettings] = useState<FineTuneMeSettings>(ftmStorage.getAll())
  const [hardwareStatus, setHardwareStatus] = useState<HardwareStatus | null>(null)
  const [providers, setProviders] = useState<Record<string, Provider>>({})
  const [loadingProviders, setLoadingProviders] = useState(true)
  const [showGroqKey, setShowGroqKey] = useState(false)
  const [showOpenAIKey, setShowOpenAIKey] = useState(false)
  const [showAnthropicKey, setShowAnthropicKey] = useState(false)
  const [loading, setLoading] = useState(false)
  const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "saved">("idle")
  const [hardwareError, setHardwareError] = useState(false)
  const [backendOffline, setBackendOffline] = useState(false)

  // Load providers when modal is opened
  useEffect(() => {
    if (isOpen) {
      loadProviders()
    }
  }, [isOpen])

  // Load hardware status when tab is opened
  useEffect(() => {
    if (isOpen && activeTab === "hardware") {
      loadHardwareStatus()
    }
  }, [isOpen, activeTab])

  const loadProviders = async () => {
    setLoadingProviders(true)
    setBackendOffline(false)
    try {
      const data = await providerAPI.getProviders()
      setProviders(data)
      setBackendOffline(false)
    } catch (error) {
      // Silent failure - expected when backend is offline
      setBackendOffline(true)
      // Use fallback to show cloud providers in case of error
      setProviders({
        groq: { name: "Groq", available: true, requires_api_key: true, models: [] },
        openai: { name: "OpenAI", available: true, requires_api_key: true, models: [] },
        anthropic: { name: "Anthropic Claude", available: true, requires_api_key: true, models: [] }
      })
    } finally {
      setLoadingProviders(false)
    }
  }

  const loadHardwareStatus = async () => {
    // Skip hardware fetch if we already know backend is offline
    if (backendOffline) {
      setHardwareStatus(null)
      setHardwareError(true)
      setLoading(false)
      return
    }

    setLoading(true)
    setHardwareError(false)
    try {
      const response = await api.get("/system/health")
      setHardwareStatus(response.data)
      setHardwareError(false)
    } catch (error) {
      // Silent failure - expected in cloud mode or when backend is offline
      setHardwareStatus(null)
      setHardwareError(true)
    } finally {
      setLoading(false)
    }
  }

  const retryConnection = async () => {
    // Clear offline flag and try to reconnect
    setBackendOffline(false)
    await loadProviders()
    await loadHardwareStatus()
  }

  const handleSave = () => {
    setSaveStatus("saving")
    ftmStorage.setAll(settings)

    setTimeout(() => {
      setSaveStatus("saved")
      setTimeout(() => {
        setSaveStatus("idle")
        onClose()
      }, 500)
    }, 300)
  }

  const handleReset = () => {
    if (confirm("Reset all settings to defaults? API keys will be cleared.")) {
      ftmStorage.clear()
      setSettings(ftmStorage.getAll())
      setSaveStatus("saved")
      setTimeout(() => setSaveStatus("idle"), 1500)
    }
  }

  const handleClearSecrets = () => {
    if (confirm("Clear all saved API keys?")) {
      ftmStorage.clearSecrets()
      setSettings({ ...settings, apiKey: '', groqApiKey: '', openaiApiKey: '', anthropicApiKey: '' })
    }
  }

  if (!isOpen) return null

  const getTierBadgeColor = (tier: "GREEN" | "YELLOW" | "RED") => {
    switch (tier) {
      case "GREEN":
        return "bg-green-50 border-green-200 text-green-900"
      case "YELLOW":
        return "bg-yellow-50 border-yellow-200 text-yellow-900"
      case "RED":
        return "bg-red-50 border-red-200 text-red-900"
    }
  }

  const getTierEmoji = (tier: "GREEN" | "YELLOW" | "RED") => {
    switch (tier) {
      case "GREEN":
        return "✅"
      case "YELLOW":
        return "⚡"
      case "RED":
        return "⛔"
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full mx-4 max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b bg-gray-50">
          <div className="flex items-center gap-3">
            <Settings className="w-6 h-6 text-blue-600" />
            <div>
              <h2 className="text-xl font-bold">Settings</h2>
              <p className="text-sm text-gray-500">FineTuneMe V2.0</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="border-b bg-white">
          <nav className="flex px-6">
            <button
              onClick={() => setActiveTab("general")}
              className={`py-4 px-4 border-b-2 font-medium text-sm transition-colors ${activeTab === "general"
                  ? "border-blue-500 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                }`}
            >
              General
            </button>
            <button
              onClick={() => setActiveTab("secrets")}
              className={`py-4 px-4 border-b-2 font-medium text-sm flex items-center gap-2 transition-colors ${activeTab === "secrets"
                  ? "border-blue-500 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                }`}
            >
              <Key className="w-4 h-4" />
              API Secrets
            </button>
            <button
              onClick={() => setActiveTab("hardware")}
              className={`py-4 px-4 border-b-2 font-medium text-sm flex items-center gap-2 transition-colors ${activeTab === "hardware"
                  ? "border-blue-500 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                }`}
            >
              <Cpu className="w-4 h-4" />
              Hardware Health
            </button>
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {activeTab === "general" && (
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Default Provider
                </label>
                {loadingProviders ? (
                  <div className="text-sm text-gray-500">Loading providers...</div>
                ) : (
                  <select
                    value={settings.provider}
                    onChange={(e) => setSettings({ ...settings, provider: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    {/* Only show available providers */}
                    {Object.entries(providers)
                      .filter(([_, info]) => info.available)
                      .map(([key, info]) => (
                        <option key={key} value={key}>
                          {info.name}
                        </option>
                      ))}
                    {Object.keys(providers).filter(k => providers[k].available).length === 0 && (
                      <option value="" disabled>No providers available</option>
                    )}
                  </select>
                )}
                <p className="mt-1 text-xs text-gray-500">
                  Your preferred AI provider for dataset generation
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Default Role
                </label>
                <select
                  value={settings.role}
                  onChange={(e) => setSettings({ ...settings, role: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="teacher">Teacher - Educational Q&A</option>
                  <option value="strict_auditor">Strict Auditor - Critical Analysis</option>
                  <option value="technical_analyst">Technical Analyst - Code Deep-Dive</option>
                  <option value="researcher">Researcher - Analytical Insights</option>
                  <option value="custom">Custom - Your Own Prompt</option>
                </select>
                <p className="mt-1 text-xs text-gray-500">
                  The persona used to generate questions and answers
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Default Output Format
                </label>
                <select
                  value={settings.format}
                  onChange={(e) => setSettings({ ...settings, format: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="sharegpt">ShareGPT (Conversation format)</option>
                  <option value="alpaca">Alpaca (Instruction format)</option>
                  <option value="jsonl">JSONL (Line-delimited JSON)</option>
                </select>
                <p className="mt-1 text-xs text-gray-500">
                  The format for generated dataset files
                </p>
              </div>

              <div className="pt-4 border-t">
                <p className="text-xs text-gray-500">
                  These settings are saved locally in your browser and will be remembered across sessions.
                </p>
              </div>
            </div>
          )}

          {activeTab === "secrets" && (
            <div className="space-y-6">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-start gap-3">
                <Key className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-blue-800">
                  <p className="font-medium mb-1">Security Notice</p>
                  <p>API keys are stored locally in your browser only. They are never sent to our servers except when making API requests to the respective providers.</p>
                </div>
              </div>

              {/* Groq API Key */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Groq API Key
                </label>
                <div className="relative">
                  <input
                    type={showGroqKey ? "text" : "password"}
                    value={settings.groqApiKey}
                    onChange={(e) => setSettings({ ...settings, groqApiKey: e.target.value })}
                    placeholder="gsk_..."
                    className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                  <button
                    type="button"
                    onClick={() => setShowGroqKey(!showGroqKey)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    {showGroqKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                <p className="mt-1 text-xs text-gray-500">
                  Get your API key at <a href="https://console.groq.com" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">console.groq.com</a>
                </p>
              </div>

              {/* OpenAI API Key */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  OpenAI API Key
                </label>
                <div className="relative">
                  <input
                    type={showOpenAIKey ? "text" : "password"}
                    value={settings.openaiApiKey}
                    onChange={(e) => setSettings({ ...settings, openaiApiKey: e.target.value })}
                    placeholder="sk-..."
                    className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                  <button
                    type="button"
                    onClick={() => setShowOpenAIKey(!showOpenAIKey)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    {showOpenAIKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                <p className="mt-1 text-xs text-gray-500">
                  Get your API key at <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">platform.openai.com/api-keys</a>
                </p>
              </div>

              {/* Anthropic API Key */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Anthropic API Key
                </label>
                <div className="relative">
                  <input
                    type={showAnthropicKey ? "text" : "password"}
                    value={settings.anthropicApiKey}
                    onChange={(e) => setSettings({ ...settings, anthropicApiKey: e.target.value })}
                    placeholder="sk-ant-..."
                    className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                  <button
                    type="button"
                    onClick={() => setShowAnthropicKey(!showAnthropicKey)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    {showAnthropicKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                <p className="mt-1 text-xs text-gray-500">
                  Get your API key at <a href="https://console.anthropic.com/" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">console.anthropic.com</a>
                </p>
              </div>

              <div className="pt-4 border-t">
                <button
                  onClick={handleClearSecrets}
                  className="text-sm text-red-600 hover:text-red-700 font-medium"
                >
                  Clear All API Keys
                </button>
                <p className="mt-1 text-xs text-gray-500">
                  Remove all saved API keys from local storage
                </p>
              </div>
            </div>
          )}

          {activeTab === "hardware" && (
            <div className="space-y-4">
              {loading ? (
                <div className="flex items-center justify-center py-12">
                  <RefreshCw className="w-8 h-8 animate-spin text-blue-500" />
                  <span className="ml-3 text-gray-600">Loading hardware status...</span>
                </div>
              ) : hardwareError ? (
                <div className="text-center py-12">
                  <div className="mb-4">
                    <Cpu className="w-16 h-16 text-gray-300 mx-auto mb-3" />
                    <p className="text-gray-600 font-medium">Hardware Info Unavailable</p>
                    <p className="text-gray-500 text-sm mt-2 max-w-sm mx-auto">
                      Hardware monitoring is unavailable. This usually happens when running in Cloud-Only mode or if the backend is offline.
                    </p>
                  </div>
                  <button
                    onClick={retryConnection}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm"
                  >
                    Retry Connection
                  </button>
                </div>
              ) : hardwareStatus ? (
                <div className="space-y-6">
                  {/* GPU Status Badge */}
                  <div className={`border-2 rounded-lg p-5 ${getTierBadgeColor(hardwareStatus.hardware.tier)}`}>
                    <div className="flex items-start gap-4">
                      <div className="text-4xl">{getTierEmoji(hardwareStatus.hardware.tier)}</div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="font-bold text-lg">{hardwareStatus.hardware.gpu_name}</h3>
                          {hardwareStatus.hardware.tier === "YELLOW" && (
                            <span className="px-2 py-0.5 bg-yellow-200 text-yellow-800 text-xs font-medium rounded">
                              Experimental
                            </span>
                          )}
                        </div>

                        <div className="space-y-1 text-sm">
                          {hardwareStatus.hardware.vram_gb && (
                            <p><span className="font-medium">VRAM:</span> {hardwareStatus.hardware.vram_gb}GB</p>
                          )}
                          {hardwareStatus.hardware.driver_version && (
                            <p><span className="font-medium">Driver:</span> {hardwareStatus.hardware.driver_version}</p>
                          )}
                          {hardwareStatus.hardware.compute_capability && (
                            <p><span className="font-medium">Compute Capability:</span> {hardwareStatus.hardware.compute_capability}</p>
                          )}
                          {hardwareStatus.hardware.pytorch_mode && (
                            <p><span className="font-medium">PyTorch Mode:</span> {hardwareStatus.hardware.pytorch_mode}</p>
                          )}
                        </div>

                        <div className="mt-3 pt-3 border-t border-current border-opacity-20">
                          <p className="font-semibold text-sm mb-1">
                            {hardwareStatus.hardware.tier === "GREEN" && "Ollama: Fully Supported ✓"}
                            {hardwareStatus.hardware.tier === "YELLOW" && "Ollama: Experimental (May be unstable)"}
                            {hardwareStatus.hardware.tier === "RED" && "Ollama: Disabled ✗"}
                          </p>
                          <p className="text-sm opacity-90">{hardwareStatus.hardware.message}</p>
                          {hardwareStatus.hardware.recommendation && (
                            <p className="text-sm mt-2 font-medium">
                              💡 {hardwareStatus.hardware.recommendation}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* PyTorch Info */}
                  <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                    <h4 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                      <span className="text-lg">⚙️</span>
                      PyTorch Environment
                    </h4>
                    <div className="space-y-2 text-sm text-gray-700">
                      <div className="flex justify-between">
                        <span className="font-medium">Installed:</span>
                        <span>{hardwareStatus.pytorch.installed ? "Yes ✓" : "No ✗"}</span>
                      </div>
                      {hardwareStatus.pytorch.version && (
                        <div className="flex justify-between">
                          <span className="font-medium">Version:</span>
                          <span className="font-mono text-xs">{hardwareStatus.pytorch.version}</span>
                        </div>
                      )}
                      <div className="flex justify-between">
                        <span className="font-medium">CUDA Available:</span>
                        <span>{hardwareStatus.pytorch.cuda_available ? "Yes ✓" : "No ✗"}</span>
                      </div>
                      {hardwareStatus.pytorch.cuda_version && (
                        <div className="flex justify-between">
                          <span className="font-medium">CUDA Version:</span>
                          <span>{hardwareStatus.pytorch.cuda_version}</span>
                        </div>
                      )}
                      <div className="flex justify-between">
                        <span className="font-medium">GPU Devices:</span>
                        <span>{hardwareStatus.pytorch.device_count}</span>
                      </div>
                    </div>
                  </div>

                  {/* Provider Status */}
                  <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                    <h4 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                      <span className="text-lg">🤖</span>
                      AI Provider Status
                    </h4>
                    <div className="space-y-2">
                      {Object.entries(hardwareStatus.providers).map(([provider, info]) => (
                        <div key={provider} className="flex items-center justify-between text-sm">
                          <span className="font-medium capitalize">{provider}</span>
                          <div className="flex items-center gap-2">
                            <span className={`px-2 py-1 rounded text-xs font-medium ${info.status === "ready"
                                ? "bg-green-100 text-green-800"
                                : info.status === "experimental"
                                  ? "bg-yellow-100 text-yellow-800"
                                  : "bg-red-100 text-red-800"
                              }`}>
                              {info.status}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <button
                    onClick={loadHardwareStatus}
                    className="w-full py-2 px-4 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 flex items-center justify-center gap-2"
                  >
                    <RefreshCw className="w-4 h-4" />
                    Refresh Status
                  </button>
                </div>
              ) : (
                <div className="text-center py-12">
                  <p className="text-gray-500 mb-4">Failed to load hardware status</p>
                  <button
                    onClick={retryConnection}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                  >
                    Retry
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        {activeTab !== "hardware" && (
          <div className="flex items-center justify-end gap-3 p-6 border-t bg-gray-50">
            <button
              onClick={handleReset}
              className="px-4 py-2 text-gray-700 hover:text-gray-900 font-medium"
            >
              Reset to Defaults
            </button>
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-700 hover:text-gray-900 font-medium"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saveStatus === "saving"}
              className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 font-medium disabled:opacity-50 min-w-[100px]"
            >
              {saveStatus === "saving" && "Saving..."}
              {saveStatus === "saved" && "Saved ✓"}
              {saveStatus === "idle" && "Save Changes"}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
