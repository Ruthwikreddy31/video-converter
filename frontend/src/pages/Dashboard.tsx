import { useState, useEffect } from 'react'
import { videoApi, Stats } from '../api/videoApi'
import { Film, Zap, CheckCircle2, XCircle, Clock, TrendingUp, Loader2 } from 'lucide-react'

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    videoApi.getStats()
      .then(setStats)
      .catch(() => setError('Could not load stats. Make sure the backend is running.'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-cinema-gold animate-spin" />
      </div>
    )
  }

  if (error || !stats) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12 text-center">
        <p className="text-cinema-text-dim">{error || 'No data available'}</p>
      </div>
    )
  }

  const formatLabel: Record<string, string> = {
    scope: 'Scope (2.39:1)',
    digital_imax: 'Digital IMAX (1.90:1)',
    full_imax: 'Full IMAX (1.43:1)',
  }

  const formatColor: Record<string, string> = {
    scope: 'bg-amber-500',
    digital_imax: 'bg-blue-500',
    full_imax: 'bg-purple-500',
  }

  const totalFormatCount = Object.values(stats.format_breakdown).reduce((a, b) => a + b, 0)

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
      <div className="mb-8">
        <h1 className="font-display text-2xl font-bold text-cinema-text">Dashboard</h1>
        <p className="text-cinema-text-dim text-sm mt-1">Processing statistics and analytics</p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
        {[
          { icon: Film, label: 'Total Videos', value: stats.total_videos, color: 'text-cinema-gold' },
          { icon: Zap, label: 'Conversions', value: stats.total_conversions, color: 'text-blue-400' },
          { icon: CheckCircle2, label: 'Completed', value: stats.completed_conversions, color: 'text-green-400' },
          { icon: XCircle, label: 'Failed', value: stats.failed_conversions, color: 'text-red-400' },
        ].map(({ icon: Icon, label, value, color }) => (
          <div key={label} className="cinema-card p-5">
            <Icon className={`w-5 h-5 ${color} mb-3`} />
            <p className="text-cinema-text text-2xl font-bold font-mono">{value}</p>
            <p className="text-cinema-text-dim text-xs mt-1">{label}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
        {/* Format breakdown */}
        <div className="cinema-card p-6">
          <h3 className="text-cinema-text font-medium mb-5 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-cinema-gold" />
            Format Breakdown
          </h3>
          <div className="space-y-4">
            {Object.entries(stats.format_breakdown).map(([fmt, count]) => (
              <div key={fmt}>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-cinema-text text-sm">{formatLabel[fmt] || fmt}</span>
                  <span className="text-cinema-text-dim text-xs font-mono">{count} conversions</span>
                </div>
                <div className="h-2 bg-cinema-black rounded-full overflow-hidden">
                  <div
                    className={`h-full ${formatColor[fmt] || 'bg-cinema-gold'} rounded-full transition-all`}
                    style={{ width: totalFormatCount > 0 ? `${(count / totalFormatCount) * 100}%` : '0%' }}
                  />
                </div>
              </div>
            ))}
            {Object.keys(stats.format_breakdown).length === 0 && (
              <p className="text-cinema-text-dim text-sm">No conversions yet</p>
            )}
          </div>
        </div>

        {/* Performance metrics */}
        <div className="cinema-card p-6">
          <h3 className="text-cinema-text font-medium mb-5 flex items-center gap-2">
            <Clock className="w-4 h-4 text-cinema-gold" />
            Performance
          </h3>
          <div className="space-y-4">
            <div className="flex justify-between py-3 border-b border-cinema-border">
              <span className="text-cinema-text-dim text-sm">Success Rate</span>
              <span className="text-green-400 font-mono text-sm font-medium">{stats.success_rate}%</span>
            </div>
            <div className="flex justify-between py-3 border-b border-cinema-border">
              <span className="text-cinema-text-dim text-sm">Avg Processing Time</span>
              <span className="text-cinema-text font-mono text-sm">{stats.avg_processing_time_seconds}s</span>
            </div>
            <div className="flex justify-between py-3">
              <span className="text-cinema-text-dim text-sm">Most Used Format</span>
              <span className="text-cinema-gold font-mono text-sm">
                {formatLabel[stats.most_used_format] || stats.most_used_format}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
