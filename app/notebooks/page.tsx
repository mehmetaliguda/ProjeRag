'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAppStore } from '@/lib/store'
import { NotebookCard } from '@/components/notebook-card'
import { NotebookDialog } from '@/components/notebook-dialog'
import { MSSQLConfigPanel } from '@/components/mssql-config-panel'
import { ThemeSwitcher } from '@/components/theme-switcher'
import { Button } from '@/components/ui/button'
import { Plus } from 'lucide-react'

export default function NotebooksPage() {
  const router = useRouter()
  const { notebooks, createNotebook } = useAppStore()
  const [showDialog, setShowDialog] = useState(false)
  const [showMSSQL, setShowMSSQL] = useState(false)

  const validNotebooks = notebooks.filter(
    (notebook): notebook is NonNullable<typeof notebook> => notebook != null
  )
  const [selectedNotebookId, setSelectedNotebookId] = useState<string>(
    () => validNotebooks[0]?.id ?? ''
  )

  // Eğer seçili notebook silinmişse veya henüz seçim yapılmamışsa,
  // listedeki ilk notebook'a düş.
  useEffect(() => {
    const stillExists = validNotebooks.some((n) => n.id === selectedNotebookId)
    if (!stillExists && validNotebooks.length > 0) {
      setSelectedNotebookId(validNotebooks[0].id)
    }
  }, [validNotebooks, selectedNotebookId])

  const selectedNotebook = validNotebooks.find((n) => n.id === selectedNotebookId)

  const handleCreateNotebook = (name: string) => {
    createNotebook(name)
    setShowDialog(false)
  }

  const handleOpenNotebook = (notebookId: string) => {
    router.push(`/chat/${notebookId}`)
  }

  return (
    <div className="min-h-screen bg-background text-foreground page-enter">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="flex items-center justify-between px-6 pt-4 pb-0">
          <div>
            <h1 className="text-3xl font-bold">My Notebooks</h1>
            <p className="mt-1 text-sm text-muted-foreground">Organize and manage your knowledge</p>
          </div>
          <div className="flex items-center gap-3">
            <ThemeSwitcher />
            <Button onClick={() => setShowDialog(true)} className="gap-2">
              <Plus className="h-4 w-4" />
              New Notebook
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-8">
        {/* Notebooks Grid */}
        <section className="mb-12">
          <div className="space-y-2 mb-6">
            <h2 className="text-xl font-semibold">Notebooks</h2>
            <p className="text-sm text-muted-foreground">
              {notebooks.filter(Boolean).length} notebook{notebooks.filter(Boolean).length !== 1 ? 's' : ''}
            </p>
          </div>

          {notebooks.length === 0 ? (
            <div className="rounded-lg border-2 border-dashed border-border bg-card p-12 text-center">
              <div className="space-y-2">
                <p className="text-lg font-medium text-foreground">No notebooks yet</p>
                <p className="text-sm text-muted-foreground">Create your first notebook to get started</p>
                <Button onClick={() => setShowDialog(true)} variant="outline" className="mt-4">
                  <Plus className="h-4 w-4 mr-2" />
                  Create Notebook
                </Button>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              {notebooks
                .filter((notebook): notebook is NonNullable<typeof notebook> => notebook != null)
                .map((notebook) => (
                  <NotebookCard
                    key={notebook.id}
                    notebook={notebook}
                    onOpen={() => handleOpenNotebook(notebook.id)}
                  />
                ))}
            </div>
          )}
        </section>

        {/* MSSQL Configuration Section */}
        <section>
          <div className="space-y-4">
            <div className="space-y-2">
              <h2 className="text-xl font-semibold">Data Sources</h2>
              <p className="text-sm text-muted-foreground">
                Configure additional knowledge sources for your notebooks
              </p>
            </div>

            {validNotebooks.length === 0 ? (
              <div className="rounded-lg border-2 border-dashed border-border bg-card p-8 text-center">
                <p className="text-sm text-muted-foreground">
                  Data source configuration requires a notebook. Create a notebook first.
                </p>
              </div>
            ) : (
              <>
                <div className="max-w-xs space-y-2">
                  <label htmlFor="mssql-notebook-select" className="text-sm font-medium">
                    Notebook
                  </label>
                  <select
                    id="mssql-notebook-select"
                    value={selectedNotebookId}
                    onChange={(e) => setSelectedNotebookId(e.target.value)}
                    className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                  >
                    {validNotebooks.map((notebook) => (
                      <option key={notebook.id} value={notebook.id}>
                        {notebook.name}
                      </option>
                    ))}
                  </select>
                </div>

                {selectedNotebook && (
                  <MSSQLConfigPanel notebookId={Number(selectedNotebook.id)} />
                )}
              </>
            )}
          </div>
        </section>
      </main>

      {/* Create Notebook Dialog */}
      <NotebookDialog
        open={showDialog}
        onOpenChange={setShowDialog}
        onCreate={handleCreateNotebook}
      />
    </div>
  )
}