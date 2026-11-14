import { useEffect, useRef, useState } from 'react'
import type { PipelineStatusData, LogItem, DashboardSummaryData } from '../types/api'

interface SSEHandlers {
  onPipelineStatus?: (status: PipelineStatusData) => void
  onSnapshot?: (snapshot: DashboardSummaryData) => void
  onLogEntry?: (log: LogItem) => void
  onCollectionUpdate?: (update: any) => void
}

export function useSSE(handlers: SSEHandlers) {
  const [connected, setConnected] = useState(false)
  const [lastHeartbeat, setLastHeartbeat] = useState<number | null>(null)
  const handlersRef = useRef(handlers)
  handlersRef.current = handlers

  useEffect(() => {
    const es = new EventSource('/api/stream')

    es.onopen = () => {
      setConnected(true)
    }

    es.onerror = () => {
      setConnected(false)
    }

    es.addEventListener('pipeline_status', (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data) as PipelineStatusData
        handlersRef.current.onPipelineStatus?.(data)
      } catch (err) {
        console.error('Failed to parse pipeline_status SSE:', err)
      }
    })

    es.addEventListener('snapshot', (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data) as DashboardSummaryData
        handlersRef.current.onSnapshot?.(data)
      } catch (err) {
        console.error('Failed to parse snapshot SSE:', err)
      }
    })

    es.addEventListener('log_entry', (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data) as LogItem
        handlersRef.current.onLogEntry?.(data)
      } catch (err) {
        console.error('Failed to parse log_entry SSE:', err)
      }
    })

    es.addEventListener('collection_update', (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data)
        handlersRef.current.onCollectionUpdate?.(data)
      } catch (err) {
        console.error('Failed to parse collection_update SSE:', err)
      }
    })

    es.addEventListener('heartbeat', () => {
      setLastHeartbeat(Date.now())
    })

    return () => {
      es.close()
    }
  }, [])

  return { connected, lastHeartbeat }
}
