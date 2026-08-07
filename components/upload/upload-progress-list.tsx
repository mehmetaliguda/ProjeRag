'use client'

import { CheckCircle2, Loader2, XCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

export type UploadItemStatus = 'uploading' | 'success' | 'error'

export interface UploadProgressItem {
  id: string
  fileName: string
  status: UploadItemStatus
  errorMessage?: string
}

interface UploadProgressListProps {
  items: UploadProgressItem[]
}

/**
 * Küçük bir dosya başına durum satırı listesi.
 * uploading -> spinner, success -> check, error -> X + hata mesajı.
 */
export function UploadProgressList({ items }: UploadProgressListProps) {
  if (items.length === 0) return null

  return (
    <ul className="mt-3 space-y-1.5">
      {items.map((item) => (
        <li
          key={item.id}
          className={cn(
            'flex items-start gap-2 rounded-md border px-2.5 py-1.5 text-xs',
            item.status === 'error'
              ? 'border-destructive/30 bg-destructive/5 text-destructive'
              : 'border-border bg-muted/40 text-muted-foreground'
          )}
        >
          <span className="mt-0.5 shrink-0">
            {item.status === 'uploading' && (
              <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
            )}
            {item.status === 'success' && (
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
            )}
            {item.status === 'error' && (
              <XCircle className="h-3.5 w-3.5 text-destructive" />
            )}
          </span>
          <span className="min-w-0 flex-1">
            <span className="block truncate font-medium text-foreground">
              {item.fileName}
            </span>
            {item.status === 'error' && item.errorMessage && (
              <span className="block text-[11px] leading-tight text-destructive/90">
                {item.errorMessage}
              </span>
            )}
          </span>
        </li>
      ))}
    </ul>
  )
}
