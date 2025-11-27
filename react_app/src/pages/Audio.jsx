import { useState, useEffect, useRef } from 'react'
import { useSearchParams, Link } from 'react-router-dom'

/**
 * Audio Page
 *
 * A feed of audio clips - podcast-style reports, updates, summaries.
 * Key features:
 * - Card layout for browsing audio clips
 * - Direct link to specific audio: ?id=12345
 * - Perfect for sharing via SMS/WhatsApp
 * - Agent can send "Listen to my research summary: /app/audio?id=xxx"
 */

// Sample audio data (will be replaced with API fetch)
const SAMPLE_AUDIO = [
  {
    id: 'audio-001',
    title: 'Weekly Research Summary',
    description: 'Overview of key findings from your cognitive graph this week, including new connections and insights discovered.',
    type: 'report',
    duration: '5:32',
    date: '2024-11-27',
    tags: ['weekly', 'research', 'summary'],
    status: 'ready',
  },
  {
    id: 'audio-002',
    title: 'Job Market Update',
    description: 'Analysis of recent job postings matching your profile. 3 new opportunities identified with high match scores.',
    type: 'update',
    duration: '3:15',
    date: '2024-11-26',
    tags: ['jobs', 'career', 'update'],
    status: 'ready',
  },
  {
    id: 'audio-003',
    title: 'Project Alpha Deep Dive',
    description: 'Detailed breakdown of Project Alpha progress, blockers, and recommended next steps based on your notes.',
    type: 'report',
    duration: '8:47',
    date: '2024-11-25',
    tags: ['project', 'alpha', 'deep-dive'],
    status: 'ready',
  },
  {
    id: 'audio-004',
    title: 'Morning Brief',
    description: 'Quick update on your schedule, pending tasks, and key items requiring attention today.',
    type: 'brief',
    duration: '2:10',
    date: '2024-11-27',
    tags: ['daily', 'brief', 'tasks'],
    status: 'ready',
  },
  {
    id: 'audio-005',
    title: 'Research: AI Ethics Paper',
    description: 'Summary and key takeaways from the AI Ethics paper you saved. Includes connections to your existing research.',
    type: 'research',
    duration: '6:22',
    date: '2024-11-24',
    tags: ['research', 'ai', 'ethics'],
    status: 'generating',
  },
]

const TYPE_CONFIG = {
  report: { icon: '📊', color: 'bg-blue-500', label: 'Report' },
  update: { icon: '📰', color: 'bg-green-500', label: 'Update' },
  brief: { icon: '☀️', color: 'bg-yellow-500', label: 'Brief' },
  research: { icon: '🔬', color: 'bg-purple-500', label: 'Research' },
  podcast: { icon: '🎙️', color: 'bg-red-500', label: 'Podcast' },
}

