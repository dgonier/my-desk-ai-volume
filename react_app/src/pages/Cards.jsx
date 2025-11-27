import { useState, useEffect, useMemo } from 'react'
import { useSearchParams, Link } from 'react-router-dom'

// Node type configuration
const NODE_CONFIG = {
  User: { bg: 'bg-emerald-500', icon: '👤', filter: 'identity' },
  Persona: { bg: 'bg-purple-500', icon: '🤖', filter: 'identity' },
  Trait: { bg: 'bg-violet-500', icon: '✨', filter: 'identity' },
  Preference: { bg: 'bg-teal-500', icon: '⚙️', filter: 'identity' },
  Memory: { bg: 'bg-pink-400', icon: '🧠', filter: 'identity' },
  Person: { bg: 'bg-blue-500', icon: '🧑', filter: 'people' },
  Organization: { bg: 'bg-pink-500', icon: '🏢', filter: 'people' },
  Company: { bg: 'bg-amber-500', icon: '🏛️', filter: 'people' },
  Project: { bg: 'bg-purple-500', icon: '📁', filter: 'projects' },
  Task: { bg: 'bg-amber-500', icon: '✅', filter: 'projects' },
  Goal: { bg: 'bg-cyan-500', icon: '🎯', filter: 'projects' },
  Insight: { bg: 'bg-cyan-500', icon: '💡', filter: 'research' },
  Document: { bg: 'bg-lime-500', icon: '📄', filter: 'documents' },
  Chunk: { bg: 'bg-lime-400', icon: '📝', filter: 'documents' },
  Unknown: { bg: 'bg-gray-500', icon: '📌', filter: 'other' },
}

const FILTERS = [
  { id: 'all', label: 'All', icon: '🌐' },
  { id: 'identity', label: 'Identity', icon: '🤖' },
  { id: 'people', label: 'People', icon: '👥' },
  { id: 'projects', label: 'Projects', icon: '📁' },
  { id: 'research', label: 'Research', icon: '🔬' },
  { id: 'documents', label: 'Documents', icon: '📄' },
]

