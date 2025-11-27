import { useState, useCallback, useEffect, useMemo } from 'react'
import { Link } from 'react-router-dom'
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

// Node type colors
const NODE_COLORS = {
  User: { bg: '#10b981', border: '#059669', text: '#fff' },
  Person: { bg: '#3b82f6', border: '#2563eb', text: '#fff' },
  Company: { bg: '#f59e0b', border: '#d97706', text: '#fff' },
  Organization: { bg: '#8b5cf6', border: '#7c3aed', text: '#fff' },
  Insight: { bg: '#06b6d4', border: '#0891b2', text: '#fff' },
  Unknown: { bg: '#6b7280', border: '#4b5563', text: '#fff' },
}

// Relationship type colors
const REL_COLORS = {
  KNOWS: '#3b82f6',
  FAMILY: '#ec4899',
  WORKS_WITH: '#8b5cf6',
  FRIEND: '#10b981',
  CONTACTED: '#6b7280',
  default: '#94a3b8',
}

// Custom node component
function PersonNode({ data, selected }) {
  const colors = NODE_COLORS[data.type] || NODE_COLORS.Unknown
  return (
    <div
      className={`px-4 py-3 rounded-xl shadow-lg border-2 min-w-[140px] text-center cursor-pointer transition-all ${
        selected ? 'ring-2 ring-offset-2 ring-blue-500' : ''
      }`}
      style={{
        backgroundColor: colors.bg,
        borderColor: colors.border,
        color: colors.text,
      }}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!bg-white !w-3 !h-3 !border-2 !border-gray-400"
      />
      <Handle
        type="source"
        position={Position.Bottom}
        className="!bg-white !w-3 !h-3 !border-2 !border-gray-400"
      />
      <Handle
        type="target"
        position={Position.Left}
        id="left"
        className="!bg-white !w-3 !h-3 !border-2 !border-gray-400"
      />
      <Handle
        type="source"
        position={Position.Right}
        id="right"
        className="!bg-white !w-3 !h-3 !border-2 !border-gray-400"
      />

      <div className="text-xs opacity-80 mb-1 font-medium">{data.type}</div>
      <div className="font-bold text-base">{data.label}</div>
      {data.relationship && (
        <div className="text-xs opacity-80 mt-1 bg-white/20 rounded px-2 py-0.5">
          {data.relationship}
        </div>
      )}
      {data.email && (
        <div className="text-xs opacity-70 mt-1 truncate max-w-[150px]">{data.email}</div>
      )}
    </div>
  )
}

const nodeTypes = { person: PersonNode }

// Layout helper - radial layout around user
function getLayoutedElements(user, people, relationships) {
  const nodes = []
  const edges = []

  // Center position for user
  const centerX = 400
  const centerY = 300
  const radius = 250

  // Add user node at center
  if (user) {
    nodes.push({
      id: user.id,
      type: 'person',
      position: { x: centerX - 70, y: centerY - 40 },
      data: {
        label: user.name || 'You',
        type: 'User',
        email: user.email,
      },
    })
  }

  // Add people nodes in a circle around user
  // Sort by significance (higher = closer to center)
  const sortedPeople = [...people].sort((a, b) => (b.significance || 0) - (a.significance || 0))

  sortedPeople.forEach((person, index) => {
    // Higher significance = smaller radius (closer to center)
    const sig = person.significance || 3
    const personRadius = radius * (1 - (sig - 1) * 0.15) // sig 5 = 60% of radius, sig 1 = 100%
    const angle = (2 * Math.PI * index) / sortedPeople.length - Math.PI / 2
    const x = centerX + personRadius * Math.cos(angle) - 70
    const y = centerY + personRadius * Math.sin(angle) - 40

    nodes.push({
      id: person.id,
      type: 'person',
      position: { x, y },
      data: {
        label: person.name || 'Unknown',
        type: 'Person',
        email: person.email,
        relationship: person.relationship_type || person.relationship,
        significance: person.significance,
      },
    })
  })

  // Add edges for relationships
  relationships.forEach((rel, index) => {
    const relType = rel.type || 'KNOWS'
    edges.push({
      id: `e-${index}`,
      source: rel.source,
      target: rel.target,
      type: 'smoothstep',
      animated: relType === 'FAMILY',
      label: formatRelationType(relType),
      labelStyle: { fontSize: 10, fontWeight: 500 },
      labelBgStyle: { fill: '#f1f5f9', fillOpacity: 0.9 },
      labelBgPadding: [4, 2],
      style: { stroke: REL_COLORS[relType] || REL_COLORS.default, strokeWidth: 2 },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: REL_COLORS[relType] || REL_COLORS.default,
      },
    })
  })

  return { nodes, edges }
}