// Audio player component
function AudioPlayer({ audio, onClose, isFullscreen }) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [progress, setProgress] = useState(0)
  const [currentTime, setCurrentTime] = useState('0:00')
  const audioRef = useRef(null)

  // Simulate playback (replace with actual audio element)
  useEffect(() => {
    let interval
    if (isPlaying) {
      interval = setInterval(() => {
        setProgress(prev => {
          if (prev >= 100) {
            setIsPlaying(false)
            return 0
          }
          return prev + 0.5
        })
      }, 100)
    }
    return () => clearInterval(interval)
  }, [isPlaying])

  // Update time display
  useEffect(() => {
    const [mins, secs] = audio.duration.split(':').map(Number)
    const totalSeconds = mins * 60 + secs
    const currentSeconds = Math.floor((progress / 100) * totalSeconds)
    const m = Math.floor(currentSeconds / 60)
    const s = currentSeconds % 60
    setCurrentTime(`${m}:${s.toString().padStart(2, '0')}`)
  }, [progress, audio.duration])

  const config = TYPE_CONFIG[audio.type] || TYPE_CONFIG.report

  const PlayerContent = (
    <div className={`${isFullscreen ? 'p-6' : 'p-4'}`}>
      {/* Header with close */}
      {isFullscreen && (
        <div className="flex items-center justify-between mb-6">
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-full"
          >
            <svg className="w-6 h-6 text-gray-600 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          <span className={`text-xs px-2 py-1 rounded-full text-white ${config.color}`}>
            {config.icon} {config.label}
          </span>
        </div>
      )}

      {/* Album art / visualization */}
      <div className={`${isFullscreen ? 'w-64 h-64 mx-auto mb-8' : 'w-16 h-16 mr-4 flex-shrink-0'} ${config.color} rounded-2xl flex items-center justify-center`}>
        <span className={`${isFullscreen ? 'text-6xl' : 'text-2xl'}`}>{config.icon}</span>
      </div>

      {/* Info */}
      <div className={isFullscreen ? 'text-center mb-8' : 'flex-1 min-w-0'}>
        <h3 className={`font-semibold text-gray-900 dark:text-white ${isFullscreen ? 'text-xl mb-2' : 'truncate'}`}>
          {audio.title}
        </h3>
        {isFullscreen && (
          <p className="text-gray-500 dark:text-gray-400 text-sm mb-4">
            {audio.description}
          </p>
        )}
        <p className={`text-gray-500 text-xs ${isFullscreen ? '' : 'truncate'}`}>
          {audio.date} • {audio.duration}
        </p>
      </div>

      {/* Progress bar */}
      <div className={`${isFullscreen ? 'mb-6' : 'mt-3'}`}>
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <span>{currentTime}</span>
          <div className="flex-1 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
            <div
              className={`h-full ${config.color} rounded-full transition-all`}
              style={{ width: `${progress}%` }}
            />
          </div>
          <span>{audio.duration}</span>
        </div>
      </div>

      {/* Controls */}
      <div className={`flex items-center justify-center ${isFullscreen ? 'gap-6' : 'gap-4 mt-3'}`}>
        <button className="p-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300">
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12.066 11.2a1 1 0 000 1.6l5.334 4A1 1 0 0019 16V8a1 1 0 00-1.6-.8l-5.333 4zM4.066 11.2a1 1 0 000 1.6l5.334 4A1 1 0 0011 16V8a1 1 0 00-1.6-.8l-5.334 4z" />
          </svg>
        </button>

        <button
          onClick={() => setIsPlaying(!isPlaying)}
          className={`${isFullscreen ? 'w-16 h-16' : 'w-10 h-10'} ${config.color} rounded-full flex items-center justify-center text-white shadow-lg hover:opacity-90 transition-opacity`}
        >
          {isPlaying ? (
            <svg className={`${isFullscreen ? 'w-8 h-8' : 'w-5 h-5'}`} fill="currentColor" viewBox="0 0 24 24">
              <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
            </svg>
          ) : (
            <svg className={`${isFullscreen ? 'w-8 h-8' : 'w-5 h-5'} ml-1`} fill="currentColor" viewBox="0 0 24 24">
              <path d="M8 5v14l11-7z" />
            </svg>
          )}
        </button>

        <button className="p-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300">
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.933 12.8a1 1 0 000-1.6L6.6 7.2A1 1 0 005 8v8a1 1 0 001.6.8l5.333-4zM19.933 12.8a1 1 0 000-1.6l-5.333-4A1 1 0 0013 8v8a1 1 0 001.6.8l5.333-4z" />
          </svg>
        </button>
      </div>

      {/* Share button (fullscreen only) */}
      {isFullscreen && (
        <div className="mt-8 flex justify-center gap-4">
          <button className="px-4 py-2 bg-gray-100 dark:bg-gray-800 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 flex items-center gap-2">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
            </svg>
            Share Link
          </button>
          <button className="px-4 py-2 bg-gray-100 dark:bg-gray-800 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 flex items-center gap-2">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Download
          </button>
        </div>
      )}
    </div>
  )

  if (isFullscreen) {
    return (
      <div className="fixed inset-0 z-50 bg-white dark:bg-gray-900 flex flex-col">
        <div className="flex-1 flex items-center justify-center">
          <div className="w-full max-w-md">
            {PlayerContent}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 flex items-center">
      {PlayerContent}
    </div>
  )
}

