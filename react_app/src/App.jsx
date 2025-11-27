import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom'
import './App.css'
import { ThemeProvider, useTheme } from './contexts/ThemeContext'

// Pages - Claude can add new pages here
import Home from './pages/Home'
import JobsFeed from './pages/JobsFeed'
import Write from './pages/Write'
import Research from './pages/Research'
import Relationships from './pages/Relationships'
import Projects from './pages/Projects'
import Graph from './pages/Graph'
import Cards from './pages/Cards'
import Read from './pages/Read'
import Audio from './pages/Audio'
// import NewsFeed from './pages/NewsFeed'

// Universal Chat - available on all pages
import UniversalChat from './components/UniversalChat'

// Dark mode toggle button
function ThemeToggle() {
  const { isDark, toggleTheme } = useTheme()
  return (
    <button
      onClick={toggleTheme}
      className="p-2 rounded-lg bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
      title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
    >
      {isDark ? (
        <svg className="w-5 h-5 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" clipRule="evenodd" />
        </svg>
      ) : (
        <svg className="w-5 h-5 text-gray-700" fill="currentColor" viewBox="0 0 20 20">
          <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" />
        </svg>
      )}
    </button>
  )
}

// Layout wrapper that conditionally shows nav
function Layout({ children }) {
  const location = useLocation()
  // Full screen pages that have their own header/nav
  const isFullScreenPage = ['/write', '/read', '/audio', '/research', '/relationships', '/projects', '/graph', '/cards'].includes(location.pathname)

  // These pages have their own full-screen layout
  if (isFullScreenPage) {
    return children
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors">
      {/* Navigation */}
      <nav className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-6xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <Link to="/" className="text-xl font-bold text-gray-900 dark:text-white">
              my-desk.ai
            </Link>
            <div className="flex items-center gap-4">
              <Link to="/" className="text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white">Home</Link>
              <Link to="/graph" className="text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white">Graph</Link>
              <Link to="/write" className="text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white">Write</Link>
              <Link to="/read" className="text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white">Read</Link>
              <Link to="/audio" className="text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white">Audio</Link>
              <ThemeToggle />
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main>
        {children}
      </main>
    </div>
  )
}

function App() {
  // Get the basename dynamically from the current URL
  // URL format: /{username}/app -> basename is /{username}/app
  const pathname = window.location.pathname
  const appIndex = pathname.indexOf('/app')
  const basename = appIndex !== -1 ? pathname.substring(0, appIndex + 4) : '/app'

  return (
    <ThemeProvider>
      <BrowserRouter basename={basename}>
        <Layout>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/graph" element={<Graph />} />
            <Route path="/cards" element={<Cards />} />
            <Route path="/write" element={<Write />} />
            <Route path="/read" element={<Read />} />
            <Route path="/audio" element={<Audio />} />
            <Route path="/jobs-feed" element={<JobsFeed />} />
            {/* Legacy routes - still accessible */}
            <Route path="/research" element={<Research />} />
            <Route path="/relationships" element={<Relationships />} />
            <Route path="/projects" element={<Projects />} />
            {/* Claude adds new routes here */}
          </Routes>
        </Layout>
        {/* Universal Chat - floating FAB available on all pages, defaults open */}
        <UniversalChat defaultOpen={true} />
      </BrowserRouter>
    </ThemeProvider>
  )
}

export default App
