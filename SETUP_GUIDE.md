# RAG Chat Frontend - Setup Guide

## Quick Start

### 1. Prerequisites

Ensure you have:
- Node.js 18+ installed
- pnpm package manager
- Your Flask RAG backend running (see backend setup below)

### 2. Installation

```bash
# Install dependencies
pnpm install

# Start development server
pnpm dev
```

The app will open at `http://localhost:3000`

### 3. Configure Backend

When you first load the app, it defaults to `http://127.0.0.1:5000`. If your backend is running elsewhere:

1. Click the backend URL in the top header (e.g., "Backend: 127.0.0.1:5000")
2. Enter your custom backend URL
3. Click "Update"

The URL persists for your session.

## Backend Integration

### Expected Backend Endpoints

Your Flask backend should implement these endpoints:

#### 1. Chat Endpoint
```
POST /chat
Content-Type: application/json

{
  "query": "What is in the document?"
}

Response:
{
  "response": "The document contains...",
  "sources": [
    {
      "document": "file.pdf",
      "page": 1,
      "excerpt": "..."
    }
  ]
}
```

#### 2. Upload Endpoint
```
POST /upload
Content-Type: multipart/form-data

file: [binary file data]

Response:
{
  "filename": "file.pdf",
  "size": 1024000,
  "uploaded_at": "2026-08-06T06:30:00Z"
}
```

#### 3. Get Documents Endpoint
```
GET /documents

Response:
{
  "documents": [
    {
      "name": "file.pdf",
      "size": 1024000,
      "uploaded_at": "2026-08-06T06:30:00Z"
    }
  ]
}
```

#### 4. Delete Document Endpoint
```
POST /delete/<filename>

Response: 200 OK
```

#### 5. Reset Endpoint (Optional)
```
POST /reset

Response: 200 OK
```

### CORS Configuration

Ensure your Flask backend has CORS enabled:

```python
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
```

### Example Backend Configuration

Here's a minimal Flask setup that works with this frontend:

```python
from flask import Flask, request, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    query = data.get('query', '')
    # Your RAG logic here
    return jsonify({
        'response': f'Response to: {query}',
        'sources': []
    })

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files.get('file')
    if not file:
        return {'error': 'No file provided'}, 400
    
    filename = file.filename
    file.save(f'uploads/{filename}')
    
    return jsonify({
        'filename': filename,
        'size': os.path.getsize(f'uploads/{filename}'),
        'uploaded_at': '2026-08-06T06:30:00Z'
    })

@app.route('/documents', methods=['GET'])
def get_documents():
    documents = []
    for filename in os.listdir('uploads/'):
        filepath = f'uploads/{filename}'
        documents.append({
            'name': filename,
            'size': os.path.getsize(filepath),
            'uploaded_at': '2026-08-06T06:30:00Z'
        })
    return jsonify({'documents': documents})

@app.route('/delete/<filename>', methods=['POST'])
def delete_document(filename):
    os.remove(f'uploads/{filename}')
    return '', 200

if __name__ == '__main__':
    os.makedirs('uploads', exist_ok=True)
    app.run(debug=True, port=5000)
```

## Frontend Project Structure

```
/vercel/share/v0-project/
├── app/
│   ├── layout.tsx              # Root layout with theme provider
│   ├── page.tsx                # Main app page
│   ├── globals.css             # Global styles & themes
│   └── favicon.ico
├── components/
│   ├── sidebar.tsx             # Conversation sidebar
│   ├── chat-panel.tsx          # Main chat area
│   ├── message.tsx             # Individual message component
│   ├── chat-input.tsx          # Message input with file upload
│   ├── documents-list.tsx      # Document list display
│   ├── theme-provider.tsx      # Theme management
│   └── ui/
│       └── button.tsx          # shadcn/ui button
├── hooks/
│   └── use-rag-client.ts       # RAG API client hook
├── lib/
│   ├── store.ts                # Zustand state management
│   ├── api-client.ts           # API client implementation
│   └── utils.ts                # Utility functions
├── public/
│   ├── icon.svg
│   ├── icon-light-32x32.png
│   └── icon-dark-32x32.png
├── package.json
├── tsconfig.json
├── tailwind.config.js
├── next.config.mjs
├── components.json
├── README.md
└── SETUP_GUIDE.md
```

