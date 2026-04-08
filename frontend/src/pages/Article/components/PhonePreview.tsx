import { useState } from 'react'
import { Select } from 'antd'
import { Article } from '@/services/article'

interface PhonePreviewProps {
  article: Article | null
}

export default function PhonePreview({ article }: PhonePreviewProps) {
  const [device, setDevice] = useState('iphone14')
  
  const devices: Record<string, { width: number; height: number; name: string }> = {
    iphone14: { width: 390, height: 844, name: 'iPhone 14' },
    iphoneSe: { width: 375, height: 667, name: 'iPhone SE' },
    pixel5: { width: 393, height: 851, name: 'Pixel 5' }
  }
  
  const currentDevice = devices[device]
  
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0 }}>
      <div style={{ marginBottom: '16px', flexShrink: 0 }}>
        <Select 
          value={device} 
          onChange={setDevice}
          style={{ width: '100%' }}
          options={Object.entries(devices).map(([key, val]) => ({
            value: key,
            label: val.name
          }))}
        />
      </div>
      
      <div 
        style={{
          flex: 1,
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'flex-start',
          overflow: 'auto',
          minHeight: 0
        }}
      >
        <div
          style={{
            width: currentDevice.width,
            height: currentDevice.height,
            border: '8px solid #333',
            borderRadius: '30px',
            overflow: 'hidden',
            backgroundColor: '#fff',
            boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
            flexShrink: 0
          }}
        >
          <div
            style={{
              width: '100%',
              height: '100%',
              overflow: 'auto',
              WebkitOverflowScrolling: 'touch'
            }}
          >
            {article?.content_html ? (
              <div 
                dangerouslySetInnerHTML={{ __html: article.content_html }}
                style={{ padding: '16px' }}
              />
            ) : (
              <div 
                style={{ 
                  display: 'flex', 
                  justifyContent: 'center', 
                  alignItems: 'center', 
                  height: '100%',
                  color: '#999'
                }}
              >
                暂无预览内容
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}