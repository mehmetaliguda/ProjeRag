'use client'

import { useAppStore } from '@/lib/store'
import { Button } from '@/components/ui/button'
import {
  Plus,
  Menu,
  X,
  Trash2,
  MessageCircle,
  ChevronRight,
} from 'lucide-react'

interface SidebarProps {
  notebookId: string
}

export function Sidebar({ notebookId }: SidebarProps) {
  const {
    notebooks,
    currentConversationId,
    sidebarOpen,
    setSidebarOpen,
    createConversation,
    deleteConversation,
    setCurrentConversation,
  } = useAppStore()

  const notebook = notebooks.find((nb) => nb.id === notebookId)
  const conversations = notebook?.conversations || []

  const handleNewConversation = () => {
    const title = `Chat ${conversations.length + 1}`
    createConversation(notebookId, title)
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
        className={`fixed md:relative h-screen w-64 bg-card border-r border-border flex flex-col transition-all duration-300 z-40 md:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Header */}
        <div className="p-4 border-b border-border">
          <Button
            onClick={handleNewConversation}
            className="w-full gap-2"
            size="sm"
          >
            <Plus size={16} />
            New Chat
          </Button>
        </div>

        {/* Conversations List */}
        <div className="flex-1 overflow-y-auto p-2">
          {conversations.length === 0 ? (
            <div className="text-center py-8 px-2 text-muted-foreground text-sm">
              <MessageCircle size={32} className="mx-auto mb-2 opacity-50" />
              <p>No conversations yet</p>
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
                      {conv.messages.length} messages
                    </p>
                  </button>
                  <button
                    onClick={() => deleteConversation(notebookId, conv.id)}
                    className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-destructive/10 rounded"
                    aria-label="Delete conversation"
                  >
                    <Trash2 size={14} className="text-destructive" />
                  </button>
                </div>
              ))}
            </div>
          )}
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
            Close
            <ChevronRight size={16} />
          </Button>
        </div>
      </aside>
    </>
  )
}
