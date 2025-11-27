import { useState, useEffect, useRef, useCallback } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

/**
 * Read Page
 *
 * A reading view for documents, articles, and research papers.
 * Key features:
 * - Select text → chat popup appears
 * - "Remember this for project X" → saves to cognitive graph
 * - Mobile-friendly: chat goes fullscreen
 * - Load documents via ?document=<id> query param
 */

// Sample documents (will be replaced with API fetch)
const SAMPLE_DOCUMENTS = {
  'sample-1': {
    id: 'sample-1',
    title: 'Introduction to Cognitive Graphs',
    author: 'Research Team',
    date: '2024-01-15',
    content: `# Introduction to Cognitive Graphs

A cognitive graph is a knowledge representation system that models information the way human memory works - through associations and connections.

## Why Cognitive Graphs?

Traditional databases store information in rigid tables. But human knowledge is interconnected:

- **People** connect to **projects** they work on
- **Ideas** link to **research** that inspired them
- **Memories** associate with **emotions** and **contexts**

## Core Concepts

### Nodes
Nodes represent entities: people, projects, documents, insights, memories. Each node has:
- A type (Person, Project, Insight, etc.)
- Properties (name, description, created_at)
- Relationships to other nodes

### Edges
Edges represent relationships between nodes:
- WORKS_ON (Person → Project)
- INSPIRED_BY (Insight → Document)
- REMEMBERS (User → Memory)

## Building Your Graph

As you interact with the system, your cognitive graph grows:

1. **Capture** - Save interesting passages, ideas, contacts
2. **Connect** - Link related concepts together
3. **Query** - Ask questions that traverse your knowledge
4. **Discover** - Find unexpected connections

> "The value of a cognitive graph isn't in the individual nodes, but in the patterns that emerge from their connections."

## Applications

- **Research**: Track sources, quotes, and how ideas connect
- **Project Management**: See who knows what and who works with whom
- **Personal Knowledge**: Build a second brain that grows with you
- **AI Assistance**: Give your AI agent context about your world

---

*Select any text above and click "Save to Graph" to remember it for later.*
`
  },
  'sample-2': {
    id: 'sample-2',
    title: 'The Art of Prompt Engineering',
    author: 'AI Research',
    date: '2024-02-20',
    content: `# The Art of Prompt Engineering

Prompt engineering is the practice of crafting inputs to AI systems to get desired outputs.

## Key Principles

### 1. Be Specific
Vague prompts get vague results. Instead of "write about dogs," try "write a 200-word overview of golden retriever temperament for first-time dog owners."

### 2. Provide Context
AI doesn't know your situation. Include relevant background:
- Who is the audience?
- What's the purpose?
- What constraints exist?

### 3. Use Examples
Show, don't just tell. Provide examples of the format or style you want.

### 4. Iterate
Your first prompt is rarely perfect. Refine based on outputs.

## Advanced Techniques

### Chain of Thought
Ask the AI to "think step by step" for complex reasoning tasks.

### Role Assignment
"You are an expert data scientist..." can shift the response style and depth.

### Structured Output
Request specific formats: "Return as JSON with fields: title, summary, tags"

## Common Mistakes

- **Too long**: Burying the key request in paragraphs of context
- **Too short**: Not providing enough information for a good response
- **Ambiguous**: Using terms that could mean multiple things

> "The best prompts are conversations, not commands."
`
  }
}

// Selection popup for saving text to graph
function SelectionPopup({ selection, position, onSave, onClose }) {
  const [note, setNote] = useState('')
  const [project, setProject] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const popupRef = useRef(null)

  // Close on click outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (popupRef.current && !popupRef.current.contains(e.target)) {
        onClose()
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [onClose])

  const handleSave = async () => {
    setIsSaving(true)
    await onSave({ text: selection, note, project })
    setIsSaving(false)
    onClose()
  }

  return (
    <div
      ref={popupRef}
      className="fixed z-50 bg-white dark:bg-gray-800 rounded-xl shadow-2xl border border-gray-200 dark:border-gray-700 p-4 w-80 max-w-[90vw]"
      style={{
        left: Math.min(position.x, window.innerWidth - 340),
        top: Math.min(position.y + 10, window.innerHeight - 300)
      }}
    >
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          <span>💾</span> Save to Graph
        </h3>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Selected text preview */}
      <div className="bg-purple-50 dark:bg-purple-900/30 rounded-lg p-3 mb-3 text-sm text-gray-700 dark:text-gray-300 max-h-24 overflow-y-auto">
        "{selection.slice(0, 200)}{selection.length > 200 ? '...' : ''}"
      </div>

      {/* Note input */}
      <div className="mb-3">
        <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
          Why is this important?
        </label>
        <input
          type="text"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="e.g., Key insight for my thesis..."
          className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-700 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 border-0"
        />
      </div>

      {/* Project selector */}
      <div className="mb-4">
        <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
          Link to project (optional)
        </label>
        <input
          type="text"
          value={project}
          onChange={(e) => setProject(e.target.value)}
          placeholder="e.g., Research Paper, Job Search..."
          className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-700 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 border-0"
        />
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={handleSave}
          disabled={isSaving}
          className="flex-1 px-4 py-2 bg-purple-500 text-white rounded-lg font-medium hover:bg-purple-600 disabled:opacity-50 flex items-center justify-center gap-2"
        >
          {isSaving ? (
            <>
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Saving...
            </>
          ) : (
            <>
              <span>💾</span> Save Reference
            </>
          )}
        </button>
      </div>
    </div>
  )
}

