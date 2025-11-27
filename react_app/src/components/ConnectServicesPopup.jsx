import { useState, useEffect } from 'react'

// Service configurations
const SERVICES = [
  {
    id: 'linkedin',
    name: 'LinkedIn',
    description: 'Import your professional profile, connections, and career history',
    icon: (
      <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
        <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
      </svg>
    ),
    color: 'from-blue-600 to-blue-700',
    bgColor: 'bg-blue-50 dark:bg-blue-900/30',
    textColor: 'text-blue-600 dark:text-blue-400',
  },
  {
    id: 'github',
    name: 'GitHub',
    description: 'Connect your repositories, contributions, and coding activity',
    icon: (
      <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
        <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
      </svg>
    ),
    color: 'from-gray-700 to-gray-900',
    bgColor: 'bg-gray-100 dark:bg-gray-800',
    textColor: 'text-gray-900 dark:text-gray-100',
  },
  {
    id: 'google',
    name: 'Google Services',
    description: 'Already connected via login. Includes Calendar, Gmail, Drive, and more.',
    icon: (
      <svg className="w-6 h-6" viewBox="0 0 24 24">
        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
        <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
      </svg>
    ),
    color: 'from-green-500 to-green-600',
    bgColor: 'bg-green-50 dark:bg-green-900/30',
    textColor: 'text-green-600 dark:text-green-400',
    alreadyConnected: true,
  },
]

export default function ConnectServicesPopup({ isOpen, onClose, onComplete }) {
  const [serviceStatus, setServiceStatus] = useState({})
  const [loading, setLoading] = useState(true)
  const [connecting, setConnecting] = useState(null)

  // Fetch OAuth status on mount
  useEffect(() => {
    if (isOpen) {
      fetchOAuthStatus()
    }
  }, [isOpen])

  const fetchOAuthStatus = async () => {
    try {
      const response = await fetch('/oauth/status')
      if (response.ok) {
        const status = await response.json()
        setServiceStatus(status)
      }
    } catch (error) {
      console.error('Failed to fetch OAuth status:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleConnect = (serviceId) => {
    setConnecting(serviceId)
    // Redirect to OAuth flow - this will redirect back to the app after auth
    window.location.href = `/oauth/connect/${serviceId}?redirect=${encodeURIComponent(window.location.pathname + '?showConnectPopup=1')}`
  }

  const handleSkip = () => {
    // Save preference to not show again for this session
    sessionStorage.setItem('skipConnectServices', 'true')
    onClose()
  }

  const handleDone = () => {
    onComplete?.()
    onClose()
  }

  const connectedCount = Object.values(serviceStatus).filter(Boolean).length + 1 // +1 for Google (always connected via login)

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
              Connect Your Services
            </h2>
            <button
              onClick={handleSkip}
              className="text-gray-400 hover:text-gray-500 dark:hover:text-gray-300"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <p className="text-gray-600 dark:text-gray-400">
            Connect your accounts to help your AI agent understand you better and provide personalized assistance.
          </p>
        </div>

        {/* Services List */}
        <div className="p-6 space-y-4">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
            </div>
          ) : (
            <>
              {SERVICES.map((service) => {
                const isConnected = service.alreadyConnected || serviceStatus[service.id]
                const isCurrentlyConnecting = connecting === service.id

                return (
                  <div
                    key={service.id}
                    className={`${service.bgColor} rounded-xl p-4 transition-all ${
                      isConnected ? 'ring-2 ring-green-500' : ''
                    }`}
                  >
                    <div className="flex items-start gap-4">
                      <div className={`${service.textColor} flex-shrink-0`}>
                        {service.icon}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <h3 className="font-semibold text-gray-900 dark:text-white">
                            {service.name}
                          </h3>
                          {isConnected && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200">
                              <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                              </svg>
                              Connected
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                          {service.description}
                        </p>
                      </div>
                      {!isConnected && (
                        <button
                          onClick={() => handleConnect(service.id)}
                          disabled={isCurrentlyConnecting}
                          className={`flex-shrink-0 px-4 py-2 bg-gradient-to-r ${service.color} text-white rounded-lg font-medium text-sm hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed`}
                        >
                          {isCurrentlyConnecting ? (
                            <span className="flex items-center gap-2">
                              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                              </svg>
                              Connecting...
                            </span>
                          ) : (
                            'Connect'
                          )}
                        </button>
                      )}
                    </div>
                  </div>
                )
              })}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50 rounded-b-2xl">
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {connectedCount} of {SERVICES.length} services connected
            </p>
            <div className="flex gap-3">
              <button
                onClick={handleSkip}
                className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition-colors"
              >
                Skip for now
              </button>
              <button
                onClick={handleDone}
                className="px-6 py-2 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-lg font-medium hover:opacity-90 transition-opacity"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
