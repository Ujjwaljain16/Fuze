import React, { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import api from '../services/api'
import { 
  TrendingUp, BarChart3, Clock, Target, Zap, BookOpen, 
  CheckCircle, Star, Calendar, Activity, Brain, Users
} from 'lucide-react'

const Analytics = () => {
  const { isAuthenticated } = useAuth()
  const [analytics, setAnalytics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [timeRange, setTimeRange] = useState('week') // week, month, all

  useEffect(() => {
    if (isAuthenticated) {
      fetchAnalytics()
    }
  }, [isAuthenticated, timeRange])

  const fetchAnalytics = async () => {
    try {
      setLoading(true)
      // Fetch user analytics data
      const response = await api.get(`/api/analytics/overview?range=${timeRange}`)
      setAnalytics(response.data)
    } catch (error) {
      console.error('Failed to fetch analytics:', error)
      // Mock data for now since endpoint doesn't exist yet
      setAnalytics(getMockAnalytics())
    } finally {
      setLoading(false)
    }
  }

  const getMockAnalytics = () => {
    return {
      summary: {
        totalBookmarks: 127,
        totalProjects: 12,
        totalRecommendations: 234,
        learningStreak: 14
      },
      thisWeek: {
        bookmarksAdded: 18,
        projectsCreated: 2,
        recommendationsViewed: 45,
        timeSpent: '12.5 hours'
      },
      topTechnologies: [
        { name: 'Python', count: 45, proficiency: 80 },
        { name: 'React', count: 38, proficiency: 65 },
        { name: 'Docker', count: 28, proficiency: 55 },
        { name: 'Node.js', count: 22, proficiency: 70 },
        { name: 'PostgreSQL', count: 19, proficiency: 60 }
      ],
      learningProgress: [
        { date: 'Mon', value: 2.5 },
        { date: 'Tue', value: 1.8 },
        { date: 'Wed', value: 3.2 },
        { date: 'Thu', value: 2.1 },
        { date: 'Fri', value: 2.9 },
        { date: 'Sat', value: 0 },
        { date: 'Sun', value: 0 }
      ],
      recentActivity: [
        { type: 'bookmark', title: 'Flask REST API Tutorial', time: '2 hours ago' },
        { type: 'project', title: 'Build E-commerce API', time: '5 hours ago' },
        { type: 'recommendation', title: 'PostgreSQL Optimization', time: '1 day ago' }
      ]
    }
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900 flex items-center justify-center p-4">
        <div className="text-center">
          <BarChart3 className="w-16 h-16 text-blue-400 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-white mb-2">Analytics Dashboard</h2>
          <p className="text-gray-300">Please login to view your analytics</p>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900 flex items-center justify-center">
        <div className="text-center">
          <Activity className="w-12 h-12 text-blue-400 animate-pulse mx-auto mb-4" />
          <p className="text-gray-300">Loading analytics...</p>
        </div>
      </div>
    )
  }

  const { summary, thisWeek, topTechnologies, learningProgress } = analytics

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold text-white mb-2">📊 Learning Analytics</h1>
              <p className="text-gray-300">Track your progress and learning journey</p>
            </div>
            <div className="flex gap-2">
              {['week', 'month', 'all'].map((range) => (
                <button
                  key={range}
                  onClick={() => setTimeRange(range)}
                  className={`px-4 py-2 rounded-xl font-medium transition-all ${
                    timeRange === range
                      ? 'bg-blue-500 text-white'
                      : 'bg-white/10 text-gray-300 hover:bg-white/20'
                  }`}
                >
                  {range === 'week' ? 'This Week' : range === 'month' ? 'This Month' : 'All Time'}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-gradient-to-br from-blue-500/20 to-blue-600/20 backdrop-blur-lg rounded-2xl p-6 border border-blue-500/30">
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 bg-blue-500/30 rounded-xl">
                <BookOpen className="w-6 h-6 text-blue-300" />
              </div>
              <span className="text-2xl">📚</span>
            </div>
            <h3 className="text-gray-300 text-sm mb-1">Total Bookmarks</h3>
            <p className="text-3xl font-bold text-white">{summary.totalBookmarks}</p>
            <p className="text-green-400 text-sm mt-2">+{thisWeek.bookmarksAdded} this week</p>
          </div>

          <div className="bg-gradient-to-br from-purple-500/20 to-purple-600/20 backdrop-blur-lg rounded-2xl p-6 border border-purple-500/30">
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 bg-purple-500/30 rounded-xl">
                <Target className="w-6 h-6 text-purple-300" />
              </div>
              <span className="text-2xl">🎯</span>
            </div>
            <h3 className="text-gray-300 text-sm mb-1">Active Projects</h3>
            <p className="text-3xl font-bold text-white">{summary.totalProjects}</p>
            <p className="text-green-400 text-sm mt-2">+{thisWeek.projectsCreated} this week</p>
          </div>

          <div className="bg-gradient-to-br from-green-500/20 to-green-600/20 backdrop-blur-lg rounded-2xl p-6 border border-green-500/30">
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 bg-green-500/30 rounded-xl">
                <Zap className="w-6 h-6 text-green-300" />
              </div>
              <span className="text-2xl">⚡</span>
            </div>
            <h3 className="text-gray-300 text-sm mb-1">Recommendations</h3>
            <p className="text-3xl font-bold text-white">{summary.totalRecommendations}</p>
            <p className="text-green-400 text-sm mt-2">+{thisWeek.recommendationsViewed} viewed</p>
          </div>

          <div className="bg-gradient-to-br from-orange-500/20 to-orange-600/20 backdrop-blur-lg rounded-2xl p-6 border border-orange-500/30">
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 bg-orange-500/30 rounded-xl">
                <Activity className="w-6 h-6 text-orange-300" />
              </div>
              <span className="text-2xl">🔥</span>
            </div>
            <h3 className="text-gray-300 text-sm mb-1">Learning Streak</h3>
            <p className="text-3xl font-bold text-white">{summary.learningStreak} days</p>
            <p className="text-orange-400 text-sm mt-2">{thisWeek.timeSpent} this week</p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          {/* Learning Progress Chart */}
          <div className="lg:col-span-2 bg-white/10 backdrop-blur-lg rounded-2xl p-6 border border-white/20">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-white flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-blue-400" />
                Learning Activity
              </h2>
              <span className="text-sm text-gray-400">Hours per day</span>
            </div>
            <div className="flex items-end justify-between h-64 gap-4">
              {learningProgress.map((day, idx) => {
                const maxValue = Math.max(...learningProgress.map(d => d.value))
                const heightPercent = (day.value / maxValue) * 100
                return (
                  <div key={idx} className="flex-1 flex flex-col items-center gap-2">
                    <div className="relative w-full flex items-end justify-center" style={{ height: '200px' }}>
                      <div 
                        className="w-full bg-gradient-to-t from-blue-500 to-purple-500 rounded-t-lg transition-all hover:from-blue-400 hover:to-purple-400 cursor-pointer"
                        style={{ height: `${heightPercent}%`, minHeight: day.value > 0 ? '10px' : '0' }}
                        title={`${day.value} hours`}
                      />
                    </div>
                    <span className="text-xs text-gray-400">{day.date}</span>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Technology Mastery */}
          <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-6 border border-white/20">
            <h2 className="text-xl font-semibold text-white mb-6 flex items-center gap-2">
              <Brain className="w-5 h-5 text-purple-400" />
              Technology Mastery
            </h2>
            <div className="space-y-4">
              {topTechnologies.map((tech, idx) => (
                <div key={idx}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-gray-200 font-medium">{tech.name}</span>
                    <span className="text-sm text-gray-400">{tech.proficiency}%</span>
                  </div>
                  <div className="w-full bg-gray-700/50 rounded-full h-2">
                    <div 
                      className="bg-gradient-to-r from-blue-500 to-purple-500 h-2 rounded-full transition-all"
                      style={{ width: `${tech.proficiency}%` }}
                    />
                  </div>
                  <span className="text-xs text-gray-500 mt-1">{tech.count} resources</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Insights */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Learning Insights */}
          <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-6 border border-white/20">
            <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
              <Star className="w-5 h-5 text-yellow-400" />
              Learning Insights
            </h2>
            <div className="space-y-4">
              <div className="p-4 bg-blue-500/20 border border-blue-500/30 rounded-xl">
                <p className="text-blue-300 text-sm">🎯 Peak Learning Time</p>
                <p className="text-white font-semibold mt-1">9-11 AM weekdays</p>
              </div>
              <div className="p-4 bg-green-500/20 border border-green-500/30 rounded-xl">
                <p className="text-green-300 text-sm">📈 Trending Up</p>
                <p className="text-white font-semibold mt-1">Python +15% this month</p>
              </div>
              <div className="p-4 bg-purple-500/20 border border-purple-500/30 rounded-xl">
                <p className="text-purple-300 text-sm">💡 Recommendation</p>
                <p className="text-white font-semibold mt-1">Focus on Docker this week</p>
              </div>
            </div>
          </div>

          {/* Quick Stats */}
          <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-6 border border-white/20">
            <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-green-400" />
              Quick Stats
            </h2>
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 bg-gradient-to-br from-blue-500/10 to-blue-600/10 rounded-xl border border-blue-500/20">
                <p className="text-blue-300 text-xs mb-1">Avg. Quality Score</p>
                <p className="text-2xl font-bold text-white">8.4/10</p>
              </div>
              <div className="p-4 bg-gradient-to-br from-green-500/10 to-green-600/10 rounded-xl border border-green-500/20">
                <p className="text-green-300 text-xs mb-1">Completion Rate</p>
                <p className="text-2xl font-bold text-white">67%</p>
              </div>
              <div className="p-4 bg-gradient-to-br from-purple-500/10 to-purple-600/10 rounded-xl border border-purple-500/20">
                <p className="text-purple-300 text-xs mb-1">AI Recommendations</p>
                <p className="text-2xl font-bold text-white">89%</p>
              </div>
              <div className="p-4 bg-gradient-to-br from-orange-500/10 to-orange-600/10 rounded-xl border border-orange-500/20">
                <p className="text-orange-300 text-xs mb-1">Weekly Growth</p>
                <p className="text-2xl font-bold text-white">+12%</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Analytics

