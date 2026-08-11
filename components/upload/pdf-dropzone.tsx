'use client'

import { useCallback, useRef, useState } from 'react'
import { UploadCloud } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAppStore } from '@/lib/store'
import { ragClient } from '@/lib/api-client'
import type { Document } from '@/lib/store'
import {
  UploadProgressList,
  type UploadProgressItem,
} from '@/components/upload/upload-progress-list'

interface PdfDropzoneProps {
  notebookId: string
}

function isPdfFile(file: File): boolean {
  return (
    file.type === 'application/pdf' ||
    file.name.toLowerCase().endsWith('.pdf')
  )
}

function makeTempId() {
  return `temp-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
}

export function PdfDropzone({ notebookId }: PdfDropzoneProps) {
  const addDocumentsToNotebook = useAppStore((s) => s.addDocumentsToNotebook)
  const removeDocumentFromNotebook = useAppStore(
    (s) => s.removeDocumentFromNotebook
  )
  const updateDocumentStatus = useAppStore((s) => s.updateDocumentStatus)

  const [isDragging, setIsDragging] = useState(false)
  const [rejectedWarning, setRejectedWarning] = useState<string | null>(null)
  const [progressItems, setProgressItems] = useState<UploadProgressItem[]>([])
  const dragCounter = useRef(0)
  const inputRef = useRef<HTMLInputElement>(null)

  const clearWarningSoon = useCallback(() => {
    window.setTimeout(() => setRejectedWarning(null), 4000)
  }, [])

  const handleFiles = useCallback(
    async (fileList: FileList | null) => {
      if (!fileList || fileList.length === 0) return

      const allFiles = Array.from(fileList)
      const pdfFiles = allFiles.filter(isPdfFile)
      const rejected = allFiles.filter((f) => !isPdfFile(f))

      if (rejected.length > 0) {
        setRejectedWarning(
          `Sadece PDF dosyaları desteklenir. Yoksayıldı: ${rejected
            .map((f) => f.name)
            .join(', ')}`
        )
        clearWarningSoon()
      }

      if (pdfFiles.length === 0) return

      // 1. Placeholder Document'lar oluştur, hemen listeye ekle.
      const placeholders: Document[] = pdfFiles.map((file) => ({
        id: makeTempId(),
        name: file.name,
        status: 'uploading',
      })) as Document[]

      addDocumentsToNotebook(notebookId, placeholders)

      setProgressItems((prev) => [
        ...prev,
        ...placeholders.map((p) => ({
          id: p.id,
          fileName: p.name,
          status: 'uploading' as const,
        })),
      ])

      // 2. Backend'e paralel yükle.
      const { succeeded, failed } = await ragClient.createRooms(pdfFiles, notebookId)

      // 3. Başarılı olanları gerçek room bilgisiyle değiştir.
      succeeded.forEach((room, index) => {
        if (!room) return   // <-- yeni: room undefined ise sessizce atla, tüm döngüyü kesme

        // succeeded sırası pdfFiles ile birebir eşleşmeyebileceğinden
        // eşleşmeyi dosya adına göre en iyi çaba ile yapıyoruz.
        const roomName = (room as any).name
        const matchIndex = placeholders.findIndex(
          (p) => p.name === roomName
        )
        const placeholder =
          matchIndex !== -1 ? placeholders[matchIndex] : placeholders[index]
        if (!placeholder) return

        // matchIndex placeholders ile ayni sirada olan pdfFiles'a da karsilik gelir,
        // bu yuzden gercek dosya boyutunu oradan alabiliyoruz.
        const matchedFile = matchIndex !== -1 ? pdfFiles[matchIndex] : pdfFiles[index]

        removeDocumentFromNotebook(notebookId, placeholder.id)
        addDocumentsToNotebook(notebookId, [
          {
            id: (room as any).id,
            name: (room as any).name,
            size: matchedFile?.size ?? 0,
            uploadedAt: (room as any).created_at
              ? new Date((room as any).created_at)
              : new Date(),
            status: 'ready',
          },
        ])

        setProgressItems((prev) =>
          prev.map((item) =>
            item.id === placeholder.id
              ? { ...item, status: 'success' }
              : item
          )
        )
      })

      // 4. Başarısız olanları kaldır, hata göster.
      failed.forEach((failure: any, index: number) => {
        const placeholder =
          placeholders[
            placeholders.length - failed.length + index
          ] ?? placeholders.find((p) => p.name === failure?.fileName)

        if (placeholder) {
          removeDocumentFromNotebook(notebookId, placeholder.id)
          setProgressItems((prev) =>
            prev.map((item) =>
              item.id === placeholder.id
                ? {
                    ...item,
                    status: 'error',
                    errorMessage:
                      failure?.message ?? 'Yükleme başarısız oldu.',
                  }
                : item
            )
          )
        }
      })
    },
    [addDocumentsToNotebook, clearWarningSoon, notebookId, removeDocumentFromNotebook, updateDocumentStatus]
  )

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const onDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    dragCounter.current += 1
    setIsDragging(true)
  }, [])

  const onDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    dragCounter.current -= 1
    if (dragCounter.current <= 0) {
      dragCounter.current = 0
      setIsDragging(false)
    }
  }, [])

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      dragCounter.current = 0
      setIsDragging(false)
      handleFiles(e.dataTransfer.files)
    },
    [handleFiles]
  )

  const onInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      handleFiles(e.target.files)
      // aynı dosyayı tekrar seçebilmek için sıfırla
      e.target.value = ''
    },
    [handleFiles]
  )

  return (
    <div className="w-full">
      <div
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click()
        }}
        onDragOver={onDragOver}
        onDragEnter={onDragEnter}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        className={cn(
          'flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-4 py-6 text-center transition-colors',
          isDragging
            ? 'border-primary bg-primary/5'
            : 'border-muted-foreground/25 hover:border-muted-foreground/40 hover:bg-muted/30'
        )}
      >
        <UploadCloud
          className={cn(
            'h-6 w-6',
            isDragging ? 'text-primary' : 'text-muted-foreground'
          )}
        />
        <p className="text-sm text-muted-foreground">
          <span className="font-medium text-foreground">
            PDF&apos;leri buraya sürükleyin
          </span>{' '}
          veya seçin
        </p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept="application/pdf"
          onChange={onInputChange}
          className="hidden"
        />
      </div>

      {rejectedWarning && (
        <p className="mt-2 text-xs text-destructive">{rejectedWarning}</p>
      )}

      <UploadProgressList items={progressItems} />
    </div>
  )
}