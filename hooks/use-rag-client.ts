import { useCallback, useRef, useEffect } from 'react'
import { useAppStore } from '@/lib/store'
import { RAGClient, ChatRequest, ChatResponse, UploadResponse } from '@/lib/api-client'

/**
 * Hook for managing RAG API client with automatic backend URL syncing
 */
export function useRAGClient() {
  const { backendUrl } = useAppStore()
  const clientRef = useRef<RAGClient | null>(null)

  // Initialize client on first load and sync URL changes
  useEffect(() => {
    if (!clientRef.current) {
      clientRef.current = new RAGClient(backendUrl)
    } else {
      clientRef.current.setBaseURL(backendUrl)
    }
  }, [backendUrl])

  const chat = useCallback(
    async (request: ChatRequest): Promise<ChatResponse> => {
      if (!clientRef.current) {
        throw new Error('RAG client not initialized')
      }
      return clientRef.current.chat(request)
    },
    []
  )

  const uploadFile = useCallback(
    async (file: File): Promise<UploadResponse> => {
      if (!clientRef.current) {
        throw new Error('RAG client not initialized')
      }
      return clientRef.current.uploadFile(file)
    },
    []
  )

  const deleteDocument = useCallback(
    async (filename: string): Promise<void> => {
      if (!clientRef.current) {
        throw new Error('RAG client not initialized')
      }
      return clientRef.current.deleteDocument(filename)
    },
    []
  )

  const getDocuments = useCallback(async () => {
    if (!clientRef.current) {
      throw new Error('RAG client not initialized')
    }
    return clientRef.current.getDocuments()
  }, [])

  const resetContext = useCallback(async () => {
    if (!clientRef.current) {
      throw new Error('RAG client not initialized')
    }
    return clientRef.current.resetContext()
  }, [])

  return {
    chat,
    uploadFile,
    deleteDocument,
    getDocuments,
    resetContext,
  }
}
