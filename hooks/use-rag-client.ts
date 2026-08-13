'use client'

import { useCallback, useState } from 'react'
import { useAppStore } from '@/lib/store'
import { ragClient } from '@/lib/api-client'
import type { Message } from '@/lib/store'

interface UseRagClientOptions {
  notebookId: string
  conversationId: string
}

interface UseRagClientResult {
  sendMessage: (query: string) => Promise<void>
  isSending: boolean
  error: string | null
}

function createId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID()
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

export function useRagClient({ notebookId, conversationId }: UseRagClientOptions): UseRagClientResult {
  const addMessage = useAppStore((state) => state.addMessage)
  const useServerSync = useAppStore((state) => state.useServerSync)
  const [isSending, setIsSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const sendMessage = useCallback(
    async (query: string) => {
      const trimmed = query.trim()
      if (!trimmed || !notebookId || !conversationId) return

      setError(null)

      // Optimistically add the user's message.
      const userMessage: Message = {
        id: createId(),
        role: 'user',
        content: trimmed,
        timestamp: new Date(),
      }
      addMessage(notebookId, conversationId, userMessage)

      // Selected sources for this conversation drive which documents the
      // backend is allowed to retrieve from.
      const conversation = useAppStore
        .getState()
        .notebooks.find((n) => n.id === notebookId)
        ?.conversations.find((c) => c.id === conversationId)
      const documentIds = conversation?.selectedDocumentIds ?? []

      setIsSending(true)
      if (useServerSync) {
        ragClient.setCurrentConversation(conversationId)
      }
      try {
        if (documentIds.length === 0) {
          throw new Error('Lütfen en az bir kaynak seçin.')
        }
        const response = await ragClient.chat({
          query: trimmed,
          documentIds,
        })

        const assistantMessage: Message = {
          id: createId(),
          role: 'assistant',
          content: response.response,
          timestamp: new Date(),
          citations: response.citations,
        }
        addMessage(notebookId, conversationId, assistantMessage)
      } catch (err) {
        console.error('[useRagClient] sendMessage failed:', {
          notebookId,
          conversationId,
          message: err instanceof Error ? err.message : String(err),
        })
        const message = err instanceof Error ? err.message : 'Mesaj gönderilirken bir hata oluştu.'
        setError(message)

        const errorMessage: Message = {
          id: createId(),
          role: 'assistant',
          content: 'Üzgünüm, bir hata oluştu. Lütfen tekrar deneyin.',
          timestamp: new Date(),
        }
        addMessage(notebookId, conversationId, errorMessage)
      } finally {
        setIsSending(false)
      }
    },
    [notebookId, conversationId, addMessage, useServerSync]
  )

  return { sendMessage, isSending, error }
}
