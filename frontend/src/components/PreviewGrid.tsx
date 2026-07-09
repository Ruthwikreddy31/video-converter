import { useState, useEffect, useRef } from 'react'
import { Play, Pause, Volume2, VolumeX, Maximize2, Loader2, Film, Monitor, Tv, Eye, Layers } from 'lucide-react'
import clsx from 'clsx'

import { ensureAbsoluteUrl } from '../api/videoApi'

interface Props {
  videoId: string
  videoUrl?: string
}

interface FormatOption {
  key: string
  label: string
  ratioText: string
  ratio: number // aspect ratio decimal (width / height)
  desc: string
  icon: any
}

const FORMAT_OPTIONS: FormatOption[] = [
  {
    key: 'imax_70mm',
    label: 'IMAX 70MM',
    ratioText: '1.43:1',
    ratio: 1.43,
    desc: 'Original 15/70 film IMAX format',
    icon: Film
  },
  {
    key: 'large_format',
    label: 'Large Format',
    ratioText: '1.85:1 | 2.39:1',
    ratio: 1.85,
    desc: 'Premium Large Format screens',
    icon: Monitor
  },
  {
    key: 'imax_digital',
    label: 'IMAX',
    ratioText: '1.90:1',
    ratio: 1.90,
    desc: 'Digital IMAX/Xenon projection format',
    icon: Monitor
  },
  {
    key: '70mm_std',
    label: '70MM',
    ratioText: '2.20:1',
    ratio: 2.20,
    desc: 'Standard Todd-AO 70mm theatrical print',
    icon: Layers
  },
  {
    key: '35mm_std',
    label: '35MM',
    ratioText: '2.39:1',
    ratio: 2.39,
    desc: 'Anamorphic widescreen theatrical standard',
    icon: Tv
  },
  {
    key: 'dolby_vision',
    label: 'Dolby Vision',
    ratioText: '1.85:1 | 2.39:1',
    ratio: 1.85,
    desc: 'High dynamic range theatrical presentation',
    icon: Eye
  }
]

