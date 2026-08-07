'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { useAppStore } from '@/lib/store'
import { useRagClient } from '@/hooks/use-rag-client'
import { ResizableSidebar } from '@/components/sidebar/resizable-sidebar'
import { ChatMessage } from '@/components/chat/chat-message'
import { CitationPanel } from '@/components/citation-panel'
import { Button } from '@/components/ui/button'
import { ArrowLeft, Send } from 'lucide-react'

export default function ChatPage() {
  const router = useRouter()
  const params = useParams()
  const notebookId = params.notebookId as string

  const {
    setCurrentNotebook,
    notebooks,
    currentNotebookId,
    currentConversationId,
    createConversation,
    setCurrentConversation,
  } = useAppStore()

  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (notebookId && notebookId !== currentNotebookId) {
      setCurrentNotebook(notebookId)
    }
  }, [notebookId, currentNotebookId, setCurrentNotebook])

  const currentNotebook = notebooks.find((nb) => nb.id === notebookId)

  // Ensure there's always an active conversation to chat in — if the
  // notebook has none yet, create one automatically on first visit.
  useEffect(() => {
    if (!currentNotebook) return
    if (currentNotebook.conversations.length === 0) {
      createConversation(notebookId, 'Yeni Sohbet')
    } else if (!currentConversationId) {
      setCurrentConversation(notebookId, currentNotebook.conversations[0].id)
    }
  }, [currentNotebook, notebookId, currentConversationId, createConversation, setCurrentConversation])

  const currentConversation = currentNotebook?.conversations.find(
    (c) => c.id === currentConversationId
  )
  const conversationId = currentConversation?.id ?? ''

  const { sendMessage, isSending, error } = useRagClient({ notebookId, conversationId })

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [currentConversation?.messages.length])

  const handleGoBack = () => {
    router.push('/notebooks')
  }

  const handleSend = async () => {
    const query = input.trim()
    if (!query || isSending || !conversationId) return
    setInput('')
    await sendMessage(query)
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex h-screen w-full bg-background text-foreground overflow-hidden page-enter">
      {/* SOL: Sohbet geçmişi + kaynaklar */}
      <aside className="w-72 flex-shrink-0 border-r border-border">
        <ResizableSidebar notebookId={notebookId} />
      </aside>

      {/* ORTA: Sohbet alanı */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Back Navigation Header */}
        <div className="border-b border-border bg-background/50 px-4 py-3 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={handleGoBack} className="gap-2">
              <ArrowLeft className="h-4 w-4" />
              Back to Notebooks
            </Button>
            {currentNotebook && (
              <span className="text-sm text-muted-foreground">• {currentNotebook.name}</span>
            )}
          </div>
        </div>

        {/* Mesaj listesi */}
        <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
          {!currentConversation || currentConversation.messages.length === 0 ? (
            <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
              Sorularınızı sormaya başlayın.
            </div>
          ) : (
            currentConversation.messages.map((message) => (
              <ChatMessage key={message.id} message={message} />
            ))
          )}
          {isSending && (
            <div className="flex justify-start">
              <div className="rounded-lg bg-gray-100 px-4 py-2.5 text-sm text-gray-500">
                Yanıt yazılıyor…
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {error && (
          <div className="px-4 pb-2 text-xs text-red-600">{error}</div>
        )}

        {/* Mesaj giriş kutusu */}
        <div className="flex-shrink-0 border-t border-border p-4">
          <div className="flex items-end gap-2">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Bir soru yazın…"
              rows={1}
              disabled={!conversationId}
              className="flex-1 resize-none rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
            />
            <Button
              onClick={handleSend}
              disabled={!input.trim() || isSending || !conversationId}
              size="icon"
              className="flex-shrink-0"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* SAĞ: Citation paneli — activeCitation doluyken kendi kendine
          görünür, layout'ta sabit bir kolon ayırmaya gerek yok (fixed). */}
      <CitationPanel />
    </div>
  )
}