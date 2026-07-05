import { useState, useEffect } from 'react'
import { videoApi, ConversionHistoryItem } from '../api/videoApi'
import { Download, Clock, CheckCircle2, XCircle, Loader2, Film, AlertCircle } from 'lucide-react'
import clsx from 'clsx'

const FORMAT_LABELS: Record<string, string> = {
  scope: 'Scope',
  digital_imax: 'Digital IMAX',
  full_imax: 'Full IMAX',
}

const FORMAT_COLORS: Record<string, string> = {
  scope: 'scope-badge',
  digital_imax: 'imax-badge',
  full_imax: 'full-imax-badge',
}

export default function History() {
  const [items, setItems] = useState<ConversionHistoryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    videoApi.getHistory()
      .then(setItems)
      .catch(() => setError('Could not load history. Make sure the backend is running.'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-cinema-gold animate-spin" />
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
      <div className="mb-8">
        <h1 className="font-display text-2xl font-bold text-cinema-text">Conversion History</h1>
        <p className="text-cinema-text-dim text-sm mt-1">{items.length} conversions</p>
      </div>

      {error && (
        <div className="flex items-center gap-3 bg-red-500/10 border border-red-500/20 rounded-xl p-4 mb-6">
          <AlertCircle className="w-4 h-4 text-red-400" />
          <p className="text-red-400 text-sm">{error}</p>
        </div>
      )}

      {items.length === 0 ? (
        <div className="cinema-card p-16 text-center">
          <Film className="w-10 h-10 text-cinema-text-dim/40 mx-auto mb-3" />
          <p className="text-cinema-text-dim">No conversions yet.</p>
          <p className="text-cinema-text-dim/60 text-sm mt-1">Convert a video to see history here.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <div key={item.id} className="cinema-card p-4 flex items-center gap-4">
              {/* Thumbnail */}
              <div className="w-16 h-10 rounded-lg bg-cinema-black overflow-hidden flex-shrink-0">
                {item.thumbnail_url ? (
                  <img src={item.thumbnail_url} alt="" className="w-full h-full object-cover" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <Film className="w-4 h-4 text-cinema-text-dim/40" />
                  </div>
                )}
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <p className="text-cinema-text text-sm font-medium truncate">{item.filename}</p>
                <div className="flex items-center gap-3 mt-1">
                  <span className={FORMAT_COLORS[item.target_format] || 'standard-badge'}>
                    {FORMAT_LABELS[item.target_format] || item.target_format}
                  </span>
                  {item.processing_time && (
                    <span className="flex items-center gap-1 text-cinema-text-dim text-xs">
                      <Clock className="w-3 h-3" />
                      {item.processing_time.toFixed(1)}s
                    </span>
                  )}
                  {item.crop_method && (
                    <span className="text-cinema-text-dim text-xs">{item.crop_method}</span>
                  )}
                </div>
              </div>

              {/* Status */}
              <div className="flex items-center gap-3 flex-shrink-0">
                {item.status === 'completed' ? (
                  <CheckCircle2 className="w-4 h-4 text-green-400" />
                ) : item.status === 'failed' ? (
                  <XCircle className="w-4 h-4 text-red-400" />
                ) : (
                  <Loader2 className="w-4 h-4 text-cinema-gold animate-spin" />
                )}

                {item.output_url && item.status === 'completed' && (
                  <a
                    href={item.output_url}
                    download
                    className="flex items-center gap-2 px-3 py-1.5 bg-cinema-gold text-cinema-black text-xs font-semibold rounded-lg hover:bg-amber-400 transition-colors"
                  >
                    <Download className="w-3 h-3" />
                    Download
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
