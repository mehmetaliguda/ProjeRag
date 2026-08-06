'use client'

import { Document } from '@/lib/store'
import { FileText, Loader2, AlertCircle, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface DocumentsListProps {
  documents: Document[]
  onRemove?: (docId: string) => void
}

export function DocumentsList({ documents, onRemove }: DocumentsListProps) {
  if (documents.length === 0) {
    return (
      <div className="text-center py-8 px-4">
        <FileText className="mx-auto mb-2 text-muted-foreground" size={32} />
        <p className="text-sm text-muted-foreground">No documents uploaded yet</p>
      </div>
    )
  }

  const getStatusColor = (status: Document['status']) => {
    switch (status) {
      case 'ready':
        return 'text-green-500'
      case 'processing':
        return 'text-blue-500'
      case 'error':
        return 'text-red-500'
      default:
        return 'text-yellow-500'
    }
  }

  const getStatusIcon = (status: Document['status']) => {
    switch (status) {
      case 'processing':
      case 'uploading':
        return <Loader2 size={16} className="animate-spin" />
      case 'error':
        return <AlertCircle size={16} />
      default:
        return <FileText size={16} />
    }
  }

  return (
    <div className="space-y-2">
      {documents.map((doc) => (
        <div
          key={doc.id}
          className="flex items-center gap-3 p-3 rounded-lg bg-muted/50 hover:bg-muted transition-colors"
        >
          <div className={`flex-shrink-0 ${getStatusColor(doc.status)}`}>
            {getStatusIcon(doc.status)}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{doc.name}</p>
            <p className="text-xs text-muted-foreground">
              {(doc.size / 1024 / 1024).toFixed(2)} MB
              {doc.status !== 'ready' && ` • ${doc.status}`}
            </p>
          </div>
          {onRemove && doc.status === 'ready' && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onRemove(doc.id)}
              aria-label="Remove document"
              className="flex-shrink-0"
            >
              <Trash2 size={16} />
            </Button>
          )}
        </div>
      ))}
    </div>
  )
}
