import { useState, useRef, useCallback } from 'react'
import { Upload, Link2, X, AlertCircle, Film, Loader2 } from 'lucide-react'
import { videoApi, UploadResponse, DownloadProgress } from '../api/videoApi'
import clsx from 'clsx'

interface Props {
  onVideoReady: (videoId: string, info: any, thumbnailUrl: string, filename: string, videoUrl?: string) => void
}

type Tab = 'upload' | 'youtube'

export default function UploadVideo({ onVideoReady }: Props) {
  const [tab, setTab] = useState<Tab>('upload')
  const [isDragging, setIsDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [youtubeUrl, setYoutubeUrl] = useState('')
  const [ytProgress, setYtProgress] = useState<DownloadProgress | null>(null)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const handleFile = useCallback(async (file: File) => {
    setError(null)
    setUploading(true)
    setUploadProgress(0)

    try {
      const result: UploadResponse = await videoApi.uploadVideo(file, setUploadProgress)
      onVideoReady(result.video_id, result.info, result.thumbnail_url, result.filename, result.video_url)
    } catch (e: any) {
      setError(e.message || 'Upload failed')
    } finally {
      setUploading(false)
      setUploadProgress(0)
    }
  }, [onVideoReady])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }, [handleFile])

  const handleYoutubeDownload = async () => {
    if (!youtubeUrl.trim()) return
    setError(null)

    try {
      const { video_id } = await videoApi.startYoutubeDownload(youtubeUrl)
      setYtProgress({ status: 'starting', progress: 0, message: 'Starting download...' })

      pollRef.current = setInterval(async () => {
        try {
          const progress = await videoApi.getDownloadProgress(video_id)
          setYtProgress(progress)

          if (progress.status === 'complete') {
            clearInterval(pollRef.current!)
            if (progress.video_id && progress.info && progress.thumbnail_url) {
              onVideoReady(progress.video_id, progress.info, progress.thumbnail_url, 'YouTube Video', progress.video_url)
            }
          } else if (progress.status === 'error') {
            clearInterval(pollRef.current!)
            setError(progress.message)
            setYtProgress(null)
          }
        } catch {
          clearInterval(pollRef.current!)
        }
      }, 1500)
    } catch (e: any) {
      setError(e.message || 'Download failed')
      setYtProgress(null)
    }
  }

  const isProcessing = uploading || (ytProgress && ytProgress.status !== 'complete' && ytProgress.status !== 'error')

  return (
    <div className="cinema-card p-6">
      {/* Tab selector */}
      <div className="flex gap-1 p-1 bg-cinema-black rounded-lg mb-6 w-fit">
        {(['upload', 'youtube'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => { setTab(t); setError(null) }}
            className={clsx(
              'flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all',
              tab === t
                ? 'bg-cinema-gold text-cinema-black'
                : 'text-cinema-text-dim hover:text-cinema-text'
            )}
          >
            {t === 'upload' ? <Upload className="w-3.5 h-3.5" /> : <Link2 className="w-3.5 h-3.5" />}
            {t === 'upload' ? 'Local File' : 'YouTube URL'}
          </button>
        ))}
      </div>

      {/* Upload area */}
      {tab === 'upload' && (
        <div>
          <div
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            onClick={() => !isProcessing && fileInputRef.current?.click()}
            className={clsx(
              'relative border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all',
              isDragging
                ? 'border-cinema-gold bg-cinema-gold/5 gold-glow'
                : 'border-cinema-muted hover:border-cinema-gold/40 hover:bg-cinema-gold/2',
              isProcessing && 'pointer-events-none'
            )}
          >
            {isProcessing ? (
              <div className="space-y-4">
                <Loader2 className="w-10 h-10 text-cinema-gold animate-spin mx-auto" />
                <p className="text-cinema-text-dim text-sm">Uploading & analyzing...</p>
                <div className="progress-bar max-w-xs mx-auto">
                  <div className="progress-fill" style={{ width: `${uploadProgress}%` }} />
                </div>
                <p className="text-cinema-gold font-mono text-sm">{uploadProgress}%</p>
              </div>
            ) : (
              <div className="space-y-3">
                <Film className="w-10 h-10 text-cinema-text-dim mx-auto" />
                <div>
                  <p className="text-cinema-text font-medium">Drop video here or click to browse</p>
                  <p className="text-cinema-text-dim text-sm mt-1">MP4, MOV, MKV, AVI, WEBM · Max 2GB</p>
                </div>
              </div>
            )}
          </div>
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            accept=".mp4,.mov,.mkv,.avi,.webm"
            onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
          />
        </div>
      )}

      {/* YouTube area */}
      {tab === 'youtube' && (
        <div className="space-y-4">
          <div className="flex gap-2">
            <div className="flex-1 relative">
              <Link2 className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-cinema-text-dim" />
              <input
                type="url"
                value={youtubeUrl}
                onChange={(e) => setYoutubeUrl(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleYoutubeDownload()}
                placeholder="https://www.youtube.com/watch?v=..."
                disabled={!!isProcessing}
                className="w-full bg-cinema-black border border-cinema-border rounded-lg pl-10 pr-4 py-3 text-cinema-text text-sm placeholder:text-cinema-text-dim focus:border-cinema-gold/50 focus:outline-none focus:ring-1 focus:ring-cinema-gold/20 disabled:opacity-50"
              />
            </div>
            <button
              onClick={handleYoutubeDownload}
              disabled={!youtubeUrl.trim() || !!isProcessing}
              className="px-5 py-3 bg-cinema-gold text-cinema-black text-sm font-semibold rounded-lg hover:bg-amber-400 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Download
            </button>
          </div>

          {ytProgress && (
            <div className="bg-cinema-black rounded-lg p-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-cinema-text-dim text-sm">{ytProgress.message}</span>
                <span className="text-cinema-gold font-mono text-sm">{ytProgress.progress}%</span>
              </div>
              <div className="progress-bar">
                <div
                  className={clsx(
                    "progress-fill",
                    ytProgress.status === 'analyzing' && 'animate-pulse'
                  )}
                  style={{ width: `${ytProgress.progress}%` }}
                />
              </div>
            </div>
          )}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mt-4 flex items-start gap-3 bg-red-500/10 border border-red-500/20 rounded-lg p-4">
          <AlertCircle className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-red-400 text-sm font-medium">Error</p>
            <p className="text-red-400/80 text-sm mt-0.5">{error}</p>
          </div>
          <button onClick={() => setError(null)} className="ml-auto text-red-400/60 hover:text-red-400">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  )
}
