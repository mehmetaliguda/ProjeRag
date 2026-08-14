'use client'

import { Message } from '@/lib/store'
import type { CitationInfo } from '@/lib/api-client'
import { Copy, Check, BookOpen } from 'lucide-react'
import { useState } from 'react'

interface MessageProps {
  message: Message
}

export function MessageComponent({ message }: MessageProps) {
  const [copied, setCopied] = useState(false)
  const [showCitations, setShowCitations] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const isUser = message.role === 'user'
  const hasCitations = message.citations && Object.keys(message.citations).length > 0

  return (
    <div className={`flex gap-3 mb-4 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          isUser
            ? 'bg-primary text-primary-foreground'
            : 'bg-muted text-muted-foreground'
        }`}
      >
        {isUser ? 'U' : 'A'}
      </div>
      <div className="flex-1 max-w-2xl">
        <div
          className={`rounded-lg px-4 py-2 ${
            isUser
              ? 'bg-primary text-primary-foreground ml-auto'
              : 'bg-muted text-muted-foreground'
          }`}
        >
          <p className="text-sm whitespace-pre-wrap break-words">{message.content}</p>
        </div>

        {/* Citations - SADECE asistan mesajlarında ve citation varsa */}
        {!isUser && hasCitations && (
          <div className="mt-1">
            <button
              onClick={() => setShowCitations(!showCitations)}
              className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 transition-colors"
            >
              <BookOpen size={14} />
              <span>
                {showCitations
                  ? 'Kaynakları gizle'
                  : `${Object.keys(message.citations ?? {}).length} kaynak göster`
                }
              </span>
            </button>
            {showCitations && (
              <div className="mt-2 p-2 bg-gray-50 dark:bg-gray-800 rounded-md text-xs space-y-1 border border-gray-200 dark:border-gray-700 max-h-60 overflow-y-auto">
                {Object.entries(message.citations ?? {}).map(([key, citation]: [string, CitationInfo]) => (
                  <div
                    key={key}
                    className="border-b border-gray-200 dark:border-gray-700 last:border-0 py-1.5"
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-blue-600">[{key}]</span>
                      {citation.page !== null && citation.page !== undefined && citation.page >= 0 && (
                        <span className="text-gray-500">Sayfa {citation.page + 1}</span>
                      )}
                      {citation.room_id && (
                        <span className="text-gray-400 text-[10px]">(Kaynak: {citation.room_id})</span>
                      )}
                      {citation.timestamp && (
                        <span className="ml-auto opacity-70 text-[10px]">
                          {new Date(citation.timestamp).toLocaleTimeString()}
                        </span>
                      )}
                    </div>
                    {citation.text && (
                      <p className="text-gray-600 dark:text-gray-400 mt-0.5 text-[11px] line-clamp-3">
                        {citation.text}
                      </p>
                    )}
                    {citation.pdf_url && (
                      <a
                        href={citation.pdf_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline block mt-0.5 text-[11px]"
                      >
                        PDF'de görüntüle →
                      </a>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        <div
          className={`flex items-center gap-2 mt-1 text-xs text-muted-foreground ${
            isUser ? 'justify-end' : 'justify-start'
          }`}
        >
          <time>{new Date(message.timestamp).toLocaleTimeString()}</time>
          {!isUser && (
            <button
              onClick={handleCopy}
              className="hover:text-foreground transition-colors"
              aria-label="Copy message"
            >
              {copied ? <Check size={14} /> : <Copy size={14} />}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}