export default function PreviewGrid({ videoId, videoUrl }: Props) {
  const [activeFormat, setActiveFormat] = useState<FormatOption>(FORMAT_OPTIONS[0])
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [volume, setVolume] = useState(0.8)
  const [isMuted, setIsMuted] = useState(false)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [videoLoaded, setVideoLoaded] = useState(false)

  const videoRef = useRef<HTMLVideoElement>(null)
  const playerContainerRef = useRef<HTMLDivElement>(null)

  // Sync state with HTML5 Video element events
  useEffect(() => {
    const video = videoRef.current
    if (!video) return

    const handlePlay = () => setIsPlaying(true)
    const handlePause = () => setIsPlaying(false)
    const handleTimeUpdate = () => setCurrentTime(video.currentTime)
    const handleDurationChange = () => setDuration(video.duration)
    const handleLoadedMetadata = () => {
      setDuration(video.duration)
      setVideoLoaded(true)
    }

    video.addEventListener('play', handlePlay)
    video.addEventListener('pause', handlePause)
    video.addEventListener('timeupdate', handleTimeUpdate)
    video.addEventListener('durationchange', handleDurationChange)
    video.addEventListener('loadedmetadata', handleLoadedMetadata)

    // Force play status if already playing
    setIsPlaying(!video.paused)

    return () => {
      video.removeEventListener('play', handlePlay)
      video.removeEventListener('pause', handlePause)
      video.removeEventListener('timeupdate', handleTimeUpdate)
      video.removeEventListener('durationchange', handleDurationChange)
      video.removeEventListener('loadedmetadata', handleLoadedMetadata)
    }
  }, [videoUrl])

  const togglePlay = () => {
    const video = videoRef.current
    if (!video) return
    if (video.paused) {
      video.play().catch(() => {})
    } else {
      video.pause()
    }
  }

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const video = videoRef.current
    if (!video) return
    const newTime = parseFloat(e.target.value)
    video.currentTime = newTime
    setCurrentTime(newTime)
  }

  const toggleMute = () => {
    const video = videoRef.current
    if (!video) return
    video.muted = !isMuted
    setIsMuted(!isMuted)
  }

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const video = videoRef.current
    if (!video) return
    const newVol = parseFloat(e.target.value)
    video.volume = newVol
    setVolume(newVol)
    if (newVol > 0 && isMuted) {
      video.muted = false;
      setIsMuted(false);
    }
  }

  const toggleFullscreen = () => {
    const container = playerContainerRef.current
    if (!container) return

    if (!document.fullscreenElement) {
      container.requestFullscreen().then(() => {
        setIsFullscreen(true)
      }).catch(() => {})
    } else {
      document.exitFullscreen().then(() => {
        setIsFullscreen(false)
      }).catch(() => {})
    }
  }

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement)
    }
    document.addEventListener('fullscreenchange', handleFullscreenChange)
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange)
  }, [])

  const formatTime = (time: number) => {
    if (isNaN(time)) return '0:00'
    const minutes = Math.floor(time / 60)
    const seconds = Math.floor(time % 60)
    return `${minutes}:${seconds.toString().padStart(2, '0')}`
  }

  const streamUrl = ensureAbsoluteUrl(videoUrl ? videoUrl : `/uploads/${videoId}.mp4`)

  return (
    <div className="bg-cinema-black/40 border border-cinema-border rounded-2xl p-6 space-y-6">
      {/* Format Selector Tabs */}
      <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
        {FORMAT_OPTIONS.map((opt) => {
          const Icon = opt.icon
          const isActive = activeFormat.key === opt.key
          return (
            <button
              key={opt.key}
              onClick={() => setActiveFormat(opt)}
              className={clsx(
                'flex flex-col items-center justify-between p-3 rounded-xl border transition-all text-center group min-h-[92px]',
                isActive
                  ? 'bg-cinema-gold/10 border-cinema-gold text-cinema-gold font-semibold shadow-lg shadow-cinema-gold/10'
                  : 'bg-cinema-card/50 border-cinema-border hover:border-cinema-muted text-cinema-text-dim hover:text-cinema-text'
              )}
            >
              <Icon className={clsx('w-5 h-5 mb-2 transition-transform group-hover:scale-105', isActive ? 'text-cinema-gold' : 'text-cinema-text-dim')} />
              <div className="flex-1 flex flex-col justify-center">
                <span className="text-[10px] sm:text-xs tracking-wider uppercase font-mono">{opt.label}</span>
                <span className="text-[9px] sm:text-[10px] font-mono opacity-80 mt-0.5">{opt.ratioText}</span>
              </div>
            </button>
          )
        })}
      </div>

      {/* Video Preview Container */}
      <div 
        ref={playerContainerRef}
        className={clsx(
          "relative bg-black rounded-2xl border border-cinema-border overflow-hidden flex flex-col items-center justify-center transition-all duration-300",
          isFullscreen ? "w-screen h-screen" : "w-full"
        )}
      >
        {/* Dynamic Aspect Ratio Wrapper */}
        <div 
          className="relative w-full overflow-hidden transition-all duration-500 ease-out bg-black flex items-center justify-center"
          style={{ 
            aspectRatio: `${activeFormat.ratio}`,
            maxWidth: isFullscreen ? `calc((100vh - 84px) * ${activeFormat.ratio})` : '100%',
            maxHeight: isFullscreen ? 'calc(100vh - 84px)' : '450px'
          }}
        >
          <video
            ref={videoRef}
            src={streamUrl}
            className="w-full h-full object-cover select-none"
            playsInline
            loop
            onClick={togglePlay}
          />

          {!videoLoaded && (
            <div className="absolute inset-0 bg-cinema-black/80 flex flex-col items-center justify-center gap-3">
              <Loader2 className="w-8 h-8 text-cinema-gold animate-spin" />
              <span className="text-sm text-cinema-text-dim">Loading cinema preview...</span>
            </div>
          )}

          {/* Format Indicator Overlay */}
          <div className="absolute top-4 left-4 bg-black/70 border border-cinema-border px-3 py-1.5 rounded-lg text-xs font-mono text-cinema-gold backdrop-blur-sm pointer-events-none">
            {activeFormat.label} ({activeFormat.ratioText})
          </div>
        </div>

        {/* Custom Video Controls */}
        <div className="w-full bg-cinema-black border-t border-cinema-border px-4 py-3 flex flex-col gap-2.5">
          {/* Progress / Timeline slider */}
          <div className="flex items-center gap-3 group">
            <span className="text-[10px] font-mono text-cinema-text-dim w-8 text-right">
              {formatTime(currentTime)}
            </span>
            <input
              type="range"
              min={0}
              max={duration || 100}
              value={currentTime}
              onChange={handleSeek}
              className="flex-1 h-1.5 rounded-full appearance-none cursor-pointer bg-cinema-border outline-none accent-cinema-gold group-hover:h-2 transition-all"
              style={{
                background: `linear-gradient(to right, #d4a843 0%, #d4a843 ${(currentTime / (duration || 1)) * 100}%, #27272a ${(currentTime / (duration || 1)) * 100}%, #27272a 100%)`
              }}
            />
            <span className="text-[10px] font-mono text-cinema-text-dim w-8">
              {formatTime(duration)}
            </span>
          </div>

          {/* Lower controls row */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              {/* Play/Pause */}
              <button 
                onClick={togglePlay}
                className="p-1.5 rounded-lg text-cinema-text-dim hover:text-cinema-text hover:bg-cinema-card/50 transition-colors"
                title={isPlaying ? 'Pause' : 'Play'}
              >
                {isPlaying ? <Pause className="w-4 h-4 text-cinema-gold" /> : <Play className="w-4 h-4" />}
              </button>

              {/* Volume & Mute */}
              <div className="flex items-center gap-2">
                <button
                  onClick={toggleMute}
                  className="p-1.5 rounded-lg text-cinema-text-dim hover:text-cinema-text hover:bg-cinema-card/50 transition-colors"
                  title={isMuted ? 'Unmute' : 'Mute'}
                >
                  {isMuted || volume === 0 ? <VolumeX className="w-4 h-4 text-red-400" /> : <Volume2 className="w-4 h-4" />}
                </button>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.05}
                  value={isMuted ? 0 : volume}
                  onChange={handleVolumeChange}
                  className="w-16 h-1 rounded-full appearance-none cursor-pointer bg-cinema-border outline-none accent-cinema-text hover:h-1.5 transition-all"
                />
              </div>
            </div>

            {/* Right side controls */}
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono text-cinema-text-dim bg-cinema-card px-2.5 py-1 rounded-md border border-cinema-border">
                SIMULATED PREVIEW
              </span>
              <button
                onClick={toggleFullscreen}
                className="p-1.5 rounded-lg text-cinema-text-dim hover:text-cinema-text hover:bg-cinema-card/50 transition-colors"
                title="Fullscreen"
              >
                <Maximize2 className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
