import { useState, useRef, useEffect, useCallback } from 'react'
import { useLocation } from 'react-router-dom'

/**
 * Universal Chat Component
 *
 * A floating chat interface that:
 * - Appears as a FAB (Floating Action Button) in bottom-right
 * - Opens a side panel for conversation
 * - Automatically knows what page/context the user is on
 * - Uses the Persona Agent for all interactions
 * - Supports tool use (cognitive tree, delegation to Claude Code, etc.)
 */

// Page context mapping - describes what each page is for
const PAGE_CONTEXT = {
  '/': {
    name: 'Home',
    description: 'Dashboard overview showing recent activity and quick actions',
    capabilities: ['view recent projects', 'quick navigation', 'overview stats']
  },
  '/graph': {
    name: 'Cognitive Graph',
    description: 'Interactive knowledge graph showing all connected nodes - identity, people, projects, research, and documents',
    capabilities: ['explore connections', 'filter by category', 'search nodes', 'view relationships']
  },
  '/cards': {
    name: 'Cards View',
    description: 'Card-based browsing of cognitive graph - ideal for mobile or scanning',
    capabilities: ['browse nodes', 'filter by category', 'quick search', 'view details']
  },
  '/projects': {
    name: 'Projects',
    description: 'Project management with cognitive graph visualization',
    capabilities: ['view/edit projects', 'manage tasks', 'add people', 'view relationships']
  },
  '/relationships': {
    name: 'People & Relationships',
    description: 'Relationship graph showing people and their connections',
    capabilities: ['view contacts', 'manage relationships', 'link people to projects']
  },
  '/write': {
    name: 'Writing',
    description: 'Long-form writing and document creation',
    capabilities: ['draft documents', 'edit content', 'manage chapters']
  },
  '/read': {
    name: 'Reading',
    description: 'Read documents, research papers, and saved content with annotations',
    capabilities: ['read documents', 'save references to graph', 'annotate passages', 'link to projects']
  },
  '/audio': {
    name: 'Audio',
    description: 'Listen to podcast-style reports, summaries, and updates from your AI agent',
    capabilities: ['play audio clips', 'share links', 'browse by type', 'filter reports']
  },
  '/research': {
    name: 'Research',
    description: 'Research workspace for gathering and organizing information',
    capabilities: ['web search', 'save findings', 'organize research']
  },
  '/jobs-feed': {
    name: 'Jobs Feed',
    description: 'Job listings and career opportunities',
    capabilities: ['browse jobs', 'save listings', 'track applications']
  }
}