// Audio card for the feed
function AudioCard({ audio, onPlay, isActive }) {
  const config = TYPE_CONFIG[audio.type] || TYPE_CONFIG.report
  const isGenerating = audio.status === 'generating'

  return (
    <div
      onClick={() => !isGenerating && onPlay(audio)}
      className={`bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4 cursor-pointer transition-all ${
        isActive ? 'ring-2 ring-purple-500' : 'hover:shadow-md hover:border-purple-300 dark:hover:border-purple-600'
      } ${isGenerating ? 'opacity-60 cursor-wait' : ''}`}
    >
      <div className="flex items-start gap-4">
        {/* Icon */}
        <div className={`w-14 h-14 ${config.color} rounded-xl flex items-center justify-center flex-shrink-0`}>
          {isGenerating ? (
            <div className="w-6 h-6 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : (
            <span className="text-2xl">{config.icon}</span>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-xs px-2 py-0.5 rounded-full text-white ${config.color}`}>
              {config.label}
            </span>
            {isGenerating && (
              <span className="text-xs text-yellow-600 dark:text-yellow-400">Generating...</span>
            )}
          </div>
          <h3 className="font-semibold text-gray-900 dark:text-white truncate">{audio.title}</h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 line-clamp-2 mt-1">{audio.description}</p>
          <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
            <span>{audio.date}</span>
            <span>•</span>
            <span>{audio.duration}</span>
          </div>
        </div>

        {/* Play button */}
        {!isGenerating && (
          <button className={`w-10 h-10 ${config.color} rounded-full flex items-center justify-center text-white flex-shrink-0 hover:opacity-90 transition-opacity`}>
            <svg className="w-5 h-5 ml-0.5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M8 5v14l11-7z" />
            </svg>
          </button>
        )}
      </div>

      {/* Tags */}
      <div className="flex flex-wrap gap-1 mt-3">
        {audio.tags.map(tag => (
          <span
            key={tag}
            className="text-xs px-2 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded-full"
          >
            #{tag}
          </span>
        ))}
      </div>
    </div>
  )
}

// Filter pills
function FilterPills({ filters, activeFilter, onFilterChange }) {
  return (
    <div className="flex gap-2 overflow-x-auto pb-2 -mx-4 px-4">
      {filters.map(filter => (
        <button
          key={filter.id}
          onClick={() => onFilterChange(filter.id)}
          className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${
            activeFilter === filter.id
              ? 'bg-purple-500 text-white'
              : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
          }`}
        >
          {filter.icon} {filter.label}
        </button>
      ))}
    </div>
  )
}

export default function Audio() {
  const [searchParams, setSearchParams] = useSearchParams()
  const audioId = searchParams.get('id')

  const [audioList] = useState(SAMPLE_AUDIO)
  const [activeAudio, setActiveAudio] = useState(null)
  const [showFullscreen, setShowFullscreen] = useState(false)
  const [activeFilter, setActiveFilter] = useState('all')

  const filters = [
    { id: 'all', label: 'All', icon: '🎵' },
    { id: 'report', label: 'Reports', icon: '📊' },
    { id: 'update', label: 'Updates', icon: '📰' },
    { id: 'brief', label: 'Briefs', icon: '☀️' },
    { id: 'research', label: 'Research', icon: '🔬' },
  ]

  // Handle direct link to audio
  useEffect(() => {
    if (audioId) {
      const audio = audioList.find(a => a.id === audioId)
      if (audio) {
        setActiveAudio(audio)
        // On mobile, go fullscreen automatically for direct links
        if (window.innerWidth < 768) {
          setShowFullscreen(true)
        }
      }
    }
  }, [audioId, audioList])

  const handlePlay = (audio) => {
    setActiveAudio(audio)
    setSearchParams({ id: audio.id })
    // On mobile, go fullscreen
    if (window.innerWidth < 768) {
      setShowFullscreen(true)
    }
  }

  const handleCloseFullscreen = () => {
    setShowFullscreen(false)
  }

  // Filter audio
  const filteredAudio = activeFilter === 'all'
    ? audioList
    : audioList.filter(a => a.type === activeFilter)

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-4 py-3">
        <div className="max-w-2xl mx-auto">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-3">
              <Link to="/" className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                </svg>
              </Link>
              <h1 className="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                <span>🎧</span> Audio
              </h1>
            </div>
            <span className="text-sm text-gray-500">{filteredAudio.length} clips</span>
          </div>

          {/* Filters */}
          <FilterPills
            filters={filters}
            activeFilter={activeFilter}
            onFilterChange={setActiveFilter}
          />
        </div>
      </header>

      {/* Content */}
      <main className="max-w-2xl mx-auto p-4">
        {/* Currently playing (desktop mini player) */}
        {activeAudio && !showFullscreen && window.innerWidth >= 768 && (
          <div className="mb-4">
            <AudioPlayer audio={activeAudio} isFullscreen={false} />
          </div>
        )}

        {/* Audio feed */}
        <div className="space-y-4">
          {filteredAudio.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <span className="text-4xl block mb-3">🎵</span>
              <p>No audio clips yet</p>
              <p className="text-sm mt-1">Your agent will create reports and summaries here</p>
            </div>
          ) : (
            filteredAudio.map(audio => (
              <AudioCard
                key={audio.id}
                audio={audio}
                onPlay={handlePlay}
                isActive={activeAudio?.id === audio.id}
              />
            ))
          )}
        </div>
      </main>

      {/* Fullscreen player (mobile) */}
      {showFullscreen && activeAudio && (
        <AudioPlayer
          audio={activeAudio}
          isFullscreen={true}
          onClose={handleCloseFullscreen}
        />
      )}
    </div>
  )
}
