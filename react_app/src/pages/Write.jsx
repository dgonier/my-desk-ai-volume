import { useState, useCallback, useRef, useEffect } from 'react'
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels'
import CodeMirror from '@uiw/react-codemirror'
import { markdown, markdownLanguage } from '@codemirror/lang-markdown'
import { languages } from '@codemirror/language-data'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import 'katex/dist/katex.min.css'

const DEFAULT_CONTENT = `# Welcome to Write

This is an **Overleaf-style** writing environment with Claude AI assistance.

## Features

- **Live Preview**: See your formatted document as you type
- **Math Support**: Write LaTeX math like $E = mc^2$ or display equations:

$$
\\int_{-\\infty}^{\\infty} e^{-x^2} dx = \\sqrt{\\pi}
$$

- **Code Blocks**: Syntax highlighted code

\`\`\`python
def hello_world():
    print("Hello from my-desk.ai!")
\`\`\`

- **Claude Chat**: Ask Claude for help with your writing

## Getting Started

1. Edit your document in the left panel
2. See the live preview on the right
3. Chat with Claude below for writing assistance

---

*Start writing your masterpiece!*
`

function Write() {
  const [content, setContent] = useState(DEFAULT_CONTENT)
  const [messages, setMessages] = useState([])
  const [chatInput, setChatInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [documents, setDocuments] = useState([
    { id: 1, name: 'Untitled Document', content: DEFAULT_CONTENT }
  ])
  const [activeDocId, setActiveDocId] = useState(1)
  const chatEndRef = useRef(null)

  // Scroll chat to bottom when new messages arrive
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleEditorChange = useCallback((value) => {
    setContent(value)
    // Update the active document
    setDocuments(docs =>
      docs.map(doc =>
        doc.id === activeDocId ? { ...doc, content: value } : doc
      )
    )
  }, [activeDocId])

  const sendMessage = async () => {
    if (!chatInput.trim() || isLoading) return

    const userMessage = chatInput.trim()
    setChatInput('')
    setMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setIsLoading(true)

    try {
      // Include document context in the prompt
      const contextPrompt = `I'm writing a document. Here's my current content:

---
${content}
---

User's question: ${userMessage}

Please help with their writing. If they ask for edits, provide the updated text clearly.`

      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: contextPrompt })
      })

      if (!response.ok) throw new Error('Chat request failed')

      const data = await response.json()
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.response || data.message || 'No response received'
      }])
    } catch (error) {
      console.error('Chat error:', error)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Error: ${error.message}. Make sure you're logged in.`
      }])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const createNewDocument = () => {
    const newId = Math.max(...documents.map(d => d.id)) + 1
    const newDoc = { id: newId, name: `Document ${newId}`, content: '' }
    setDocuments([...documents, newDoc])
    setActiveDocId(newId)
    setContent('')
  }

  const applyEdit = (newContent) => {
    setContent(newContent)
    setDocuments(docs =>
      docs.map(doc =>
        doc.id === activeDocId ? { ...doc, content: newContent } : doc
      )
    )
  }

  return (
    <div className="h-screen flex flex-col bg-gray-900">
      {/* Top toolbar */}
      <div className="bg-gray-800 border-b border-gray-700 px-4 py-2 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <span className="text-white font-semibold">Write</span>
          <div className="flex gap-1">
            {documents.map(doc => (
              <button
                key={doc.id}
                onClick={() => {
                  setActiveDocId(doc.id)
                  setContent(doc.content)
                }}
                className={`px-3 py-1 text-sm rounded ${
                  doc.id === activeDocId
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
              >
                {doc.name}
              </button>
            ))}
            <button
              onClick={createNewDocument}
              className="px-2 py-1 text-sm bg-gray-700 text-gray-300 hover:bg-gray-600 rounded"
            >
              +
            </button>
          </div>
        </div>
        <div className="flex gap-2">
          <button className="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700">
            Export
          </button>
        </div>
      </div>

      {/* Main content area */}
      <div className="flex-1 overflow-hidden">
        <PanelGroup direction="horizontal">
          {/* Editor Panel */}
          <Panel defaultSize={50} minSize={30}>
            <div className="h-full bg-gray-900">
              <CodeMirror
                value={content}
                height="100%"
                theme="dark"
                extensions={[
                  markdown({ base: markdownLanguage, codeLanguages: languages })
                ]}
                onChange={handleEditorChange}
                className="h-full"
                style={{ height: '100%' }}
              />
            </div>
          </Panel>

          <PanelResizeHandle className="w-1 bg-gray-700 hover:bg-blue-500 transition-colors cursor-col-resize" />

          {/* Preview + Chat Panel */}
          <Panel defaultSize={50} minSize={30}>
            <PanelGroup direction="vertical">
              {/* Preview Panel */}
              <Panel defaultSize={60} minSize={20}>
                <div className="h-full bg-white overflow-auto p-6">
                  <div className="prose prose-lg max-w-none">
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm, remarkMath]}
                      rehypePlugins={[rehypeKatex]}
                      components={{
                        code({ node, inline, className, children, ...props }) {
                          const match = /language-(\w+)/.exec(className || '')
                          return !inline ? (
                            <pre className="bg-gray-100 p-4 rounded-lg overflow-x-auto">
                              <code className={className} {...props}>
                                {children}
                              </code>
                            </pre>
                          ) : (
                            <code className="bg-gray-100 px-1 rounded" {...props}>
                              {children}
                            </code>
                          )
                        }
                      }}
                    >
                      {content}
                    </ReactMarkdown>
                  </div>
                </div>
              </Panel>

              <PanelResizeHandle className="h-1 bg-gray-300 hover:bg-blue-500 transition-colors cursor-row-resize" />

              {/* Chat Panel */}
              <Panel defaultSize={40} minSize={15}>
                <div className="h-full bg-gray-50 flex flex-col">
                  {/* Chat header */}
                  <div className="bg-white border-b px-4 py-2 flex items-center justify-between">
                    <span className="font-medium text-gray-700">Claude Assistant</span>
                    <span className="text-xs text-gray-500">Ask for help with your writing</span>
                  </div>

                  {/* Messages */}
                  <div className="flex-1 overflow-y-auto p-4 space-y-3">
                    {messages.length === 0 && (
                      <div className="text-gray-500 text-sm text-center py-8">
                        <p>Ask Claude to help with your writing.</p>
                        <p className="text-xs mt-2">Try: "Help me improve the introduction" or "Add a section about..."</p>
                      </div>
                    )}
                    {messages.map((msg, i) => (
                      <div
                        key={i}
                        className={`p-3 rounded-lg ${
                          msg.role === 'user'
                            ? 'bg-blue-100 ml-8'
                            : 'bg-white border mr-8'
                        }`}
                      >
                        <div className="text-xs text-gray-500 mb-1">
                          {msg.role === 'user' ? 'You' : 'Claude'}
                        </div>
                        <div className="text-sm whitespace-pre-wrap">{msg.content}</div>
                      </div>
                    ))}
                    {isLoading && (
                      <div className="bg-white border p-3 rounded-lg mr-8">
                        <div className="text-xs text-gray-500 mb-1">Claude</div>
                        <div className="text-sm text-gray-400">Thinking...</div>
                      </div>
                    )}
                    <div ref={chatEndRef} />
                  </div>

                  {/* Input */}
                  <div className="border-t bg-white p-3">
                    <div className="flex gap-2">
                      <textarea
                        value={chatInput}
                        onChange={(e) => setChatInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Ask Claude for help..."
                        className="flex-1 resize-none border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        rows={2}
                      />
                      <button
                        onClick={sendMessage}
                        disabled={isLoading || !chatInput.trim()}
                        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Send
                      </button>
                    </div>
                  </div>
                </div>
              </Panel>
            </PanelGroup>
          </Panel>
        </PanelGroup>
      </div>
    </div>
  )
}

export default Write
