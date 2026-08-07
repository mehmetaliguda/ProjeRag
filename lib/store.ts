import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { ragClient, CitationInfo } from '@/lib/api-client'

export type ThemeType = 'light' | 'dark' | 'dust-pink' | 'blue' | 'green' | 'purple'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  citations?: Record<string, CitationInfo>
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
  selectedDocumentIds: string[] // Track multiple selected documents (from notebook.documents)
  createdAt: Date
  updatedAt: Date
}

export interface Notebook {
  currentConversationId: string
  id: string
  name: string
  documentCount: number
  documents: Document[] // Notebook-global; shared across all conversations
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

  // Document actions (notebook-global)
  addDocumentsToNotebook: (notebookId: string, documents: Document[]) => void
  removeDocumentFromNotebook: (notebookId: string, docId: string) => void
  updateDocumentStatus: (notebookId: string, docId: string, status: Document['status']) => void
  getNotebookDocuments: (notebookId: string) => Document[]

  // Document selection actions (multi-select)
  toggleDocumentSelection: (notebookId: string, conversationId: string, docId: string) => void
  selectAllDocuments: (notebookId: string, conversationId: string) => void
  clearDocumentSelection: (notebookId: string, conversationId: string) => void
  getSelectedDocuments: (notebookId: string, conversationId: string) => Document[]

  // Citation panel state
  activeCitation: CitationInfo | null
  setActiveCitation: (citation: CitationInfo | null) => void

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
      activeCitation: null,

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
          documents: [],
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

      // Document actions (notebook-global — shared across all conversations)
      addDocumentsToNotebook: (notebookId: string, documents: Document[]) => {
        const { currentConversationId } = get()

        set((state) => ({
          notebooks: state.notebooks.map((nb) => {
            if (nb.id !== notebookId) return nb

            // id'ye gore dedupe et: ayni id zaten varsa yeni gelenle degistir, yoksa ekle
            const existingIds = new Set(nb.documents.map((d) => d.id))
            const merged = [
              ...nb.documents.filter((d) => !documents.some((nd) => nd.id === d.id)),
              ...documents,
            ]
            const newlyAddedIds = documents
              .filter((d) => !existingIds.has(d.id))
              .map((d) => d.id)

            return {
              ...nb,
              documentCount: merged.length,
              documents: merged,
              // ISTISNA: aktif conversation bu notebook'a aitse ve selectedDocumentIds
              // bossa, yeni eklenen dokumanlari otomatik secili yap.
              conversations: nb.conversations.map((c) =>
                c.id === currentConversationId && c.selectedDocumentIds.length === 0
                  ? {
                      ...c,
                      selectedDocumentIds: newlyAddedIds,
                      updatedAt: new Date(),
                    }
                  : c
              ),
              updatedAt: new Date(),
            }
          }),
        }))
      },

      removeDocumentFromNotebook: (notebookId: string, docId: string) => {
        set((state) => ({
          notebooks: state.notebooks.map((nb) =>
            nb.id === notebookId
              ? {
                  ...nb,
                  documentCount: Math.max(0, nb.documentCount - 1),
                  documents: nb.documents.filter((d) => d.id !== docId),
                  // Silinen belge, notebook'taki TUM conversation'larin secim
                  // listesinden de cikarilir.
                  conversations: nb.conversations.map((c) => ({
                    ...c,
                    selectedDocumentIds: c.selectedDocumentIds.filter((id) => id !== docId),
                    updatedAt: new Date(),
                  })),
                  updatedAt: new Date(),
                }
              : nb
          ),
        }))
      },

      updateDocumentStatus: (notebookId: string, docId: string, status: Document['status']) => {
        set((state) => ({
          notebooks: state.notebooks.map((nb) =>
            nb.id === notebookId
              ? {
                  ...nb,
                  documents: nb.documents.map((d) =>
                    d.id === docId ? { ...d, status } : d
                  ),
                  updatedAt: new Date(),
                }
              : nb
          ),
        }))
      },

      getNotebookDocuments: (notebookId: string) => {
        const state = get()
        const notebook = state.notebooks.find((nb) => nb.id === notebookId)
        return notebook?.documents || []
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
                          selectedDocumentIds: nb.documents.map((d) => d.id),
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
        if (!notebook || !conversation) return []
        return notebook.documents.filter((d) => conversation.selectedDocumentIds.includes(d.id))
      },

      setActiveCitation: (citation: CitationInfo | null) => {
        set({ activeCitation: citation })
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
              selectedDocumentIds: [],
              createdAt: new Date(),
              updatedAt: new Date(),
            }))

            return {
              id: nb.id,
              name: nb.name,
              documentCount: 0,
              documents: [],
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
      version: 2,
      storage: createJSONStorage(() => localStorage, {
        reviver: (_key, value) => {
          if (typeof value === 'string' && ISO_DATE_RE.test(value)) {
            return new Date(value)
          }
          return value
        },
      }),
      // v1 -> v2: Document, Conversation seviyesinden Notebook seviyesine tasindi.
      // Eski state'te her conversation kendi documents[] dizisine sahipti; artik
      // bu dizi notebook.documents altinda TEK ve PAYLASIMLI. Eski kullanicilarin
      // localStorage verisini kaybetmemesi icin burada donusturuyoruz.
      migrate: (persistedState: unknown, version: number) => {
        const state = persistedState as { notebooks?: any[] } & Record<string, unknown>

        if (version >= 2 || !state?.notebooks) {
          return state as AppStore
        }

        const notebooks = state.notebooks.map((nb: any) => {
          // Eski conversation'lardaki documents dizilerini id'ye gore dedupe ederek topla
          const collected = new Map<string, Document>()
          for (const conv of nb.conversations || []) {
            for (const doc of conv.documents || []) {
              collected.set(doc.id, doc)
            }
          }

          const conversations = (nb.conversations || []).map((conv: any) => {
            const oldDocs: Document[] = conv.documents || []
            const { documents: _drop, ...rest } = conv
            return {
              ...rest,
              // selectedDocumentIds yoksa eski conversation'daki dokuman id'lerini kullan
              selectedDocumentIds:
                conv.selectedDocumentIds && conv.selectedDocumentIds.length > 0
                  ? conv.selectedDocumentIds
                  : oldDocs.map((d) => d.id),
            }
          })

          return {
            ...nb,
            documents: Array.from(collected.values()),
            conversations,
          }
        })

        return { ...state, notebooks } as AppStore
      },
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