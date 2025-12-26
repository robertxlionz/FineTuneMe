"use client"

import { useState, useEffect } from "react"
import { CheckCircle, AlertCircle, Download, RefreshCw, FileCode2, Sparkles } from "lucide-react"
import { projectAPI, API_URL } from "@/lib/api"

interface ProjectStatusProps {
  projectId: number
  onReset: () => void
}

interface ProjectData {
  id: number
  status: "processing" | "completed" | "failed"
  progress: number
  error_message?: string
  filename?: string
  dataset_format?: string
}

interface ProcessingStep {
  threshold: number
  label: string
  description: string
}

const PROCESSING_STEPS: ProcessingStep[] = [
  { threshold: 0, label: "Initializing", description: "Preparing your document for processing" },
  { threshold: 20, label: "Ingesting", description: "Reading and analyzing document content" },
  { threshold: 40, label: "Generating Conversations", description: "AI is creating synthetic dialogues" },
  { threshold: 70, label: "Formatting", description: "Structuring data into your chosen format" },
  { threshold: 90, label: "Finalizing", description: "Quality checks and final touches" },
  { threshold: 100, label: "Complete", description: "Dataset ready for download" }
]

export default function ProjectStatus({ projectId, onReset }: ProjectStatusProps) {
  const [project, setProject] = useState<ProjectData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [datasetPreview, setDatasetPreview] = useState<string[]>([])
  const [showConfetti, setShowConfetti] = useState(false)

  // Poll project status every 2 seconds
  useEffect(() => {
    const fetchProject = async () => {
      try {
        const data = await projectAPI.getProject(projectId)
        setProject(data)
        setLoading(false)
        setError("")

        // Trigger confetti on first completion detection
        if (data.status === "completed" && !showConfetti) {
          setShowConfetti(true)
          // Auto-load preview when completed
          loadDatasetPreview()
        }
      } catch (err: any) {
        setError(err.response?.data?.detail || "Failed to fetch project status")
        setLoading(false)
      }
    }

    // Initial fetch
    fetchProject()

    // Set up polling interval (only if not completed or failed)
    const intervalId = setInterval(() => {
      if (project?.status !== "completed" && project?.status !== "failed") {
        fetchProject()
      }
    }, 2000)

    // Cleanup interval on unmount
    return () => clearInterval(intervalId)
  }, [projectId, project?.status, showConfetti])

  // Load dataset preview (first 5-10 lines)
  const loadDatasetPreview = async () => {
    try {
      const downloadUrl = `${API_URL}/projects/${projectId}/download`
      const response = await fetch(downloadUrl)
      const text = await response.text()

      // Split by lines and take first 10
      const lines = text.split('\n').filter(line => line.trim()).slice(0, 10)
      setDatasetPreview(lines)
    } catch (err) {
      console.error("Failed to load dataset preview:", err)
    }
  }

  // Get current processing step based on progress
  const getCurrentStep = (): ProcessingStep => {
    const progress = project?.progress || 0

    // Find the highest threshold that progress has passed
    for (let i = PROCESSING_STEPS.length - 1; i >= 0; i--) {
      if (progress >= PROCESSING_STEPS[i].threshold) {
        return PROCESSING_STEPS[i]
      }
    }

    return PROCESSING_STEPS[0]
  }

  const currentStep = getCurrentStep()
  const downloadUrl = `${API_URL}/projects/${projectId}/download`

  // Loading state
  if (loading) {
    return (
      <div className="backdrop-blur-xl bg-white/80 dark:bg-gray-800/80 rounded-2xl shadow-2xl border border-white/20 dark:border-gray-700/50 p-8">
        <div className="flex flex-col items-center justify-center space-y-4">
          <RefreshCw className="h-12 w-12 text-blue-500 animate-spin" />
          <p className="text-gray-600 dark:text-gray-300">Loading project status...</p>
        </div>
      </div>
    )
  }

  // Error state (network/fetch error)
  if (error && !project) {
    return (
      <div className="backdrop-blur-xl bg-white/80 dark:bg-gray-800/80 rounded-2xl shadow-2xl border border-white/20 dark:border-gray-700/50 p-8">
        <div className="flex flex-col items-center justify-center space-y-4">
          <AlertCircle className="h-16 w-16 text-red-500" />
          <h3 className="text-xl font-semibold text-gray-900 dark:text-white">Connection Error</h3>
          <p className="text-gray-600 dark:text-gray-300 text-center">{error}</p>
          <button
            onClick={onReset}
            className="mt-4 px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
          >
            Back to Upload
          </button>
        </div>
      </div>
    )
  }

  // Failed status
  if (project?.status === "failed") {
    return (
      <div className="backdrop-blur-xl bg-white/80 dark:bg-gray-800/80 rounded-2xl shadow-2xl border border-white/20 dark:border-gray-700/50 p-8">
        <div className="flex flex-col items-center justify-center space-y-4">
          <AlertCircle className="h-16 w-16 text-red-500" />
          <h3 className="text-xl font-semibold text-gray-900 dark:text-white">Processing Failed</h3>
          <p className="text-red-600 dark:text-red-400 text-center max-w-md">
            {project.error_message || "An error occurred during dataset generation"}
          </p>
          <div className="flex gap-3 mt-4">
            <button
              onClick={onReset}
              className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Completed status
  if (project?.status === "completed") {
    return (
      <div className="backdrop-blur-xl bg-white/80 dark:bg-gray-800/80 rounded-2xl shadow-2xl border border-white/20 dark:border-gray-700/50 p-8 space-y-6">
        {/* Success Header with Animation */}
        <div className="flex flex-col items-center justify-center space-y-4 relative">
          {showConfetti && (
            <div className="absolute inset-0 pointer-events-none">
              {/* Simple confetti effect with CSS */}
              <div className="absolute top-0 left-1/4 w-2 h-2 bg-green-400 rounded-full animate-ping"></div>
              <div className="absolute top-0 right-1/4 w-2 h-2 bg-blue-400 rounded-full animate-ping" style={{ animationDelay: '0.2s' }}></div>
              <div className="absolute top-0 left-1/3 w-2 h-2 bg-yellow-400 rounded-full animate-ping" style={{ animationDelay: '0.4s' }}></div>
              <div className="absolute top-0 right-1/3 w-2 h-2 bg-purple-400 rounded-full animate-ping" style={{ animationDelay: '0.6s' }}></div>
            </div>
          )}

          <CheckCircle className="h-16 w-16 text-green-500 animate-pulse" />
          <h3 className="text-2xl font-bold bg-gradient-to-r from-green-600 to-emerald-600 bg-clip-text text-transparent">
            Dataset Generated Successfully!
          </h3>
          {project.filename && (
            <p className="text-gray-600 dark:text-gray-300">
              Processed: <span className="font-medium">{project.filename}</span>
            </p>
          )}
        </div>

        {/* Download Button */}
        <div className="flex flex-col gap-3">
          <a
            href={downloadUrl}
            download
            className="flex items-center justify-center gap-2 w-full py-3 px-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white rounded-lg font-medium shadow-lg transition-all transform hover:scale-105"
          >
            <Download className="h-5 w-5" />
            Download Dataset
          </a>

          <button
            onClick={onReset}
            className="w-full py-2.5 px-4 border-2 border-gray-300 dark:border-gray-600 hover:border-blue-500 dark:hover:border-blue-400 text-gray-700 dark:text-gray-300 rounded-lg font-medium transition-colors"
          >
            Process Another File
          </button>
        </div>

        {/* Dataset Preview */}
        {datasetPreview.length > 0 && (
          <div className="mt-6">
            <div className="flex items-center gap-2 mb-3">
              <FileCode2 className="h-5 w-5 text-blue-500" />
              <h4 className="text-lg font-semibold text-gray-900 dark:text-white">Dataset Preview</h4>
              <span className="text-xs text-gray-500 dark:text-gray-400">(First {datasetPreview.length} lines)</span>
            </div>

            <div className="bg-gray-900 dark:bg-black rounded-lg p-4 overflow-x-auto">
              <pre className="text-xs text-green-400 font-mono leading-relaxed">
                {datasetPreview.map((line, idx) => (
                  <div key={idx} className="hover:bg-gray-800 px-2 -mx-2 rounded">
                    {line}
                  </div>
                ))}
              </pre>
            </div>

            <p className="mt-2 text-xs text-gray-500 dark:text-gray-400 text-center">
              Verify the quality before using in production
            </p>
          </div>
        )}
      </div>
    )
  }

  // Processing status
  return (
    <div className="backdrop-blur-xl bg-white/80 dark:bg-gray-800/80 rounded-2xl shadow-2xl border border-white/20 dark:border-gray-700/50 p-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col items-center justify-center space-y-2">
        <Sparkles className="h-12 w-12 text-blue-500 animate-pulse" />
        <h3 className="text-2xl font-bold text-gray-900 dark:text-white">
          Generating Your Dataset
        </h3>
        <p className="text-gray-600 dark:text-gray-400 text-center">
          This may take several minutes depending on document size
        </p>
      </div>

      {/* Progress Bar */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="font-medium text-gray-700 dark:text-gray-300">
            {currentStep.label}
          </span>
          <span className="font-semibold text-blue-600 dark:text-blue-400">
            {project?.progress || 0}%
          </span>
        </div>

        {/* Progress bar track */}
        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 overflow-hidden">
          {/* Progress bar fill with gradient */}
          <div
            className="h-full bg-gradient-to-r from-blue-500 to-indigo-600 transition-all duration-500 ease-out rounded-full relative overflow-hidden"
            style={{ width: `${project?.progress || 0}%` }}
          >
            {/* Animated shine effect */}
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-shimmer"></div>
          </div>
        </div>

        <p className="text-sm text-gray-600 dark:text-gray-400 text-center mt-2">
          {currentStep.description}
        </p>
      </div>

      {/* Processing Steps Indicator */}
      <div className="grid grid-cols-3 gap-2 mt-6">
        {PROCESSING_STEPS.filter(step => step.threshold < 100).map((step, idx) => {
          const isActive = (project?.progress || 0) >= step.threshold
          const isCurrent = currentStep.threshold === step.threshold

          return (
            <div
              key={idx}
              className={`p-2 rounded-lg text-center transition-all ${
                isCurrent
                  ? 'bg-blue-100 dark:bg-blue-900/30 border-2 border-blue-500'
                  : isActive
                  ? 'bg-green-100 dark:bg-green-900/20 border border-green-500'
                  : 'bg-gray-100 dark:bg-gray-700/30 border border-gray-300 dark:border-gray-600'
              }`}
            >
              <div className={`text-xs font-medium ${
                isCurrent
                  ? 'text-blue-700 dark:text-blue-300'
                  : isActive
                  ? 'text-green-700 dark:text-green-300'
                  : 'text-gray-500 dark:text-gray-400'
              }`}>
                {step.label}
              </div>
            </div>
          )
        })}
      </div>

      {/* Info Box */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800/50 rounded-lg p-4">
        <p className="text-sm text-blue-800 dark:text-blue-200">
          <span className="font-semibold">Pro Tip:</span> Feel free to close this window.
          Your dataset will continue processing in the background.
        </p>
      </div>
    </div>
  )
}
