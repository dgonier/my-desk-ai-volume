import { useState, useCallback, useEffect, useRef } from 'react'
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
  Project: { bg: '#8b5cf6', border: '#7c3aed', text: '#fff' },
  Person: { bg: '#3b82f6', border: '#2563eb', text: '#fff' },
  Task: { bg: '#f59e0b', border: '#d97706', text: '#fff' },
  Insight: { bg: '#06b6d4', border: '#0891b2', text: '#fff' },
  Organization: { bg: '#ec4899', border: '#db2777', text: '#fff' },
  Unknown: { bg: '#6b7280', border: '#4b5563', text: '#fff' },
}

// Icons for node types
const NODE_ICONS = {
  User: '👤',
  Project: '📁',
  Person: '🧑',
  Task: '✅',
  Insight: '💡',
  Organization: '🏢',
}

// Custom node component
function GraphNode({ data, selected }) {
  const colors = NODE_COLORS[data.type] || NODE_COLORS.Unknown
  const icon = data.icon || NODE_ICONS[data.type] || '📄'

  return (
    <div
      className={`px-4 py-3 rounded-xl shadow-lg border-2 min-w-[120px] max-w-[180px] text-center cursor-pointer transition-all ${
        selected ? 'ring-2 ring-offset-2 ring-blue-500 scale-105' : ''
      }`}
      style={{
        backgroundColor: colors.bg,
        borderColor: colors.border,
        color: colors.text,
      }}
    >
      <Handle type="target" position={Position.Top} className="!bg-white !w-2 !h-2" />
      <Handle type="source" position={Position.Bottom} className="!bg-white !w-2 !h-2" />
      <Handle type="target" position={Position.Left} id="left" className="!bg-white !w-2 !h-2" />
      <Handle type="source" position={Position.Right} id="right" className="!bg-white !w-2 !h-2" />

      <div className="text-xl mb-1">{icon}</div>
      <div className="text-xs opacity-80 mb-0.5">{data.type}</div>
      <div className="font-bold text-sm truncate">{data.label}</div>
      {data.status && (
        <div className="text-xs opacity-70 mt-1">{data.status}</div>
      )}
    </div>
  )
}

const nodeTypes = { graphNode: GraphNode }

