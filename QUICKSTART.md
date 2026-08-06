# RAG Chat Frontend - Quick Start (5 minutes)

## 🚀 Start Here

### Step 1: Start the Dev Server
```bash
cd /vercel/share/v0-project
pnpm dev
```
The app opens at `http://localhost:3000` (or wait for the terminal message)

### Step 2: Open Your Browser
Navigate to `http://localhost:3000` and you should see:
- Left sidebar with "New Chat" button
- Main chat area with upload instructions
- Dark theme by default

### Step 3: Configure Backend (if needed)
1. Click the backend URL in the header: "Backend: 127.0.0.1:5000"
2. Enter your Flask backend URL (e.g., `http://localhost:5000`)
3. Click "Update"

That's it! You're ready to go. 🎉

---

## 📚 Next Steps

### Test the Chat
1. Click "New Chat" to create a conversation
2. Click the paperclip icon to upload a document (PDF, TXT, DOC, DOCX)
3. Wait for it to process
4. Type a question: "What is in this document?"
5. Press Enter to get a response from your AI

### More Features
- **Switch Conversations**: Click any conversation in the sidebar
- **Delete Conversation**: Hover and click the trash icon
- **Remove Document**: Click trash on document in the list
- **Toggle Theme**: Click "Light/Dark mode" button at bottom
- **Configure Backend**: Click the backend URL to change it

---

## ⚠️ Before You Start

Make sure your **Flask backend is running** on the configured URL:
- Default: `http://127.0.0.1:5000`
- Check that these endpoints exist:
  - `POST /chat`
  - `POST /upload`
  - `GET /documents`

If you get "No response from server" errors, verify:
1. Your backend is running: `python app.py`
2. The URL is correct (click the header to check)
3. CORS is enabled on your Flask app
4. No firewall is blocking the connection

---

## 📖 Full Documentation

- **README.md** - Complete feature list and usage guide
- **SETUP_GUIDE.md** - Installation, deployment, and troubleshooting
- **IMPLEMENTATION_SUMMARY.md** - Architecture and technical details

---

## 🎯 What You Have

✅ Production-ready frontend
✅ Dark/light themes
✅ Multi-conversation support
✅ Document management
✅ Responsive design (works on mobile)
✅ Type-safe TypeScript
✅ Ready to integrate with your backend

---

## 🔧 Common Commands

```bash
# Start development server
pnpm dev

# Build for production
pnpm build

# Start production server
pnpm start

# Run linter
pnpm lint
```

---

## 💡 Pro Tips

1. **Use Shift+Enter** for multi-line messages
2. **Click message timestamps** to copy (assistant messages only)
3. **Backend URL is remembered** during your session
4. **Theme preference persists** in localStorage
5. **Each conversation is independent** with its own documents

---

## ❓ Troubleshooting

**Q: Backend connection error?**
A: Click the backend URL in the header to configure it correctly

**Q: File won't upload?**
A: Ensure file is PDF/TXT/DOC/DOCX and backend is running

**Q: Chat not responding?**
A: Check browser console (F12) and backend logs

**Q: Theme not changing?**
A: Clear localStorage: `localStorage.clear()` then refresh

---

## 🚢 Ready to Deploy?

When you're ready to go live:

### Deploy to Vercel (Recommended)
```bash
vercel deploy
```

### Deploy Anywhere Else
```bash
pnpm build
pnpm start
```

See `SETUP_GUIDE.md` for full deployment instructions.

---

**Happy chatting!** 🎉

Any questions? Check the documentation or review the code comments.
