# RAG Chat Frontend

A modern, NotebookLM-style web interface for interacting with a Retrieval-Augmented Generation (RAG) system built with Ollama and Flask.

## Features

- **Multi-conversation support**: Create and manage multiple chat conversations simultaneously
- **Document management**: Upload PDF/TXT/DOC/DOCX files and process them for Q&A
- **Real-time chat**: Ask questions about your documents and get AI-powered responses
- **Dark/Light themes**: Toggle between dark and light modes for comfortable viewing
- **Responsive design**: Optimized for desktop and mobile devices
- **Backend configuration**: Easily switch between different backend servers
- **Message history**: Maintain full conversation history with timestamps
- **Document tracking**: Monitor document upload status (uploading, processing, ready, error)

## Getting Started

### Prerequisites

- Node.js 18+ with pnpm
- Flask backend running on `http://localhost:5000` (or custom URL)

### Installation

1. Install dependencies:
```bash
pnpm install
```

2. Start the development server:
```bash
pnpm dev
```

3. Open `http://localhost:3000` in your browser

## Configuration

### Backend URL

The default backend URL is `http://127.0.0.1:5000`. To change it:

1. Click on the backend URL in the header (e.g., "Backend: 127.0.0.1:5000")
2. Enter your custom backend URL
3. Click "Update"

The URL is remembered throughout your session.

## Project Structure

```
src/
├── app/
│   ├── layout.tsx          # Root layout with theme provider
│   ├── page.tsx            # Main application page
│   └── globals.css         # Global styles
├── components/
│   ├── sidebar.tsx         # Left sidebar with conversations
│   ├── chat-panel.tsx      # Main chat area
│   ├── message.tsx         # Individual message component
│   ├── chat-input.tsx      # Message input with file upload
│   ├── documents-list.tsx  # Document management
│   └── theme-provider.tsx  # Theme management
├── lib/
│   ├── store.ts            # Zustand state management
│   └── api-client.ts       # Flask backend client
```

## Key Components

### Zustand Store (`lib/store.ts`)

Centralized state management for:
- Conversations and messages
- Documents
- Theme preference
- Backend URL configuration

### RAG API Client (`lib/api-client.ts`)

Handles communication with the Flask backend:
- **`POST /chat`** - Send a message and get responses
- **`POST /upload`** - Upload documents
- **`GET /documents`** - List all documents
- **`POST /delete/<filename>`** - Delete a document
- **`POST /reset`** - Clear context

### Message Types

**Message**:
```typescript
{
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}
```

**Document**:
```typescript
{
  id: string
  name: string
  size: number
  uploadedAt: Date
  status: 'uploading' | 'processing' | 'ready' | 'error'
}
```

## Usage

### Starting a Conversation

1. Click "New Chat" in the sidebar to create a new conversation
2. The new conversation becomes active immediately

### Uploading Documents

1. Click the paperclip icon in the chat input area
2. Select a PDF, TXT, DOC, or DOCX file
3. The file will upload and process automatically
4. Once ready, the document appears in the "Documents" section

### Asking Questions

1. Type your question in the input box
2. Press Enter or click the send button
3. The AI responds based on your uploaded documents
4. Use Shift+Enter for multi-line messages

### Managing Conversations

- **Switch**: Click any conversation in the sidebar
- **Delete**: Hover over a conversation and click the trash icon
- **Rename**: Planned feature (future MSSQL UI integration)

## Planned Features

- Conversation renaming
- Bulk document operations
- MSSQL integration for persistent storage
- Advanced search across documents
- Document previews
- Export conversation as PDF
- Sharing capabilities

## Backend API Requirements

The Flask backend should implement these endpoints:

### POST /chat
Request:
```json
{
  "query": "Your question here"
}
```

Response:
```json
{
  "response": "AI generated answer",
  "sources": [
    {
      "document": "filename.pdf",
      "page": 1,
      "excerpt": "Relevant text excerpt"
    }
  ]
}
```

### POST /upload
Multipart form data with `file` field. Returns:
```json
{
  "filename": "uploaded_file.pdf",
  "size": 12345,
  "uploaded_at": "2026-08-06T06:30:00Z"
}
```

### GET /documents
Returns:
```json
{
  "documents": [
    {
      "name": "file.pdf",
      "size": 12345,
      "uploaded_at": "2026-08-06T06:30:00Z"
    }
  ]
}
```

### POST /delete/<filename>
Deletes a document. Returns 200 on success.

### POST /reset
Clears the RAG context. Returns 200 on success.

## Troubleshooting

### Backend Connection Error

If you see "No response from server. Check if backend is running.":

1. Verify the Flask backend is running on the configured URL
2. Check the backend URL in the header
3. Ensure CORS is enabled on your backend
4. Check browser console for more details

### Document Upload Failed

1. Ensure file size is within limits (backend dependent)
2. Check file format is supported (.pdf, .txt, .doc, .docx)
3. Verify backend has write permissions
4. Check disk space on server

### Theme Not Persisting

The theme preference is stored in localStorage. It will be remembered across sessions.

## Development

### Available Scripts

- `pnpm dev` - Start development server (hot reload enabled)
- `pnpm build` - Build for production
- `pnpm start` - Start production server
- `pnpm lint` - Run ESLint

### Technologies Used

- **Framework**: Next.js 16 (App Router)
- **UI**: shadcn/ui with Tailwind CSS
- **State Management**: Zustand
- **HTTP Client**: Axios
- **Icons**: Lucide React
- **Type Safety**: TypeScript

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (iOS Safari, Chrome Mobile)

## Security Considerations

- Messages and documents are stored locally during the session
- For persistence, implement backend storage (planned MSSQL integration)
- All API calls use proper error handling and timeouts
- File uploads are validated on backend
- No sensitive data is hardcoded

## Future Improvements

- [ ] Persistent storage with MSSQL
- [ ] Conversation persistence
- [ ] User authentication
- [ ] Collaboration features
- [ ] Advanced search
- [ ] Document preview
- [ ] Conversation export
- [ ] Voice input/output
- [ ] Plugin system for custom integrations

## License

MIT

## Support

For issues or questions, please refer to the backend documentation or contact support.
