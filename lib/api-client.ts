import axios, { AxiosInstance } from 'axios'
import { getApiBaseUrl } from '@/lib/env-config'

export interface ChatRequest {
  query: string
  documentIds?: string[]
  knowledgeSources?: string[]
}

export interface ChatResponse {
  response: string
  sources?: Array<{
    document: string
    page?: number
    excerpt: string
  }>
}

export interface UploadResponse {
  filename: string
  size: number
  uploaded_at: string
}

export class RAGClient {
  private client: AxiosInstance

  constructor(baseURL?: string) {
    // Use provided baseURL, fallback to environment config, then default
    const finalBaseURL = baseURL || getApiBaseUrl() || 'http://127.0.0.1:5000'
    
    this.client = axios.create({
      baseURL: finalBaseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    })
  }

  async chat(request: ChatRequest): Promise<ChatResponse> {
    try {
      const response = await this.client.post<ChatResponse>('/chat', request)
      return response.data
    } catch (error) {
      throw this.handleError(error)
    }
  }

  async uploadFile(file: File): Promise<UploadResponse> {
    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await this.client.post<UploadResponse>('/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })
      return response.data
    } catch (error) {
      throw this.handleError(error)
    }
  }

  async getDocuments(): Promise<Array<{ name: string; size: number; uploaded_at: string }>> {
    try {
      const response = await this.client.get('/documents')
      return response.data.documents || []
    } catch (error) {
      throw this.handleError(error)
    }
  }

  async deleteDocument(filename: string): Promise<void> {
    try {
      await this.client.post(`/delete/${filename}`)
    } catch (error) {
      throw this.handleError(error)
    }
  }

  async resetContext(): Promise<void> {
    try {
      await this.client.post('/reset')
    } catch (error) {
      throw this.handleError(error)
    }
  }

  setBaseURL(baseURL: string): void {
    this.client.defaults.baseURL = baseURL
  }

  private handleError(error: any): Error {
    if (axios.isAxiosError(error)) {
      if (error.response) {
        const message =
          error.response.data?.error || error.response.statusText || 'Server error'
        return new Error(`API Error: ${message}`)
      } else if (error.request) {
        return new Error('No response from server. Check if backend is running.')
      }
    }
    return error instanceof Error ? error : new Error('Unknown error occurred')
  }
}
