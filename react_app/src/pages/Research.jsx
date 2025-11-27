import { useState, useCallback, useEffect, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels'
import ReactFlow, {
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  MarkerType,
  Position,
  Handle,
} from 'reactflow'
import 'reactflow/dist/style.css'

// Demo data for when Neo4j is unavailable
const DEMO_NODES = [
  { id: '1', type: 'Topic', name: 'AI Agents', description: 'Autonomous AI systems that can perform tasks' },
  { id: '2', type: 'Topic', name: 'LLMs', description: 'Large Language Models like GPT, Claude' },
  { id: '3', type: 'Person', name: 'Sam Altman', description: 'CEO of OpenAI' },
  { id: '4', type: 'Organization', name: 'Anthropic', description: 'AI safety company, creators of Claude' },
  { id: '5', type: 'Article', name: 'Building AI Agents', description: 'How to build autonomous agents with LLMs' },
  { id: '6', type: 'Tag', name: 'machine-learning', description: '' },
  { id: '7', type: 'Tag', name: 'automation', description: '' },
]

const DEMO_EDGES = [
  { id: 'e1-2', source: '1', target: '2', type: 'RELATED_TO' },
  { id: 'e1-5', source: '1', target: '5', type: 'ABOUT_TOPIC' },
  { id: 'e2-4', source: '2', target: '4', type: 'DEVELOPED_BY' },
  { id: 'e3-4', source: '3', target: '4', type: 'WORKS_AT' },
  { id: 'e5-6', source: '5', target: '6', type: 'TAGGED' },
  { id: 'e5-7', source: '5', target: '7', type: 'TAGGED' },
]

// Node type colors
const NODE_COLORS = {
  Topic: { bg: '#8b5cf6', border: '#7c3aed', text: '#fff' },
  Article: { bg: '#3b82f6', border: '#2563eb', text: '#fff' },
  Source: { bg: '#10b981', border: '#059669', text: '#fff' },
  Tag: { bg: '#f59e0b', border: '#d97706', text: '#fff' },
  Person: { bg: '#ec4899', border: '#db2777', text: '#fff' },
  Organization: { bg: '#6366f1', border: '#4f46e5', text: '#fff' },
  Note: { bg: '#64748b', border: '#475569', text: '#fff' },
}

// Custom node component with handles for edges
function CustomNode({ data }) {
  const colors = NODE_COLORS[data.type] || NODE_COLORS.Note
  return (
    <div
      className="px-4 py-2 rounded-lg shadow-lg border-2 min-w-[120px] text-center cursor-pointer transition-all hover:scale-105 relative"
      style={{
        backgroundColor: colors.bg,
        borderColor: colors.border,
        color: colors.text,
      }}
    >
      {/* Connection handles */}
      <Handle
        type="target"
        position={Position.Top}
        className="!bg-gray-400 !w-2 !h-2 !border-0"
      />
      <Handle
        type="source"
        position={Position.Bottom}
        className="!bg-gray-400 !w-2 !h-2 !border-0"
      />
      <Handle
        type="target"
        position={Position.Left}
        id="left"
        className="!bg-gray-400 !w-2 !h-2 !border-0"
      />
      <Handle
        type="source"
        position={Position.Right}
        id="right"
        className="!bg-gray-400 !w-2 !h-2 !border-0"
      />

      <div className="text-xs opacity-75 mb-1">{data.type}</div>
      <div className="font-semibold text-sm truncate max-w-[200px]">{data.label}</div>
      {data.description && (
        <div className="text-xs opacity-75 mt-1 truncate max-w-[200px]">{data.description}</div>
      )}
    </div>
  )
}

const nodeTypes = { custom: CustomNode }

// Layout helper using dagre-like positioning
function getLayoutedElements(nodes, edges) {
  const nodeWidth = 180
  const nodeHeight = 80
  const horizontalSpacing = 250
  const verticalSpacing = 150

  // Group nodes by type for better organization
  const nodesByType = {}
  nodes.forEach(node => {
    const type = node.data?.type || 'Other'
    if (!nodesByType[type]) nodesByType[type] = []
    nodesByType[type].push(node)
  })

  // Position nodes in a hierarchical layout
  let yOffset = 0
  const positionedNodes = []

  // Order: Topic first, then Articles, Sources, Tags, Others
  const typeOrder = ['Topic', 'Article', 'Source', 'Tag', 'Person', 'Organization', 'Note']
  const sortedTypes = Object.keys(nodesByType).sort((a, b) => {
    const aIndex = typeOrder.indexOf(a)
    const bIndex = typeOrder.indexOf(b)
    return (aIndex === -1 ? 999 : aIndex) - (bIndex === -1 ? 999 : bIndex)
  })

  sortedTypes.forEach(type => {
    const typeNodes = nodesByType[type]
    typeNodes.forEach((node, index) => {
      positionedNodes.push({
        ...node,
        position: {
          x: index * horizontalSpacing,
          y: yOffset,
        },
      })
    })
    yOffset += verticalSpacing
  })

  return { nodes: positionedNodes, edges }
}

function Research() {
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [selectedNode, setSelectedNode] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [researchInput, setResearchInput] = useState('')
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] })
  const [error, setError] = useState(null)
  const [isDemo, setIsDemo] = useState(false)

  // Convert raw data to React Flow format
  const convertToFlowFormat = useCallback((data) => {
    const flowNodes = (data.nodes || []).map((node, index) => ({
      id: String(node.id || `node-${index}`),
      type: 'custom',
      data: {
        label: node.name || node.title || 'Untitled',
        type: node.type || 'Note',
        description: node.description || node.summary || '',
        ...node,
      },
      position: { x: 0, y: 0 },
    }))

    const flowEdges = (data.edges || []).map((edge, index) => ({
      id: String(edge.id || `edge-${index}`),
      source: String(edge.source || edge.from),
      target: String(edge.target || edge.to),
      label: edge.type || edge.label || '',
      type: 'smoothstep',
      animated: edge.type === 'RESEARCHED',
      markerEnd: { type: MarkerType.ArrowClosed },
      style: { stroke: '#64748b' },
      labelStyle: { fontSize: 10, fill: '#64748b' },
    }))

    return { flowNodes, flowEdges }
  }, [])

  // Load demo data
  const loadDemoData = useCallback(() => {
    setIsDemo(true)
    const { flowNodes, flowEdges } = convertToFlowFormat({ nodes: DEMO_NODES, edges: DEMO_EDGES })
    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(flowNodes, flowEdges)
    setNodes(layoutedNodes)
    setEdges(layoutedEdges)
    setGraphData({ nodes: DEMO_NODES, edges: DEMO_EDGES })
  }, [convertToFlowFormat, setNodes, setEdges])

  // Fetch graph data from API
  const fetchGraphData = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await fetch('/api/research/graph')
      if (!response.ok) throw new Error('Failed to fetch graph data')
      const data = await response.json()

      // Check if there's an error in the response
      if (data.error) {
        console.warn('Neo4j error, loading demo data:', data.error)
        setError('Database temporarily unavailable. Showing demo data.')
        loadDemoData()
        return
      }

      setGraphData(data)
      setIsDemo(false)

      // If no data, load demo
      if (!data.nodes || data.nodes.length === 0) {
        loadDemoData()
        return
      }

      const { flowNodes, flowEdges } = convertToFlowFormat(data)
      const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(flowNodes, flowEdges)
      setNodes(layoutedNodes)
      setEdges(layoutedEdges)
    } catch (err) {
      console.error('Error fetching graph:', err)
      setError('Failed to load graph. Showing demo data.')
      loadDemoData()
    } finally {
      setIsLoading(false)
    }
  }, [setNodes, setEdges, convertToFlowFormat, loadDemoData])

  // Initial fetch
  useEffect(() => {
    fetchGraphData()
  }, [fetchGraphData])

  // Handle new connections
  const onConnect = useCallback(
    (params) => {
      setEdges((eds) =>
        addEdge(
          {
            ...params,
            type: 'smoothstep',
            markerEnd: { type: MarkerType.ArrowClosed },
          },
          eds
        )
      )
    },
    [setEdges]
  )

  // Handle node click
  const onNodeClick = useCallback((event, node) => {
    setSelectedNode(node)
  }, [])

  // Submit research query
  const handleResearch = async () => {
    if (!researchInput.trim()) return

    setIsLoading(true)
    setError(null)
    try {
      const response = await fetch('/api/research/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: researchInput }),
      })
      if (!response.ok) throw new Error('Research query failed')
      const result = await response.json()

      // Refresh graph after research
      await fetchGraphData()
      setResearchInput('')
    } catch (err) {
      console.error('Research error:', err)
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }

  // Filter nodes by search
  const filteredNodes = useMemo(() => {
    if (!searchQuery) return nodes
    return nodes.filter(
      (node) =>
        node.data.label?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        node.data.type?.toLowerCase().includes(searchQuery.toLowerCase())
    )
  }, [nodes, searchQuery])

  // Fit view when nodes change
  const onInit = useCallback((reactFlowInstance) => {
    reactFlowInstance.fitView({ padding: 0.2 })
  }, [])

  return (
    <div className="h-screen flex flex-col bg-gray-900">
      {/* Top toolbar */}
      <div className="bg-gray-800 border-b border-gray-700 px-4 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-4">
          <Link to="/" className="text-gray-400 hover:text-white transition-colors">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
          </Link>
          <span className="text-white font-semibold text-lg">Research</span>
          <span className="text-gray-400 text-sm">Knowledge Graph</span>
          {isDemo && (
            <span className="px-2 py-0.5 bg-amber-600/20 text-amber-400 text-xs rounded-full border border-amber-600/30">
              Demo Mode
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search nodes..."
            className="px-3 py-1.5 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 w-48"
          />
          <button
            onClick={fetchGraphData}
            disabled={isLoading}
            className="px-3 py-1.5 bg-gray-700 text-white rounded-lg hover:bg-gray-600 text-sm disabled:opacity-50"
          >
            {isLoading ? 'Loading...' : 'Refresh'}
          </button>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 overflow-hidden">
        <PanelGroup direction="horizontal">
          {/* Left sidebar - Research input */}
          <Panel defaultSize={25} minSize={20} maxSize={40}>
            <div className="h-full bg-gray-800 flex flex-col">
              {/* Research input section */}
              <div className="p-4 border-b border-gray-700">
                <h3 className="text-white font-medium mb-3">New Research</h3>
                <textarea
                  value={researchInput}
                  onChange={(e) => setResearchInput(e.target.value)}
                  placeholder="Enter a topic to research...&#10;&#10;Examples:&#10;- Machine learning frameworks&#10;- Climate change impacts&#10;- Startup funding strategies"
                  className="w-full h-32 px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm resize-none focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
                <button
                  onClick={handleResearch}
                  disabled={isLoading || !researchInput.trim()}
                  className="mt-3 w-full px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                >
                  {isLoading ? 'Researching...' : 'Start Research'}
                </button>
              </div>

              {/* Node types legend */}
              <div className="p-4 border-b border-gray-700">
                <h3 className="text-white font-medium mb-3">Node Types</h3>
                <div className="grid grid-cols-2 gap-2">
                  {Object.entries(NODE_COLORS).map(([type, colors]) => (
                    <div key={type} className="flex items-center gap-2">
                      <div
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: colors.bg }}
                      />
                      <span className="text-gray-300 text-xs">{type}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Stats */}
              <div className="p-4 border-b border-gray-700">
                <h3 className="text-white font-medium mb-3">Graph Stats</h3>
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-gray-700 rounded-lg p-3 text-center">
                    <div className="text-2xl font-bold text-purple-400">{nodes.length}</div>
                    <div className="text-gray-400 text-xs">Nodes</div>
                  </div>
                  <div className="bg-gray-700 rounded-lg p-3 text-center">
                    <div className="text-2xl font-bold text-blue-400">{edges.length}</div>
                    <div className="text-gray-400 text-xs">Connections</div>
                  </div>
                </div>
              </div>

              {/* Selected node details */}
              {selectedNode && (
                <div className="p-4 flex-1 overflow-y-auto">
                  <h3 className="text-white font-medium mb-3">Selected Node</h3>
                  <div className="bg-gray-700 rounded-lg p-3">
                    <div className="text-xs text-gray-400 mb-1">{selectedNode.data.type}</div>
                    <div className="text-white font-medium mb-2">{selectedNode.data.label}</div>
                    {selectedNode.data.description && (
                      <p className="text-gray-300 text-sm mb-3">{selectedNode.data.description}</p>
                    )}
                    {selectedNode.data.url && (
                      <a
                        href={selectedNode.data.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-purple-400 text-sm hover:underline block mb-2"
                      >
                        View Source
                      </a>
                    )}
                    {selectedNode.data.created_at && (
                      <div className="text-gray-400 text-xs">
                        Added: {new Date(selectedNode.data.created_at).toLocaleDateString()}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Error display */}
              {error && (
                <div className="p-4">
                  <div className="bg-red-900/50 border border-red-700 rounded-lg p-3">
                    <p className="text-red-300 text-sm">{error}</p>
                  </div>
                </div>
              )}
            </div>
          </Panel>

          <PanelResizeHandle className="w-1 bg-gray-700 hover:bg-purple-500 transition-colors cursor-col-resize" />

          {/* Main graph view */}
          <Panel defaultSize={75} minSize={50}>
            <div className="h-full w-full bg-gray-900" style={{ minHeight: '400px' }}>
              {isLoading && nodes.length === 0 ? (
                <div className="h-full flex items-center justify-center">
                  <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500 mx-auto mb-4"></div>
                    <p className="text-gray-400">Loading knowledge graph...</p>
                  </div>
                </div>
              ) : nodes.length === 0 ? (
                <div className="h-full flex items-center justify-center">
                  <div className="text-center max-w-md">
                    <div className="text-6xl mb-4">🔬</div>
                    <h2 className="text-xl font-semibold text-white mb-2">No Research Yet</h2>
                    <p className="text-gray-400 mb-6">
                      Start by entering a research topic on the left. The AI will find related
                      articles, extract entities, and build your knowledge graph.
                    </p>
                    <div className="bg-gray-800 rounded-lg p-4 text-left">
                      <p className="text-gray-300 text-sm mb-2">Try researching:</p>
                      <ul className="text-gray-400 text-sm space-y-1">
                        <li>• "Latest developments in AI agents"</li>
                        <li>• "Sustainable energy solutions"</li>
                        <li>• "Remote work productivity tips"</li>
                      </ul>
                    </div>
                  </div>
                </div>
              ) : (
                <ReactFlow
                  nodes={searchQuery ? filteredNodes : nodes}
                  edges={edges}
                  onNodesChange={onNodesChange}
                  onEdgesChange={onEdgesChange}
                  onConnect={onConnect}
                  onNodeClick={onNodeClick}
                  onInit={onInit}
                  nodeTypes={nodeTypes}
                  fitView
                  minZoom={0.1}
                  maxZoom={2}
                  defaultEdgeOptions={{
                    type: 'smoothstep',
                    markerEnd: { type: MarkerType.ArrowClosed },
                  }}
                >
                  <Background color="#374151" gap={20} />
                  <Controls className="bg-gray-800 border-gray-700" />
                  <MiniMap
                    nodeColor={(node) => NODE_COLORS[node.data?.type]?.bg || '#64748b'}
                    className="bg-gray-800 border-gray-700"
                    maskColor="rgba(0, 0, 0, 0.7)"
                  />
                </ReactFlow>
              )}
            </div>
          </Panel>
        </PanelGroup>
      </div>
    </div>
  )
}

export default Research
