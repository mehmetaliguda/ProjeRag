import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { ragClient } from '@/lib/api-client'

export type ThemeType = 'light' | 'dark' | 'dust-pink' | 'blue' | 'green' | 'purple'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

export interface Document {
  id: string
  name: string
  size: number
  uploadedAt: Date
  status: 'uploading' | 'processing' | 'ready' | 'error'
}

export interface MSSQLConfig {
  server: string
  port: number
  database: string
  username: string
  password: string
  connectionString?: string
  isConfigured: boolean
}

export interface Conversation {
  id: string
  title: string
  messages: Message[]
  documents: Document[]
  selectedDocumentIds: string[] // Track multiple selected documents
  createdAt: Date
  updatedAt: Date
}

export interface Notebook {
  id: string
  name: string
  documentCount: number
  conversations: Conversation[]
  mssqlConfig: MSSQLConfig | null
  createdAt: Date
  updatedAt: Date
}

interface AppStore {
  notebooks: Notebook[]
  currentNotebookId: string | null
  currentConversationId: string | null
  theme: ThemeType
  sidebarOpen: boolean
  backendUrl: string
  hasHydrated: boolean

  // Server sync
  useServerSync: boolean
  syncWarning: string | null

  // Notebook actions
  createNotebook: (name: string) => Promise<string>
  deleteNotebook: (id: string) => void
  renameNotebook: (id: string, name: string) => void
  setCurrentNotebook: (id: string) => void
  getCurrentNotebook: () => Notebook | null

  // Conversation actions (within notebooks)
  createConversation: (notebookId: string, title: string) => Promise<string>
  deleteConversation: (notebookId: string, conversationId: string) => void
  setCurrentConversation: (notebookId: string, conversationId: string) => void
  getCurrentConversation: () => Conversation | null

  // Message actions
  addMessage: (notebookId: string, conversationId: string, message: Message) => Promise<void>
  updateMessage: (notebookId: string, conversationId: string, messageId: string, content: string) => void

  // Document actions
  addDocument: (notebookId: string, conversationId: string, document: Document) => void
  updateDocumentStatus: (notebookId: string, conversationId: string, docId: string, status: Document['status']) => void
  removeDocument: (notebookId: string, conversationId: string, docId: string) => void

  // Document selection actions (multi-select)
  toggleDocumentSelection: (notebookId: string, conversationId: string, docId: string) => void
  selectAllDocuments: (notebookId: string, conversationId: string) => void
  clearDocumentSelection: (notebookId: string, conversationId: string) => void
  getSelectedDocuments: (notebookId: string, conversationId: string) => Document[]

  // MSSQL Config actions
  setMSSQLConfig: (notebookId: string, config: MSSQLConfig) => void
  getMSSQLConfig: (notebookId: string) => MSSQLConfig | null

  // Theme actions
  setTheme: (theme: ThemeType) => void
  setSidebarOpen: (open: boolean) => void
  setBackendUrl: (url: string) => void
  setHasHydrated: (state: boolean) => void

  // Server sync actions
  setUseServerSync: (value: boolean) => void
  loadFromServer: () => Promise<void>
  clearSyncWarning: () => void
}

// localStorage'daki her sey string olarak saklandigi icin, ISO formatindaki
// tarih string'lerini geri okurken otomatik olarak Date nesnesine ceviriyoruz.
const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$/

