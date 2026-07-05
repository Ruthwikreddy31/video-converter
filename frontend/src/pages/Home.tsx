import { useState } from 'react'
import { ArrowRight, Film, Maximize2, ChevronDown } from 'lucide-react'
import UploadVideo from '../components/UploadVideo'
import VideoInfoComponent from '../components/VideoInfo'
import ConversionOptions from '../components/ConversionOptions'
import PreviewGrid from '../components/PreviewGrid'
import { VideoInfo } from '../api/videoApi'

interface VideoState {
  videoId: string
  info: VideoInfo
  thumbnailUrl: string
  filename: string
  videoUrl?: string
}

export default function Home() {
  const [video, setVideo] = useState<VideoState | null>(null)

  const handleVideoReady = (videoId: string, info: VideoInfo, thumbnailUrl: string, filename: string, videoUrl?: string) => {
    setVideo({ videoId, info, thumbnailUrl, filename, videoUrl })
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
      {!video ? (
        /* Landing / Upload State */
        <div className="max-w-2xl mx-auto">
          {/* Hero */}
          <div className="text-center mb-10">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-cinema-gold/10 border border-cinema-gold/20 rounded-full text-cinema-gold text-xs font-mono uppercase tracking-wider mb-6">
              <Film className="w-3 h-3" />
              AI-Powered Cinema Conversion
            </div>
            <h1 className="font-display text-4xl sm:text-5xl font-bold text-cinema-text leading-tight mb-4">
              Convert any video to
              <span className="block text-cinema-gold">IMAX format</span>
            </h1>
            <p className="text-cinema-text-dim text-base max-w-lg mx-auto leading-relaxed">
              Transform YouTube videos and local files into Scope, Digital IMAX, or Full IMAX ratios
              using AI-powered smart cropping and FFmpeg processing.
            </p>
          </div>

          {/* Format ratio visualizers */}
          <div className="grid grid-cols-3 gap-3 mb-8">
            {[
              { label: 'Scope', ratio: '2.39:1', desc: 'Anamorphic', color: 'amber', width: '100%', height: '42%' },
              { label: 'Digital IMAX', ratio: '1.90:1', desc: 'Enhanced', color: 'blue', width: '100%', height: '53%' },
              { label: 'Full IMAX', ratio: '1.43:1', desc: 'Maximum', color: 'purple', width: '100%', height: '70%' },
            ].map(({ label, ratio, desc, color, height }) => (
              <div key={label} className="cinema-card p-4 text-center">
                <div className="mb-3 flex items-center justify-center">
                  <div
                    className={`rounded border border-${color}-500/30 bg-${color}-500/10`}
                    style={{ width: '100%', maxWidth: '80px', aspectRatio: ratio.replace(':1', '/ 1') }}
                  />
                </div>
                <p className={`text-${color}-400 text-xs font-semibold`}>{label}</p>
                <p className="text-cinema-text-dim text-xs font-mono">{ratio}</p>
              </div>
            ))}
          </div>

          <UploadVideo onVideoReady={handleVideoReady} />

          {/* How it works */}
          <div className="mt-10 pt-8 border-t border-cinema-border">
            <p className="text-cinema-text-dim text-xs text-center uppercase tracking-widest mb-6">How it works</p>
            <div className="flex items-center justify-center gap-2 text-cinema-text-dim text-xs">
              {['Upload / Paste URL', 'Auto-analyze', 'Choose Format', 'Convert & Download'].map((step, i, arr) => (
                <span key={step} className="flex items-center gap-2">
                  <span className="text-cinema-text">{step}</span>
                  {i < arr.length - 1 && <ArrowRight className="w-3 h-3 text-cinema-gold/40" />}
                </span>
              ))}
            </div>
          </div>
        </div>
      ) : (
        /* Processing State */
        <div>
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-cinema-text font-display text-xl font-semibold">Video Processing</h2>
              <p className="text-cinema-text-dim text-sm mt-0.5">Select a format to convert your video</p>
            </div>
            <button
              onClick={() => setVideo(null)}
              className="text-cinema-text-dim text-sm hover:text-cinema-text transition-colors px-3 py-1.5 border border-cinema-border rounded-lg hover:border-cinema-muted"
            >
              ← New Video
            </button>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left column */}
            <div className="space-y-5">
              <VideoInfoComponent
                info={video.info}
                filename={video.filename}
                thumbnailUrl={video.thumbnailUrl}
              />
              <PreviewGrid videoId={video.videoId} videoUrl={video.videoUrl} />
            </div>

            {/* Right column */}
            <div>
              <ConversionOptions
                videoId={video.videoId}
                videoWidth={video.info.width}
                videoHeight={video.info.height}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
