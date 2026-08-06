'use client'

import { useState } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Database, Check } from 'lucide-react'

export function MSSQLConfigPanel() {
  const [activeTab, setActiveTab] = useState('overview')
  const [server, setServer] = useState('')
  const [port, setPort] = useState('1433')
  const [database, setDatabase] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [connectionString, setConnectionString] = useState('')
  const [isConnecting, setIsConnecting] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState<'idle' | 'success' | 'error'>('idle')

  const handleTestConnection = async () => {
    setIsConnecting(true)
    setConnectionStatus('idle')
    
    // Simulated connection test
    await new Promise((resolve) => setTimeout(resolve, 1500))
    
    if (server && database && username) {
      setConnectionStatus('success')
    } else {
      setConnectionStatus('error')
    }
    setIsConnecting(false)
  }

  const generateConnectionString = () => {
    const str = `Server=${server};Port=${port};Database=${database};User Id=${username};Password=****;`
    setConnectionString(str)
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
                Connect a Microsoft SQL Server database to your notebooks. The RAG system will
                continuously retrieve live data from your database to answer questions alongside
                your uploaded documents.
              </p>
              <div className="mt-4 space-y-2 text-sm text-muted-foreground">
                <p>
                  ✓ Query live database tables and views
                </p>
                <p>
                  ✓ Combine database queries with document search
                </p>
                <p>
                  ✓ Support for complex SQL queries and joins
                </p>
                <p>
                  ✓ Real-time data retrieval for accurate answers
                </p>
              </div>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="config" className="p-6 space-y-6">
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
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
            </div>

            {/* Connection String Display */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="connection-string">Connection String</Label>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={generateConnectionString}
                  className="text-xs"
                >
                  Generate
                </Button>
              </div>
              <Input
                id="connection-string"
                placeholder="Auto-generated or paste existing connection string"
                value={connectionString}
                onChange={(e) => setConnectionString(e.target.value)}
                className="font-mono text-xs"
              />
            </div>

            {/* Test Connection */}
            <div className="flex items-center gap-3 pt-4">
              <Button
                onClick={handleTestConnection}
                disabled={isConnecting}
                variant="default"
              >
                {isConnecting ? 'Testing...' : 'Test Connection'}
              </Button>

              {connectionStatus === 'success' && (
                <div className="flex items-center gap-2 text-sm text-green-600">
                  <Check className="h-4 w-4" />
                  Connection successful
                </div>
              )}

              {connectionStatus === 'error' && (
                <div className="text-sm text-destructive">
                  Connection failed. Please check your credentials.
                </div>
              )}
            </div>

            <p className="text-xs text-muted-foreground">
              ℹ️ Connection testing is currently a UI placeholder. Backend integration coming soon.
            </p>
          </div>
        </TabsContent>
      </Tabs>
    </Card>
  )
}
