'use client'

import { Document } from '@/lib/store'
import { FileText, Loader2, AlertCircle, Trash2, Check } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface DocumentsMultiSelectProps {
  documents: Document[]
  selectedIds: string[]
  onToggleSelect: (docId: string) => void
  onSelectAll: () => void
  onClearAll: () => void
  onRemove?: (docId: string) => void
}

export function DocumentsMultiSelect({
  documents,
  selectedIds,
  onToggleSelect,
  onSelectAll,
  onClearAll,
  onRemove,
}: DocumentsMultiSelectProps) {
  if (documents.length === 0) {
    return (
      <div className="text-center py-8 px-4">
        <FileText className="mx-auto mb-2 text-muted-foreground" size={32} />
        <p className="text-sm text-muted-foreground">No documents uploaded yet</p>
      </div>
    )
  }

  const readyDocuments = documents.filter((d) => d.status === 'ready')
  const uploadingDocuments = documents.filter((d) => d.status !== 'ready')
  const selectedCount = selectedIds.length
  const readyCount = readyDocuments.length

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
    <div className="space-y-3">
      {/* Multi-select controls */}
      {readyDocuments.length > 0 && (
        <div className="flex items-center justify-between bg-muted/50 p-3 rounded-lg border border-border">
          <div className="text-sm">
            <span className="font-medium">
              {selectedCount} of {readyCount} selected
            </span>
          </div>
          <div className="flex gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={onSelectAll}
              disabled={selectedCount === readyCount}
              className="text-xs"
            >
              Select All
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClearAll}
              disabled={selectedCount === 0}
              className="text-xs"
            >
              Clear
            </Button>
          </div>
        </div>
      )}

      {/* Ready documents */}
      {readyDocuments.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-semibold text-muted-foreground uppercase">
            Knowledge Sources ({readyCount})
          </h4>
          {readyDocuments.map((doc) => {
            const isSelected = selectedIds.includes(doc.id)
            return (
              <button
                key={doc.id}
                onClick={() => onToggleSelect(doc.id)}
                className={`w-full flex items-center gap-3 p-3 rounded-lg transition-colors border-2 ${
                  isSelected
                    ? 'bg-primary/10 border-primary'
                    : 'bg-muted/50 hover:bg-muted border-transparent hover:border-border'
                }`}
              >
                {/* Selection checkbox */}
                <div
                  className={`flex-shrink-0 w-5 h-5 rounded border-2 flex items-center justify-center transition-colors ${
                    isSelected
                      ? 'bg-primary border-primary'
                      : 'border-border'
                  }`}
                >
                  {isSelected && <Check size={14} className="text-background" />}
                </div>

                {/* Status icon */}
                <div className={`flex-shrink-0 ${getStatusColor(doc.status)}`}>
                  {getStatusIcon(doc.status)}
                </div>

                {/* Document info */}
                <div className="flex-1 min-w-0 text-left">
                  <p className="text-sm font-medium truncate">{doc.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {(doc.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>

                {/* Delete button */}
                {onRemove && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation()
                      onRemove(doc.id)
                    }}
                    aria-label="Remove document"
                    className="flex-shrink-0"
                  >
                    <Trash2 size={16} />
                  </Button>
                )}
              </button>
            )
          })}
        </div>
      )}

      {/* Uploading documents */}
      {uploadingDocuments.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-semibold text-muted-foreground uppercase">
            Uploading ({uploadingDocuments.length})
          </h4>
          {uploadingDocuments.map((doc) => (
            <div
              key={doc.id}
              className="flex items-center gap-3 p-3 rounded-lg bg-muted/50 opacity-60"
            >
              <div className={`flex-shrink-0 ${getStatusColor(doc.status)}`}>
                {getStatusIcon(doc.status)}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{doc.name}</p>
                <p className="text-xs text-muted-foreground capitalize">
                  {doc.status}...
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
