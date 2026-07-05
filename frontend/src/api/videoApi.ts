const BASE_URL = '/api'

export interface VideoInfo {
  width: number
  height: number
  duration: number
  fps: number
  file_size: number
  aspect_ratio: string
  aspect_ratio_decimal?: number
  detected_format: string
  video_codec: string
  audio_codec: string
  bitrate?: number
}

export interface UploadResponse {
  video_id: string
  filename: string
  thumbnail_url: string
  video_url?: string
  info: VideoInfo
}

export interface VideoDetails {
  video_id: string
  filename: string
  thumbnail_url: string | null
  video_url?: string
  previews: Record<string, string>
  info: VideoInfo
}

export interface YoutubeDownloadResponse {
  video_id: string
  status: string
}

export interface DownloadProgress {
  status: 'starting' | 'downloading' | 'analyzing' | 'complete' | 'error'
  progress: number
  message: string
  video_id?: string
  info?: VideoInfo
  thumbnail_url?: string
}

export interface ConversionResponse {
  conversion_id: string
  status: string
}

export interface ConversionProgress {
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'needs_expansion'
  progress: number
  message: string
  output_url?: string
  processing_time?: number
  crop_method?: string
  needs_ai_expansion?: boolean
}

export interface ConversionHistoryItem {
  id: string
  video_id: string
  filename: string
  target_format: string
  status: string
  crop_method: string
  processing_time: number | null
  output_url: string | null
  thumbnail_url: string | null
  created_at: string
  completed_at: string | null
}

export interface Stats {
  total_videos: number
  total_conversions: number
  completed_conversions: number
  failed_conversions: number
  success_rate: number
  format_breakdown: Record<string, number>
  most_used_format: string
  avg_processing_time_seconds: number
}

export const videoApi = {
  // Upload local file with progress
  async uploadVideo(
    file: File,
    onProgress?: (pct: number) => void
  ): Promise<UploadResponse> {
    const formData = new FormData()
    formData.append('file', file)

    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest()
      xhr.open('POST', `${BASE_URL}/upload/`)

      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable && onProgress) {
          onProgress(Math.round((e.loaded / e.total) * 100))
        }
      }

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(JSON.parse(xhr.responseText))
        } else {
          const err = JSON.parse(xhr.responseText)
          reject(new Error(err.detail || 'Upload failed'))
        }
      }

      xhr.onerror = () => reject(new Error('Network error during upload'))
      xhr.send(formData)
    })
  },

  async getVideoInfo(videoId: string): Promise<VideoDetails> {
    const res = await fetch(`${BASE_URL}/upload/${videoId}/info`)
    if (!res.ok) throw new Error('Failed to get video info')
    return res.json()
  },

  async getYoutubeInfo(url: string) {
    const res = await fetch(`${BASE_URL}/youtube/info`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Failed to get YouTube info')
    }
    return res.json()
  },

  async startYoutubeDownload(url: string): Promise<YoutubeDownloadResponse> {
    const res = await fetch(`${BASE_URL}/youtube/download`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Download failed')
    }
    return res.json()
  },

  async getDownloadProgress(videoId: string): Promise<DownloadProgress> {
    const res = await fetch(`${BASE_URL}/youtube/progress/${videoId}`)
    if (!res.ok) throw new Error('Progress not found')
    return res.json()
  },

  async startConversion(
    videoId: string,
    targetFormat: string,
    cropMethod: string = 'smart'
  ): Promise<ConversionResponse> {
    const res = await fetch(`${BASE_URL}/convert/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        video_id: videoId,
        target_format: targetFormat,
        crop_method: cropMethod,
      }),
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Conversion failed to start')
    }
    return res.json()
  },

  async getConversionProgress(conversionId: string): Promise<ConversionProgress> {
    const res = await fetch(`${BASE_URL}/convert/progress/${conversionId}`)
    if (!res.ok) throw new Error('Conversion not found')
    return res.json()
  },

  async getHistory(): Promise<ConversionHistoryItem[]> {
    const res = await fetch(`${BASE_URL}/convert/history`)
    if (!res.ok) throw new Error('Failed to get history')
    return res.json()
  },

  async getStats(): Promise<Stats> {
    const res = await fetch(`${BASE_URL}/status/stats`)
    if (!res.ok) throw new Error('Failed to get stats')
    return res.json()
  },
}
