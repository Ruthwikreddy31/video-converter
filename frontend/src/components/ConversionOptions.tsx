import { useState } from 'react'
import { Loader2, Download, Info, Video, Film, Monitor, Tv, Layers, Eye } from 'lucide-react'
import { videoApi, ConversionProgress } from '../api/videoApi'
import clsx from 'clsx'

interface Format {
  key: string
  label: string
  ratio: string
  decimal: number
  description: string
  icon: any
}

const EXPORT_FORMATS: Format[] = [
  {
    key: 'imax_70mm',
    label: 'IMAX 70MM',
    ratio: '1.43:1',
    decimal: 1.43,
    description: 'Original 15/70 film IMAX format. Near-square frame for maximum vertical impact.',
    icon: Film
  },
  {
    key: 'large_format',
    label: 'Large Format',
    ratio: '1.85:1',
    decimal: 1.85,
    description: 'Premium Large Format screen presentation with tall, theatrical framing.',
    icon: Monitor
  },
  {
    key: 'imax_digital',
    label: 'IMAX (Digital)',
    ratio: '1.90:1',
    decimal: 1.90,
    description: 'Expanded aspect ratio designed for digital IMAX theater screens.',
    icon: Monitor
  },
  {
    key: '70mm_std',
    label: '70MM',
    ratio: '2.20:1',
    decimal: 2.20,
    description: 'Classic Todd-AO 70mm theatrical print aspect ratio for a wide, detailed presentation.',
    icon: Layers
  },
  {
    key: '35mm_std',
    label: '35MM / Scope',
    ratio: '2.39:1',
    decimal: 2.39,
    description: 'Classic anamorphic theatrical widescreen. Maximum horizontal field of view.',
    icon: Tv
  },
  {
    key: 'dolby_vision',
    label: 'Dolby Vision',
    ratio: '1.85:1',
    decimal: 1.85,
    description: 'High-quality Dolby Vision HDR presentation with 10-bit color depth (BT.2020).',
    icon: Eye
  }
]

interface Props {
  videoId: string
  videoWidth: number
  videoHeight: number
}

interface ConversionState {
  conversionId: string | null
  progress: ConversionProgress | null
  error: string | null
}

