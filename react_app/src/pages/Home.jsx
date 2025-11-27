import { useState, useEffect } from 'react'
import { Link, useSearchParams, useNavigate } from 'react-router-dom'
import ConnectServicesPopup from '../components/ConnectServicesPopup'

function Home() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [showConnectPopup, setShowConnectPopup] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    const showPopup = searchParams.get('showConnectPopup')
    const skipConnect = sessionStorage.getItem('skipConnectServices')
    const hasSeenPopup = localStorage.getItem('hasSeenConnectPopup')

    if (showPopup === '1' || (!hasSeenPopup && !skipConnect)) {
      setShowConnectPopup(true)
      if (showPopup) {
        searchParams.delete('showConnectPopup')
        setSearchParams(searchParams)
      }
    }
  }, [searchParams, setSearchParams])

  const handlePopupClose = () => {
    setShowConnectPopup(false)
    localStorage.setItem('hasSeenConnectPopup', 'true')
  }

  const handlePopupComplete = () => {
    localStorage.setItem('hasSeenConnectPopup', 'true')
  }

  const apps = [
    {
      name: 'Graph',
      description: 'Explore your cognitive graph - people, projects, research, and memories all connected.',
      icon: '🧠',
      path: '/graph',
      color: 'from-purple-500 to-indigo-600',
      available: true,
      filters: [
        { label: 'Identity', path: '/graph?filter=identity' },
        { label: 'People', path: '/graph?filter=people' },
        { label: 'Projects', path: '/graph?filter=projects' },
      ]
    },
    {
      name: 'Write',
      description: 'Document editor with AI assistance. Markdown with live preview and LaTeX math support.',
      icon: '✍️',
      path: '/write',
      color: 'from-emerald-500 to-teal-600',
      available: true,
    },
    {
      name: 'Read',
      description: 'Reading view for documents, research papers, and saved content with annotations.',
      icon: '📖',
      path: '/read',
      color: 'from-blue-500 to-cyan-600',
      available: true,
    },
    {
      name: 'Feed',
      description: 'Job listings, news, and updates curated by your AI agent based on your interests.',
      icon: '📰',
      path: '/jobs-feed',
      color: 'from-orange-500 to-red-500',
      available: true,
    },
    {
      name: 'Cards',
      description: 'Browse your cognitive graph as cards - perfect for mobile or quick scanning.',
      icon: '📇',
      path: '/cards',
      color: 'from-pink-500 to-rose-600',
      available: true,
      filters: [
        { label: 'People', path: '/cards?filter=people' },
        { label: 'Projects', path: '/cards?filter=projects' },
      ]
    },
    {
      name: 'Audio',
      description: 'Listen to reports, summaries, and updates from your AI agent. Shareable via link.',
      icon: '🎧',
      path: '/audio',
      color: 'from-violet-500 to-purple-600',
      available: true,
      filters: [
        { label: 'Reports', path: '/audio?type=report' },
        { label: 'Briefs', path: '/audio?type=brief' },
      ]
    },
    {
      name: 'Terminal',
      description: 'Full terminal access to your cloud development environment.',
      icon: '🖥️',
      path: '/terminal',
      color: 'from-gray-700 to-gray-900',
      available: false,
      external: true,
    },
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 transition-colors">
      {/* Hero Section */}
      <div className="max-w-6xl mx-auto px-4 pt-12 pb-8">
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent mb-4">
            my-desk.ai
          </h1>
          <p className="text-xl text-gray-600 dark:text-gray-300 max-w-2xl mx-auto">
            Your personal AI workspace. Graph, write, read, and explore with Mira.
          </p>
        </div>

        {/* Apps Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
          {apps.map((app) => {
            // Card without nested links - use div with onClick for navigation
            const handleCardClick = (e) => {
              // Don't navigate if clicking on a filter link
              if (e.target.closest('[data-filter-link]')) return
              if (app.available) {
                navigate(app.path)
              } else if (app.external) {
                window.location.href = app.path.replace('/app', '')
              }
            }

            return (
              <div
                key={app.name}
                onClick={handleCardClick}
                className={`bg-white dark:bg-gray-800 rounded-xl shadow-md overflow-hidden hover:shadow-xl transition-all duration-300 h-full transform hover:scale-[1.02] ${
                  !app.available && !app.external ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer'
                }`}
              >
                <div className={`h-2 bg-gradient-to-r ${app.color}`} />
                <div className="p-6">
                  <div className="flex items-start justify-between mb-3">
                    <span className="text-4xl">{app.icon}</span>
                  </div>
                  <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">{app.name}</h3>
                  <p className="text-gray-600 dark:text-gray-400 text-sm leading-relaxed mb-3">
                    {app.description}
                  </p>
                  {/* Quick filter links - use data attribute to prevent card navigation */}
                  {app.filters && (
                    <div className="flex flex-wrap gap-2">
                      {app.filters.map((filter) => (
                        <Link
                          key={filter.path}
                          to={filter.path}
                          data-filter-link="true"
                          className="text-xs px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded-full hover:bg-purple-100 dark:hover:bg-purple-900/30 hover:text-purple-600 dark:hover:text-purple-400 transition-colors"
                        >
                          {filter.label}
                        </Link>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>

        {/* Quick Actions */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-md p-6 mb-8">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <span>⚡</span> Quick Actions
          </h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <Link
              to="/write"
              className="flex items-center gap-3 p-3 bg-emerald-50 dark:bg-emerald-900/30 rounded-lg hover:bg-emerald-100 dark:hover:bg-emerald-900/50 transition-colors"
            >
              <span className="text-2xl">📝</span>
              <span className="font-medium text-emerald-900 dark:text-emerald-300">New Document</span>
            </Link>
            <Link
              to="/graph?filter=identity"
              className="flex items-center gap-3 p-3 bg-purple-50 dark:bg-purple-900/30 rounded-lg hover:bg-purple-100 dark:hover:bg-purple-900/50 transition-colors"
            >
              <span className="text-2xl">🤖</span>
              <span className="font-medium text-purple-900 dark:text-purple-300">View Mira</span>
            </Link>
            <Link
              to="/graph?filter=people"
              className="flex items-center gap-3 p-3 bg-blue-50 dark:bg-blue-900/30 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/50 transition-colors"
            >
              <span className="text-2xl">👥</span>
              <span className="font-medium text-blue-900 dark:text-blue-300">People</span>
            </Link>
            <Link
              to="/jobs-feed"
              className="flex items-center gap-3 p-3 bg-orange-50 dark:bg-orange-900/30 rounded-lg hover:bg-orange-100 dark:hover:bg-orange-900/50 transition-colors"
            >
              <span className="text-2xl">📰</span>
              <span className="font-medium text-orange-900 dark:text-orange-300">Browse Feed</span>
            </Link>
          </div>
        </div>

        {/* Mira Introduction */}
        <div className="bg-gradient-to-r from-purple-50 to-indigo-50 dark:from-purple-900/30 dark:to-indigo-900/30 rounded-xl p-6 border border-purple-100 dark:border-purple-800 mb-8">
          <div className="flex items-start gap-4">
            <span className="text-4xl">🤖</span>
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                Meet Mira
              </h2>
              <p className="text-gray-700 dark:text-gray-300 mb-3">
                Your thoughtful navigator through ideas. Mira remembers your conversations, learns your preferences, and helps you explore connections in your knowledge graph.
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Click the chat button in the bottom-right corner to start a conversation.
              </p>
            </div>
          </div>
        </div>

        {/* Connect Services Button */}
        <div className="text-center">
          <button
            onClick={() => setShowConnectPopup(true)}
            className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-xl font-medium hover:opacity-90 transition-opacity shadow-lg"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
            </svg>
            Connect More Services
          </button>
        </div>
      </div>

      {/* Connect Services Popup */}
      <ConnectServicesPopup
        isOpen={showConnectPopup}
        onClose={handlePopupClose}
        onComplete={handlePopupComplete}
      />
    </div>
  )
}

export default Home