// Mobile fullscreen chat for discussing selection
function MobileChat({ selection, documentTitle, onClose, onSave }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Initial system message about selection
  useEffect(() => {
    if (selection) {
      setMessages([{
        role: 'system',
        content: `Selected from "${documentTitle}":\n\n"${selection.slice(0, 500)}${selection.length > 500 ? '...' : ''}"\n\nHow would you like to save this? You can say things like:\n- "Save this for my research project"\n- "Remember this as a key insight"\n- "Link this to the AI Ethics topic"`
      }])
    }
  }, [selection, documentTitle])

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return

    const userMessage = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setIsLoading(true)

    try {
      const response = await fetch('/api/persona/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMessage,
          context: {
            page: 'read',
            action: 'save_reference',
            selection: selection,
            document_title: documentTitle
          }
        })
      })

      const data = await response.json()

      if (data.success) {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: data.response
        }])

        // Check if agent saved something
        if (data.saved_reference) {
          // Show confirmation
          setMessages(prev => [...prev, {
            role: 'system',
            content: `✅ Saved to your cognitive graph${data.saved_reference.project ? ` under "${data.saved_reference.project}"` : ''}`
          }])
        }
      } else {
        throw new Error(data.error || 'Failed to get response')
      }
    } catch (error) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Sorry, I encountered an error: ${error.message}`,
        isError: true
      }])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-white dark:bg-gray-900 flex flex-col">
      {/* Header */}
      <header className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
        <h2 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          <span>💬</span> Save Reference
        </h2>
        <button
          onClick={onClose}
          className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
        >
          <svg className="w-6 h-6 text-gray-600 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-2.5 ${
                msg.role === 'user'
                  ? 'bg-purple-500 text-white'
                  : msg.role === 'system'
                  ? 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 text-sm'
                  : msg.isError
                  ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white'
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 dark:bg-gray-800 rounded-2xl px-4 py-2.5">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
            placeholder="Tell me how to save this..."
            className="flex-1 px-4 py-3 bg-gray-100 dark:bg-gray-700 rounded-xl border-0 focus:ring-2 focus:ring-purple-500"
          />
          <button
            onClick={sendMessage}
            disabled={isLoading || !input.trim()}
            className="px-4 py-3 bg-purple-500 text-white rounded-xl hover:bg-purple-600 disabled:opacity-50"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  )
}

// Document list sidebar
function DocumentList({ documents, activeId, onSelect, onClose }) {
  return (
    <div className="h-full flex flex-col bg-white dark:bg-gray-800">
      <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
        <h2 className="font-semibold text-gray-900 dark:text-white">Documents</h2>
        <button
          onClick={onClose}
          className="lg:hidden p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-2">
        {documents.map(doc => (
          <button
            key={doc.id}
            onClick={() => onSelect(doc.id)}
            className={`w-full text-left p-3 rounded-lg mb-1 transition-colors ${
              activeId === doc.id
                ? 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300'
                : 'hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300'
            }`}
          >
            <div className="font-medium truncate">{doc.title}</div>
            <div className="text-xs text-gray-500 mt-1">{doc.author} • {doc.date}</div>
          </button>
        ))}
      </div>
    </div>
  )
}

export default function Read() {
  const [searchParams, setSearchParams] = useSearchParams()
  const documentId = searchParams.get('document') || 'sample-1'

  const [documents] = useState(Object.values(SAMPLE_DOCUMENTS))
  const [activeDocument, setActiveDocument] = useState(SAMPLE_DOCUMENTS[documentId] || SAMPLE_DOCUMENTS['sample-1'])

  const [selection, setSelection] = useState(null)
  const [selectionPosition, setSelectionPosition] = useState({ x: 0, y: 0 })
  const [showPopup, setShowPopup] = useState(false)
  const [showMobileChat, setShowMobileChat] = useState(false)
  const [showSidebar, setShowSidebar] = useState(false)

  const contentRef = useRef(null)

  // Handle document change
  const handleDocumentSelect = (id) => {
    setSearchParams({ document: id })
    setActiveDocument(SAMPLE_DOCUMENTS[id])
    setShowSidebar(false)
  }

  // Handle text selection
  const handleMouseUp = useCallback(() => {
    const selectedText = window.getSelection()?.toString().trim()
    if (selectedText && selectedText.length > 10) {
      const range = window.getSelection()?.getRangeAt(0)
      const rect = range?.getBoundingClientRect()

      if (rect) {
        setSelection(selectedText)
        setSelectionPosition({ x: rect.left, y: rect.bottom })

        // On mobile (< 768px), go straight to fullscreen chat
        if (window.innerWidth < 768) {
          setShowMobileChat(true)
        } else {
          setShowPopup(true)
        }
      }
    }
  }, [])

  // Save reference to graph
  const handleSaveReference = async ({ text, note, project }) => {
    try {
      const response = await fetch('/api/references', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text,
          note,
          project,
          source: {
            type: 'document',
            id: activeDocument.id,
            title: activeDocument.title,
            author: activeDocument.author
          }
        })
      })

      const data = await response.json()
      if (data.success) {
        // Show success toast or notification
        console.log('Reference saved:', data)
      }
    } catch (error) {
      console.error('Failed to save reference:', error)
    }
  }

  const closePopup = () => {
    setShowPopup(false)
    setSelection(null)
    window.getSelection()?.removeAllRanges()
  }

  return (
    <div className="h-screen flex flex-col bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="flex items-center justify-between px-4 py-3 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowSidebar(true)}
            className="lg:hidden p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
          >
            <svg className="w-5 h-5 text-gray-600 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <Link to="/" className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
          </Link>
          <div>
            <h1 className="font-semibold text-gray-900 dark:text-white">{activeDocument.title}</h1>
            <p className="text-xs text-gray-500">{activeDocument.author} • {activeDocument.date}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500 dark:text-gray-400 hidden sm:block">
            Select text to save references
          </span>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar - documents list */}
        <aside className={`
          ${showSidebar ? 'fixed inset-0 z-40' : 'hidden'}
          lg:relative lg:block lg:w-64 lg:border-r lg:border-gray-200 lg:dark:border-gray-700
        `}>
          {/* Mobile overlay */}
          {showSidebar && (
            <div
              className="absolute inset-0 bg-black/50 lg:hidden"
              onClick={() => setShowSidebar(false)}
            />
          )}
          <div className={`
            ${showSidebar ? 'absolute left-0 top-0 h-full w-80 max-w-[85vw]' : ''}
            lg:relative lg:w-full h-full
          `}>
            <DocumentList
              documents={documents}
              activeId={activeDocument.id}
              onSelect={handleDocumentSelect}
              onClose={() => setShowSidebar(false)}
            />
          </div>
        </aside>

        {/* Main content */}
        <main
          ref={contentRef}
          className="flex-1 overflow-y-auto bg-white dark:bg-gray-900"
          onMouseUp={handleMouseUp}
          onTouchEnd={handleMouseUp}
        >
          <article className="max-w-3xl mx-auto px-4 py-8 lg:px-8">
            <div className="prose dark:prose-invert prose-purple max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {activeDocument.content}
              </ReactMarkdown>
            </div>
          </article>
        </main>
      </div>

      {/* Selection popup (desktop) */}
      {showPopup && selection && (
        <SelectionPopup
          selection={selection}
          position={selectionPosition}
          onSave={handleSaveReference}
          onClose={closePopup}
        />
      )}

      {/* Mobile chat (fullscreen) */}
      {showMobileChat && selection && (
        <MobileChat
          selection={selection}
          documentTitle={activeDocument.title}
          onClose={() => {
            setShowMobileChat(false)
            setSelection(null)
            window.getSelection()?.removeAllRanges()
          }}
          onSave={handleSaveReference}
        />
      )}
    </div>
  )
}
