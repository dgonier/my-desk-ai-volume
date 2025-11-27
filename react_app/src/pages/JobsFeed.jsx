import { useState, useEffect } from 'react'

function JobsFeed() {
  const [jobData, setJobData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)
  const [filterLevel, setFilterLevel] = useState('')
  const [filterType, setFilterType] = useState('')
  const [userProfile, setUserProfile] = useState(null)

  const fetchUserProfile = async () => {
    try {
      const response = await fetch('/api/user-profile')
      const data = await response.json()
      if (data.profile) {
        setUserProfile(data.profile)
      }
    } catch (err) {
      console.error('Error fetching user profile:', err)
    }
  }

  const fetchJobs = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/jobs')
      const data = await response.json()
      // Handle nested structure: data.jobs contains the job data object
      setJobData(data.jobs || null)
      if (data.updated) {
        setLastUpdated(new Date(data.updated * 1000))
      }
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchUserProfile()
    fetchJobs()
  }, [])

  // Get jobs array from nested structure
  const jobs = jobData?.jobs || []

  const filteredJobs = jobs.filter(job => {
    if (filterLevel && (job.level || '').toLowerCase() !== filterLevel.toLowerCase()) return false
    if (filterType && (job.type || '').toLowerCase() !== filterType.toLowerCase()) return false
    return true
  })

  const getLevelColor = (level) => {
    const colors = {
      entry: 'bg-green-100 text-green-800',
      mid: 'bg-blue-100 text-blue-800',
      senior: 'bg-purple-100 text-purple-800',
      various: 'bg-gray-100 text-gray-800'
    }
    return colors[(level || '').toLowerCase()] || 'bg-gray-100 text-gray-800'
  }

  const getTypeColor = (type) => {
    const colors = {
      remote: 'bg-green-100 text-green-800',
      hybrid: 'bg-yellow-100 text-yellow-800',
      onsite: 'bg-red-100 text-red-800'
    }
    return colors[(type || '').toLowerCase()] || 'bg-gray-100 text-gray-800'
  }

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-48 mb-4"></div>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3].map(i => (
              <div key={i} className="bg-white rounded-lg shadow p-6">
                <div className="h-4 bg-gray-200 rounded w-3/4 mb-4"></div>
                <div className="h-3 bg-gray-200 rounded w-1/2 mb-2"></div>
                <div className="h-3 bg-gray-200 rounded w-2/3"></div>
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <div className="text-4xl mb-4">Error loading jobs</div>
          <p className="text-red-600">{error}</p>
          <button
            onClick={fetchJobs}
            className="mt-4 bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
          >
            Try Again
          </button>
        </div>
      </div>
    )
  }

  // Get user's location string
  const userLocation = userProfile?.location
    ? `${userProfile.location.city}, ${userProfile.location.state}`
    : null

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              {userProfile ? `Jobs for ${userProfile.first_name}` : 'Jobs Feed'}
            </h1>
            {userLocation && !jobData?.search_query && (
              <p className="text-gray-600 mt-2">Searching in {userLocation}</p>
            )}
            {jobData?.search_query && (
              <p className="text-gray-600 mt-2">{jobData.search_query}</p>
            )}
          </div>
          {userProfile && (
            <div className="text-right text-sm text-gray-500">
              <div className="font-medium text-gray-700">{userProfile.first_name}</div>
              <div>{userLocation}</div>
            </div>
          )}
        </div>
        {jobData?.date_retrieved && (
          <p className="text-sm text-gray-500 mt-1">
            Data from: {jobData.date_retrieved}
          </p>
        )}
        {lastUpdated && (
          <p className="text-sm text-gray-500">
            Last updated: {lastUpdated.toLocaleDateString()} {lastUpdated.toLocaleTimeString()}
          </p>
        )}
      </div>

      {/* Salary Overview */}
      {jobData?.salary_range && (
        <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg shadow p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">Salary Ranges</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="text-center">
              <div className="text-sm text-gray-500">Entry Level</div>
              <div className="text-lg font-bold text-green-600">{jobData.salary_range.entry_level}</div>
            </div>
            <div className="text-center">
              <div className="text-sm text-gray-500">Mid Level</div>
              <div className="text-lg font-bold text-blue-600">{jobData.salary_range.mid_level}</div>
            </div>
            <div className="text-center">
              <div className="text-sm text-gray-500">Senior Level</div>
              <div className="text-lg font-bold text-purple-600">{jobData.salary_range.senior_level}</div>
            </div>
          </div>
        </div>
      )}

      {/* Top Skills */}
      {jobData?.top_skills_required && (
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-3">Top Skills Required</h2>
          <div className="flex flex-wrap gap-2">
            {jobData.top_skills_required.map((skill, i) => (
              <span key={i} className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm">
                {skill}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4 mb-6 flex flex-wrap gap-4 items-center">
        <div>
          <label className="text-sm font-medium text-gray-700">Level:</label>
          <select
            value={filterLevel}
            onChange={(e) => setFilterLevel(e.target.value)}
            className="ml-2 border rounded px-2 py-1 text-sm"
          >
            <option value="">All Levels</option>
            <option value="entry">Entry</option>
            <option value="mid">Mid</option>
            <option value="senior">Senior</option>
          </select>
        </div>
        <div>
          <label className="text-sm font-medium text-gray-700">Type:</label>
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="ml-2 border rounded px-2 py-1 text-sm"
          >
            <option value="">All Types</option>
            <option value="remote">Remote</option>
            <option value="hybrid">Hybrid</option>
            <option value="onsite">On-site</option>
          </select>
        </div>
        <div className="flex-1"></div>
        <div className="text-sm text-gray-600">
          {filteredJobs.length} of {jobs.length} jobs
        </div>
        <button
          onClick={fetchJobs}
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700"
        >
          Refresh
        </button>
      </div>

      {/* Job Cards */}
      {filteredJobs.length === 0 ? (
        <div className="text-center py-16">
          <div className="text-6xl mb-4">briefcase</div>
          <h3 className="text-xl font-semibold text-gray-700 mb-2">No jobs found</h3>
          <p className="text-gray-500 mb-4">
            {jobs.length === 0
              ? `Send "find jobs for me" via WhatsApp to get started!${userLocation ? ` (Searching in ${userLocation})` : ''}`
              : 'Try adjusting your filters'}
          </p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredJobs.map((job, index) => (
            <div
              key={index}
              className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow"
            >
              <div className="flex justify-between items-start mb-3 flex-wrap gap-2">
                <span className={`px-2 py-1 rounded text-xs font-medium ${getLevelColor(job.level)}`}>
                  {job.level || 'Various'}
                </span>
                <span className={`px-2 py-1 rounded text-xs font-medium ${getTypeColor(job.type)}`}>
                  {job.type || 'Unknown'}
                </span>
              </div>
              <h3 className="font-semibold text-lg text-gray-900 mb-1 line-clamp-2">
                {job.title || 'Untitled'}
              </h3>
              <p className="text-gray-700 font-medium mb-2">{job.company || 'Unknown Company'}</p>
              <p className="text-gray-500 text-sm mb-3">
                {job.location || 'Location not specified'}
              </p>
              {job.salary && job.salary !== 'Not listed' && (
                <p className="text-green-600 font-semibold mb-3">{job.salary}</p>
              )}
              {job.benefits && (
                <p className="text-gray-500 text-sm mb-3">
                  {job.benefits}
                </p>
              )}
              <div className="flex justify-between items-center mt-4 pt-4 border-t">
                <span className="text-xs text-gray-400">{job.source || 'Unknown source'}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Nearby Cities */}
      {jobData?.nearby_cities_with_openings && (
        <div className="mt-8 bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-3">Also Hiring Nearby</h2>
          <div className="flex flex-wrap gap-2">
            {jobData.nearby_cities_with_openings.map((city, i) => (
              <span key={i} className="px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-sm">
                {city}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Sources */}
      {jobData?.sources && (
        <div className="mt-6 text-center text-sm text-gray-500">
          <p>Data aggregated from {jobData.sources.length} sources</p>
        </div>
      )}
    </div>
  )
}

export default JobsFeed