## Configuration

### Environment Variables

Create a `.env.local` file if needed (though the frontend works without it):

```env
# Optional: Override default backend URL
NEXT_PUBLIC_BACKEND_URL=http://localhost:5000
```

Note: The frontend allows changing the backend URL in the UI, so this is optional.

## Features & Usage

### Conversations
- Create multiple independent conversations
- Switch between conversations
- Delete conversations with their history

### Documents
- Upload PDF, TXT, DOC, DOCX files
- Track upload/processing status
- Remove documents from conversations
- See document size and upload time

### Chat
- Send messages with context from uploaded documents
- View message timestamps
- Copy assistant responses
- Multi-line message input (Shift+Enter)

### Themes
- Toggle between dark and light modes
- Preference persists in localStorage
- Respects system preference on first load

### Backend Management
- Click the backend URL to configure
- Change backend without reloading
- See connection status

## Troubleshooting

### "No response from server. Check if backend is running."

**Solution:**
1. Verify Flask backend is running: `python app.py`
2. Check backend URL is correct (click it in the header)
3. Ensure CORS is enabled on backend
4. Check firewall/network settings
5. Review browser console for network errors

### File upload fails

**Solution:**
1. Check file format (.pdf, .txt, .doc, .docx)
2. Verify file is not empty
3. Check backend has write permissions
4. Review server logs for errors
5. Ensure file size is within backend limits

### Chat returns no response

**Solution:**
1. Ensure documents were uploaded successfully
2. Check backend logs for processing errors
3. Verify backend has Ollama running properly
4. Try uploading a different document
5. Check for JavaScript errors in browser console

### Theme not changing

**Solution:**
1. Check browser allows localStorage
2. Clear localStorage: `localStorage.clear()`
3. Refresh the page
4. Check browser console for errors

## Development

### Available Commands

```bash
# Development server with hot reload
pnpm dev

# Build for production
pnpm build

# Start production server
pnpm start

# Run linter
pnpm lint
```

### Project Stack

- **Framework**: Next.js 16 (React 19)
- **Styling**: Tailwind CSS v4
- **UI Components**: shadcn/ui
- **State**: Zustand
- **HTTP**: Axios with error handling
- **Icons**: Lucide React
- **Type Safety**: TypeScript 5.7

### Key Files to Understand

1. **`lib/store.ts`** - All app state management
2. **`lib/api-client.ts`** - Backend communication
3. **`components/chat-panel.tsx`** - Main chat logic
4. **`app/page.tsx`** - App entry point

## Deployment

### To Vercel

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel
```

### To Other Hosts

```bash
# Build production bundle
pnpm build

# Start production server
pnpm start
```

## Performance Optimization

The frontend includes:
- Responsive design optimized for mobile
- Efficient re-renders using Zustand
- Optimistic UI updates
- Auto-scroll to latest messages
- Lazy loading for conversations

## Security Notes

- Messages stored locally during session only
- No sensitive data in localStorage
- All API calls use proper error handling
- File uploads validated on backend
- CORS headers properly configured

## Next Steps

1. Get your Flask backend running
2. Note the backend URL
3. Start the dev server: `pnpm dev`
4. Update backend URL if needed
5. Upload test documents
6. Start chatting!

## Support & Issues

For frontend issues:
1. Check the browser console (F12)
2. Review the server logs: `pnpm dev` output
3. Verify backend is running and accessible
4. Check the README.md for feature documentation

For backend issues:
1. Review backend logs
2. Test endpoints with curl/Postman
3. Ensure Ollama is running
4. Verify document processing

## Additional Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [Tailwind CSS](https://tailwindcss.com)
- [shadcn/ui](https://ui.shadcn.com)
- [Zustand](https://zustand.docs.pmnd.rs/)
