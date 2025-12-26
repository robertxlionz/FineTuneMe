/**
 * Type-safe localStorage wrapper for FineTuneMe V2.0
 * Persists user settings across browser sessions
 *
 * Security: API keys stored locally, never sent to backend except during API requests
 */

export interface FineTuneMeSettings {
  provider: string
  apiKey: string // Legacy - kept for backward compatibility (Groq)
  groqApiKey: string
  openaiApiKey: string
  anthropicApiKey: string
  model: string
  role: string
  format: string
}

const STORAGE_KEYS = {
  PROVIDER: 'ftm_provider',
  API_KEY: 'ftm_api_key', // Legacy - Groq
  GROQ_API_KEY: 'ftm_groq_api_key',
  OPENAI_API_KEY: 'ftm_openai_api_key',
  ANTHROPIC_API_KEY: 'ftm_anthropic_api_key',
  MODEL: 'ftm_model',
  ROLE: 'ftm_role',
  FORMAT: 'ftm_format',
} as const

const DEFAULT_SETTINGS: FineTuneMeSettings = {
  provider: 'ollama',
  apiKey: '', // Legacy
  groqApiKey: '',
  openaiApiKey: '',
  anthropicApiKey: '',
  model: '',
  role: 'teacher',
  format: 'sharegpt',
}

class FineTuneMeStorage {
  /**
   * Check if localStorage is available
   */
  private isAvailable(): boolean {
    try {
      const test = '__storage_test__'
      localStorage.setItem(test, test)
      localStorage.removeItem(test)
      return true
    } catch {
      console.warn('localStorage not available - using in-memory fallback')
      return false
    }
  }

  /**
   * Get a single setting value
   */
  get(key: keyof typeof STORAGE_KEYS): string {
    if (!this.isAvailable()) {
      const defaultKey = key.toLowerCase() as keyof FineTuneMeSettings
      return DEFAULT_SETTINGS[defaultKey] || ''
    }

    try {
      const value = localStorage.getItem(STORAGE_KEYS[key])
      if (value !== null) {
        return value
      }

      // Return default
      const defaultKey = key.toLowerCase() as keyof FineTuneMeSettings
      return DEFAULT_SETTINGS[defaultKey] || ''
    } catch (error) {
      console.warn(`Failed to read ${key} from localStorage:`, error)
      const defaultKey = key.toLowerCase() as keyof FineTuneMeSettings
      return DEFAULT_SETTINGS[defaultKey] || ''
    }
  }

  /**
   * Set a single setting value
   */
  set(key: keyof typeof STORAGE_KEYS, value: string): void {
    if (!this.isAvailable()) return

    try {
      localStorage.setItem(STORAGE_KEYS[key], value)
    } catch (error) {
      console.warn(`Failed to save ${key} to localStorage:`, error)
    }
  }

  /**
   * Get all settings
   */
  getAll(): FineTuneMeSettings {
    return {
      provider: this.get('PROVIDER'),
      apiKey: this.get('API_KEY'), // Legacy
      groqApiKey: this.get('GROQ_API_KEY') || this.get('API_KEY'), // Fallback to legacy
      openaiApiKey: this.get('OPENAI_API_KEY'),
      anthropicApiKey: this.get('ANTHROPIC_API_KEY'),
      model: this.get('MODEL'),
      role: this.get('ROLE'),
      format: this.get('FORMAT'),
    }
  }

  /**
   * Set all settings at once
   */
  setAll(settings: Partial<FineTuneMeSettings>): void {
    if (settings.provider !== undefined) this.set('PROVIDER', settings.provider)
    if (settings.apiKey !== undefined) this.set('API_KEY', settings.apiKey) // Legacy
    if (settings.groqApiKey !== undefined) this.set('GROQ_API_KEY', settings.groqApiKey)
    if (settings.openaiApiKey !== undefined) this.set('OPENAI_API_KEY', settings.openaiApiKey)
    if (settings.anthropicApiKey !== undefined) this.set('ANTHROPIC_API_KEY', settings.anthropicApiKey)
    if (settings.model !== undefined) this.set('MODEL', settings.model)
    if (settings.role !== undefined) this.set('ROLE', settings.role)
    if (settings.format !== undefined) this.set('FORMAT', settings.format)
  }

  /**
   * Clear all settings (reset to defaults)
   */
  clear(): void {
    if (!this.isAvailable()) return

    try {
      Object.values(STORAGE_KEYS).forEach(key => {
        localStorage.removeItem(key)
      })
    } catch (error) {
      console.warn('Failed to clear localStorage:', error)
    }
  }

  /**
   * Clear only sensitive data (API keys)
   * Use this for security when user logs out or clears secrets
   */
  clearSecrets(): void {
    this.set('API_KEY', '')
    this.set('GROQ_API_KEY', '')
    this.set('OPENAI_API_KEY', '')
    this.set('ANTHROPIC_API_KEY', '')
  }

  /**
   * Check if user has saved any settings
   */
  hasSettings(): boolean {
    if (!this.isAvailable()) return false

    try {
      return localStorage.getItem(STORAGE_KEYS.PROVIDER) !== null
    } catch {
      return false
    }
  }

  /**
   * Export settings as JSON (for backup/debugging)
   */
  export(): string {
    return JSON.stringify(this.getAll(), null, 2)
  }

  /**
   * Import settings from JSON (for restore)
   */
  import(json: string): boolean {
    try {
      const settings = JSON.parse(json) as Partial<FineTuneMeSettings>
      this.setAll(settings)
      return true
    } catch (error) {
      console.error('Failed to import settings:', error)
      return false
    }
  }

  /**
   * Get storage size (for debugging)
   */
  getStorageInfo(): { used: number; available: boolean } {
    if (!this.isAvailable()) {
      return { used: 0, available: false }
    }

    try {
      const allSettings = this.export()
      const sizeInBytes = new Blob([allSettings]).size
      return {
        used: sizeInBytes,
        available: true
      }
    } catch {
      return { used: 0, available: false }
    }
  }
}

// Export singleton instance
export const ftmStorage = new FineTuneMeStorage()

// Export helper functions for convenience
export const loadSettings = () => ftmStorage.getAll()
export const saveSettings = (settings: Partial<FineTuneMeSettings>) => ftmStorage.setAll(settings)
export const clearAllSettings = () => ftmStorage.clear()
export const clearApiKeys = () => ftmStorage.clearSecrets()
