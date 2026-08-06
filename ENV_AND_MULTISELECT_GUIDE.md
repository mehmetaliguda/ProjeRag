# Environment Configuration & Multi-Select Implementation Guide

## Overview

This document describes two major improvements implemented in the RAG Chat application:

1. **Centralized Environment Configuration** - Single `.env` file for all backend configuration
2. **Multi-Select Knowledge Sources** - Select multiple documents/sources for queries

---

## Part 1: Frontend Environment Configuration

### Problem Solved

Previously, the backend URL was hardcoded (`http://127.0.0.1:5000`) and scattered across the codebase. Users had to manually edit multiple files or use UI dialogs to change the backend. This was error-prone and not scalable.

### Solution

All backend configuration is now centralized in a single `.env.local` file that reads environment variables at application startup.

### Setup

1. **Copy the example file:**
   ```bash
   cp .env.local.example .env.local
   ```

2. **Edit `.env.local` with your backend server details:**
   ```env
   # Point to your backend server (change this ONE value to switch backends)
   NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:5000
   
   # Optional: Specify individual components if needed
   # NEXT_PUBLIC_BACKEND_HOST=127.0.0.1
   # NEXT_PUBLIC_BACKEND_PORT=5000
   # NEXT_PUBLIC_UPLOAD_API_URL=http://127.0.0.1:5000/upload
   # NEXT_PUBLIC_WEBSOCKET_URL=ws://127.0.0.1:5000/ws
   ```

### Available Environment Variables

| Variable | Purpose | Example | Required |
|----------|---------|---------|----------|
| `NEXT_PUBLIC_API_BASE_URL` | Main backend server address | `http://api.example.com:5000` | ✓ Yes |
| `NEXT_PUBLIC_BACKEND_HOST` | Backend hostname (extracted automatically) | `api.example.com` | Optional |
| `NEXT_PUBLIC_BACKEND_PORT` | Backend port (extracted automatically) | `5000` | Optional |
| `NEXT_PUBLIC_UPLOAD_API_URL` | Custom upload endpoint | `http://api.example.com/files` | Optional |
| `NEXT_PUBLIC_WEBSOCKET_URL` | WebSocket server (future use) | `ws://api.example.com/ws` | Optional |

### How It Works

1. **Env Config Module** (`lib/env-config.ts`):
   - Reads `NEXT_PUBLIC_*` variables at runtime
   - Parses URLs to extract host/port
   - Provides helper functions for components

2. **API Client** (`lib/api-client.ts`):
   - Automatically uses `getApiBaseUrl()` on initialization
   - Respects manually set backend URLs
   - Falls back gracefully with defaults

3. **Chat Panel** (`components/chat-panel.tsx`):
   - Initializes RAG client with environment config
   - Can still be overridden via UI if needed

### Usage in Code

```typescript
// Anywhere in your components:
import { getApiBaseUrl, getBackendConfig } from '@/lib/env-config'

const baseUrl = getApiBaseUrl() // Returns 'http://127.0.0.1:5000'
const config = getBackendConfig() // Returns full config object
```

### Deployment Examples

**Local Development (Default):**
```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:5000
```

**Docker Compose:**
```env
NEXT_PUBLIC_API_BASE_URL=http://backend:5000
```

**Remote Server:**
```env
NEXT_PUBLIC_API_BASE_URL=https://api.mycompany.com:5000
```

**Vercel/Production:**
```env
NEXT_PUBLIC_API_BASE_URL=https://api.production.com
```

---

## Part 2: Multi-Select Knowledge Sources

### Problem Solved

Previously, users could only interact with one document at a time. For real-world RAG applications, users need to:
- Query across multiple documents simultaneously
- Select/deselect specific sources for focused searches
- See which sources are included in the current query
- Manage multiple knowledge sources (PDFs, docs, databases)

### Solution

Implemented a complete multi-select system with visual UI, state management, and API integration.

### Features

#### 1. Multi-Select UI Component
New component: `DocumentsMultiSelect` (`components/documents-multi-select.tsx`)

- **Visual checkboxes** for each document
- **Selection counter** showing "3 of 5 selected"
- **Select All / Clear All buttons** for bulk operations
- **Separate sections** for ready vs uploading documents
- **Delete buttons** for removing documents
- **Responsive design** that works on all screen sizes

#### 2. State Management
Updated store (`lib/store.ts`):

```typescript
// Each conversation now tracks selected documents
interface Conversation {
  selectedDocumentIds: string[]
  // ... other fields
}

// New actions available:
toggleDocumentSelection(notebookId, conversationId, docId)
selectAllDocuments(notebookId, conversationId)
clearDocumentSelection(notebookId, conversationId)
getSelectedDocuments(notebookId, conversationId)
```

#### 3. API Integration
Updated `ChatRequest` interface (`lib/api-client.ts`):

```typescript
export interface ChatRequest {
  query: string
  documentIds?: string[]      // New: array of selected doc IDs
  knowledgeSources?: string[] // New: names of sources used
}
```

