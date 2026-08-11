import axios, { AxiosInstance } from 'axios'
import { getApiBaseUrl } from '@/lib/env-config'

export interface ChatRequest {
  query: string
  documentIds?: string[]        // artik gercekten kullaniliyor: secili room id'leri
  knowledgeSources?: string[]   // dokunulmadi, kapsam disi
}

export interface ChatResponse {
  response: string
  citations: Record<string, CitationInfo>   // ham şekli koru, dönüştürme
  status: string                             // eksik olan alan
}

export interface UploadResponse {
  filename: string
  size: number
  uploaded_at: string
}

// Backend: /notebooks
export interface Notebook {
  id: string
  name: string
}

// Backend: /notebooks/<nb_id>/conversations
export interface Conversation {
  id: string
  title: string
}

// Backend: /conversations/<conv_id>/messages
export interface ConversationMessage {
  id: string
  role: string
  content: string
  timestamp: string
}

// Backend'deki room yapısı
export interface Room {
  id: string
  name: string
}

// Tek bir citation'ın şekli — store.ts ve UI bileşenleri bunu import eder
export interface CitationInfo {
  page: number | null
  text: string
  pdf_url: string | null
}

// Backend'den gelen chat yanıtı
export interface BackendChatResponse {
  text: string
  citations: Record<string, CitationInfo>
  status: string
}

export class RAGClient {
  private client: AxiosInstance
  private currentRoomId: string | null = null
  private currentConversationId: string | null = null

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
      const hasDocumentIds = !!request.documentIds && request.documentIds.length > 0

      if (!this.currentRoomId && !hasDocumentIds) {
        throw new Error('Önce bir oda (room) oluşturmalı veya seçmelisiniz!')
      }

      const payload: Record<string, unknown> = {
        room: hasDocumentIds ? request.documentIds![0] : this.currentRoomId,
        soru: request.query
      }

      // documentIds doluysa selected room'lari payload'a ekle ve currentRoomId'i
      // de senkron tut, boylece sonraki chat() cagrilarinda tekrar hata alinmaz.
      if (hasDocumentIds) {
        payload.rooms = request.documentIds
        this.currentRoomId = request.documentIds![0]
      }

      if (this.currentConversationId) {
        payload.conversation_id = this.currentConversationId
      }

      const response = await this.client.post<BackendChatResponse>('/chat-client', payload)

