import { useState, useEffect, useRef } from 'react'
import { message } from 'antd'

interface UseStreamGenerationOptions {
  url: string
  onData?: (chunk: string) => void
  onComplete?: (result: any) => void
  onError?: (error: string) => void
}

export function useStreamGeneration() {
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamContent, setStreamContent] = useState('')
  const eventSourceRef = useRef<EventSource | null>(null)

  const startStream = async ({ url, onData, onComplete, onError }: UseStreamGenerationOptions) => {
    setIsStreaming(true)
    setStreamContent('')
    
    try {
      const eventSource = new EventSource(url)
      eventSourceRef.current = eventSource
      
      let fullContent = ''
      
      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          
          if (data.done) {
            eventSource.close()
            setIsStreaming(false)
            eventSourceRef.current = null
            onComplete?.(data)
          } else if (data.error) {
            eventSource.close()
            setIsStreaming(false)
            eventSourceRef.current = null
            onError?.(data.error)
            message.error(data.error)
          } else if (data.content) {
            fullContent += data.content
            setStreamContent(fullContent)
            onData?.(data.content)
          }
        } catch (e) {
          console.error('Failed to parse SSE data:', e)
        }
      }
      
      eventSource.onerror = (error) => {
        console.error('SSE error:', error)
        eventSource.close()
        setIsStreaming(false)
        eventSourceRef.current = null
        onError?.('连接失败，请重试')
        message.error('连接失败，请重试')
      }
      
    } catch (error) {
      setIsStreaming(false)
      const errorMsg = error instanceof Error ? error.message : '未知错误'
      onError?.(errorMsg)
      message.error(errorMsg)
    }
  }

  const stopStream = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
    setIsStreaming(false)
  }

  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }
    }
  }, [])

  return {
    isStreaming,
    streamContent,
    startStream,
    stopStream
  }
}