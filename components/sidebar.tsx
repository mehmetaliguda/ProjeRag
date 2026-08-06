'use client'

import { useState } from 'react'
import { useAppStore } from '@/lib/store'
import { RAGClient } from '@/lib/api-client'
import { Button } from '@/components/ui/button'
import { DocumentsMultiSelect } from '@/components/documents-multi-select'
import {
  Plus,
  Menu,
  X,
  Trash2,
  MessageCircle,
  ChevronRight,
  ChevronDown,
  FileText,
} from 'lucide-react'

interface SidebarProps {
  notebookId: string
}

export function Sidebar({ notebookId }: SidebarProps) {
  const {
    notebooks,
    currentConversationId,
    sidebarOpen,
    backendUrl,
    setSidebarOpen,
    createConversation,
    deleteConversation,
    setCurrentConversation,
    toggleDocumentSelection,
    selectAllDocuments,
    clearDocumentSelection,
    removeDocument,
  } = useAppStore()

  // VS Code'daki explorer paneli gibi: iki bolum, her biri bagimsiz acilip kapanabilir
  const [sourcesOpen, setSourcesOpen] = useState(true)
  const [historyOpen, setHistoryOpen] = useState(true)

  const notebook = notebooks.find((nb) => nb.id === notebookId)
  const conversations = notebook?.conversations || []
  const conversation = conversations.find((c) => c.id === currentConversationId)
  const documents = conversation?.documents || []

  const handleNewConversation = () => {
    const title = `Chat ${conversations.length + 1}`
    createConversation(notebookId, title)
  }

  const handleRemoveDocument = async (docId: string) => {
    if (!conversation) return
    const doc = documents.find((d) => d.id === docId)
    if (!doc) return

    try {
      const client = new RAGClient(backendUrl)
      await client.deleteDocument(doc.name)
      removeDocument(notebookId, conversation.id, docId)
    } catch (err) {
      console.error('[v0] Delete error:', err)
    }
  }

  return (
    <>
      {/* Mobile Toggle Button */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="md:hidden fixed top-4 left-4 z-50 p-2 hover:bg-muted rounded-lg transition-colors"
        aria-label="Toggle sidebar"
      >
        {sidebarOpen ? <X size={24} /> : <Menu size={24} />}
      </button>

      {/* Sidebar Overlay */}
      {sidebarOpen && (
        <div
          className="md:hidden fixed inset-0 bg-black/50 z-40"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed md:relative h-screen w-72 bg-card border-r border-border flex flex-col transition-all duration-300 z-40 md:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Header */}
        <div className="p-4 border-b border-border">
          <Button onClick={handleNewConversation} className="w-full gap-2" size="sm">
            <Plus size={16} />
            Yeni Sohbet
          </Button>
        </div>

        {/* Alt alta duran, acilip kapanan paneller (VS Code sol panel mantigi) */}
        <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
          {/* KAYNAKLAR (PDF secimi) */}
          <div
            className={`flex flex-col border-b border-border ${
              sourcesOpen ? 'max-h-[45%]' : ''
            }`}
          >
            <button
              onClick={() => setSourcesOpen((v) => !v)}
              className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors shrink-0"
            >
              {sourcesOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              <FileText size={14} />
              <span className="flex-1 text-left">Kaynaklar</span>
              <span className="text-[10px] font-normal normal-case bg-muted px-1.5 py-0.5 rounded-full">
                {documents.length}
              </span>
            </button>

            {sourcesOpen && (
              <div className="px-2 pb-3 overflow-y-auto">
                {!conversation ? (
                  <p className="text-xs text-muted-foreground px-1 py-2">
                    Önce bir sohbet seçin
                  </p>
                ) : documents.length === 0 ? (
                  <p className="text-xs text-muted-foreground px-1 py-2">
                    Henüz belge yüklenmedi
                  </p>
                ) : (
                  <DocumentsMultiSelect
                    documents={documents}
                    selectedIds={conversation.selectedDocumentIds}
                    onToggleSelect={(docId) => toggleDocumentSelection(notebookId, conversation.id, docId)}
                    onSelectAll={() => selectAllDocuments(notebookId, conversation.id)}
                    onClearAll={() => clearDocumentSelection(notebookId, conversation.id)}
                    onRemove={handleRemoveDocument}
                  />
                )}
              </div>
            )}
          </div>

          {/* SOHBET GECMISI */}
          <div className="flex flex-col flex-1 min-h-0">
            <button
              onClick={() => setHistoryOpen((v) => !v)}
              className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors shrink-0"
            >
              {historyOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              <MessageCircle size={14} />
              <span className="flex-1 text-left">Sohbet Geçmişi</span>
              <span className="text-[10px] font-normal normal-case bg-muted px-1.5 py-0.5 rounded-full">
                {conversations.length}
              </span>
            </button>

            {historyOpen && (
              <div className="flex-1 overflow-y-auto px-2 pb-2">
                {conversations.length === 0 ? (
                  <div className="text-center py-8 px-2 text-muted-foreground text-sm">
                    <MessageCircle size={32} className="mx-auto mb-2 opacity-50" />
                    <p>Henüz sohbet yok</p>
                  </div>
                ) : (
                  <div className="space-y-1">
                    {conversations.map((conv) => (
                      <div
                        key={conv.id}
                        className={`flex items-center gap-2 p-2 rounded-lg transition-colors group cursor-pointer ${
                          currentConversationId === conv.id
                            ? 'bg-primary/10 text-primary'
                            : 'hover:bg-muted'
                        }`}
                      >
                        <button
                          onClick={() => setCurrentConversation(notebookId, conv.id)}
                          className="flex-1 text-left min-w-0"
                        >
                          <p className="text-sm truncate font-medium">{conv.title}</p>
                          <p className="text-xs text-muted-foreground truncate">
                            {conv.messages.length} mesaj · {conv.documents.length} belge
                          </p>
                        </button>
                        <button
                          onClick={() => deleteConversation(notebookId, conv.id)}
                          className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-destructive/10 rounded"
                          aria-label="Sohbeti sil"
                        >
                          <Trash2 size={14} className="text-destructive" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="border-t border-border p-4">
          {/* Close on Mobile */}
          <Button
            variant="outline"
            size="sm"
            onClick={() => setSidebarOpen(false)}
            className="w-full md:hidden gap-2"
          >
            Kapat
            <ChevronRight size={16} />
          </Button>
        </div>
      </aside>
    </>
  )
}