// Card component for each node
function NodeCard({ node, onClick }) {
  const config = NODE_CONFIG[node.type] || NODE_CONFIG.Unknown

  return (
    <div
      onClick={() => onClick(node)}
      className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4 cursor-pointer hover:shadow-md hover:border-purple-300 dark:hover:border-purple-600 transition-all"
    >
      <div className="flex items-start gap-3">
        <div className={`w-10 h-10 ${config.bg} rounded-lg flex items-center justify-center text-xl flex-shrink-0`}>
          {config.icon}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs px-2 py-0.5 bg-gray-100 dark:bg-gray-700 rounded-full text-gray-600 dark:text-gray-400">
              {node.type}
            </span>
            {node.strength && (
              <span className="text-xs text-purple-500">{Math.round(node.strength * 100)}%</span>
            )}
          </div>
          <h3 className="font-semibold text-gray-900 dark:text-white truncate">
            {node.name || node.label || node.type}
          </h3>
          {(node.tagline || node.description || node.content) && (
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1 line-clamp-2">
              {node.tagline || node.description || node.content}
            </p>
          )}
          {node.core_values?.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {node.core_values.slice(0, 3).map((v, i) => (
                <span key={i} className="text-xs px-1.5 py-0.5 bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 rounded">
                  {v}
                </span>
              ))}
            </div>
          )}
          {node.created_at && (
            <p className="text-xs text-gray-400 mt-2">
              {new Date(node.created_at).toLocaleDateString()}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

// Detail modal
function NodeModal({ node, onClose }) {
  if (!node) return null
  const config = NODE_CONFIG[node.type] || NODE_CONFIG.Unknown

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-white dark:bg-gray-800 rounded-2xl max-w-lg w-full max-h-[80vh] overflow-hidden shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className={`${config.bg} p-6 text-white`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-3xl">{config.icon}</span>
              <div>
                <h2 className="text-xl font-bold">{node.name || node.label || node.type}</h2>
                <p className="text-white/80 text-sm">{node.type}</p>
              </div>
            </div>
            <button onClick={onClose} className="p-2 hover:bg-white/20 rounded-full">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          {node.tagline && <p className="mt-2 text-white/90">{node.tagline}</p>}
        </div>

        <div className="p-6 overflow-auto max-h-[50vh] space-y-4">
          {node.personality_summary && (
            <Section title="Personality">
              <p className="text-gray-700 dark:text-gray-300">{node.personality_summary}</p>
            </Section>
          )}
          {node.description && (
            <Section title="Description">
              <p className="text-gray-700 dark:text-gray-300">{node.description}</p>
            </Section>
          )}
          {node.content && (
            <Section title="Content">
              <p className="text-gray-700 dark:text-gray-300">{node.content}</p>
            </Section>
          )}
          {node.core_values?.length > 0 && (
            <Section title="Core Values">
              <div className="flex flex-wrap gap-2">
                {node.core_values.map((v, i) => (
                  <span key={i} className="px-3 py-1 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded-full text-sm">
                    {v}
                  </span>
                ))}
              </div>
            </Section>
          )}
          {node.quirks?.length > 0 && (
            <Section title="Quirks">
              <ul className="space-y-2">
                {node.quirks.map((q, i) => (
                  <li key={i} className="flex gap-2 text-sm text-gray-700 dark:text-gray-300">
                    <span className="text-purple-500">•</span>
                    <span>{q}</span>
                  </li>
                ))}
              </ul>
            </Section>
          )}
          {node.strength && (
            <Section title="Strength">
              <div className="flex items-center gap-3">
                <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-3">
                  <div className="bg-purple-500 h-3 rounded-full" style={{ width: `${node.strength * 100}%` }} />
                </div>
                <span className="text-sm font-medium">{Math.round(node.strength * 100)}%</span>
              </div>
            </Section>
          )}
          {node.confidence && (
            <Section title="Confidence">
              <div className="flex items-center gap-3">
                <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-3">
                  <div className="bg-green-500 h-3 rounded-full" style={{ width: `${node.confidence * 100}%` }} />
                </div>
                <span className="text-sm font-medium">{Math.round(node.confidence * 100)}%</span>
              </div>
            </Section>
          )}
        </div>

        <div className="p-4 border-t border-gray-200 dark:border-gray-700 flex justify-between items-center">
          {node.created_at && (
            <span className="text-sm text-gray-500">Created {new Date(node.created_at).toLocaleDateString()}</span>
          )}
          <Link
            to={`/graph?search=${encodeURIComponent(node.name || node.label || '')}`}
            className="text-sm text-purple-500 hover:text-purple-600"
          >
            View in Graph →
          </Link>
        </div>
      </div>
    </div>
  )
}

const Section = ({ title, children }) => (
  <div>
    <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase mb-2">{title}</h4>
    {children}
  </div>
)

export default function Cards() {
  const [searchParams, setSearchParams] = useSearchParams()
  const activeFilter = searchParams.get('filter') || 'all'

  const [nodes, setNodes] = useState([])
  const [selectedNode, setSelectedNode] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')

  useEffect(() => { fetchData() }, [])

  const fetchData = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch('/api/cognitive/graph')
      const data = await response.json()
      if (data.success) {
        setNodes(data.nodes || [])
      } else {
        setError(data.error || 'Failed to load')
      }
    } catch (err) {
      setError(`Connection error: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const setFilter = (filter) => {
    setSearchParams(filter === 'all' ? {} : { filter })
  }

  const filteredNodes = useMemo(() => {
    let result = nodes

    if (activeFilter !== 'all') {
      result = result.filter(n => NODE_CONFIG[n.type]?.filter === activeFilter)
    }

    if (search.trim()) {
      const q = search.toLowerCase()
      result = result.filter(n =>
        n.name?.toLowerCase().includes(q) ||
        n.label?.toLowerCase().includes(q) ||
        n.description?.toLowerCase().includes(q) ||
        n.content?.toLowerCase().includes(q) ||
        n.type?.toLowerCase().includes(q)
      )
    }

    return result
  }, [nodes, activeFilter, search])

  const nodeCounts = useMemo(() => {
    const counts = { all: nodes.length }
    FILTERS.forEach(f => {
      if (f.id !== 'all') {
        counts[f.id] = nodes.filter(n => NODE_CONFIG[n.type]?.filter === f.id).length
      }
    })
    return counts
  }, [nodes])

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-4 py-3">
        <div className="max-w-6xl mx-auto">
          <div className="flex items-center justify-between mb-3">
            <h1 className="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <span>📇</span> Cards
            </h1>
            <div className="flex items-center gap-2">
              <Link to="/graph" className="text-sm text-purple-500 hover:text-purple-600 flex items-center gap-1">
                <span>🧠</span> Graph View
              </Link>
              <button onClick={fetchData} disabled={loading} className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg">
                <svg className={`w-5 h-5 text-gray-600 ${loading ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </button>
            </div>
          </div>

          {/* Search */}
          <div className="relative mb-3">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search nodes..."
              className="w-full pl-10 pr-4 py-2 bg-gray-100 dark:bg-gray-700 border-0 rounded-xl text-gray-900 dark:text-white focus:ring-2 focus:ring-purple-500"
            />
            <svg className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>

          {/* Filters */}
          <div className="flex gap-2 overflow-x-auto pb-1 -mx-4 px-4">
            {FILTERS.map(f => (
              <button
                key={f.id}
                onClick={() => setFilter(f.id)}
                className={`px-3 py-1.5 rounded-full text-sm font-medium flex items-center gap-1.5 whitespace-nowrap transition-colors ${
                  activeFilter === f.id
                    ? 'bg-purple-500 text-white'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
                }`}
              >
                <span>{f.icon}</span>
                <span>{f.label}</span>
                <span className={`text-xs px-1.5 py-0.5 rounded-full ${activeFilter === f.id ? 'bg-white/20' : 'bg-gray-200 dark:bg-gray-600'}`}>
                  {nodeCounts[f.id] || 0}
                </span>
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-6xl mx-auto p-4">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="w-10 h-10 border-4 border-purple-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : error ? (
          <div className="text-center py-20">
            <p className="text-red-500 mb-4">{error}</p>
            <button onClick={fetchData} className="px-4 py-2 bg-purple-500 text-white rounded-lg">Retry</button>
          </div>
        ) : filteredNodes.length === 0 ? (
          <div className="text-center py-20 text-gray-500">
            <p>No nodes found</p>
            {activeFilter !== 'all' && (
              <button onClick={() => setFilter('all')} className="text-purple-500 mt-2">Clear filter</button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredNodes.map(node => (
              <NodeCard key={node.id} node={node} onClick={setSelectedNode} />
            ))}
          </div>
        )}
      </main>

      {/* Modal */}
      <NodeModal node={selectedNode} onClose={() => setSelectedNode(null)} />
    </div>
  )
}
