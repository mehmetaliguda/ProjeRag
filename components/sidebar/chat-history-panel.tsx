'use client'

import { useAppStore } from '@/lib/store'

interface ChatHistoryPanelProps {
  notebookId: string
}

function formatTimestamp(date: Date): string {
  try {
    return new Intl.DateTimeFormat('tr-TR', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(date))
  } catch {
    return ''
  }
}

export function ChatHistoryPanel({ notebookId }: ChatHistoryPanelProps) {
  const notebook = useAppStore((state) => state.notebooks.find((n) => n.id === notebookId))
  const currentConversationId = useAppStore((state) => state.currentConversationId)
  const createConversation = useAppStore((state) => state.createConversation)
  const setCurrentConversation = useAppStore((state) => state.setCurrentConversation)

  const conversations = notebook?.conversations ?? []
  const sortedConversations = [...conversations].sort(
    (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
  )

  const handleNewConversation = () => {
    createConversation(notebookId, 'Yeni Sohbet')
  }

  return (
    <div className="h-full flex flex-col border-b border-gray-100">
      <div className="flex-shrink-0 p-3 border-b border-gray-100">
        <button
          onClick={handleNewConversation}
          className="w-full flex items-center justify-center gap-1.5 rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
        >
          <span className="text-base leading-none">+</span>
          Yeni Sohbet
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {sortedConversations.length === 0 ? (
          <div className="flex h-full items-center justify-center px-4 py-8 text-center text-sm text-gray-400">
            Henüz sohbet yok
          </div>
        ) : (
          <ul className="divide-y divide-gray-100">
            {sortedConversations.map((conversation) => {
              const isActive = conversation.id === currentConversationId
              return (
                <li key={conversation.id}>
                  <button
                    onClick={() => setCurrentConversation(notebookId, conversation.id)}
                    className={`w-full text-left px-3 py-2.5 transition-colors ${
                      isActive ? 'bg-blue-50 border-l-2 border-blue-600' : 'hover:bg-gray-50 border-l-2 border-transparent'
                    }`}
                  >
                    <div
                      className={`truncate text-sm ${
                        isActive ? 'font-medium text-blue-700' : 'text-gray-800'
                      }`}
                    >
                      {conversation.title || 'Yeni Sohbet'}
                    </div>
                    <div className="mt-0.5 text-xs text-gray-400">
                      {formatTimestamp(conversation.updatedAt)}
                    </div>
                  </button>
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </div>
  )
}