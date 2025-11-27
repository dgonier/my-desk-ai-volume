import { useState, useCallback, useEffect, useMemo } from 'react'
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

// Node type configuration - colors, icons, and display settings
const NODE_CONFIG = {
  // Core identity
  User: { bg: '#10b981', border: '#059669', text: '#fff', icon: '👤', category: 'identity' },
  Persona: { bg: '#8b5cf6', border: '#7c3aed', text: '#fff', icon: '🤖', category: 'identity' },

  // People & Organizations
  Person: { bg: '#3b82f6', border: '#2563eb', text: '#fff', icon: '🧑', category: 'people' },
  Organization: { bg: '#ec4899', border: '#db2777', text: '#fff', icon: '🏢', category: 'people' },
  Company: { bg: '#f59e0b', border: '#d97706', text: '#fff', icon: '🏛️', category: 'people' },

  // Work & Projects
  Project: { bg: '#8b5cf6', border: '#7c3aed', text: '#fff', icon: '📁', category: 'projects' },
  Task: { bg: '#f59e0b', border: '#d97706', text: '#fff', icon: '✅', category: 'projects' },
  Goal: { bg: '#06b6d4', border: '#0891b2', text: '#fff', icon: '🎯', category: 'projects' },

  // Knowledge & Research
  Insight: { bg: '#06b6d4', border: '#0891b2', text: '#fff', icon: '💡', category: 'research' },
  Document: { bg: '#84cc16', border: '#65a30d', text: '#fff', icon: '📄', category: 'research' },
  Memory: { bg: '#f472b6', border: '#ec4899', text: '#fff', icon: '🧠', category: 'research' },

  // Persona traits
  Trait: { bg: '#a855f7', border: '#9333ea', text: '#fff', icon: '✨', category: 'identity' },
  Preference: { bg: '#14b8a6', border: '#0d9488', text: '#fff', icon: '⚙️', category: 'identity' },

  // Default
  Unknown: { bg: '#6b7280', border: '#4b5563', text: '#fff', icon: '📌', category: 'other' },
}

// Filter categories
const FILTER_CATEGORIES = [
  { id: 'all', label: 'All Nodes', icon: '🌐' },
  { id: 'identity', label: 'Identity', icon: '🤖', types: ['User', 'Persona', 'Trait', 'Preference', 'Memory'] },
  { id: 'people', label: 'People', icon: '👥', types: ['Person', 'Organization', 'Company'] },
  { id: 'projects', label: 'Projects', icon: '📁', types: ['Project', 'Task', 'Goal'] },
  { id: 'research', label: 'Research', icon: '🔬', types: ['Insight', 'Document'] },
]

// Relationship colors
const REL_COLORS = {
  // People relationships
  KNOWS: '#3b82f6',
  FAMILY: '#ec4899',
  WORKS_WITH: '#8b5cf6',
  FRIEND: '#10b981',
  CONTACTED: '#6b7280',

  // Project relationships
  WORKS_ON: '#8b5cf6',
  OWNS: '#f59e0b',
  ASSIGNED_TO: '#06b6d4',

  // Persona relationships
  HAS_TRAIT: '#a855f7',
  HAS_MEMORY: '#f472b6',
  LEARNED_PREFERENCE: '#14b8a6',

  default: '#94a3b8',
}

// Custom node component
function GraphNode({ data, selected }) {
  const config = NODE_CONFIG[data.type] || NODE_CONFIG.Unknown

  return (
    <div
      className={`px-4 py-3 rounded-xl shadow-lg border-2 min-w-[120px] max-w-[200px] text-center cursor-pointer transition-all ${
        selected ? 'ring-2 ring-offset-2 ring-purple-500 scale-105' : 'hover:scale-102'
      }`}
      style={{
        backgroundColor: config.bg,
        borderColor: config.border,
        color: config.text,
      }}
    >
      <Handle type="target" position={Position.Top} className="!bg-white !w-2 !h-2" />
      <Handle type="source" position={Position.Bottom} className="!bg-white !w-2 !h-2" />
      <Handle type="target" position={Position.Left} id="left" className="!bg-white !w-2 !h-2" />
      <Handle type="source" position={Position.Right} id="right" className="!bg-white !w-2 !h-2" />

      <div className="text-xl mb-1">{config.icon}</div>
      <div className="text-xs opacity-80 mb-0.5">{data.type}</div>
      <div className="font-bold text-sm truncate">{data.label}</div>
      {data.subtitle && (
        <div className="text-xs opacity-70 mt-1 truncate">{data.subtitle}</div>
      )}
    </div>
  )
}

