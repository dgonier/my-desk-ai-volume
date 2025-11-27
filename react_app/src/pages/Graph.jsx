import { useState, useCallback, useEffect, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels'
import ReactFlow, {
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType,
  Position,
  Handle,
} from 'reactflow'
import 'reactflow/dist/style.css'

// Node type configuration
const NODE_CONFIG = {
  // Core identity
  User: { bg: '#10b981', border: '#059669', text: '#fff', icon: '👤', filter: 'identity' },
  Persona: { bg: '#8b5cf6', border: '#7c3aed', text: '#fff', icon: '🤖', filter: 'identity' },
  Trait: { bg: '#a855f7', border: '#9333ea', text: '#fff', icon: '✨', filter: 'identity' },
  Preference: { bg: '#14b8a6', border: '#0d9488', text: '#fff', icon: '⚙️', filter: 'identity' },
  Memory: { bg: '#f472b6', border: '#ec4899', text: '#fff', icon: '🧠', filter: 'identity' },

  // People
  Person: { bg: '#3b82f6', border: '#2563eb', text: '#fff', icon: '🧑', filter: 'people' },
  Organization: { bg: '#ec4899', border: '#db2777', text: '#fff', icon: '🏢', filter: 'people' },
  Company: { bg: '#f59e0b', border: '#d97706', text: '#fff', icon: '🏛️', filter: 'people' },

  // Projects
  Project: { bg: '#8b5cf6', border: '#7c3aed', text: '#fff', icon: '📁', filter: 'projects' },
  Task: { bg: '#f59e0b', border: '#d97706', text: '#fff', icon: '✅', filter: 'projects' },
  Goal: { bg: '#06b6d4', border: '#0891b2', text: '#fff', icon: '🎯', filter: 'projects' },

  // Research
  Insight: { bg: '#06b6d4', border: '#0891b2', text: '#fff', icon: '💡', filter: 'research' },
  Document: { bg: '#84cc16', border: '#65a30d', text: '#fff', icon: '📄', filter: 'documents' },
  Chunk: { bg: '#a3e635', border: '#84cc16', text: '#333', icon: '📝', filter: 'documents' },

  Unknown: { bg: '#6b7280', border: '#4b5563', text: '#fff', icon: '📌', filter: 'other' },
}

// Available filters
const FILTERS = [
  { id: 'all', label: 'All', icon: '🌐' },
  { id: 'identity', label: 'Identity', icon: '🤖' },
  { id: 'people', label: 'People', icon: '👥' },
  { id: 'projects', label: 'Projects', icon: '📁' },
  { id: 'research', label: 'Research', icon: '🔬' },
  { id: 'documents', label: 'Documents', icon: '📄' },
]

// Relationship colors
const REL_COLORS = {
  KNOWS: '#3b82f6',
  FAMILY: '#ec4899',
  WORKS_WITH: '#8b5cf6',
  WORKS_ON: '#8b5cf6',
  HAS_TRAIT: '#a855f7',
  HAS_MEMORY: '#f472b6',
  LEARNED_PREFERENCE: '#14b8a6',
  OWNS: '#f59e0b',
  CONTAINS: '#84cc16',
  default: '#94a3b8',
}

// Custom node component
function GraphNode({ data, selected }) {
  const config = NODE_CONFIG[data.type] || NODE_CONFIG.Unknown

  return (
    <div
      className={`px-4 py-3 rounded-xl shadow-lg border-2 min-w-[120px] max-w-[200px] text-center cursor-pointer transition-all ${
        selected ? 'ring-2 ring-offset-2 ring-purple-500 scale-105' : ''
      }`}
      style={{ backgroundColor: config.bg, borderColor: config.border, color: config.text }}
    >
      <Handle type="target" position={Position.Top} className="!bg-white !w-2 !h-2" />
      <Handle type="source" position={Position.Bottom} className="!bg-white !w-2 !h-2" />
      <Handle type="target" position={Position.Left} id="left" className="!bg-white !w-2 !h-2" />
      <Handle type="source" position={Position.Right} id="right" className="!bg-white !w-2 !h-2" />

      <div className="text-xl mb-1">{config.icon}</div>
      <div className="text-xs opacity-80 mb-0.5">{data.type}</div>
      <div className="font-bold text-sm truncate">{data.label}</div>
      {data.subtitle && <div className="text-xs opacity-70 mt-1 truncate">{data.subtitle}</div>}
    </div>
  )
}

const nodeTypes = { graphNode: GraphNode }

// Layout nodes in circular pattern
function layoutGraph(nodes, edges) {
  const centerX = 500
  const centerY = 400

  // Find center node (User or Persona)
  const center = nodes.find(n => n.type === 'User') || nodes.find(n => n.type === 'Persona') || nodes[0]
  if (!center) return []

  const directlyConnected = new Set()
  edges.forEach(edge => {
    if (edge.source === center.id) directlyConnected.add(edge.target)
    if (edge.target === center.id) directlyConnected.add(edge.source)
  })

  const connectedNodes = nodes.filter(n => n.id !== center.id && directlyConnected.has(n.id))
  const otherNodes = nodes.filter(n => n.id !== center.id && !directlyConnected.has(n.id))

  const layoutedNodes = [{
    id: center.id,
    type: 'graphNode',
    position: { x: centerX - 60, y: centerY - 40 },
    data: {
      type: center.type,
      label: center.name || center.label || center.type,
      subtitle: center.tagline || center.description?.slice(0, 30),
    },
  }]

  // Inner circle
  connectedNodes.forEach((node, i) => {
    const angle = (2 * Math.PI * i) / Math.max(connectedNodes.length, 1) - Math.PI / 2
    layoutedNodes.push({
      id: node.id,
      type: 'graphNode',
      position: { x: centerX + 220 * Math.cos(angle) - 60, y: centerY + 220 * Math.sin(angle) - 40 },
      data: {
        type: node.type,
        label: node.name || node.label || node.type,
        subtitle: node.strength ? `Strength: ${node.strength}` : node.content?.slice(0, 30),
      },
    })
  })

  // Outer circle
  otherNodes.forEach((node, i) => {
    const angle = (2 * Math.PI * i) / Math.max(otherNodes.length, 1) - Math.PI / 4
    layoutedNodes.push({
      id: node.id,
      type: 'graphNode',
      position: { x: centerX + 380 * Math.cos(angle) - 60, y: centerY + 380 * Math.sin(angle) - 40 },
      data: {
        type: node.type,
        label: node.name || node.label || node.type,
        subtitle: node.description?.slice(0, 30),
      },
    })
  })

  return layoutedNodes
}

function formatEdges(edges) {
  return edges.map(edge => ({
    id: `${edge.source}-${edge.target}-${edge.type || 'rel'}`,
    source: edge.source,
    target: edge.target,
    type: 'smoothstep',
    animated: edge.type === 'HAS_MEMORY' || edge.type === 'WORKS_ON',
    label: edge.type?.replace(/_/g, ' '),
    labelStyle: { fontSize: 10, fill: '#666' },
    labelBgStyle: { fill: 'white', fillOpacity: 0.8 },
    style: { stroke: REL_COLORS[edge.type] || REL_COLORS.default, strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: REL_COLORS[edge.type] || REL_COLORS.default },
  }))
}

// Detail panel
function NodeDetail({ node, onClose }) {
  if (!node) return null
  const config = NODE_CONFIG[node.type] || NODE_CONFIG.Unknown

  return (
    <div className="h-full flex flex-col">
      <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{config.icon}</span>
          <div>
            <h3 className="font-bold text-lg text-gray-900 dark:text-white">{node.name || node.label || node.type}</h3>
            <span className="text-sm text-gray-500">{node.type}</span>
          </div>
        </div>
        <button onClick={onClose} className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div className="flex-1 overflow-auto p-4 space-y-4 text-sm">
        {node.tagline && <Field label="Tagline" value={node.tagline} />}
        {node.description && <Field label="Description" value={node.description} />}
        {node.content && <Field label="Content" value={node.content} />}
        {node.personality_summary && <Field label="Personality" value={node.personality_summary} />}
        {node.core_values?.length > 0 && (
          <div>
            <Label>Core Values</Label>
            <div className="flex flex-wrap gap-1">
              {node.core_values.map((v, i) => (
                <span key={i} className="px-2 py-0.5 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 text-xs rounded-full">{v}</span>
              ))}
            </div>
          </div>
        )}
        {node.quirks?.length > 0 && (
          <div>
            <Label>Quirks</Label>
            <ul className="space-y-1 text-gray-700 dark:text-gray-300">
              {node.quirks.slice(0, 5).map((q, i) => <li key={i} className="flex gap-2"><span className="text-purple-500">•</span>{q}</li>)}
            </ul>
          </div>
        )}
        {node.strength && <ProgressField label="Strength" value={node.strength} color="purple" />}
        {node.confidence && <ProgressField label="Confidence" value={node.confidence} color="green" />}
        {node.created_at && <Field label="Created" value={new Date(node.created_at).toLocaleDateString()} />}
      </div>
    </div>
  )
}

const Label = ({ children }) => <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase mb-1">{children}</h4>
const Field = ({ label, value }) => <div><Label>{label}</Label><p className="text-gray-900 dark:text-white">{value}</p></div>
const ProgressField = ({ label, value, color }) => (
  <div>
    <Label>{label}</Label>
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
        <div className={`bg-${color}-500 h-2 rounded-full`} style={{ width: `${value * 100}%` }} />
      </div>
      <span className="text-gray-600 dark:text-gray-400">{value}</span>
    </div>
  </div>
)

export default function Graph() {
  const [searchParams, setSearchParams] = useSearchParams()
  const activeFilter = searchParams.get('filter') || 'all'

  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [rawNodes, setRawNodes] = useState([])
  const [rawEdges, setRawEdges] = useState([])
  const [selectedNode, setSelectedNode] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')

  useEffect(() => { fetchGraph() }, [])

  const fetchGraph = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch('/api/cognitive/graph')
      const data = await response.json()
      if (data.success) {
        setRawNodes(data.nodes || [])
        setRawEdges(data.edges || [])
      } else {
        setError(data.error || 'Failed to load graph')
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

  const filteredData = useMemo(() => {
    let filteredNodes = rawNodes
    let filteredEdges = rawEdges

    if (activeFilter !== 'all') {
      filteredNodes = rawNodes.filter(n => {
        const config = NODE_CONFIG[n.type]
        return config?.filter === activeFilter
      })
      const nodeIds = new Set(filteredNodes.map(n => n.id))
      filteredEdges = rawEdges.filter(e => nodeIds.has(e.source) && nodeIds.has(e.target))
    }

    if (search.trim()) {
      const q = search.toLowerCase()
      filteredNodes = filteredNodes.filter(n =>
        n.name?.toLowerCase().includes(q) ||
        n.label?.toLowerCase().includes(q) ||
        n.description?.toLowerCase().includes(q) ||
        n.content?.toLowerCase().includes(q) ||
        n.type?.toLowerCase().includes(q)
      )
      const nodeIds = new Set(filteredNodes.map(n => n.id))
      filteredEdges = filteredEdges.filter(e => nodeIds.has(e.source) && nodeIds.has(e.target))
    }

    return { nodes: filteredNodes, edges: filteredEdges }
  }, [rawNodes, rawEdges, activeFilter, search])

  useEffect(() => {
    setNodes(layoutGraph(filteredData.nodes, filteredData.edges))
    setEdges(formatEdges(filteredData.edges))
  }, [filteredData])

  const onNodeClick = useCallback((_, node) => {
    setSelectedNode(rawNodes.find(n => n.id === node.id))
  }, [rawNodes])

  const nodeCounts = useMemo(() => {
    const counts = { all: rawNodes.length }
    FILTERS.forEach(f => {
      if (f.id !== 'all') {
        counts[f.id] = rawNodes.filter(n => NODE_CONFIG[n.type]?.filter === f.id).length
      }
    })
    return counts
  }, [rawNodes])

  return (
    <div className="h-screen flex flex-col bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <span>🧠</span> Graph
            </h1>
            <div className="relative">
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search..."
                className="pl-8 pr-4 py-1.5 bg-gray-100 dark:bg-gray-700 border-0 rounded-lg text-sm w-64 focus:ring-2 focus:ring-purple-500"
              />
              <svg className="w-4 h-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {FILTERS.map(f => (
              <button
                key={f.id}
                onClick={() => setFilter(f.id)}
                className={`px-3 py-1.5 rounded-full text-sm font-medium flex items-center gap-1.5 transition-colors ${
                  activeFilter === f.id
                    ? 'bg-purple-500 text-white'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200'
                }`}
              >
                <span>{f.icon}</span>
                <span>{f.label}</span>
                <span className={`text-xs px-1.5 py-0.5 rounded-full ${activeFilter === f.id ? 'bg-white/20' : 'bg-gray-200 dark:bg-gray-600'}`}>
                  {nodeCounts[f.id] || 0}
                </span>
              </button>
            ))}
            <button onClick={fetchGraph} disabled={loading} className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg" title="Refresh">
              <svg className={`w-5 h-5 text-gray-600 dark:text-gray-400 ${loading ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
          </div>
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {loading ? (
          <div className="h-full flex items-center justify-center">
            <div className="w-12 h-12 border-4 border-purple-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : error ? (
          <div className="h-full flex items-center justify-center flex-col gap-4">
            <p className="text-red-500">{error}</p>
            <button onClick={fetchGraph} className="px-4 py-2 bg-purple-500 text-white rounded-lg">Retry</button>
          </div>
        ) : (
          <PanelGroup direction="horizontal">
            <Panel defaultSize={selectedNode ? 70 : 100} minSize={50}>
              <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onNodeClick={onNodeClick}
                nodeTypes={nodeTypes}
                fitView
                fitViewOptions={{ padding: 0.2 }}
                minZoom={0.2}
                maxZoom={2}
              >
                <Background color="#ddd" gap={20} />
                <Controls />
                <MiniMap nodeColor={(n) => (NODE_CONFIG[n.data?.type] || NODE_CONFIG.Unknown).bg} maskColor="rgba(0,0,0,0.1)" />
              </ReactFlow>
            </Panel>
            {selectedNode && (
              <>
                <PanelResizeHandle className="w-1 bg-gray-200 dark:bg-gray-700 hover:bg-purple-500" />
                <Panel defaultSize={30} minSize={20} maxSize={50}>
                  <div className="h-full bg-white dark:bg-gray-800 border-l border-gray-200 dark:border-gray-700">
                    <NodeDetail node={selectedNode} onClose={() => setSelectedNode(null)} />
                  </div>
                </Panel>
              </>
            )}
          </PanelGroup>
        )}
      </div>

      {/* Footer */}
      <footer className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 px-4 py-2 text-sm text-gray-500">
        <div className="flex items-center justify-between">
          <span>{filteredData.nodes.length} nodes · {filteredData.edges.length} relationships</span>
          {activeFilter !== 'all' && (
            <button onClick={() => setFilter('all')} className="text-purple-500 hover:text-purple-600">Clear filter</button>
          )}
        </div>
      </footer>
    </div>
  )
}
