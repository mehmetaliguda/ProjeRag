'use client'

import { useEffect, useState } from 'react'
import { Database } from 'lucide-react'
import { useAppStore } from '@/lib/store'
import type { Document } from '@/lib/store'
import { ragClient } from '@/lib/api-client'
import { PdfDropzone } from '@/components/upload/pdf-dropzone'

const EMPTY_DOCUMENTS: Document[] = []
const EMPTY_SELECTED_IDS: string[] = []

interface SourcesPanelProps {
  notebookId: string
  conversationId: string
}

const STATUS_STYLES: Record<Document['status'], { label: string; className: string }> = {
  uploading: { label: 'Yükleniyor', className: 'bg-blue-100 text-blue-700' },
  processing: { label: 'İşleniyor', className: 'bg-amber-100 text-amber-700' },
  ready: { label: 'Hazır', className: 'bg-green-100 text-green-700' },
  error: { label: 'Hata', className: 'bg-red-100 text-red-700' },
}

export function SourcesPanel({ notebookId, conversationId }: SourcesPanelProps) {
  const getNotebookDocuments = useAppStore((state) => state.getNotebookDocuments)
  const documents = useAppStore((state) => {
    const notebook = state.notebooks.find((n) => n.id === notebookId)
    return notebook?.documents ?? EMPTY_DOCUMENTS
  })
  void getNotebookDocuments // available if preferred over direct selector

  const selectedDocumentIds = useAppStore((state) => {
    const notebook = state.notebooks.find((n) => n.id === notebookId)
    const conversation = notebook?.conversations.find((c) => c.id === conversationId)
    return conversation?.selectedDocumentIds ?? EMPTY_SELECTED_IDS
  })

  const toggleDocumentSelection = useAppStore((state) => state.toggleDocumentSelection)
  const selectAllDocuments = useAppStore((state) => state.selectAllDocuments)
  const clearDocumentSelection = useAppStore((state) => state.clearDocumentSelection)
  const removeDocumentFromNotebook = useAppStore((state) => state.removeDocumentFromNotebook)

  const hasDocuments = documents.length > 0
  const hasConversation = Boolean(conversationId)

  const [isMSSQLConfigured, setIsMSSQLConfigured] = useState(false)
  const mssqlSourceId = `mssql:${notebookId}`

  useEffect(() => {
    let cancelled = false

    async function checkMSSQLConfig() {
      try {
        const config = await ragClient.getMSSQLConfig(notebookId)
        if (!cancelled) setIsMSSQLConfigured(Boolean(config?.is_configured))
      } catch {
        if (!cancelled) setIsMSSQLConfigured(false)
      }
    }

    if (notebookId) checkMSSQLConfig()
    return () => {
      cancelled = true
    }
  }, [notebookId])

  const hasSelectableSources = hasDocuments || isMSSQLConfigured
  const isDisabled = Boolean(!hasConversation || !hasSelectableSources)

  return (
    <div className="h-full flex flex-col">
      <div className="flex-shrink-0 flex items-center justify-between px-3 py-2 border-b border-gray-100">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500">Kaynaklar</h3>
        <div className="flex items-center gap-3">
          <button
    onClick={() => hasConversation && selectAllDocuments(notebookId, conversationId)}
    disabled={isDisabled}
    className="text-xs text-blue-600 hover:underline disabled:text-gray-300 disabled:no-underline"
  >
    Tümünü Seç
  </button>
  <button
    onClick={() => hasConversation && clearDocumentSelection(notebookId, conversationId)}
    disabled={isDisabled}
    className="text-xs text-blue-600 hover:underline disabled:text-gray-300 disabled:no-underline"
  >
    Seçimi Temizle
  </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {!hasDocuments && !isMSSQLConfigured ? (
          <div className="flex h-full items-center justify-center px-4 py-8 text-center text-sm text-gray-400">
            Henüz kaynak eklenmedi
          </div>
        ) : (
          <ul className="divide-y divide-gray-100">
            {isMSSQLConfigured && (
              <li className="flex items-center gap-2 bg-blue-50/40 px-3 py-2.5 hover:bg-blue-50">
                <input
                  type="checkbox"
                  checked={selectedDocumentIds.includes(mssqlSourceId)}
                  disabled={!hasConversation}
                  onChange={() =>
                    toggleDocumentSelection(notebookId, conversationId, mssqlSourceId)
                  }
                  className="h-4 w-4 flex-shrink-0 rounded border-gray-300 text-blue-600"
                />
                <Database className="h-3.5 w-3.5 flex-shrink-0 text-blue-600" />
                <span className="min-w-0 flex-1 truncate text-sm font-medium text-gray-800">
                  SQL Kaynağı
                </span>
                <span className="flex-shrink-0 rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-medium text-blue-700">
                  Bağlı
                </span>
              </li>
            )}
            {documents.map((doc) => {
              const isSelected = selectedDocumentIds.includes(doc.id)
              const statusStyle = STATUS_STYLES[doc.status]
              return (
                <li key={doc.id} className="flex items-center gap-2 px-3 py-2.5 hover:bg-gray-50">
                  <input
                    type="checkbox"
                    checked={isSelected}
                    disabled={!hasConversation}
                    onChange={() => toggleDocumentSelection(notebookId, conversationId, doc.id)}
                    className="h-4 w-4 flex-shrink-0 rounded border-gray-300 text-blue-600"
                  />
                  <span className="min-w-0 flex-1 truncate text-sm text-gray-800" title={doc.name}>
                    {doc.name}
                  </span>
                  <span
                    className={`flex-shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium ${statusStyle.className}`}
                  >
                    {statusStyle.label}
                  </span>
                  <button
                    onClick={() => {
  removeDocumentFromNotebook(notebookId, doc.id).catch((err) => {
    console.error('Kaynak silinemedi:', err)
    alert(err instanceof Error ? err.message : 'Kaynak silinemedi.')
  })
}}
                    aria-label={`${doc.name} kaynağını sil`}
                    className="flex-shrink-0 rounded p-1 text-gray-400 transition-colors hover:bg-red-50 hover:text-red-600"
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth={2}
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      className="h-3.5 w-3.5"
                    >
                      <line x1="18" y1="6" x2="6" y2="18" />
                      <line x1="6" y1="6" x2="18" y2="18" />
                    </svg>
                  </button>
                </li>
              )
            })}
          </ul>
        )}
      </div>

      <div className="flex-shrink-0 border-t border-gray-100 p-3">
        <PdfDropzone notebookId={notebookId} />
      </div>
    </div>
  )
}