const nodeTypes = { graphNode: GraphNode }

// Layout nodes using force-directed-like positioning
function layoutGraph(nodes, edges, centerNode = null) {
  const layoutedNodes = []
  const centerX = 500
  const centerY = 400

  // Find center node (User or Persona)
  const center = centerNode || nodes.find(n => n.type === 'User') || nodes.find(n => n.type === 'Persona') || nodes[0]

  if (!center) return []

  // Group nodes by their connection to center
  const directlyConnected = new Set()
  edges.forEach(edge => {
    if (edge.source === center.id) directlyConnected.add(edge.target)
    if (edge.target === center.id) directlyConnected.add(edge.source)
  })

  const connectedNodes = nodes.filter(n => n.id !== center.id && directlyConnected.has(n.id))
  const otherNodes = nodes.filter(n => n.id !== center.id && !directlyConnected.has(n.id))

  // Position center node
  layoutedNodes.push({
    id: center.id,
    type: 'graphNode',
    position: { x: centerX - 60, y: centerY - 40 },
    data: {
      type: center.type,
      label: center.name || center.label || center.type,
      subtitle: center.tagline || center.description?.slice(0, 30),
    },
  })

  // Position directly connected nodes in inner circle
  const innerRadius = 220
  connectedNodes.forEach((node, i) => {
    const angle = (2 * Math.PI * i) / Math.max(connectedNodes.length, 1) - Math.PI / 2
    layoutedNodes.push({
      id: node.id,
      type: 'graphNode',
      position: {
        x: centerX + innerRadius * Math.cos(angle) - 60,
        y: centerY + innerRadius * Math.sin(angle) - 40,
      },
      data: {
        type: node.type,
        label: node.name || node.label || node.type,
        subtitle: node.strength ? `Strength: ${node.strength}` : node.content?.slice(0, 30),
      },
    })
  })

  // Position other nodes in outer circle
  const outerRadius = 380
  otherNodes.forEach((node, i) => {
    const angle = (2 * Math.PI * i) / Math.max(otherNodes.length, 1) - Math.PI / 4
    layoutedNodes.push({
      id: node.id,
      type: 'graphNode',
      position: {
        x: centerX + outerRadius * Math.cos(angle) - 60,
        y: centerY + outerRadius * Math.sin(angle) - 40,
      },
      data: {
        type: node.type,
        label: node.name || node.label || node.type,
        subtitle: node.description?.slice(0, 30),
      },
    })
  })

  return layoutedNodes
}

// Format edges for ReactFlow
function formatEdges(edges) {
  return edges.map(edge => ({
    id: `${edge.source}-${edge.target}-${edge.type || 'rel'}`,
    source: edge.source,
    target: edge.target,
    type: 'smoothstep',
    animated: edge.type === 'WORKS_ON' || edge.type === 'HAS_MEMORY',
    label: edge.type?.replace(/_/g, ' '),
    labelStyle: { fontSize: 10, fill: '#666' },
    labelBgStyle: { fill: 'white', fillOpacity: 0.8 },
    style: {
      stroke: REL_COLORS[edge.type] || REL_COLORS.default,
      strokeWidth: 2,
    },
    markerEnd: {
      type: MarkerType.ArrowClosed,
      color: REL_COLORS[edge.type] || REL_COLORS.default,
    },
  }))
}

