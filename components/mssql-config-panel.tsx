'use client'

import { useEffect, useState } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Database, Check, Loader2, Trash2 } from 'lucide-react'

// Flask backend'in calistigi adres. Ihtiyaca gore prop ile override edilebilir.
const DEFAULT_API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:5000'

interface MSSQLConfigPanelProps {
  notebookId: number
  apiBaseUrl?: string
}

interface MSSQLConfigResponse {
  is_configured: boolean
  server?: string
  port?: number
  database_name?: string
  username?: string
  table_name?: string
  timestamp_column?: string
  text_columns?: string[]
  updated_at?: string
}

export function MSSQLConfigPanel({ notebookId, apiBaseUrl = DEFAULT_API_BASE_URL }: MSSQLConfigPanelProps) {
  const [activeTab, setActiveTab] = useState('overview')

  // Baglanti bilgileri
  const [server, setServer] = useState('')
  const [port, setPort] = useState('1433')
  const [database, setDatabase] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')

  // Backend'in retrieval icin ihtiyac duydugu alanlar (oncesinde formda yoktu)
  const [tableName, setTableName] = useState('')
  const [timestampColumn, setTimestampColumn] = useState('')
  const [textColumnsInput, setTextColumnsInput] = useState('')

  const [isLoadingConfig, setIsLoadingConfig] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState<'idle' | 'success' | 'error'>('idle')
  const [errorMessage, setErrorMessage] = useState('')
  const [savedConfig, setSavedConfig] = useState<MSSQLConfigResponse | null>(null)

  // Sayfa acildiginda mevcut config'i getir (parola asla donmez, sadece
  // is_configured + diger alanlar gelir).
  useEffect(() => {
    let cancelled = false

    async function loadConfig() {
      setIsLoadingConfig(true)
      try {
        const res = await fetch(`${apiBaseUrl}/notebooks/${notebookId}/mssql-config`)
        const data: MSSQLConfigResponse = await res.json()
        if (cancelled) return

        if (data.is_configured) {
          setSavedConfig(data)
          setServer(data.server ?? '')
          setPort(String(data.port ?? '1433'))
          setDatabase(data.database_name ?? '')
          setUsername(data.username ?? '')
          setTableName(data.table_name ?? '')
          setTimestampColumn(data.timestamp_column ?? '')
          setTextColumnsInput((data.text_columns ?? []).join(', '))
        }
      } catch {
        // Config yuklenemedi (ag hatasi vb.) - formu bos birak, kullanici
        // sifirdan girebilir.
      } finally {
        if (!cancelled) setIsLoadingConfig(false)
      }
    }

    loadConfig()
    return () => {
      cancelled = true
    }
  }, [apiBaseUrl, notebookId])

  const handleSaveAndTest = async () => {
    setIsSaving(true)
    setConnectionStatus('idle')
    setErrorMessage('')

    const textColumns = textColumnsInput
      .split(',')
      .map((c) => c.trim())
      .filter(Boolean)

    const isUpdate = !!savedConfig
    const missingCore = !server || !database || !username || !tableName || !timestampColumn || textColumns.length === 0
    const missingPassword = !isUpdate && !password

    if (missingCore || missingPassword) {
      setConnectionStatus('error')
      setErrorMessage(
        isUpdate
          ? 'Server, Database, Username, Table, Timestamp Column ve en az bir Text Column zorunlu.'
          : 'Server, Database, Username, Password, Table, Timestamp Column ve en az bir Text Column zorunlu.'
      )
      setIsSaving(false)
      return
    }

    try {
      const res = await fetch(`${apiBaseUrl}/notebooks/${notebookId}/mssql-config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          server,
          port: Number(port) || 1433,
          database_name: database,
          username,
          // Guncellemede parola bos birakilirsa gonderilmez; backend
          // mevcut sifreli parolayi korur.
          ...(password ? { password } : {}),
          table_name: tableName,
          timestamp_column: timestampColumn,
          text_columns: textColumns,
        }),
      })
      const data = await res.json()

      if (!res.ok) {
        // Backend, DB'ye yazmadan once gercek bir baglanti testi yapiyor;
        // basarisizsa buraya 400 + aciklayici hata mesaji dusuyor.
        setConnectionStatus('error')
        setErrorMessage(data.error || 'Baglanti testi basarisiz oldu.')
        return
      }

      setConnectionStatus('success')
      setSavedConfig(data)
      setPassword('') // parola asla state'te tutulmaya devam etmesin
    } catch (e) {
      setConnectionStatus('error')
      setErrorMessage('Sunucuya ulasilamadi. API adresini kontrol edin.')
    } finally {
      setIsSaving(false)
    }
  }

  const handleDelete = async () => {
    setIsDeleting(true)
    setErrorMessage('')
    try {
      const res = await fetch(`${apiBaseUrl}/notebooks/${notebookId}/mssql-config`, {
        method: 'DELETE',
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        setErrorMessage(data.error || 'Silme islemi basarisiz oldu.')
        return
      }
      setSavedConfig(null)
      setConnectionStatus('idle')
      setServer('')
      setPort('1433')
      setDatabase('')
      setUsername('')
      setPassword('')
      setTableName('')
      setTimestampColumn('')
      setTextColumnsInput('')
    } catch {
      setErrorMessage('Sunucuya ulasilamadi. API adresini kontrol edin.')
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <Card className="overflow-hidden">
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="w-full justify-start rounded-none border-b border-border bg-transparent p-0">
          <TabsTrigger
            value="overview"
            className="rounded-none border-b-2 border-transparent px-6 py-3 data-[state=active]:border-primary"
          >
            Overview
          </TabsTrigger>
          <TabsTrigger
            value="config"
            className="rounded-none border-b-2 border-transparent px-6 py-3 data-[state=active]:border-primary"
          >
            Configuration
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="p-6 space-y-4">
          <div className="flex items-start gap-4">
            <Database className="h-12 w-12 text-primary flex-shrink-0 mt-1" />
            <div className="flex-1 space-y-2">
              <h3 className="font-semibold text-lg">SQL Server Integration</h3>
              <p className="text-sm text-muted-foreground">
                Connect a Microsoft SQL Server database to this notebook. The RAG system will
                query the most recent rows live at chat time to answer questions alongside your
                uploaded documents.
              </p>
              <div className="mt-4 space-y-2 text-sm text-muted-foreground">
                <p>✓ Query live database tables, newest rows first</p>
                <p>✓ Combine database results with document search</p>
                <p>✓ Context-budgeted for the configured LLM (no overflow)</p>
                <p>✓ Password stored encrypted, never returned by the API</p>
              </div>
              {savedConfig && (
                <div className="mt-4 flex items-center gap-2 text-sm text-green-600">
                  <Check className="h-4 w-4" />
                  Configured: {savedConfig.database_name} / {savedConfig.table_name}
                </div>
              )}
            </div>
          </div>
        </TabsContent>

        <TabsContent value="config" className="p-6 space-y-6">
          {isLoadingConfig ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading configuration...
            </div>
          ) : (
            <>
              <div className="space-y-4">
                <h4 className="font-medium">Database Credentials</h4>

                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="server">Server</Label>
                    <Input
                      id="server"
                      placeholder="localhost or server.domain.com"
                      value={server}
                      onChange={(e) => setServer(e.target.value)}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="port">Port</Label>
                    <Input
                      id="port"
                      type="number"
                      placeholder="1433"
                      value={port}
                      onChange={(e) => setPort(e.target.value)}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="database">Database Name</Label>
                    <Input
                      id="database"
                      placeholder="your_database_name"
                      value={database}
                      onChange={(e) => setDatabase(e.target.value)}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="username">Username</Label>
                    <Input
                      id="username"
                      placeholder="sa or your_username"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                    />
                  </div>

                  <div className="space-y-2 md:col-span-2">
                    <Label htmlFor="password">
                      Password {savedConfig && <span className="text-xs text-muted-foreground">(leave blank to keep current)</span>}
                    </Label>
                    <Input
                      id="password"
                      type="password"
                      placeholder={savedConfig ? '•••• (kayıtlı, değiştirmek için yeniden gir)' : '••••••••'}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                    />
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <h4 className="font-medium">Log Retrieval Settings</h4>
                <p className="text-xs text-muted-foreground">
                  These tell the RAG system where and how to read the newest log rows.
                </p>

                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="table-name">Table Name</Label>
                    <Input
                      id="table-name"
                      placeholder="e.g. app_logs"
                      value={tableName}
                      onChange={(e) => setTableName(e.target.value)}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="timestamp-column">Timestamp Column</Label>
                    <Input
                      id="timestamp-column"
                      placeholder="e.g. created_at"
                      value={timestampColumn}
                      onChange={(e) => setTimestampColumn(e.target.value)}
                    />
                  </div>

                  <div className="space-y-2 md:col-span-2">
                    <Label htmlFor="text-columns">Text Columns (comma-separated)</Label>
                    <Input
                      id="text-columns"
                      placeholder="e.g. message, level, source"
                      value={textColumnsInput}
                      onChange={(e) => setTextColumnsInput(e.target.value)}
                    />
                  </div>
                </div>

                <p className="text-xs text-muted-foreground">
                  Table, column, and timestamp names may only contain letters, numbers, and
                  underscores (validated by the backend before any query runs).
                </p>
              </div>

              {/* Save & Test */}
              <div className="flex items-center gap-3 pt-2">
                <Button onClick={handleSaveAndTest} disabled={isSaving} variant="default">
                  {isSaving ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                      Testing & saving...
                    </>
                  ) : (
                    'Save & Test Connection'
                  )}
                </Button>

                {savedConfig && (
                  <Button onClick={handleDelete} disabled={isDeleting} variant="outline" className="text-destructive">
                    {isDeleting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Trash2 className="h-4 w-4 mr-2" />}
                    Remove
                  </Button>
                )}

                {connectionStatus === 'success' && (
                  <div className="flex items-center gap-2 text-sm text-green-600">
                    <Check className="h-4 w-4" />
                    Connected and saved
                  </div>
                )}
              </div>

              {errorMessage && <div className="text-sm text-destructive">{errorMessage}</div>}

              <p className="text-xs text-muted-foreground">
                The connection is tested on the server before anything is saved. If the test
                fails, nothing is written to the database.
              </p>
            </>
          )}
        </TabsContent>
      </Tabs>
    </Card>
  )
}