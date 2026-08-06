/**
 * Environment Configuration Module
 * 
 * Centralized configuration for all backend URLs and API endpoints.
 * Never hard-code IP addresses, localhost, or ports directly in code.
 * 
 * Usage:
 *   import { getBackendConfig } from '@/lib/env-config'
 *   const config = getBackendConfig()
 *   const url = config.apiBaseUrl
 */

export interface BackendConfig {
  apiBaseUrl: string
  backendHost: string
  backendPort: number
  uploadApiUrl: string
  websocketUrl?: string
}

function getBackendConfig(): BackendConfig {
  // Get from environment variables or fall back to defaults
  const apiBaseUrl =
    process.env.NEXT_PUBLIC_API_BASE_URL || 
    process.env.NEXT_PUBLIC_BACKEND_URL ||
    'http://127.0.0.1:5000'

  const backendHost =
    process.env.NEXT_PUBLIC_BACKEND_HOST ||
    extractHost(apiBaseUrl) ||
    '127.0.0.1'

  const backendPort =
    parseInt(process.env.NEXT_PUBLIC_BACKEND_PORT || '5000', 10)

  const uploadApiUrl =
    process.env.NEXT_PUBLIC_UPLOAD_API_URL ||
    `${apiBaseUrl}/upload`

  const websocketUrl = process.env.NEXT_PUBLIC_WEBSOCKET_URL

  return {
    apiBaseUrl,
    backendHost,
    backendPort,
    uploadApiUrl,
    websocketUrl,
  }
}

function extractHost(url: string): string {
  try {
    const urlObj = new URL(url)
    return urlObj.hostname || '127.0.0.1'
  } catch {
    return '127.0.0.1'
  }
}

/**
 * Get the full backend API base URL
 * This should be used for all API requests
 */
export function getApiBaseUrl(): string {
  return getBackendConfig().apiBaseUrl
}

/**
 * Get the backend host
 */
export function getBackendHost(): string {
  return getBackendConfig().backendHost
}

/**
 * Get the backend port
 */
export function getBackendPort(): number {
  return getBackendConfig().backendPort
}

/**
 * Get the upload API URL
 */
export function getUploadApiUrl(): string {
  return getBackendConfig().uploadApiUrl
}

/**
 * Get the WebSocket URL (optional)
 */
export function getWebSocketUrl(): string | undefined {
  return getBackendConfig().websocketUrl
}

export default getBackendConfig
