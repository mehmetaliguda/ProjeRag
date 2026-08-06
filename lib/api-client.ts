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

// Backend'deki room yapısı
export interface Room {
  id: string
  display_name: string
  pdf_path: string
  image_dir: string
  created_at: string
}

// Backend'den gelen chat yanıtı
export interface BackendChatResponse {
  text: string
  citations: Record<string, {
    page: number
    image: string | null
    text: string
    pdf_url: string | null
  }>
  status: string
}

export class RAGClient {
  private client: AxiosInstance
  private currentRoomId: string | null = null

  constructor(baseURL?: string) {
    const finalBaseURL = baseURL || getApiBaseUrl() || 'http://127.0.0.1:5000'
    
    this.client = axios.create({
      baseURL: finalBaseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    })
  }

  // Backend: POST /chat-client
  // Beklenen: { "room": "room_id", "soru": "user_question" }
  // Dönen: { "text": "...", "citations": {...}, "status": "success" }
  async chat(request: ChatRequest): Promise<ChatResponse> {
    try {
      if (!this.currentRoomId) {
        throw new Error('Önce bir oda (room) oluşturmalı veya seçmelisiniz!')
      }

      const payload = {
        room: this.currentRoomId,
        soru: request.query
      }

      const response = await this.client.post<BackendChatResponse>('/chat-client', payload)
      
      // Backend yanıtını frontend formatına çevir
      const sources = Object.entries(response.data.citations || {}).map(([id, citation]) => ({
        document: citation.text?.substring(0, 50) + '...' || 'Kaynak',
        page: citation.page !== undefined ? citation.page + 1 : undefined,
        excerpt: citation.text || '',
        image_url: citation.image || undefined,
        pdf_url: citation.pdf_url || undefined
      }))

      return {
        response: response.data.text || 'Yanıt alındı',
        sources: sources.length > 0 ? sources : undefined
      }
    } catch (error) {
      throw this.handleError(error)
    }
  }

  // Backend: POST /rooms
  // Beklenen: multipart/form-data ile 'file' alanında PDF
  // Dönen: { "room": { "id": "...", "display_name": "...", ... } }
  async uploadFile(file: File): Promise<UploadResponse> {
    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await this.client.post('/rooms', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })

      // Room ID'yi kaydet
      if (response.data.room?.id) {
        this.currentRoomId = response.data.room.id
      }

      return {
        filename: response.data.room?.display_name || file.name,
        size: file.size,
        uploaded_at: response.data.room?.created_at || new Date().toISOString()
      }
    } catch (error) {
      throw this.handleError(error)
    }
  }

  // Backend: GET /rooms
  // Dönen: { "rooms": [ { "id": "...", "display_name": "...", ... } ] }
  async getDocuments(): Promise<Array<{ name: string; size: number; uploaded_at: string }>> {
    try {
      const response = await this.client.get('/rooms')
      const rooms = response.data.rooms || []
      
      return rooms.map((room: Room) => ({
        name: room.display_name || room.id || 'Belge',
        size: 0, // Backend size döndürmüyor
        uploaded_at: room.created_at || new Date().toISOString()
      }))
    } catch (error) {
      throw this.handleError(error)
    }
  }

  // Backend: GET /rooms (tüm room'ları listele)
  async getRooms(): Promise<Room[]> {
    try {
      const response = await this.client.get('/rooms')
      return response.data.rooms || []
    } catch (error) {
      throw this.handleError(error)
    }
  }

  // Backend: POST /rooms (yeni room oluştur)
  async createRoom(file: File): Promise<Room> {
    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await this.client.post('/rooms', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })

      if (response.data.room?.id) {
        this.currentRoomId = response.data.room.id
      }

      return response.data.room
    } catch (error) {
      throw this.handleError(error)
    }
  }

  // Mevcut room'u set et
  setCurrentRoom(roomId: string): void {
    this.currentRoomId = roomId
  }

  // Mevcut room'u getir
  getCurrentRoom(): string | null {
    return this.currentRoomId
  }

  // Backend: GET /source-pdf/<room_id>
  async getPdfUrl(roomId: string): Promise<string> {
    return `${this.client.defaults.baseURL}/source-pdf/${roomId}`
  }

  // Backend: GET /images/<room_id>/<filename>
  async getImageUrl(roomId: string, filename: string): Promise<string> {
    return `${this.client.defaults.baseURL}/images/${roomId}/${filename}`
  }

  // Not: Backend'de delete ve reset endpoint'leri yok
  async deleteDocument(filename: string): Promise<void> {
    console.warn('Silme işlemi backend tarafından desteklenmiyor:', filename)
    throw new Error('Bu işlevsellik backend\'de bulunmuyor')
  }

  async resetContext(): Promise<void> {
    console.warn('Sıfırlama işlemi backend tarafından desteklenmiyor')
    throw new Error('Bu işlevsellik backend\'de bulunmuyor')
  }

  setBaseURL(baseURL: string): void {
    this.client.defaults.baseURL = baseURL
  }

  private handleError(error: any): Error {
    if (axios.isAxiosError(error)) {
      if (error.response) {
        const message =
          error.response.data?.error || 
          error.response.data?.message ||
          error.response.statusText || 
          'Server error'
        return new Error(`API Error: ${message}`)
      } else if (error.request) {
        return new Error('No response from server. Check if backend is running.')
      }
    }
    return error instanceof Error ? error : new Error('Unknown error occurred')
  }
}

// Singleton instance oluştur
export const ragClient = new RAGClient()