      return {
        response: response.data.text || 'Yanıt alındı',
        citations: response.data.citations || {},
        status: response.data.status,
      }
    } catch (error) {
      throw this.handleError(error)
    }
  }

  // Backend: POST /rooms
  // Beklenen: multipart/form-data ile 'file' alanında PDF
  // Dönen (flat): { "id": "...", "name": "..." }
  async uploadFile(file: File, notebookId: string): Promise<UploadResponse> {
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('notebook_id', notebookId)

      const response = await this.client.post('/rooms', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })

      const room = response.data

      if (room?.id) {
        this.currentRoomId = room.id
      }

      return {
        filename: room?.name || file.name,
        size: file.size,
        uploaded_at: new Date().toISOString()
      }
    } catch (error) {
      throw this.handleError(error)
    }
  }

  // Backend: GET /rooms
  // Dönen: { "rooms": [ { "id": "...", "name": "..." } ] }
  async getDocuments(): Promise<Array<{ name: string; size: number; uploaded_at: string }>> {
    try {
      const response = await this.client.get('/rooms')
      const rooms = response.data.rooms || []
      
      return rooms.map((room: Room) => ({
        name: room.name || room.id || 'Belge',
        size: 0, // Backend size döndürmüyor
        uploaded_at: new Date().toISOString()
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
  // Beklenen: multipart/form-data ile 'file' alanında PDF
  // Dönen (flat): { "id": "...", "name": "..." }
async createRoom(file: File, notebookId: string): Promise<Room> {
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('notebook_id', notebookId)

      const response = await this.client.post('/rooms', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })

      const room = response.data

      if (room?.id) {
        this.currentRoomId = room.id
      }

      return room
    } catch (error) {
      throw this.handleError(error)
    }
}

  // Backend /rooms TEK dosya kabul ediyor; coklu dosya icin bu metod
  // createRoom'u her dosya icin paralel cagirir. Promise.allSettled kullanildigi
  // icin bir dosyanin basarisiz olmasi digerlerini etkilemez.
  // Not: createRoom icindeki `this.currentRoomId = ...` yan etkisi burada da
  // calisir; sirali cagrilarda en son basariyla yuklenen room currentRoomId
  // olarak kalir. Bu kabul edilebilir cunku artik chat() hangi room'lari
  // kullanacagini documentIds ile acikca biliyor.
async createRooms(files: File[], notebookId: string): Promise<{ succeeded: Room[]; failed: { file: string; error: string }[] }> {
    const results = await Promise.allSettled(files.map((file) => this.createRoom(file, notebookId)))

    const succeeded: Room[] = []
    const failed: { file: string; error: string }[] = []

    results.forEach((result, index) => {
      if (result.status === 'fulfilled') {
        succeeded.push(result.value)
      } else {
        failed.push({
          file: files[index].name,
          error: result.reason instanceof Error ? result.reason.message : 'Bilinmeyen hata',
        })
      }
    })

    return { succeeded, failed }
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

  // Mevcut conversation'ı set et
  setCurrentConversation(conversationId: string | null): void {
    this.currentConversationId = conversationId
  }

  // Mevcut conversation'ı getir
  getCurrentConversation(): string | null {
    return this.currentConversationId
  }

  // Backend: POST /notebooks
  // Beklenen: { "name": "..." }
  // Dönen: { "id": "...", "name": "..." }
async createNotebook(name: string): Promise<Notebook> {
    try {
      const response = await this.client.post<Notebook>('/notebooks', { name })
      return { ...response.data, id: String(response.data.id) }
    } catch (error) {
      throw this.handleError(error)
    }
  }

  // Backend: GET /notebooks
  // Dönen: [ { "id": "...", "name": "..." } ]
async getNotebooks(): Promise<Notebook[]> {
    try {
      const response = await this.client.get<Notebook[]>('/notebooks')
      return response.data.map((nb) => ({ ...nb, id: String(nb.id) }))
    } catch (error) {
      throw this.handleError(error)
    }
  }

  // Backend: POST /notebooks/<nb_id>/conversations
  // Beklenen: { "title": "..." }
  // Dönen: { "id": "...", "title": "..." }
async createConversation(notebookId: string, title: string): Promise<Conversation> {
    try {
      const response = await this.client.post<Conversation>(
        `/notebooks/${notebookId}/conversations`,
        { title }
      )
      return { ...response.data, id: String(response.data.id) }
    } catch (error) {
      throw this.handleError(error)
    }
  }

  // Backend: GET /notebooks/<nb_id>/conversations
  // Dönen: [ { "id": "...", "title": "..." } ]
async getConversations(notebookId: string): Promise<Conversation[]> {
    try {
      const response = await this.client.get<Conversation[]>(
        `/notebooks/${notebookId}/conversations`
      )
      return response.data.map((c) => ({ ...c, id: String(c.id) }))
    } catch (error) {
      throw this.handleError(error)
    }
  }

  // Backend: POST /conversations/<conv_id>/messages
  // Beklenen: { "role": "...", "content": "..." }
  // Dönen: { "id": "...", "role": "...", "content": "...", "timestamp": "..." }
  async addMessage(conversationId: string, message: { role: string; content: string }): Promise<void> {
    try {
      await this.client.post(`/conversations/${conversationId}/messages`, message)
    } catch (error) {
      throw this.handleError(error)
    }
  }

  // Backend: GET /conversations/<conv_id>/messages
  // Dönen: [ { "id": "...", "role": "...", "content": "...", "timestamp": "..." } ]
  async getMessages(conversationId: string): Promise<ConversationMessage[]> {
    try {
      const response = await this.client.get<ConversationMessage[]>(
        `/conversations/${conversationId}/messages`
      )
      return response.data
    } catch (error) {
      throw this.handleError(error)
    }
  }

  // Backend: DELETE /conversations/<conv_id>
  async deleteConversation(conversationId: string): Promise<void> {
    try {
      await this.client.delete(`/conversations/${conversationId}`)
    } catch (error) {
      throw this.handleError(error)
    }
  }

  // Backend: DELETE /rooms/<room_id>
  async deleteRoom(roomId: string): Promise<void> {
    try {
      await this.client.delete(`/rooms/${roomId}`)

      if (this.currentRoomId === roomId) {
        this.currentRoomId = null
      }
    } catch (error) {
      throw this.handleError(error)
    }
  }

  // Not: Backend'de dosya adına göre silme/reset endpoint'i yok; room id
  // ile silmek için deleteRoom() kullanılmalı.
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