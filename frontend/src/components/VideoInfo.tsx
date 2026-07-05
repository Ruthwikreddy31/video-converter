import { VideoInfo as VideoInfoType } from '../api/videoApi'
import { Clock, Maximize2, Zap, HardDrive, Monitor, Film } from 'lucide-react'
import clsx from 'clsx'

interface Props {
  info: VideoInfoType
  filename: string
  thumbnailUrl?: string | null
}

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  return `${m}:${String(s).padStart(2, '0')}`
}

function formatSize(bytes: number): string {
  if (bytes > 1e9) return `${(bytes / 1e9).toFixed(1)} GB`
  if (bytes > 1e6) return `${(bytes / 1e6).toFixed(1)} MB`
  return `${(bytes / 1e3).toFixed(0)} KB`
}

function getFormatBadge(format: string) {
  if (format.toLowerCase().includes('scope')) return { class: 'scope-badge', label: format }
  if (format.toLowerCase().includes('imax') && format.includes('1.90')) return { class: 'imax-badge', label: format }
  if (format.toLowerCase().includes('full imax')) return { class: 'full-imax-badge', label: format }
  return { class: 'standard-badge', label: format }
}

export default function VideoInfoComponent({ info, filename, thumbnailUrl }: Props) {
  const badge = getFormatBadge(info.detected_format)

  const stats = [
    { icon: Maximize2, label: 'Resolution', value: `${info.width}×${info.height}` },
    { icon: Monitor, label: 'Aspect Ratio', value: info.aspect_ratio },
    { icon: Clock, label: 'Duration', value: formatDuration(info.duration) },
    { icon: Zap, label: 'Frame Rate', value: `${info.fps} fps` },
    { icon: HardDrive, label: 'File Size', value: formatSize(info.file_size) },
    { icon: Film, label: 'Codec', value: `${info.video_codec.toUpperCase()} / ${info.audio_codec.toUpperCase()}` },
  ]

  return (
    <div className="cinema-card overflow-hidden">
      {/* Thumbnail header */}
      {thumbnailUrl && (
        <div className="relative w-full bg-cinema-black" style={{ aspectRatio: '16/7' }}>
          <img
            src={thumbnailUrl}
            alt="Video thumbnail"
            className="w-full h-full object-cover opacity-80"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-cinema-card via-transparent to-transparent" />
          <div className="absolute bottom-3 left-4 right-4 flex items-end justify-between">
            <p className="text-cinema-text text-sm font-medium truncate max-w-xs">{filename}</p>
            <span className={badge.class}>{badge.label}</span>
          </div>
        </div>
      )}

      <div className="p-5">
        {!thumbnailUrl && (
          <div className="flex items-center justify-between mb-4">
            <p className="text-cinema-text font-medium truncate">{filename}</p>
            <span className={badge.class}>{badge.label}</span>
          </div>
        )}

        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {stats.map(({ icon: Icon, label, value }) => (
            <div key={label} className="bg-cinema-black rounded-lg p-3">
              <div className="flex items-center gap-2 mb-1">
                <Icon className="w-3 h-3 text-cinema-gold/60" />
                <span className="text-cinema-text-dim text-xs uppercase tracking-wider">{label}</span>
              </div>
              <p className="text-cinema-text text-sm font-mono font-medium">{value}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
