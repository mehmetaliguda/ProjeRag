'use client'

import { useEffect } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { useAppStore } from '@/lib/store'
import { ChatPanel } from '@/components/chat-panel'
import { Sidebar } from '@/components/sidebar'
import { Button } from '@/components/ui/button'
import { ArrowLeft } from 'lucide-react'

export default function ChatPage() {
  const router = useRouter()
  const params = useParams()
  const notebookId = params.notebookId as string
  const { setCurrentNotebook, notebooks, currentNotebookId } = useAppStore()

  useEffect(() => {
    if (notebookId && notebookId !== currentNotebookId) {
      setCurrentNotebook(notebookId)
    }
  }, [notebookId, currentNotebookId, setCurrentNotebook])

  const handleGoBack = () => {
    router.push('/notebooks')
  }

  const currentNotebook = notebooks.find((nb) => nb.id === notebookId)

  return (
    <div className="flex h-screen w-full bg-background text-foreground overflow-hidden page-enter">
      <Sidebar notebookId={notebookId} />
      
      <div className="flex-1 flex flex-col">
        {/* Back Navigation Header */}
        <div className="border-b border-border bg-background/50 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleGoBack}
              className="gap-2"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to Notebooks
            </Button>
            {currentNotebook && (
              <span className="text-sm text-muted-foreground">
                • {currentNotebook.name}
              </span>
            )}
          </div>
        </div>

        {/* Chat Area */}
        <ChatPanel notebookId={notebookId} />
      </div>
    </div>
  )
}
