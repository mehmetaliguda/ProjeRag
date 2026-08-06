'use client'

import { useState, useRef, useEffect } from 'react'
import { useAppStore } from '@/lib/store'
import { RAGClient } from '@/lib/api-client'
import { getApiBaseUrl } from '@/lib/env-config'
import { MessageComponent } from '@/components/message'
import { ChatInput } from '@/components/chat-input'
import { ThemeSwitcher } from '@/components/theme-switcher'
import { AlertCircle, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface ChatPanelProps {
  notebookId: string
}

export function ChatPanel({ notebookId }: ChatPanelProps) {
  const {
    notebooks,
    currentConversationId,
    createConversation,
    addMessage,
    addDocument,
    updateDocumentStatus,
    getSelectedDocuments,
    backendUrl,
    setBackendUrl,
  } = useAppStore()

  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [ragClient, setRagClient] = useState<RAGClient>(() => new RAGClient(getApiBaseUrl()))
  const [showBackendSetup, setShowBackendSetup] = useState(false)
  const [tempBackendUrl, setTempBackendUrl] = useState(backendUrl || getApiBaseUrl())
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const notebook = notebooks.find((nb) => nb.id === notebookId)
  const conversation = notebook?.conversations.find((c) => c.id === currentConversationId)

  // Update RAG client when backend URL changes
  useEffect(() => {
    ragClient.setBaseURL(backendUrl)
  }, [backendUrl, ragClient])

  // Create initial conversation if none exists
  useEffect(() => {
    if (notebookId && notebook && notebook.conversations.length === 0) {
      createConversation(notebookId, 'Chat')
    }
  }, [notebookId, notebook, createConversation])

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [conversation?.messages])

  const handleSendMessage = async (content: string) => {
    if (!conversation || !notebookId) return

    setError(null)
    setIsLoading(true)

    // Add user message immediately
    const userMessage = {
      id: `msg-${Date.now()}`,
      role: 'user' as const,
      content,
      timestamp: new Date(),
    }
    addMessage(notebookId, conversation.id, userMessage)

    try {
      // Get selected documents for the query (varsayilan olarak hepsi secili gelir)
      const selectedDocs = getSelectedDocuments(notebookId, conversation.id)
      const documentIds = selectedDocs.map((d) => d.id)

      const response = await ragClient.chat({
        query: content,
        documentIds: documentIds.length > 0 ? documentIds : undefined,
        knowledgeSources: selectedDocs.map((d) => d.name),
      })

      const assistantMessage = {
        id: `msg-${Date.now()}-1`,
        role: 'assistant' as const,
        content: response.response,
        timestamp: new Date(),
      }
      addMessage(notebookId, conversation.id, assistantMessage)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get response'
      setError(errorMessage)
      console.error('[v0] Chat error:', errorMessage)
    } finally {
      setIsLoading(false)
    }
  }

  const handleUploadFile = async (file: File) => {
    if (!conversation || !notebookId) return

    setError(null)
    const docId = `doc-${Date.now()}`

    // Add document with uploading status (store, kaynagi otomatik olarak secili kaynaklara ekler)
    addDocument(notebookId, conversation.id, {
      id: docId,
      name: file.name,
      size: file.size,
      uploadedAt: new Date(),
      status: 'uploading',
    })

    try {
      updateDocumentStatus(notebookId, conversation.id, docId, 'processing')
      await ragClient.uploadFile(file)
      updateDocumentStatus(notebookId, conversation.id, docId, 'ready')
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Upload failed'
      setError(errorMessage)
      updateDocumentStatus(notebookId, conversation.id, docId, 'error')
      console.error('[v0] Upload error:', errorMessage)
    }
  }

  const handleUpdateBackend = () => {
    setBackendUrl(tempBackendUrl)
    setShowBackendSetup(false)
  }

  if (!conversation) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-4 text-center">
        <div className="text-4xl mb-4">📚</div>
        <h2 className="text-2xl font-bold mb-2">No conversation selected</h2>
        <p className="text-muted-foreground mb-6">Create a new conversation to get started</p>
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col h-screen md:h-full">
      {/* Header with Theme Switcher Integration */}
      <div className="border-b border-border p-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold truncate">{conversation.title}</h1>
          <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
            <span>{conversation.messages.length} messages</span>
            <span>•</span>
            <span>{conversation.documents.length} documents</span>
            <span>•</span>
            <button
              onClick={() => setShowBackendSetup(!showBackendSetup)}
              className="hover:text-foreground transition-colors"
            >
              Backend: {backendUrl.split('//')[1] || backendUrl}
            </button>
          </div>
        </div>
        {/* Theme Logo / Dropdown Toggle Button */}
        <div className="flex items-center gap-2">
          <ThemeSwitcher />
        </div>
      </div>

      {/* Backend Setup */}
      {showBackendSetup && (
        <div className="border-b border-border bg-muted/50 p-4">
          <div className="space-y-2">
            <label className="block text-sm font-medium">Backend URL</label>
            <div className="flex gap-2">
              <input
                type="text"
                value={tempBackendUrl}
                onChange={(e) => setTempBackendUrl(e.target.value)}
                placeholder="http://localhost:5000"
                className="flex-1 px-3 py-2 bg-background rounded-lg border border-border text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <Button
                size="sm"
                onClick={handleUpdateBackend}
              >
                Update
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  setShowBackendSetup(false)
                  setTempBackendUrl(backendUrl)
                }}
              >
                Cancel
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {conversation.messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="text-5xl mb-4">💬</div>
            <h3 className="text-lg font-semibold mb-2">Start the conversation</h3>
            <p className="text-sm text-muted-foreground max-w-sm">
              Upload documents and ask questions about them. The AI will provide
              answers based on the content.
            </p>
          </div>
        ) : (
          <>
            {conversation.messages.map((msg) => (
              <MessageComponent key={msg.id} message={msg} />
            ))}
            {isLoading && (
              <div className="flex gap-3 mb-4">
                <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-muted text-muted-foreground">
                  A
                </div>
                <div className="flex items-center gap-2 p-3 bg-muted rounded-lg">
                  <Loader2 size={16} className="animate-spin" />
                  <span className="text-sm">Thinking...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Error Alert */}
      {error && (
        <div className="border-t border-border bg-destructive/10 p-3 flex items-start gap-2">
          <AlertCircle size={16} className="text-destructive flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-destructive">Error</p>
            <p className="text-xs text-destructive/80">{error}</p>
          </div>
        </div>
      )}

      {/* Chat Input (belge secimi artik sol panelde / Sidebar bileseninde) */}
      <div className="border-t border-border p-4">
        <ChatInput
          onSendMessage={handleSendMessage}
          onUploadFile={handleUploadFile}
          disabled={!conversation}
          isLoading={isLoading}
        />
      </div>
    </div>
  )
}
