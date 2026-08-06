'use client'

import { useState, useRef } from 'react'
import { Button } from '@/components/ui/button'
import { Send, Paperclip, Loader2 } from 'lucide-react'

interface ChatInputProps {
  onSendMessage: (message: string) => Promise<void>
  onUploadFile?: (file: File) => Promise<void>
  disabled?: boolean
  isLoading?: boolean
}

export function ChatInput({
  onSendMessage,
  onUploadFile,
  disabled = false,
  isLoading = false,
}: ChatInputProps) {
  const [message, setMessage] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleSend = async () => {
    if (!message.trim() || isSending || isLoading) return

    setIsSending(true)
    try {
      await onSendMessage(message)
      setMessage('')
    } catch (error) {
      console.error('[v0] Error sending message:', error)
    } finally {
      setIsSending(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Don't submit while composing (IME input)
    if (e.nativeEvent.isComposing) return
    // Also check for Safari Desktop composition event
    if (e.keyCode === 229) return

    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !onUploadFile) return

    setIsUploading(true)
    try {
      await onUploadFile(file)
    } catch (error) {
      console.error('[v0] Error uploading file:', error)
    } finally {
      setIsUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex gap-2">
        {onUploadFile && (
          <>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.txt,.doc,.docx"
              onChange={handleFileSelect}
              disabled={isUploading || disabled}
              className="hidden"
              aria-label="Upload file"
            />
            <Button
              variant="outline"
              size="icon"
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading || disabled || isSending}
              aria-label="Attach file"
            >
              {isUploading ? (
                <Loader2 size={20} className="animate-spin" />
              ) : (
                <Paperclip size={20} />
              )}
            </Button>
          </>
        )}
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question about your documents..."
          disabled={disabled || isLoading}
          className="flex-1 px-3 py-2 bg-muted text-foreground rounded-lg border border-border focus:outline-none focus:ring-2 focus:ring-primary resize-none"
          rows={3}
        />
        <Button
          onClick={handleSend}
          disabled={!message.trim() || isSending || isLoading || disabled}
          size="icon"
          aria-label="Send message"
        >
          {isSending ? (
            <Loader2 size={20} className="animate-spin" />
          ) : (
            <Send size={20} />
          )}
        </Button>
      </div>
      <p className="text-xs text-muted-foreground px-1">
        Shift + Enter for new line
      </p>
    </div>
  )
}
