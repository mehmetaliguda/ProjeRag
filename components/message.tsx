'use client'

import { Message } from '@/lib/store'
import { Copy, Check } from 'lucide-react'
import { useState } from 'react'

interface MessageProps {
  message: Message
}

export function MessageComponent({ message }: MessageProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const isUser = message.role === 'user'

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