export default function ConversionOptions({ videoId }: Props) {
  const [conversions, setConversions] = useState<Record<string, ConversionState>>({})

  const getConvState = (key: string): ConversionState =>
    conversions[key] || { conversionId: null, progress: null, error: null }

  const startConversion = async (format: Format) => {
    if (getConvState(format.key).progress?.status === 'processing') return

    // Initialize state
    setConversions(prev => ({
      ...prev,
      [format.key]: {
        conversionId: null,
        progress: { status: 'pending', progress: 0, message: 'Queueing...' },
        error: null
      }
    }))

    try {
      // Default crop method is smart cropping
      const { conversion_id } = await videoApi.startConversion(videoId, format.key, 'smart')

      setConversions(prev => ({
        ...prev,
        [format.key]: {
          conversionId: conversion_id,
          progress: { status: 'pending', progress: 5, message: 'Starting...' },
          error: null
        }
      }))

      // Poll for progress
      const poll = setInterval(async () => {
        try {
          const progress = await videoApi.getConversionProgress(conversion_id)
          setConversions(prev => ({
            ...prev,
            [format.key]: { ...prev[format.key], progress }
          }))

          if (['completed', 'failed', 'needs_expansion'].includes(progress.status)) {
            clearInterval(poll)
          }
        } catch {
          clearInterval(poll)
        }
      }, 1200)
    } catch (e: any) {
      setConversions(prev => ({
        ...prev,
        [format.key]: { conversionId: null, progress: null, error: e.message }
      }))
    }
  }

  return (
    <div className="bg-cinema-black/40 border border-cinema-border rounded-2xl p-6 space-y-6">
      <div>
        <h3 className="text-cinema-text font-display text-lg font-semibold flex items-center gap-2">
          <Video className="w-5 h-5 text-cinema-gold" />
          Cinema Export Options
        </h3>
        <p className="text-cinema-text-dim text-xs mt-1">
          Export your video directly into professional cinema aspect ratios using AI smart cropping.
        </p>
      </div>

      <div className="space-y-4">
        {EXPORT_FORMATS.map((format) => {
          const state = getConvState(format.key)
          const { progress, error } = state
          const isProcessing = progress?.status === 'pending' || progress?.status === 'processing'
          const isComplete = progress?.status === 'completed'
          const needsExpansion = progress?.status === 'needs_expansion'
          const Icon = format.icon

          return (
            <div
              key={format.key}
              className="bg-cinema-card/40 border border-cinema-border rounded-xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:border-cinema-muted transition-colors"
            >
              {/* Left Side: Format info */}
              <div className="flex items-start gap-3.5 flex-1">
                <div className="p-2.5 bg-cinema-gold/10 border border-cinema-gold/20 rounded-lg text-cinema-gold flex-shrink-0 mt-0.5">
                  <Icon className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm text-cinema-text">{format.label}</span>
                    <span className="text-[10px] font-mono bg-cinema-black px-2 py-0.5 rounded border border-cinema-border text-cinema-gold">
                      {format.ratio}
                    </span>
                  </div>
                  <p className="text-cinema-text-dim text-xs mt-1 leading-relaxed max-w-md">
                    {format.description}
                  </p>
                </div>
              </div>

              {/* Right Side: Action Button or Progress */}
              <div className="w-full md:w-auto flex-shrink-0 flex flex-col justify-center min-w-[150px]">
                {/* Standard Download/Convert trigger */}
                {!isProcessing && !isComplete && !needsExpansion && (
                  <button
                    onClick={() => startConversion(format)}
                    className="w-full py-2.5 px-4 bg-cinema-gold hover:bg-amber-500 text-cinema-black text-xs font-bold rounded-lg transition-colors flex items-center justify-center gap-1.5 shadow-md shadow-cinema-gold/10"
                  >
                    <Download className="w-3.5 h-3.5" />
                    Convert & Download
                  </button>
                )}

                {/* Progress bar */}
                {isProcessing && (
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between text-[10px]">
                      <span className="text-cinema-text-dim truncate max-w-[100px]">{progress?.message}</span>
                      <span className="font-mono text-cinema-gold">{progress?.progress}%</span>
                    </div>
                    <div className="progress-bar w-full">
                      <div
                        className="absolute inset-y-0 left-0 bg-cinema-gold rounded-full transition-all duration-300"
                        style={{ width: `${progress?.progress}%` }}
                      />
                    </div>
                  </div>
                )}

                {/* Completed - Download ready */}
                {isComplete && progress.output_url && (
                  <a
                    href={progress.output_url}
                    download
                    className="w-full py-2.5 px-4 bg-green-600 hover:bg-green-500 text-white text-xs font-semibold rounded-lg transition-colors flex items-center justify-center gap-1.5 shadow-md shadow-green-500/10"
                  >
                    <Download className="w-3.5 h-3.5" />
                    Download File
                  </a>
                )}

                {/* Needs expansion fallback warning */}
                {needsExpansion && (
                  <div className="text-center space-y-2">
                    <div className="flex items-center gap-1 text-[10px] text-amber-500 justify-center">
                      <Info className="w-3 h-3 flex-shrink-0" />
                      <span>Border Safe Mode Required</span>
                    </div>
                    <button
                      onClick={() => startConversion({ ...format, key: `${format.key}_border` })}
                      className="w-full py-1.5 px-2 bg-amber-500/10 border border-amber-500/30 text-amber-400 text-[10px] font-semibold rounded-lg hover:bg-amber-500/20 transition-colors"
                    >
                      Export with Borders
                    </button>
                  </div>
                )}

                {/* Error presentation */}
                {error && (
                  <div className="text-[10px] text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg p-2 text-center">
                    Failed. Click to retry.
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
