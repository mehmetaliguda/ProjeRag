'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { useAppStore } from '@/lib/store'
import { ChatHistoryPanel } from './chat-history-panel'
import { SourcesPanel } from './sources-panel'

interface ResizableSidebarProps {
  notebookId: string
}

const MIN_TOP_PERCENT = 20
const MAX_TOP_PERCENT = 80
const DEFAULT_TOP_PERCENT = 50
const STORAGE_KEY = 'sidebar-top-height-percent'

export function ResizableSidebar({ notebookId }: ResizableSidebarProps) {
  const [topHeightPercent, setTopHeightPercent] = useState<number>(DEFAULT_TOP_PERCENT)
  const [isDragging, setIsDragging] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  // Optional persistence — not required, but nice to have.
  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(STORAGE_KEY)
      if (stored) {
        const parsed = parseFloat(stored)
        if (!Number.isNaN(parsed) && parsed >= MIN_TOP_PERCENT && parsed <= MAX_TOP_PERCENT) {
          setTopHeightPercent(parsed)
        }
      }
    } catch {
      // localStorage may be unavailable — ignore silently.
    }
  }, [])

  const currentConversationId = useAppStore((state) => state.currentConversationId)
  const notebooks = useAppStore((state) => state.notebooks)
  const notebook = notebooks.find((n) => n.id === notebookId)
  const resolvedConversationId = currentConversationId ?? notebook?.conversations[0]?.id ?? null

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  useEffect(() => {
    if (!isDragging) return

    const handleMouseMove = (e: MouseEvent) => {
      if (!containerRef.current) return
      const rect = containerRef.current.getBoundingClientRect()
      const relativeY = e.clientY - rect.top
      let percent = (relativeY / rect.height) * 100
      percent = Math.min(MAX_TOP_PERCENT, Math.max(MIN_TOP_PERCENT, percent))
      setTopHeightPercent(percent)
    }

    const handleMouseUp = () => {
      setIsDragging(false)
      try {
        window.localStorage.setItem(STORAGE_KEY, String(topHeightPercent))
      } catch {
        // ignore
      }
    }

    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('mouseup', handleMouseUp)
    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isDragging])

  return (
    <div ref={containerRef} className="h-full flex flex-col select-none">
      <div
        className="min-h-0 overflow-hidden"
        style={{ height: `${topHeightPercent}%` }}
      >
        <ChatHistoryPanel notebookId={notebookId} />
      </div>

      <div
        role="separator"
        aria-orientation="horizontal"
        onMouseDown={handleMouseDown}
        className={`h-1 flex-shrink-0 cursor-row-resize transition-colors ${
          isDragging ? 'bg-blue-500' : 'bg-gray-200 hover:bg-blue-400'
        }`}
      />

      <div
        className="min-h-0 overflow-hidden flex-1"
        style={{ height: `${100 - topHeightPercent}%` }}
      >
        <SourcesPanel notebookId={notebookId} conversationId={resolvedConversationId ?? ''} />
      </div>
    </div>
  )
}