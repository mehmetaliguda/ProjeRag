'use client'

import { useState } from 'react'
import { useAppStore } from '@/lib/store'
import type { Notebook } from '@/lib/store'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Trash2, BookOpen, MoreVertical } from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

interface NotebookCardProps {
  notebook: Notebook
  onOpen: () => void
}

export function NotebookCard({ notebook, onOpen }: NotebookCardProps) {
  const { deleteNotebook } = useAppStore()
  const [isDeleting, setIsDeleting] = useState(false)

  const handleDelete = () => {
    if (confirm(`Delete notebook "${notebook.name}"?`)) {
      setIsDeleting(true)
      deleteNotebook(notebook.id)
    }
  }

  return (
    <Card className="group relative overflow-hidden transition-all duration-200 hover:shadow-md">
      <div
        className="absolute inset-0 bg-gradient-to-br from-primary/10 to-transparent opacity-0 transition-opacity duration-200 group-hover:opacity-100"
        aria-hidden="true"
      />
      
      <div className="relative p-6">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-semibold text-foreground truncate group-hover:text-primary transition-colors">
              {notebook.name}
            </h3>
            <p className="mt-1 text-sm text-muted-foreground">
              {notebook.documentCount} document{notebook.documentCount !== 1 ? 's' : ''}
            </p>
          </div>
          
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0 opacity-0 transition-opacity group-hover:opacity-100"
              >
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={handleDelete} disabled={isDeleting}>
                <Trash2 className="h-4 w-4 mr-2 text-destructive" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        {/* Content */}
        <div className="mb-4 min-h-12">
          <p className="text-xs text-muted-foreground">
            Last updated: {notebook.updatedAt.toLocaleDateString()}
          </p>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between">
          <div className="text-xs text-muted-foreground">
            Created {notebook.createdAt.toLocaleDateString()}
          </div>
          <Button
            onClick={onOpen}
            size="sm"
            className="gap-2 opacity-0 transition-opacity group-hover:opacity-100"
          >
            <BookOpen className="h-4 w-4" />
            Open
          </Button>
        </div>

        {/* MSSQL Badge */}
        {notebook.mssqlConfig?.isConfigured && (
          <div className="absolute top-3 right-3 h-2 w-2 rounded-full bg-green-500" title="MSSQL configured" />
        )}
      </div>
    </Card>
  )
}