// Layout nodes in a hierarchical structure around user
function layoutGraph(nodes, edges) {
  const layoutedNodes = []
  const centerX = 400
  const centerY = 300

  // Find user node
  const userNode = nodes.find(n => n.type === 'User')
  const projectNodes = nodes.filter(n => n.type === 'Project')
  const otherNodes = nodes.filter(n => n.type !== 'User' && n.type !== 'Project')

  // Position user at center
  if (userNode) {
    layoutedNodes.push({
      id: userNode.id,
      type: 'graphNode',
      position: { x: centerX - 60, y: centerY - 40 },
      data: { ...userNode, label: userNode.name || 'You' },
    })
  }

  // Position projects in a circle around user
  const projectRadius = 200
  projectNodes.forEach((proj, i) => {
    const angle = (2 * Math.PI * i) / Math.max(projectNodes.length, 1) - Math.PI / 2
    layoutedNodes.push({
      id: proj.id,
      type: 'graphNode',
      position: {
        x: centerX + projectRadius * Math.cos(angle) - 60,
        y: centerY + projectRadius * Math.sin(angle) - 40,
      },
      data: { ...proj, label: proj.name },
    })
  })

  // Position other nodes (people, tasks, etc.) around their connected projects
  const nodeToProject = {}
  edges.forEach(edge => {
    const sourceNode = nodes.find(n => n.id === edge.source)
    const targetNode = nodes.find(n => n.id === edge.target)
    if (sourceNode?.type === 'Project' && targetNode && targetNode.type !== 'User') {
      nodeToProject[targetNode.id] = sourceNode.id
    }
  })

  // Group other nodes by project
  const nodesByProject = {}
  otherNodes.forEach(node => {
    const projectId = nodeToProject[node.id] || 'unassigned'
    if (!nodesByProject[projectId]) nodesByProject[projectId] = []
    nodesByProject[projectId].push(node)
  })

  // Position nodes around their projects
  Object.entries(nodesByProject).forEach(([projectId, projectOtherNodes]) => {
    const projectLayoutNode = layoutedNodes.find(n => n.id === projectId)
    const basePosX = projectLayoutNode ? projectLayoutNode.position.x + 60 : centerX
    const basePosY = projectLayoutNode ? projectLayoutNode.position.y + 40 : centerY
    const nodeRadius = 120

    projectOtherNodes.forEach((node, i) => {
      const angle = (2 * Math.PI * i) / Math.max(projectOtherNodes.length, 1)
      layoutedNodes.push({
        id: node.id,
        type: 'graphNode',
        position: {
          x: basePosX + nodeRadius * Math.cos(angle) - 60,
          y: basePosY + nodeRadius * Math.sin(angle) - 40,
        },
        data: { ...node, label: node.name || node.title || node.content?.slice(0, 30) || 'Node' },
      })
    })
  })

  // Create edges
  const layoutedEdges = edges.map((edge, i) => ({
    id: `e-${i}`,
    source: edge.source,
    target: edge.target,
    type: 'smoothstep',
    animated: edge.type?.includes('OWNS') || edge.type?.includes('HAS'),
    label: edge.type?.replace(/_/g, ' ').toLowerCase(),
    labelStyle: { fontSize: 9, fontWeight: 500 },
    labelBgStyle: { fill: '#f1f5f9', fillOpacity: 0.8 },
    style: { stroke: '#94a3b8', strokeWidth: 1.5 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#94a3b8' },
  }))

  return { nodes: layoutedNodes, edges: layoutedEdges }
}

export default function Projects() {
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [loading, setLoading] = useState(true)
  const [selectedNode, setSelectedNode] = useState(null)
  const [projects, setProjects] = useState([])
  const [activeProject, setActiveProject] = useState(null)

  // Chat state
  const [chatMessages, setChatMessages] = useState([])
  const [chatInput, setChatInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const chatEndRef = useRef(null)

  // New project dialog
  const [showNewProject, setShowNewProject] = useState(false)
  const [newProjectName, setNewProjectName] = useState('')

  // Fetch full graph
  const fetchGraph = useCallback(async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/graph/full')
      const data = await response.json()

      if (data.success) {
        const { nodes: layoutedNodes, edges: layoutedEdges } = layoutGraph(data.nodes, data.edges)
        setNodes(layoutedNodes)
        setEdges(layoutedEdges)
      }
    } catch (err) {
      console.error('Failed to fetch graph:', err)
    } finally {
      setLoading(false)
    }
  }, [setNodes, setEdges])

  // Fetch projects list
  const fetchProjects = useCallback(async () => {
    try {
      const response = await fetch('/api/projects')
      const data = await response.json()
      if (data.success) {
        setProjects(data.projects)
      }
    } catch (err) {
      console.error('Failed to fetch projects:', err)
    }
  }, [])

  // Initialize default projects
  const initializeDefaults = useCallback(async () => {
    try {
      const response = await fetch('/api/projects/initialize-defaults', { method: 'POST' })
      const data = await response.json()
      if (data.success && data.created.length > 0) {
        await fetchProjects()
        await fetchGraph()
      }
    } catch (err) {
      console.error('Failed to initialize defaults:', err)
    }
  }, [fetchProjects, fetchGraph])

  useEffect(() => {
    initializeDefaults()
    fetchGraph()
    fetchProjects()
  }, [initializeDefaults, fetchGraph, fetchProjects])

  // Scroll chat to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages])

  // Handle node click
  const onNodeClick = useCallback((event, node) => {
    setSelectedNode(node)
    if (node.data.type === 'Project') {
      setActiveProject(node)
      // Start enrichment chat for this project
      setChatMessages([{
        role: 'assistant',
        content: `Let's enrich the **${node.data.label}** project. Tell me more about it - what's the main goal, who's involved, and what are the key tasks?`
      }])
    }
  }, [])

  // Send chat message
  const sendMessage = async () => {
    if (!chatInput.trim() || !activeProject) return

    const userMessage = chatInput.trim()
    setChatInput('')
    setChatMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setChatLoading(true)

    try {
      const response = await fetch(`/api/projects/${activeProject.id}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMessage }),
      })
      const data = await response.json()

      if (data.success) {
        // Show what was created
        let actionText = ''
        if (data.actions?.length > 0) {
          const actionDescriptions = data.actions.map(a => {
            if (a.type === 'created_person') return `Added person: ${a.name}${a.role ? ` (${a.role})` : ''}`
            if (a.type === 'created_task') return `Added task: ${a.title}`
            if (a.type === 'created_insight') return `Added insight`
            return `Action: ${a.type}`
          })
          actionText = '\n\n' + actionDescriptions.join('\n')
        }

        setChatMessages(prev => [...prev, {
          role: 'assistant',
          content: data.response + actionText,
          actions: data.actions,
          enrichment_level: data.enrichment_level,
        }])

        // Refresh graph if actions were taken
        if (data.actions?.length > 0) {
          await fetchGraph()
          await fetchProjects()
        }
      } else {
        setChatMessages(prev => [...prev, {
          role: 'assistant',
          content: `Error: ${data.error}`,
          isError: true,
        }])
      }
    } catch (err) {
      setChatMessages(prev => [...prev, {
        role: 'assistant',
        content: `Error: ${err.message}`,
        isError: true,
      }])
    } finally {
      setChatLoading(false)
    }
  }

  // Create new project
  const createProject = async () => {
    if (!newProjectName.trim()) return

    try {
      const response = await fetch('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newProjectName.trim() }),
      })
      const data = await response.json()

      if (data.success) {
        setShowNewProject(false)
        setNewProjectName('')
        await fetchProjects()
        await fetchGraph()

        // Start chat with new project
        setActiveProject({ id: data.project.id, data: data.project })
        setChatMessages([{
          role: 'assistant',
          content: `Great! I've created the **${data.project.name}** project. Let's set it up - what's this project about and what are you trying to achieve?`
        }])
      }
    } catch (err) {
      console.error('Failed to create project:', err)
    }
  }

  // Research project
  const researchProject = async (projectId) => {
    setChatLoading(true)
    setChatMessages(prev => [...prev, {
      role: 'system',
      content: 'Researching your emails and calendar for related information...'
    }])

    try {
      const response = await fetch(`/api/projects/${projectId}/research`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ focus: 'all' }),
      })
      const data = await response.json()

      if (data.success) {
        setChatMessages(prev => [...prev, {
          role: 'assistant',
          content: `Research complete for **${data.project}**. ${data.result?.nodes_created || 0} new contacts found, ${data.result?.relationships_created || 0} connections made.`
        }])
        await fetchGraph()
        await fetchProjects()
      } else {
        setChatMessages(prev => [...prev, {
          role: 'assistant',
          content: `Research failed: ${data.error}`,
          isError: true,
        }])
      }
    } catch (err) {
      setChatMessages(prev => [...prev, {
        role: 'assistant',
        content: `Research error: ${err.message}`,
        isError: true,
      }])
    } finally {
      setChatLoading(false)
    }
  }

  return (
    <div className="h-screen flex flex-col bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-4 py-3">
        <div className="flex items-center justify-between max-w-7xl mx-auto">
          <div className="flex items-center gap-4">
            <Link to="/" className="text-gray-500 hover:text-gray-700 dark:text-gray-400">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
            </Link>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">Projects</h1>
            <span className="text-sm text-gray-500 dark:text-gray-400">
              {projects.length} projects, {nodes.length} nodes
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowNewProject(true)}
              className="px-3 py-1.5 text-sm bg-purple-500 text-white rounded-lg hover:bg-purple-600 transition-colors"
            >
              + New Project
            </button>
            <button
              onClick={() => { fetchGraph(); fetchProjects(); }}
              disabled={loading}
              className="px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600"
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
          <Panel defaultSize={60} minSize={40}>
            <div className="h-full relative">
              {loading && (
                <div className="absolute inset-0 flex items-center justify-center bg-white/80 dark:bg-gray-900/80 z-10">
                  <div className="flex flex-col items-center gap-2">
                    <div className="w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full animate-spin" />
                    <span className="text-gray-600 dark:text-gray-400">Loading graph...</span>
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
                fitViewOptions={{ padding: 0.3 }}
              >
                <Controls className="!bg-white dark:!bg-gray-800" />
                <MiniMap
                  className="!bg-gray-100 dark:!bg-gray-800"
                  nodeColor={(node) => NODE_COLORS[node.data?.type]?.bg || '#6b7280'}
                />
                <Background variant="dots" gap={20} size={1} />
              </ReactFlow>
            </div>
          </Panel>

          <PanelResizeHandle className="w-1 bg-gray-200 dark:bg-gray-700 hover:bg-purple-500 transition-colors cursor-col-resize" />

          {/* Chat + Details Panel */}
          <Panel defaultSize={40} minSize={25}>
            <div className="h-full flex flex-col bg-white dark:bg-gray-800">
              {/* Project selector */}
              <div className="p-3 border-b border-gray-200 dark:border-gray-700">
                <label className="text-xs text-gray-500 dark:text-gray-400 mb-1 block">Active Project</label>
                <select
                  value={activeProject?.id || ''}
                  onChange={(e) => {
                    const proj = projects.find(p => p.id === e.target.value)
                    if (proj) {
                      setActiveProject({ id: proj.id, data: proj })
                      setChatMessages([{
                        role: 'assistant',
                        content: `Let's work on **${proj.name}**. What would you like to do?`
                      }])
                    }
                  }}
                  className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white"
                >
                  <option value="">Select a project...</option>
                  {projects.map(proj => (
                    <option key={proj.id} value={proj.id}>
                      {proj.icon || '📁'} {proj.name} {proj.is_default ? '(default)' : ''}
                    </option>
                  ))}
                </select>

                {activeProject && (
                  <div className="mt-2 flex gap-2">
                    <button
                      onClick={() => researchProject(activeProject.id)}
                      disabled={chatLoading}
                      className="flex-1 px-2 py-1 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded hover:bg-blue-200 dark:hover:bg-blue-900/50 disabled:opacity-50"
                    >
                      Research Emails
                    </button>
                  </div>
                )}
              </div>

              {/* Chat messages */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {chatMessages.length === 0 ? (
                  <div className="text-center text-gray-500 dark:text-gray-400 mt-8">
                    <p className="text-lg mb-2">Select or create a project to start</p>
                    <p className="text-sm">Chat with the AI to enrich your projects with people, tasks, and insights</p>
                  </div>
                ) : (
                  chatMessages.map((msg, i) => (
                    <div
                      key={i}
                      className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div
                        className={`max-w-[85%] rounded-lg px-4 py-2 ${
                          msg.role === 'user'
                            ? 'bg-purple-500 text-white'
                            : msg.role === 'system'
                            ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-200'
                            : msg.isError
                            ? 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200'
                            : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white'
                        }`}
                      >
                        <div className="text-sm whitespace-pre-wrap">{msg.content}</div>
                        {msg.actions?.length > 0 && (
                          <div className="mt-2 pt-2 border-t border-gray-200 dark:border-gray-600">
                            <div className="text-xs text-gray-500 dark:text-gray-400">
                              Graph updated: {msg.actions.length} change(s)
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  ))
                )}
                {chatLoading && (
                  <div className="flex justify-start">
                    <div className="bg-gray-100 dark:bg-gray-700 rounded-lg px-4 py-2">
                      <div className="flex items-center gap-2 text-gray-500">
                        <div className="w-2 h-2 bg-purple-500 rounded-full animate-pulse" />
                        <div className="w-2 h-2 bg-purple-500 rounded-full animate-pulse delay-75" />
                        <div className="w-2 h-2 bg-purple-500 rounded-full animate-pulse delay-150" />
                      </div>
                    </div>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>

              {/* Chat input */}
              <div className="p-3 border-t border-gray-200 dark:border-gray-700">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
                    placeholder={activeProject ? "Tell me about this project..." : "Select a project first..."}
                    disabled={!activeProject || chatLoading}
                    className="flex-1 px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white placeholder-gray-400 disabled:opacity-50"
                  />
                  <button
                    onClick={sendMessage}
                    disabled={!activeProject || chatLoading || !chatInput.trim()}
                    className="px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Send
                  </button>
                </div>
              </div>

              {/* Selected node details */}
              {selectedNode && selectedNode.data.type !== 'User' && (
                <div className="p-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
                  <h4 className="font-medium text-gray-900 dark:text-white mb-2">
                    {selectedNode.data.icon || NODE_ICONS[selectedNode.data.type]} {selectedNode.data.label}
                  </h4>
                  <div className="text-xs text-gray-500 dark:text-gray-400 space-y-1">
                    <div>Type: {selectedNode.data.type}</div>
                    {selectedNode.data.status && <div>Status: {selectedNode.data.status}</div>}
                    {selectedNode.data.description && (
                      <div className="mt-2 text-gray-600 dark:text-gray-300">{selectedNode.data.description}</div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </Panel>
        </PanelGroup>
      </div>

      {/* New Project Dialog */}
      {showNewProject && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 w-full max-w-md shadow-xl">
            <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">Create New Project</h3>
            <input
              type="text"
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && createProject()}
              placeholder="Project name..."
              autoFocus
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white mb-4"
            />
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => { setShowNewProject(false); setNewProjectName(''); }}
                className="px-4 py-2 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={createProject}
                disabled={!newProjectName.trim()}
                className="px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600 disabled:opacity-50"
              >
                Create
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