When user sends a message:
```typescript
// Automatically includes selected documents
const selectedDocs = getSelectedDocuments(notebookId, conversationId)
const response = await ragClient.chat({
  query: userMessage,
  documentIds: selectedDocs.map(d => d.id),
  knowledgeSources: selectedDocs.map(d => d.name),
})
```

#### 4. Backend Expectations

Your backend should now receive:
```json
{
  "query": "What does the policy say about X?",
  "documentIds": ["doc-123", "doc-456"],
  "knowledgeSources": ["policy.pdf", "handbook.docx"]
}
```

Your backend can then:
- Filter RAG context to only these documents
- Return which sources were used in the answer
- Track source citations

### Usage Flow

1. **User uploads documents** → Appears in "Knowledge Sources" section
2. **User selects documents** → Checkbox gets checked, counter updates
3. **User sends message** → Selected document IDs sent to backend
4. **Backend searches only selected sources** → Faster, more focused answers
5. **Backend returns answer** → Optionally with source citations

### Extending for Future Knowledge Sources

The system is designed to support multiple source types:

```typescript
// Currently supported:
- PDF
- DOC/DOCX
- TXT
- Any uploaded file

// Future support (same UI, just change backend):
- MSSQL/Database tables
- Markdown files
- PowerPoint presentations
- External APIs
- Vector databases
- Embedding stores
```

All sources appear in the same multi-select interface - users don't need to know the difference.

### Component Integration

**In `ChatPanel`:**
```typescript
<DocumentsMultiSelect
  documents={conversation.documents}
  selectedIds={conversation.selectedDocumentIds}
  onToggleSelect={(docId) => toggleDocumentSelection(...)}
  onSelectAll={() => selectAllDocuments(...)}
  onClearAll={() => clearDocumentSelection(...)}
  onRemove={handleRemoveDocument}
/>
```

**What you can customize:**
- Label text (currently "Knowledge Sources")
- Button sizes and colors
- Selection behavior
- Visual styling via Tailwind classes

### Backend Implementation Notes

When you receive the request with `documentIds` and `knowledgeSources`:

1. **Filter embeddings** to only these documents
2. **Reduce search scope** for faster queries
3. **Track source usage** for answer citations
4. **Validate selections** (ensure user can access these sources)
5. **(Optional) Return metadata** showing which sources were used

### Testing the Feature

1. Create a notebook and open it
2. Upload a document (or multiple)
3. Wait for upload to complete (status changes to "ready")
4. Click the checkbox next to a document
5. Counter shows "1 of X selected"
6. Send a message - it goes to backend with `documentIds`

---

## Migration Guide

### If you're upgrading from the old version:

1. **Update your backend** to accept the new `ChatRequest` format:
   ```python
   # Before
   @app.post('/chat')
   def chat(query: str):
       # search all documents
   
   # After  
   @app.post('/chat')
   def chat(request: ChatRequest):
       document_ids = request.documentIds  # NEW
       if document_ids:
           # Filter RAG context to these documents
   ```

2. **Update Conversation model** if using database:
   ```python
   # Add to your Conversation schema
   selected_document_ids: List[str] = []
   ```

3. **Test with UI** - no frontend code changes needed

---

## Files Changed/Added

### New Files:
- `lib/env-config.ts` - Environment configuration module
- `.env.local` - Your local environment configuration
- `.env.local.example` - Template for env variables
- `components/documents-multi-select.tsx` - Multi-select UI component
- `ENV_AND_MULTISELECT_GUIDE.md` - This guide

### Modified Files:
- `lib/store.ts` - Added selection tracking and methods
- `lib/api-client.ts` - Added env config, updated ChatRequest
- `components/chat-panel.tsx` - Integrated multi-select, env config
- `app/.env.local` - Environment configuration

---

## Troubleshooting

### Issue: Backend not connecting
**Solution:** 
- Check `.env.local` has correct `NEXT_PUBLIC_API_BASE_URL`
- Verify backend is running at that address
- Check browser console for CORS errors

### Issue: Documents not showing up
**Solution:**
- Ensure documents are uploaded and status is "ready"
- Check store for `selectedDocumentIds` in Zustand DevTools
- Verify backend is receiving document IDs

### Issue: Selected documents not being sent
**Solution:**
- Check that `toggleDocumentSelection` is being called
- Verify `getSelectedDocuments` returns the selected items
- Check API request in Network tab of DevTools

---

## Performance Considerations

- **Multi-select reduces latency** - searching 2-3 documents is faster than all documents
- **Smaller search scope** - more relevant results
- **Better resource usage** - backend processes less data
- **User experience** - users can focus their queries

---

## Future Enhancements

Potential features to add:
- Source filtering by type (PDFs only, databases only)
- Search history with previous selections
- Saved source collections/groups
- Source performance metrics
- Search preview before sending query
- Favorite/pin frequently used sources