function formatRelationType(type) {
  return type.replace(/_/g, ' ').toLowerCase()
}

export default function Relationships() {
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedNode, setSelectedNode] = useState(null)
  const [graphData, setGraphData] = useState({ user: null, people: [], relationships: [] })
  const [runningCycle, setRunningCycle] = useState(false)
  const [cycleResult, setCycleResult] = useState(null)
  const [categories, setCategories] = useState({ person_categories: [], company_categories: [] })
  const [updatingCategory, setUpdatingCategory] = useState(false)
  const [updatingType, setUpdatingType] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

  // Fetch relationships from API
  const fetchRelationships = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch('/api/relationships')
      const data = await response.json()

      if (data.success) {
        setGraphData(data)
        const { nodes: layoutNodes, edges: layoutEdges } = getLayoutedElements(
          data.user,
          data.people,
          data.relationships
        )
        setNodes(layoutNodes)
        setEdges(layoutEdges)
      } else {
        setError(data.error || 'Failed to load relationships')
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [setNodes, setEdges])

  useEffect(() => {
    fetchRelationships()
  }, [fetchRelationships])

  // Fetch available categories
  useEffect(() => {
    const fetchCategories = async () => {
      try {
        const response = await fetch('/api/relationships/categories')
        const data = await response.json()
        if (data.success) {
          setCategories(data)
        }
      } catch (err) {
        console.error('Failed to fetch categories:', err)
      }
    }
    fetchCategories()
  }, [])

  // Update a node's category or significance
  const updateRelationship = async (nodeId, updates) => {
    setUpdatingCategory(true)
    try {
      const response = await fetch(`/api/relationships/${nodeId}/category`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      })
      const data = await response.json()
      if (data.success) {
        // Update the selected node's display
        if (selectedNode && selectedNode.id === nodeId) {
          setSelectedNode({
            ...selectedNode,
            data: {
              ...selectedNode.data,
              relationship: updates.category || selectedNode.data.relationship,
              significance: updates.significance !== undefined ? updates.significance : selectedNode.data.significance
            }
          })
        }
        // Refresh the graph to show updated data
        await fetchRelationships()
      } else {
        console.error('Failed to update relationship:', data.error)
      }
    } catch (err) {
      console.error('Error updating relationship:', err)
    } finally {
      setUpdatingCategory(false)
    }
  }

  // Legacy wrapper for category-only updates
  const updateCategory = (nodeId, newCategory) => updateRelationship(nodeId, { category: newCategory })

  // Update a node's type (Person -> Company, etc.)
  const updateNodeType = async (nodeId, newType) => {
    setUpdatingType(true)
    try {
      const response = await fetch(`/api/relationships/${nodeId}/type`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_type: newType }),
      })
      const data = await response.json()
      if (data.success) {
        // Update selected node display
        if (selectedNode && selectedNode.id === nodeId) {
          setSelectedNode({
            ...selectedNode,
            data: { ...selectedNode.data, type: newType }
          })
        }
        // Refresh the graph
        await fetchRelationships()
      } else {
        console.error('Failed to update node type:', data.error)
        alert(`Failed to update type: ${data.error}`)
      }
    } catch (err) {
      console.error('Error updating node type:', err)
      alert(`Error: ${err.message}`)
    } finally {
      setUpdatingType(false)
    }
  }

  // Delete a node
  const deleteNode = async (nodeId) => {
    setDeleting(true)
    try {
      const response = await fetch(`/api/relationships/${nodeId}`, {
        method: 'DELETE',
      })
      const data = await response.json()
      if (data.success) {
        // Clear selection and refresh
        setSelectedNode(null)
        setShowDeleteConfirm(false)
        await fetchRelationships()
      } else {
        console.error('Failed to delete node:', data.error)
        alert(`Failed to delete: ${data.error}`)
      }
    } catch (err) {
      console.error('Error deleting node:', err)
      alert(`Error: ${err.message}`)
    } finally {
      setDeleting(false)
    }
  }

  // Run a cycle to discover more relationships
  const runCycle = async (query) => {
    setRunningCycle(true)
    setCycleResult(null)
    try {
      const response = await fetch('/api/cycles/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      })
      const data = await response.json()
      setCycleResult(data)

      // Refresh the graph after cycle completes
      if (data.success) {
        await fetchRelationships()
      }
    } catch (err) {
      setCycleResult({ success: false, error: err.message })
    } finally {
      setRunningCycle(false)
    }
  }

  // Handle node click
  const onNodeClick = useCallback((event, node) => {
    setSelectedNode(node)
    setShowDeleteConfirm(false) // Reset delete confirm when selecting new node
  }, [])

  // Predefined cycle queries for relationships
  const cycleQueries = [
    { label: 'Import my contacts', query: 'Import contacts from my Google contacts and identify key relationships' },
    { label: 'Find family members', query: 'Who are the family members of people I know?' },
    { label: 'Map work connections', query: 'What are the professional relationships between people I know?' },
    { label: 'Discover mutual friends', query: 'Are there mutual connections between people in my network?' },
  ]

  return (
    <div className="h-screen flex flex-col bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-4 py-3">
        <div className="flex items-center justify-between max-w-7xl mx-auto">
          <div className="flex items-center gap-4">
            <Link
              to="/"
              className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
            </Link>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">
              Relationships
            </h1>
            <span className="text-sm text-gray-500 dark:text-gray-400">
              {graphData.counts?.people || 0} people, {graphData.counts?.relationships || 0} connections
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={fetchRelationships}
              disabled={loading}
              className="px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
            >
              {loading ? 'Loading...' : 'Refresh'}
            </button>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex">
        <PanelGroup direction="horizontal">
          {/* Graph Panel */}
          <Panel defaultSize={70} minSize={50}>
            <div className="h-full relative">
              {loading && (
                <div className="absolute inset-0 flex items-center justify-center bg-white/80 dark:bg-gray-900/80 z-10">
                  <div className="flex flex-col items-center gap-2">
                    <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
                    <span className="text-gray-600 dark:text-gray-400">Loading relationships...</span>
                  </div>
                </div>
              )}
              {error && (
                <div className="absolute inset-0 flex items-center justify-center bg-white/80 dark:bg-gray-900/80 z-10">
                  <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 max-w-md">
                    <p className="text-red-600 dark:text-red-400">{error}</p>
                    <button
                      onClick={fetchRelationships}
                      className="mt-2 text-sm text-red-600 hover:text-red-700 underline"
                    >
                      Try again
                    </button>
                  </div>
                </div>
              )}
              <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onNodeClick={onNodeClick}
                nodeTypes={nodeTypes}
                fitView
                fitViewOptions={{ padding: 0.2 }}
              >
                <Controls className="!bg-white dark:!bg-gray-800 !border-gray-200 dark:!border-gray-700" />
                <MiniMap
                  className="!bg-gray-100 dark:!bg-gray-800"
                  nodeColor={(node) => {
                    const colors = NODE_COLORS[node.data?.type] || NODE_COLORS.Unknown
                    return colors.bg
                  }}
                />
                <Background variant="dots" gap={20} size={1} />
              </ReactFlow>
            </div>
          </Panel>

          <PanelResizeHandle className="w-1 bg-gray-200 dark:bg-gray-700 hover:bg-blue-500 transition-colors cursor-col-resize" />

          {/* Sidebar Panel */}
          <Panel defaultSize={30} minSize={20}>
            <div className="h-full overflow-y-auto bg-white dark:bg-gray-800 p-4">
              {/* Cycle Actions */}
              <div className="mb-6">
                <h3 className="font-semibold text-gray-900 dark:text-white mb-3">
                  Discover Relationships
                </h3>
                <div className="space-y-2">
                  {cycleQueries.map((q, i) => (
                    <button
                      key={i}
                      onClick={() => runCycle(q.query)}
                      disabled={runningCycle}
                      className="w-full text-left px-3 py-2 text-sm bg-gray-50 dark:bg-gray-700 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors disabled:opacity-50"
                    >
                      {q.label}
                    </button>
                  ))}
                </div>

                {runningCycle && (
                  <div className="mt-3 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                    <div className="flex items-center gap-2 text-blue-600 dark:text-blue-400">
                      <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                      Running research cycle...
                    </div>
                  </div>
                )}

                {cycleResult && (
                  <div className={`mt-3 p-3 rounded-lg ${
                    cycleResult.success
                      ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400'
                      : 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400'
                  }`}>
                    {cycleResult.success ? (
                      <div>
                        <p className="font-medium">Cycle complete!</p>
                        {cycleResult.result?.findings?.length > 0 && (
                          <ul className="mt-2 text-sm space-y-1">
                            {cycleResult.result.findings.slice(0, 3).map((f, i) => (
                              <li key={i}>• {f}</li>
                            ))}
                          </ul>
                        )}
                      </div>
                    ) : (
                      <p>Error: {cycleResult.error}</p>
                    )}
                  </div>
                )}
              </div>

              {/* Selected Node Details */}
              {selectedNode && selectedNode.data.type !== 'User' && (
                <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
                  <h3 className="font-semibold text-gray-900 dark:text-white mb-3">
                    {selectedNode.data.label}
                  </h3>
                  <div className="space-y-3 text-sm">
                    {/* Node Type Selector */}
                    <div>
                      <label className="block text-gray-500 dark:text-gray-400 mb-1">Node Type</label>
                      <select
                        value={selectedNode.data.type}
                        onChange={(e) => updateNodeType(selectedNode.id, e.target.value)}
                        disabled={updatingType}
                        className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50"
                      >
                        <option value="Person">Person</option>
                        <option value="Company">Company</option>
                        <option value="Organization">Organization</option>
                      </select>
                      {updatingType && (
                        <div className="mt-1 flex items-center gap-2 text-xs text-blue-500">
                          <div className="w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin" />
                          Changing type...
                        </div>
                      )}
                    </div>
                    {selectedNode.data.email && (
                      <div className="flex justify-between items-center">
                        <span className="text-gray-500 dark:text-gray-400">Email</span>
                        <span className="text-gray-900 dark:text-white truncate max-w-[150px]">
                          {selectedNode.data.email}
                        </span>
                      </div>
                    )}

                    {/* Category Selector */}
                    <div className="pt-2">
                      <label className="block text-gray-500 dark:text-gray-400 mb-2">
                        Relationship Category
                      </label>
                      <select
                        value={selectedNode.data.relationship || 'unknown'}
                        onChange={(e) => updateCategory(selectedNode.id, e.target.value)}
                        disabled={updatingCategory}
                        className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50"
                      >
                        {selectedNode.data.type === 'Person' ? (
                          <>
                            <optgroup label="Personal">
                              <option value="family">Family</option>
                              <option value="close_friend">Close Friend</option>
                              <option value="friend">Friend</option>
                              <option value="partner">Partner</option>
                              <option value="ex">Ex</option>
                              <option value="neighbor">Neighbor</option>
                              <option value="classmate">Classmate</option>
                            </optgroup>
                            <optgroup label="Professional">
                              <option value="colleague">Colleague</option>
                              <option value="business_contact">Business Contact</option>
                              <option value="client">Client</option>
                              <option value="mentor">Mentor</option>
                              <option value="mentee">Mentee</option>
                            </optgroup>
                            <optgroup label="Other">
                              <option value="acquaintance">Acquaintance</option>
                              <option value="unknown">Unknown</option>
                            </optgroup>
                          </>
                        ) : (
                          <>
                            <optgroup label="Customer Status">
                              <option value="active_subscriber">Active Subscriber</option>
                              <option value="inactive_subscriber">Inactive Subscriber</option>
                              <option value="customer">Customer</option>
                              <option value="former_customer">Former Customer</option>
                            </optgroup>
                            <optgroup label="Work">
                              <option value="works_at">Works At</option>
                              <option value="worked_at">Worked At</option>
                              <option value="investor">Investor</option>
                            </optgroup>
                            <optgroup label="Sentiment">
                              <option value="likes">Likes</option>
                              <option value="dislikes">Dislikes</option>
                              <option value="neutral">Neutral</option>
                              <option value="interested">Interested</option>
                            </optgroup>
                            <optgroup label="Other">
                              <option value="unknown">Unknown</option>
                            </optgroup>
                          </>
                        )}
                      </select>
                    </div>

                    {/* Significance Slider */}
                    <div className="pt-3">
                      <label className="block text-gray-500 dark:text-gray-400 mb-2">
                        Significance (1-5)
                      </label>
                      <div className="flex items-center gap-3">
                        <input
                          type="range"
                          min="1"
                          max="5"
                          value={selectedNode.data.significance || 3}
                          onChange={(e) => updateRelationship(selectedNode.id, { significance: parseInt(e.target.value) })}
                          disabled={updatingCategory}
                          className="flex-1 h-2 bg-gray-200 dark:bg-gray-600 rounded-lg appearance-none cursor-pointer accent-blue-500"
                        />
                        <span className="w-8 text-center font-medium text-gray-900 dark:text-white">
                          {selectedNode.data.significance || 3}
                        </span>
                      </div>
                      <div className="flex justify-between text-xs text-gray-400 mt-1">
                        <span>Low</span>
                        <span>Critical</span>
                      </div>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                        {selectedNode.data.significance >= 4
                          ? "The system will build deeper knowledge about this relationship."
                          : selectedNode.data.significance <= 2
                          ? "Low priority - minimal research focus."
                          : "Standard priority."}
                      </p>
                    </div>

                    {updatingCategory && (
                      <div className="mt-2 flex items-center gap-2 text-sm text-blue-500">
                        <div className="w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin" />
                        Updating...
                      </div>
                    )}
                  </div>

                  <button
                    onClick={() => runCycle(`Tell me more about ${selectedNode.data.label}`)}
                    disabled={runningCycle}
                    className="mt-4 w-full px-3 py-2 text-sm bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors disabled:opacity-50"
                  >
                    Research this {selectedNode.data.type === 'Person' ? 'person' : 'entity'}
                  </button>

                  {/* Delete Node */}
                  <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                    {!showDeleteConfirm ? (
                      <button
                        onClick={() => setShowDeleteConfirm(true)}
                        className="w-full px-3 py-2 text-sm text-red-600 dark:text-red-400 border border-red-300 dark:border-red-700 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                      >
                        Delete {selectedNode.data.type}
                      </button>
                    ) : (
                      <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-3">
                        <p className="text-sm text-red-600 dark:text-red-400 mb-3">
                          Delete "{selectedNode.data.label}"? This will also remove all relationships.
                        </p>
                        <div className="flex gap-2">
                          <button
                            onClick={() => deleteNode(selectedNode.id)}
                            disabled={deleting}
                            className="flex-1 px-3 py-2 text-sm bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors disabled:opacity-50"
                          >
                            {deleting ? 'Deleting...' : 'Confirm Delete'}
                          </button>
                          <button
                            onClick={() => setShowDeleteConfirm(false)}
                            disabled={deleting}
                            className="flex-1 px-3 py-2 text-sm bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-200 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-500 transition-colors disabled:opacity-50"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* People List */}
              <div className="border-t border-gray-200 dark:border-gray-700 pt-4 mt-4">
                <h3 className="font-semibold text-gray-900 dark:text-white mb-3">
                  People ({graphData.people?.length || 0})
                </h3>
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {graphData.people?.map((person) => (
                    <div
                      key={person.id}
                      onClick={() => {
                        const node = nodes.find(n => n.id === person.id)
                        if (node) setSelectedNode(node)
                      }}
                      className="p-2 rounded-lg bg-gray-50 dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600 cursor-pointer transition-colors"
                    >
                      <div className="font-medium text-gray-900 dark:text-white text-sm">
                        {person.name || 'Unknown'}
                      </div>
                      {person.relationship_type && (
                        <div className="text-xs text-gray-500 dark:text-gray-400">
                          {person.relationship_type}
                        </div>
                      )}
                    </div>
                  ))}
                  {(!graphData.people || graphData.people.length === 0) && (
                    <p className="text-sm text-gray-500 dark:text-gray-400 italic">
                      No people found. Run a cycle to import contacts.
                    </p>
                  )}
                </div>
              </div>
            </div>
          </Panel>
        </PanelGroup>
      </div>
    </div>
  )
}