// Detail panel for selected node
function NodeDetailPanel({ node, onClose }) {
  if (!node) return null

  const config = NODE_CONFIG[node.type] || NODE_CONFIG.Unknown

  return (
    <div className="h-full flex flex-col">
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">{config.icon}</span>
            <div>
              <h3 className="font-bold text-lg text-gray-900 dark:text-white">
                {node.name || node.label || node.type}
              </h3>
              <span className="text-sm text-gray-500 dark:text-gray-400">{node.type}</span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-4 space-y-4">
        {/* Properties */}
        {node.tagline && (
          <div>
            <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase mb-1">Tagline</h4>
            <p className="text-gray-900 dark:text-white">{node.tagline}</p>
          </div>
        )}

        {node.description && (
          <div>
            <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase mb-1">Description</h4>
            <p className="text-gray-700 dark:text-gray-300 text-sm">{node.description}</p>
          </div>
        )}

        {node.content && (
          <div>
            <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase mb-1">Content</h4>
            <p className="text-gray-700 dark:text-gray-300 text-sm">{node.content}</p>
          </div>
        )}

        {node.personality_summary && (
          <div>
            <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase mb-1">Personality</h4>
            <p className="text-gray-700 dark:text-gray-300 text-sm">{node.personality_summary}</p>
          </div>
        )}

        {node.core_values && node.core_values.length > 0 && (
          <div>
            <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase mb-1">Core Values</h4>
            <div className="flex flex-wrap gap-1">
              {node.core_values.map((v, i) => (
                <span key={i} className="px-2 py-0.5 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 text-xs rounded-full">
                  {v}
                </span>
              ))}
            </div>
          </div>
        )}

        {node.quirks && node.quirks.length > 0 && (
          <div>
            <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase mb-1">Quirks</h4>
            <ul className="text-sm text-gray-700 dark:text-gray-300 space-y-1">
              {node.quirks.slice(0, 5).map((q, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="text-purple-500">•</span>
                  <span>{q}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {node.strength && (
          <div>
            <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase mb-1">Strength</h4>
            <div className="flex items-center gap-2">
              <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                <div
                  className="bg-purple-500 h-2 rounded-full"
                  style={{ width: `${node.strength * 100}%` }}
                />
              </div>
              <span className="text-sm text-gray-600 dark:text-gray-400">{node.strength}</span>
            </div>
          </div>
        )}

        {node.confidence && (
          <div>
            <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase mb-1">Confidence</h4>
            <div className="flex items-center gap-2">
              <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                <div
                  className="bg-green-500 h-2 rounded-full"
                  style={{ width: `${node.confidence * 100}%` }}
                />
              </div>
              <span className="text-sm text-gray-600 dark:text-gray-400">{node.confidence}</span>
            </div>
          </div>
        )}

        {node.created_at && (
          <div>
            <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase mb-1">Created</h4>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {new Date(node.created_at).toLocaleDateString()}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

export default function CognitiveGraph() {
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [rawNodes, setRawNodes] = useState([])
  const [rawEdges, setRawEdges] = useState([])
  const [selectedNode, setSelectedNode] = useState(null)
  const [activeFilter, setActiveFilter] = useState('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')

  // Fetch graph data
  useEffect(() => {
    fetchGraphData()
  }, [])

  const fetchGraphData = async () => {
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

  // Filter nodes based on active filter and search
  const filteredData = useMemo(() => {
    let filteredNodes = rawNodes
    let filteredEdges = rawEdges

    // Apply category filter
    if (activeFilter !== 'all') {
      const filterConfig = FILTER_CATEGORIES.find(f => f.id === activeFilter)
      if (filterConfig?.types) {
        const allowedTypes = new Set(filterConfig.types)
        filteredNodes = rawNodes.filter(n => allowedTypes.has(n.type))

        // Filter edges to only include those between filtered nodes
        const nodeIds = new Set(filteredNodes.map(n => n.id))
        filteredEdges = rawEdges.filter(e => nodeIds.has(e.source) && nodeIds.has(e.target))
      }
    }

    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      filteredNodes = filteredNodes.filter(n =>
        (n.name && n.name.toLowerCase().includes(query)) ||
        (n.label && n.label.toLowerCase().includes(query)) ||
        (n.description && n.description.toLowerCase().includes(query)) ||
        (n.content && n.content.toLowerCase().includes(query)) ||
        (n.type && n.type.toLowerCase().includes(query))
      )
      const nodeIds = new Set(filteredNodes.map(n => n.id))
      filteredEdges = filteredEdges.filter(e => nodeIds.has(e.source) && nodeIds.has(e.target))
    }

    return { nodes: filteredNodes, edges: filteredEdges }
  }, [rawNodes, rawEdges, activeFilter, searchQuery])

  // Layout and set nodes when filtered data changes
  useEffect(() => {
    const layoutedNodes = layoutGraph(filteredData.nodes, filteredData.edges)
    const formattedEdges = formatEdges(filteredData.edges)
    setNodes(layoutedNodes)
    setEdges(formattedEdges)
  }, [filteredData])

  // Handle node click
  const onNodeClick = useCallback((event, node) => {
    const rawNode = rawNodes.find(n => n.id === node.id)
    setSelectedNode(rawNode)
  }, [rawNodes])

  // Node counts by category
  const nodeCounts = useMemo(() => {
    const counts = { all: rawNodes.length }
    FILTER_CATEGORIES.forEach(cat => {
      if (cat.types) {
        counts[cat.id] = rawNodes.filter(n => cat.types.includes(n.type)).length
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
              <span>🧠</span> Cognitive Graph
            </h1>

            {/* Search */}
            <div className="relative">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search nodes..."
                className="pl-8 pr-4 py-1.5 bg-gray-100 dark:bg-gray-700 border-0 rounded-lg text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-purple-500 w-64"
              />
              <svg className="w-4 h-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
          </div>

          {/* Filter pills */}
          <div className="flex items-center gap-2">
            {FILTER_CATEGORIES.map(filter => (
              <button
                key={filter.id}
                onClick={() => setActiveFilter(filter.id)}
                className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors flex items-center gap-1.5 ${
                  activeFilter === filter.id
                    ? 'bg-purple-500 text-white'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                }`}
              >
                <span>{filter.icon}</span>
                <span>{filter.label}</span>
                <span className={`text-xs px-1.5 py-0.5 rounded-full ${
                  activeFilter === filter.id
                    ? 'bg-white/20'
                    : 'bg-gray-200 dark:bg-gray-600'
                }`}>
                  {nodeCounts[filter.id] || 0}
                </span>
              </button>
            ))}

            {/* Refresh button */}
            <button
              onClick={fetchGraphData}
              disabled={loading}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              title="Refresh"
            >
              <svg className={`w-5 h-5 text-gray-600 dark:text-gray-400 ${loading ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
          </div>
        </div>
      </header>

      {/* Main content */}
      <div className="flex-1 overflow-hidden">
        {loading ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <div className="w-12 h-12 border-4 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
              <p className="text-gray-500 dark:text-gray-400">Loading cognitive graph...</p>
            </div>
          </div>
        ) : error ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <p className="text-red-500 mb-4">{error}</p>
              <button
                onClick={fetchGraphData}
                className="px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600"
              >
                Retry
              </button>
            </div>
          </div>
        ) : (
          <PanelGroup direction="horizontal">
            {/* Graph panel */}
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
                <MiniMap
                  nodeColor={(node) => {
                    const config = NODE_CONFIG[node.data?.type] || NODE_CONFIG.Unknown
                    return config.bg
                  }}
                  maskColor="rgba(0,0,0,0.1)"
                />
              </ReactFlow>
            </Panel>

            {/* Detail panel */}
            {selectedNode && (
              <>
                <PanelResizeHandle className="w-1 bg-gray-200 dark:bg-gray-700 hover:bg-purple-500 transition-colors" />
                <Panel defaultSize={30} minSize={20} maxSize={50}>
                  <div className="h-full bg-white dark:bg-gray-800 border-l border-gray-200 dark:border-gray-700">
                    <NodeDetailPanel
                      node={selectedNode}
                      onClose={() => setSelectedNode(null)}
                    />
                  </div>
                </Panel>
              </>
            )}
          </PanelGroup>
        )}
      </div>

      {/* Stats footer */}
      <footer className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 px-4 py-2">
        <div className="flex items-center justify-between text-sm text-gray-500 dark:text-gray-400">
          <div className="flex items-center gap-4">
            <span>{filteredData.nodes.length} nodes</span>
            <span>{filteredData.edges.length} relationships</span>
          </div>
          <div className="flex items-center gap-2">
            {activeFilter !== 'all' && (
              <button
                onClick={() => setActiveFilter('all')}
                className="text-purple-500 hover:text-purple-600"
              >
                Clear filter
              </button>
            )}
          </div>
        </div>
      </footer>
    </div>
  )
}
