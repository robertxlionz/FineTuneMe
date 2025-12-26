"use client"

import { useState, useEffect } from "react"
import FileUpload from "@/components/FileUpload"
import SettingsModal from "@/components/SettingsModal"
import ProjectStatus from "@/components/ProjectStatus"
import { Sparkles, Shield, FileCode2, Moon, Sun, Settings } from "lucide-react"

export default function LandingPage() {
    const [uploadedProjectId, setUploadedProjectId] = useState<number | null>(null)
    const [darkMode, setDarkMode] = useState(true) // Default to dark mode
    const [showSettings, setShowSettings] = useState(false)

    // Apply dark mode class to document
    useEffect(() => {
        if (darkMode) {
            document.documentElement.classList.add('dark')
        } else {
            document.documentElement.classList.remove('dark')
        }
    }, [darkMode])

    const handleUploadSuccess = (projectId: number) => {
        setUploadedProjectId(projectId)
    }

    return (
        <div className="flex flex-col min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
            {/* Header */}
            <header className="backdrop-blur-sm bg-white/70 dark:bg-gray-900/70 border-b border-white/20 dark:border-gray-700/50 px-4 lg:px-6 h-16 flex items-center sticky top-0 z-50">
                <div className="container mx-auto max-w-7xl flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <Sparkles className="w-6 h-6 text-indigo-600 dark:text-indigo-400" />
                        <span className="font-bold text-xl bg-gradient-to-r from-indigo-600 to-purple-600 dark:from-indigo-400 dark:to-purple-400 bg-clip-text text-transparent">
                            FineTuneMe
                        </span>
                    </div>
                    <div className="flex items-center gap-2">
                        {/* Dark Mode Toggle */}
                        <button
                            onClick={() => setDarkMode(!darkMode)}
                            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                            aria-label="Toggle dark mode"
                        >
                            {darkMode ? (
                                <Sun className="w-5 h-5 text-gray-600 dark:text-gray-300" />
                            ) : (
                                <Moon className="w-5 h-5 text-gray-600 dark:text-gray-300" />
                            )}
                        </button>
                        {/* Settings Button */}
                        <button
                            onClick={() => setShowSettings(true)}
                            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                            aria-label="Open settings"
                        >
                            <Settings className="w-5 h-5 text-gray-600 dark:text-gray-300" />
                        </button>
                    </div>
                </div>
            </header>

            {/* Settings Modal */}
            <SettingsModal isOpen={showSettings} onClose={() => setShowSettings(false)} />

            <main className="flex-1">
                {/* Hero Section */}
                <section className="w-full py-16 md:py-24 lg:py-32">
                    <div className="container px-4 md:px-6 mx-auto max-w-7xl">
                        <div className="flex flex-col items-center space-y-12 text-center">
                            {/* Hero Text */}
                            <div className="space-y-6 max-w-3xl">
                                <h1 className="text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl lg:text-7xl bg-gradient-to-r from-gray-900 via-indigo-900 to-purple-900 dark:from-gray-100 dark:via-indigo-200 dark:to-purple-200 bg-clip-text text-transparent">
                                    Generate Synthetic Datasets from Your Documents
                                </h1>
                                <p className="mx-auto max-w-[700px] text-gray-600 dark:text-gray-300 text-lg md:text-xl leading-relaxed">
                                    Turn PDFs, code, and docs into high-quality training pairs. Privacy-first, local execution.
                                </p>
                            </div>

                            {/* Main Upload Card - Glassmorphism */}
                            {!uploadedProjectId && (
                                <div className="w-full max-w-3xl">
                                    <div className="backdrop-blur-xl bg-white/80 dark:bg-gray-800/80 border border-white/20 dark:border-gray-700/50 rounded-2xl shadow-2xl p-8 md:p-10">
                                        <div className="flex items-center gap-3 mb-8">
                                            <div className="p-2 bg-gradient-to-br from-indigo-500 to-purple-500 rounded-lg">
                                                <FileCode2 className="w-5 h-5 text-white" />
                                            </div>
                                            <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">Start New Project</h2>
                                        </div>
                                        <FileUpload onSuccess={handleUploadSuccess} />
                                    </div>
                                </div>
                            )}

                            {/* Project Status View */}
                            {uploadedProjectId && (
                                <div className="w-full max-w-3xl">
                                    <ProjectStatus
                                        projectId={uploadedProjectId}
                                        onReset={() => setUploadedProjectId(null)}
                                    />
                                </div>
                            )}
                        </div>
                    </div>
                </section>

                {/* Features Section */}
                <section className="w-full py-16 md:py-24">
                    <div className="container px-4 md:px-6 mx-auto max-w-6xl">
                        <div className="grid md:grid-cols-3 gap-8">
                            {/* Feature 1 */}
                            <div className="backdrop-blur-xl bg-white/60 dark:bg-gray-800/60 border border-white/20 dark:border-gray-700/50 rounded-xl p-6 hover:shadow-xl transition-shadow duration-200">
                                <div className="p-3 bg-gradient-to-br from-blue-500 to-indigo-500 rounded-lg w-fit mb-4">
                                    <Shield className="w-6 h-6 text-white" />
                                </div>
                                <h3 className="font-bold text-xl mb-3 text-gray-900 dark:text-gray-100">Privacy-First</h3>
                                <p className="text-gray-600 dark:text-gray-300 leading-relaxed">
                                    Run locally with Ollama or use cloud providers. Your data stays under your control.
                                </p>
                            </div>

                            {/* Feature 2 */}
                            <div className="backdrop-blur-xl bg-white/60 dark:bg-gray-800/60 border border-white/20 dark:border-gray-700/50 rounded-xl p-6 hover:shadow-xl transition-shadow duration-200">
                                <div className="p-3 bg-gradient-to-br from-purple-500 to-pink-500 rounded-lg w-fit mb-4">
                                    <Sparkles className="w-6 h-6 text-white" />
                                </div>
                                <h3 className="font-bold text-xl mb-3 text-gray-900 dark:text-gray-100">AI-Powered</h3>
                                <p className="text-gray-600 dark:text-gray-300 leading-relaxed">
                                    Leverages state-of-the-art LLMs to generate high-quality Q&A pairs from your documents.
                                </p>
                            </div>

                            {/* Feature 3 */}
                            <div className="backdrop-blur-xl bg-white/60 dark:bg-gray-800/60 border border-white/20 dark:border-gray-700/50 rounded-xl p-6 hover:shadow-xl transition-shadow duration-200">
                                <div className="p-3 bg-gradient-to-br from-indigo-500 to-purple-500 rounded-lg w-fit mb-4">
                                    <FileCode2 className="w-6 h-6 text-white" />
                                </div>
                                <h3 className="font-bold text-xl mb-3 text-gray-900 dark:text-gray-100">Multiple Formats</h3>
                                <p className="text-gray-600 dark:text-gray-300 leading-relaxed">
                                    Export in ShareGPT, Alpaca, or JSONL formats, ready for fine-tuning your models.
                                </p>
                            </div>
                        </div>
                    </div>
                </section>
            </main>

            {/* Footer */}
            <footer className="backdrop-blur-sm bg-white/50 dark:bg-gray-900/50 border-t border-white/20 dark:border-gray-700/50 py-8">
                <div className="container px-4 md:px-6 mx-auto text-center">
                    <div className="flex items-center justify-center gap-2 text-gray-600 dark:text-gray-400">
                        <Sparkles className="w-4 h-4" />
                        <span className="text-sm font-medium">FineTuneMe</span>
                    </div>
                </div>
            </footer>
        </div>
    )
}