export const useAppStore = create<AppStore>()(
  persist(
    (set, get) => ({
      notebooks: [],
      currentNotebookId: null,
      currentConversationId: null,
      theme: 'dark',
      sidebarOpen: true,
      backendUrl: 'http://127.0.0.1:5000',
      hasHydrated: false,
      useServerSync: false,
      syncWarning: null,

      // Notebook actions
      createNotebook: async (name: string) => {
        const { useServerSync } = get()

        // Sunucu senkronu acikken id'yi backend uretir (POST /notebooks -> {id, name});
        // basarisiz olursa lokal state'e hic dokunmadan hata firlatilir.
        const id = useServerSync
          ? (await ragClient.createNotebook(name)).id
          : `nb-${Date.now()}`

        const newNotebook: Notebook = {
          id,
          name,
          documentCount: 0,
          conversations: [],
          mssqlConfig: null,
          createdAt: new Date(),
          updatedAt: new Date(),
        }
        set((state) => ({
          notebooks: [newNotebook, ...state.notebooks],
          currentNotebookId: id,
          currentConversationId: null,
        }))
        return id
      },

      deleteNotebook: (id: string) => {
        set((state) => ({
          notebooks: state.notebooks.filter((nb) => nb.id !== id),
          currentNotebookId:
            state.currentNotebookId === id
              ? state.notebooks.find((nb) => nb.id !== id)?.id || null
              : state.currentNotebookId,
          currentConversationId: state.currentNotebookId === id ? null : state.currentConversationId,
        }))
      },

      renameNotebook: (id: string, name: string) => {
        set((state) => ({
          notebooks: state.notebooks.map((nb) =>
            nb.id === id ? { ...nb, name, updatedAt: new Date() } : nb
          ),
        }))
      },

      setCurrentNotebook: (id: string) => {
        set({ currentNotebookId: id, currentConversationId: null })
      },

      getCurrentNotebook: () => {
        const state = get()
        return state.notebooks.find((nb) => nb.id === state.currentNotebookId) || null
      },

      // Conversation actions
      createConversation: async (notebookId: string, title: string) => {
        const { useServerSync } = get()

        // POST /notebooks/<nb_id>/conversations -> {id, title}
        const convId = useServerSync
          ? (await ragClient.createConversation(notebookId, title)).id
          : `conv-${Date.now()}`

        const newConversation: Conversation = {
          id: convId,
          title,
          messages: [],
          documents: [],
          selectedDocumentIds: [],
          createdAt: new Date(),
          updatedAt: new Date(),
        }
        set((state) => ({
          notebooks: state.notebooks.map((nb) =>
            nb.id === notebookId
              ? {
                  ...nb,
                  conversations: [newConversation, ...nb.conversations],
                  updatedAt: new Date(),
                }
              : nb
          ),
          currentConversationId: convId,
        }))
        return convId
      },

      deleteConversation: (notebookId: string, conversationId: string) => {
        set((state) => ({
          notebooks: state.notebooks.map((nb) =>
            nb.id === notebookId
              ? {
                  ...nb,
                  conversations: nb.conversations.filter((c) => c.id !== conversationId),
                  updatedAt: new Date(),
                }
              : nb
          ),
          currentConversationId:
            state.currentConversationId === conversationId ? null : state.currentConversationId,
        }))
      },

      setCurrentConversation: (notebookId: string, conversationId: string) => {
        set((state) => ({
          currentNotebookId: notebookId,
          currentConversationId: conversationId,
        }))
      },

      getCurrentConversation: () => {
        const state = get()
        const notebook = state.notebooks.find((nb) => nb.id === state.currentNotebookId)
        return notebook?.conversations.find((c) => c.id === state.currentConversationId) || null
      },

      // Message actions
      addMessage: async (notebookId: string, conversationId: string, message: Message) => {
        const { useServerSync } = get()

        // POST /conversations/<conv_id>/messages -> lokal state ancak basari sonrasi guncellenir
        if (useServerSync) {
          await ragClient.addMessage(conversationId, {
            role: message.role,
            content: message.content,
          })
        }

        set((state) => ({
          notebooks: state.notebooks.map((nb) =>
            nb.id === notebookId
              ? {
                  ...nb,
                  conversations: nb.conversations.map((c) =>
                    c.id === conversationId
                      ? {
                          ...c,
                          messages: [...c.messages, message],
                          updatedAt: new Date(),
                        }
                      : c
                  ),
                  updatedAt: new Date(),
                }
              : nb
          ),
        }))
      },

      updateMessage: (notebookId: string, conversationId: string, messageId: string, content: string) => {
        set((state) => ({
          notebooks: state.notebooks.map((nb) =>
            nb.id === notebookId
              ? {
                  ...nb,
                  conversations: nb.conversations.map((c) =>
                    c.id === conversationId
                      ? {
                          ...c,
                          messages: c.messages.map((m) =>
                            m.id === messageId ? { ...m, content } : m
                          ),
                          updatedAt: new Date(),
                        }
                      : c
                  ),
                  updatedAt: new Date(),
                }
              : nb
          ),
        }))
      },

      // Document actions
      addDocument: (notebookId: string, conversationId: string, document: Document) => {
        set((state) => ({
          notebooks: state.notebooks.map((nb) =>
            nb.id === notebookId
              ? {
                  ...nb,
                  documentCount: nb.documentCount + 1,
                  conversations: nb.conversations.map((c) =>
                    c.id === conversationId
                      ? {
                          ...c,
                          documents: [...c.documents, document],
                          // Yeni yuklenen belge, kaynak secimine varsayilan olarak dahil edilir
                          selectedDocumentIds: c.selectedDocumentIds.includes(document.id)
                            ? c.selectedDocumentIds
                            : [...c.selectedDocumentIds, document.id],
                          updatedAt: new Date(),
                        }
                      : c
                  ),
                  updatedAt: new Date(),
                }
              : nb
          ),
        }))
      },

      updateDocumentStatus: (notebookId: string, conversationId: string, docId: string, status: Document['status']) => {
        set((state) => ({
          notebooks: state.notebooks.map((nb) =>
            nb.id === notebookId
              ? {
                  ...nb,
                  conversations: nb.conversations.map((c) =>
                    c.id === conversationId
                      ? {
                          ...c,
                          documents: c.documents.map((d) =>
                            d.id === docId ? { ...d, status } : d
                          ),
                          updatedAt: new Date(),
                        }
                      : c
                  ),
                  updatedAt: new Date(),
                }
              : nb
          ),
        }))
      },

      removeDocument: (notebookId: string, conversationId: string, docId: string) => {
        set((state) => ({
          notebooks: state.notebooks.map((nb) =>
            nb.id === notebookId
              ? {
                  ...nb,
                  documentCount: Math.max(0, nb.documentCount - 1),
                  conversations: nb.conversations.map((c) =>
                    c.id === conversationId
                      ? {
                          ...c,
                          documents: c.documents.filter((d) => d.id !== docId),
                          // Silinen belge kaynak secim listesinden de cikarilir
                          selectedDocumentIds: c.selectedDocumentIds.filter((id) => id !== docId),
                          updatedAt: new Date(),
                        }
                      : c
                  ),
                  updatedAt: new Date(),
                }
              : nb
          ),
        }))
      },

      // MSSQL Config actions
      setMSSQLConfig: (notebookId: string, config: MSSQLConfig) => {
        set((state) => ({
          notebooks: state.notebooks.map((nb) =>
            nb.id === notebookId
              ? { ...nb, mssqlConfig: config, updatedAt: new Date() }
              : nb
          ),
        }))
      },

      getMSSQLConfig: (notebookId: string) => {
        const state = get()
        const notebook = state.notebooks.find((nb) => nb.id === notebookId)
        return notebook?.mssqlConfig || null
      },

      // Document selection actions (multi-select)
      toggleDocumentSelection: (notebookId: string, conversationId: string, docId: string) => {
        set((state) => ({
          notebooks: state.notebooks.map((nb) =>
            nb.id === notebookId
              ? {
                  ...nb,
                  conversations: nb.conversations.map((c) =>
                    c.id === conversationId
                      ? {
                          ...c,
                          selectedDocumentIds: c.selectedDocumentIds.includes(docId)
                            ? c.selectedDocumentIds.filter((id) => id !== docId)
                            : [...c.selectedDocumentIds, docId],
                          updatedAt: new Date(),
                        }
                      : c
                  ),
                  updatedAt: new Date(),
                }
              : nb
          ),
        }))
      },

      selectAllDocuments: (notebookId: string, conversationId: string) => {
        set((state) => ({
          notebooks: state.notebooks.map((nb) =>
            nb.id === notebookId
              ? {
                  ...nb,
                  conversations: nb.conversations.map((c) =>
                    c.id === conversationId
                      ? {
                          ...c,
                          selectedDocumentIds: c.documents.map((d) => d.id),
                          updatedAt: new Date(),
                        }
                      : c
                  ),
                  updatedAt: new Date(),
                }
              : nb
          ),
        }))
      },

      clearDocumentSelection: (notebookId: string, conversationId: string) => {
        set((state) => ({
          notebooks: state.notebooks.map((nb) =>
            nb.id === notebookId
              ? {
                  ...nb,
                  conversations: nb.conversations.map((c) =>
                    c.id === conversationId
                      ? {
                          ...c,
                          selectedDocumentIds: [],
                          updatedAt: new Date(),
                        }
                      : c
                  ),
                  updatedAt: new Date(),
                }
              : nb
          ),
        }))
      },

      getSelectedDocuments: (notebookId: string, conversationId: string) => {
        const state = get()
        const notebook = state.notebooks.find((nb) => nb.id === notebookId)
        const conversation = notebook?.conversations.find((c) => c.id === conversationId)
        if (!conversation) return []
        return conversation.documents.filter((d) => conversation.selectedDocumentIds.includes(d.id))
      },

      setTheme: (theme: ThemeType) => {
        set({ theme })
        if (typeof document !== 'undefined') {
          document.documentElement.setAttribute('data-theme', theme)
        }
      },

      setSidebarOpen: (open: boolean) => {
        set({ sidebarOpen: open })
      },

      setBackendUrl: (url: string) => {
        set({ backendUrl: url })
      },

      setHasHydrated: (state: boolean) => {
        set({ hasHydrated: state })
      },

      // Server sync actions
      setUseServerSync: (value: boolean) => {
        const { notebooks } = get()
        const hasStaleLocalData = notebooks.length > 0

        set({
          useServerSync: value,
          syncWarning:
            value && hasStaleLocalData
              ? 'Sunucu senkronu acildi ancak localStorage\'da zaten notebook/conversation verisi var. Bunlar sunucuda olmayabilir - loadFromServer() cagirarak sunucudaki veriyle degistirmeni oneririz.'
              : null,
        })
      },

      clearSyncWarning: () => set({ syncWarning: null }),

      loadFromServer: async () => {
        // GET /notebooks -> [{id, name}], sonra her notebook icin
        // GET /notebooks/<nb_id>/conversations -> [{id, title}]
        // Not: mesajlar bu adimda cekilmiyor (gorev kapsaminda yok), bu yuzden
        // sunucudan gelen conversation'lar bos messages/documents ile baslar.
        const serverNotebooks = await ragClient.getNotebooks()

        const notebooks: Notebook[] = await Promise.all(
          serverNotebooks.map(async (nb) => {
            const serverConversations = await ragClient.getConversations(nb.id)
            const conversations: Conversation[] = serverConversations.map((c) => ({
              id: c.id,
              title: c.title,
              messages: [],
              documents: [],
              selectedDocumentIds: [],
              createdAt: new Date(),
              updatedAt: new Date(),
            }))

            return {
              id: nb.id,
              name: nb.name,
              documentCount: 0,
              conversations,
              mssqlConfig: null,
              createdAt: new Date(),
              updatedAt: new Date(),
            }
          })
        )

        set({
          notebooks,
          currentNotebookId: null,
          currentConversationId: null,
          syncWarning: null,
        })
      },
    }),
    {
      name: 'rag-notebook-storage',
      storage: createJSONStorage(() => localStorage, {
        reviver: (_key, value) => {
          if (typeof value === 'string' && ISO_DATE_RE.test(value)) {
            return new Date(value)
          }
          return value
        },
      }),
      // sidebarOpen / hasHydrated gibi UI-only state'leri kalici hale getirmeye gerek yok
      partialize: (state) => ({
        notebooks: state.notebooks,
        currentNotebookId: state.currentNotebookId,
        currentConversationId: state.currentConversationId,
        theme: state.theme,
        backendUrl: state.backendUrl,
        useServerSync: state.useServerSync,
      }),
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true)
        // useServerSync acikken localStorage'dan gelen eski notebook/conversation
        // verisi varsa kullaniciyi uyar (sunucudaki gercek veriyle uyusmayabilir).
        if (state?.useServerSync && state.notebooks.length > 0) {
          state.setUseServerSync(true)
        }
      },
    }
  )
)