// Chat message component
function ChatMessage({ message, personaName }) {
  const isUser = message.role === 'user'
  const isSystem = message.role === 'system'
  const isError = message.isError

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-2.5 ${
          isUser
            ? 'bg-purple-500 text-white rounded-br-md'
            : isSystem
            ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-200'
            : isError
            ? 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200'
            : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white rounded-bl-md'
        }`}
      >
        {!isUser && !isSystem && (
          <div className="text-xs font-medium text-purple-600 dark:text-purple-400 mb-1">
            {personaName || 'Assistant'}
          </div>
        )}
        <div className="text-sm whitespace-pre-wrap">{message.content}</div>

        {/* Tool calls indicator */}
        {message.toolCalls?.length > 0 && (
          <div className="mt-2 pt-2 border-t border-gray-200 dark:border-gray-600">
            <div className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1">
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              Used {message.toolCalls.length} tool(s)
            </div>
          </div>
        )}

        {/* Context used indicator */}
        {message.contextUsed && (
          <div className="mt-1 text-xs text-gray-400 dark:text-gray-500">
            {message.contextUsed.memories_retrieved > 0 &&
              `${message.contextUsed.memories_retrieved} memories`}
          </div>
        )}
      </div>
    </div>
  )
}

export default function UniversalChat({ defaultOpen = false }) {
  const [isOpen, setIsOpen] = useState(defaultOpen)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [personaName, setPersonaName] = useState(null)
  const [personaInitialized, setPersonaInitialized] = useState(false)
  const [conversationHistory, setConversationHistory] = useState([])

  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)
  const location = useLocation()

  // Get current page context
  const getCurrentContext = useCallback(() => {
    const path = location.pathname
    const pageInfo = PAGE_CONTEXT[path] || {
      name: 'Unknown Page',
      description: `Viewing ${path}`,
      capabilities: []
    }

    return {
      page: path,
      ...pageInfo,
      timestamp: new Date().toISOString()
    }
  }, [location.pathname])

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Focus input when chat opens
  useEffect(() => {
    if (isOpen) {
      inputRef.current?.focus()
    }
  }, [isOpen])

  // Initialize persona when chat first opens
  useEffect(() => {
    if (isOpen && !personaInitialized) {
      initializePersona()
    }
  }, [isOpen, personaInitialized])

  // Initialize the persona agent
  const initializePersona = async () => {
    try {
      const response = await fetch('/api/persona/initialize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })
      const data = await response.json()

      if (data.success) {
        setPersonaName(data.persona?.name || 'Assistant')
        setPersonaInitialized(true)

        // Add welcome message
        setMessages([{
          role: 'assistant',
          content: data.message || `Hi! I'm ${data.persona?.name || 'your assistant'}. How can I help you today?`,
          personaName: data.persona?.name
        }])
      }
    } catch (err) {
      console.error('Failed to initialize persona:', err)
      setMessages([{
        role: 'assistant',
        content: "Hello! I'm here to help. What would you like to do?",
        isError: false
      }])
      setPersonaInitialized(true)
    }
  }

  // Send a message
  const sendMessage = async () => {
    if (!input.trim() || isLoading) return

    const userMessage = input.trim()
    setInput('')

    // Add user message to chat
    setMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setIsLoading(true)

    try {
      // Get current page context
      const pageContext = getCurrentContext()

      const response = await fetch('/api/persona/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMessage,
          conversation_history: conversationHistory,
          page_context: pageContext
        })
      })

      const data = await response.json()

      if (data.success) {
        // Update persona name if returned
        if (data.persona_name) {
          setPersonaName(data.persona_name)
        }

        // Add assistant response
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: data.response,
          toolCalls: data.tool_calls,
          contextUsed: data.context_used
        }])

        // Update conversation history for context
        setConversationHistory(prev => [
          ...prev,
          { role: 'user', content: userMessage },
          { role: 'assistant', content: data.response }
        ].slice(-20)) // Keep last 20 messages for context

      } else {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: `Sorry, I encountered an error: ${data.error}`,
          isError: true
        }])
      }
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Connection error: ${err.message}`,
        isError: true
      }])
    } finally {
      setIsLoading(false)
    }
  }

  // Handle keyboard shortcuts
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  // Current page context display
  const pageContext = getCurrentContext()

  return (
    <>
      {/* Floating Action Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`fixed bottom-6 right-6 w-16 h-16 rounded-full shadow-2xl flex items-center justify-center transition-all duration-300 border-4 border-white dark:border-gray-900 ${
          isOpen
            ? 'bg-gray-700 hover:bg-gray-800 z-[60]'
            : 'bg-gradient-to-br from-purple-500 to-indigo-600 hover:from-purple-600 hover:to-indigo-700 hover:scale-110 z-[60]'
        }`}
        style={{ boxShadow: '0 8px 32px rgba(139, 92, 246, 0.4)' }}
        title={isOpen ? 'Close chat' : 'Chat with Mira'}
      >
        {isOpen ? (
          <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        ) : (
          <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
        )}
      </button>

      {/* Chat Panel */}
      <div
        className={`fixed bottom-28 right-6 w-96 max-w-[calc(100vw-3rem)] max-h-[70vh] bg-white dark:bg-gray-800 rounded-2xl shadow-2xl flex flex-col overflow-hidden transition-all duration-300 z-[55] border border-gray-200 dark:border-gray-700 ${
          isOpen
            ? 'opacity-100 translate-y-0 scale-100'
            : 'opacity-0 translate-y-4 scale-95 pointer-events-none'
        }`}
      >
        {/* Header */}
        <div className="px-4 py-3 bg-purple-500 text-white">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold">{personaName || 'Assistant'}</h3>
              <div className="text-xs text-purple-200 flex items-center gap-1">
                <span className="w-2 h-2 bg-green-400 rounded-full"></span>
                {pageContext.name}
              </div>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="p-1 hover:bg-purple-600 rounded-lg transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          </div>
        </div>

        {/* Context Banner */}
        <div className="px-3 py-2 bg-purple-50 dark:bg-purple-900/20 border-b border-purple-100 dark:border-purple-800">
          <div className="text-xs text-purple-600 dark:text-purple-400">
            <span className="font-medium">Context:</span> {pageContext.description}
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-1 min-h-[200px] max-h-[400px]">
          {messages.length === 0 ? (
            <div className="text-center text-gray-400 dark:text-gray-500 py-8">
              <svg className="w-12 h-12 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
              <p className="text-sm">Loading...</p>
            </div>
          ) : (
            messages.map((msg, i) => (
              <ChatMessage key={i} message={msg} personaName={personaName} />
            ))
          )}

          {/* Loading indicator */}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-gray-100 dark:bg-gray-700 rounded-2xl rounded-bl-md px-4 py-3">
                <div className="flex items-center gap-1">
                  <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="p-3 border-t border-gray-200 dark:border-gray-700">
          <div className="flex gap-2">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask me anything..."
              disabled={isLoading}
              className="flex-1 px-4 py-2.5 bg-gray-100 dark:bg-gray-700 border-0 rounded-xl text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-purple-500 focus:outline-none disabled:opacity-50"
            />
            <button
              onClick={sendMessage}
              disabled={isLoading || !input.trim()}
              className="px-4 py-2.5 bg-purple-500 text-white rounded-xl hover:bg-purple-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
