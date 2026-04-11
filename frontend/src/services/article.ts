import api from './api'

export interface Category {
  name: string
  icon: string
  example_topics: string[]
}

export interface Article {
  id: number
  user_id: number
  category: string
  title: string | null
  topic: string
  outline: string | null
  content_html: string | null
  content_text: string | null
  images: Array<{ url: string; position: number; prompt: string; type?: string; anchor_paragraph?: number; local_url?: string; storage?: string; related_text?: string; scene_subject?: string; scene_action?: string }> | null
  status: string
  word_count: number
  created_at: string
  updated_at: string
}

export interface Usage {
  used_today: number
  limit: number
  remaining: number
  reset_time: string
}

export const articleApi = {
  getCategories: () =>
    api.get<Category[]>('/articles/meta/categories'),

  generateTopics: (category: string, keyword?: string) =>
    api.post<{ topics: string[] }>('/articles/meta/generate-topics', { category, keyword }),
  
  getUsage: () =>
    api.get<Usage>('/articles/usage'),
  
  create: (data: { topic: string; category?: string; outline?: string }) =>
    api.post<Article>('/articles', data),
  
  get: (id: number) =>
    api.get<Article>(`/articles/${id}`),
  
  update: (id: number, data: Partial<Article>) =>
    api.put<Article>(`/articles/${id}`, data),
  
  delete: (id: number) =>
    api.delete(`/articles/${id}`),
  
  list: (limit: number = 10) =>
    api.get<Article[]>(`/articles?limit=${limit}`),
  
  generateOutline: (id: number, requirement?: string) =>
    api.post<{ outline: string; title: string }>(`/articles/${id}/generate-outline`, { requirement }),
  
  generateContent: (id: number, requirement?: string) =>
    api.post<{ title: string; content: string; word_count: number }>(`/articles/${id}/generate-content`, { requirement }),

  generateDraft: (id: number, requirement?: string) =>
    api.post<Article>(`/articles/${id}/generate-draft`, { requirement }),

  rewriteOutlineSection: (id: number, data: { section_text: string; requirement?: string }) =>
    api.post<{ section_text: string }>(`/articles/${id}/rewrite-outline-section`, data),

  rewriteContentSection: (id: number, data: { section_text: string; article_title?: string; requirement?: string }) =>
    api.post<{ section_text: string }>(`/articles/${id}/rewrite-content-section`, data),
  
  // 流式生成大纲
  generateOutlineStream: async (id: number, requirement?: string, onChunk?: (chunk: string, charCount: number) => void) => {
    // 从localStorage获取token
    const authStorage = localStorage.getItem('auth-storage')
    const token = authStorage ? JSON.parse(authStorage).state.token : null
    
    const response = await fetch(`/api/articles-stream/${id}/generate-outline-stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({ requirement })
    })
    
    if (!response.ok) {
      throw new Error('生成失败')
    }
    
    const reader = response.body?.getReader()
    const decoder = new TextDecoder()
    
    if (!reader) {
      throw new Error('无法读取响应流')
    }
    
    let fullContent = ''
    let title = ''
    
    while (true) {
      const { done, value } = await reader.read()
      
      if (done) {
        break
      }
      
      const chunk = decoder.decode(value, { stream: true })
      const lines = chunk.split('\n')
      
      let shouldBreak = false
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            
            if (data.done) {
              title = data.title
              shouldBreak = true
              break
            } else if (data.content) {
              fullContent = data.full_content || (fullContent + data.content)
              onChunk?.(fullContent, data.char_count || fullContent.replace(/\s/g, '').length)
            } else if (data.error) {
              throw new Error(data.error)
            }
          } catch (e) {
            // 忽略解析错误
          }
        }
      }
      
      if (shouldBreak) {
        break
      }
    }
    
    return { outline: fullContent, title }
  },
  
  // 流式生成文案
  generateContentStream: async (id: number, requirement?: string, onChunk?: (chunk: string, charCount: number) => void) => {
    // 从localStorage获取token
    const authStorage = localStorage.getItem('auth-storage')
    const token = authStorage ? JSON.parse(authStorage).state.token : null
    
    const response = await fetch(`/api/articles-stream/${id}/generate-content-stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({ requirement })
    })
    
    if (!response.ok) {
      throw new Error('生成失败')
    }
    
    const reader = response.body?.getReader()
    const decoder = new TextDecoder()
    
    if (!reader) {
      throw new Error('无法读取响应流')
    }
    
    let fullContent = ''
    let wordCount = 0
    
    while (true) {
      const { done, value } = await reader.read()
      
      if (done) {
        break
      }
      
      const chunk = decoder.decode(value, { stream: true })
      const lines = chunk.split('\n')
      
      let shouldBreak = false
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            
            if (data.done) {
              wordCount = data.word_count
              shouldBreak = true
              break
            } else if (data.content) {
              fullContent = data.full_content || (fullContent + data.content)
              onChunk?.(fullContent, data.char_count || fullContent.replace(/\s/g, '').length)
            } else if (data.error) {
              throw new Error(data.error)
            }
          } catch (e) {
            // 忽略解析错误
          }
        }
      }
      
      if (shouldBreak) {
        break
      }
    }
    
    return { content: fullContent, word_count: wordCount }
  },
  
  generateImages: (id: number) =>
    api.post<{ 
      images: Array<{ url: string; position: number; prompt: string; type?: string; anchor_paragraph?: number; local_url?: string; storage?: string; related_text?: string; scene_subject?: string; scene_action?: string }>,
      total: number,
      success: number,
      failed: number
    }>(`/articles/${id}/generate-images`),
  
  regenerateImage: (id: number, imageIndex: number) =>
    api.post<{ message: string; image: { url: string; position: number; prompt: string; type?: string; anchor_paragraph?: number; local_url?: string; storage?: string; related_text?: string; scene_subject?: string; scene_action?: string } }>(
      `/articles/${id}/regenerate-image/${imageIndex}`
    ),
  
  updateImages: (id: number, images: Array<{ url: string; position: number; prompt: string; type?: string; anchor_paragraph?: number; local_url?: string; storage?: string; related_text?: string; scene_subject?: string; scene_action?: string }>) =>
    api.put<{ message: string; images: Array<{ url: string; position: number; prompt: string; type?: string; anchor_paragraph?: number; local_url?: string; storage?: string; related_text?: string; scene_subject?: string; scene_action?: string }> }>(
      `/articles/${id}/images`,
      images
    ),
  
  deleteImage: (id: number, imageIndex: number) =>
    api.delete<{ message: string; images: Array<{ url: string; position: number; prompt: string; type?: string; anchor_paragraph?: number; local_url?: string; storage?: string; related_text?: string; scene_subject?: string; scene_action?: string }> }>(
      `/articles/${id}/images/${imageIndex}`
    ),
  
  generateHtml: (id: number) =>
    api.post<{ html: string }>(`/articles/${id}/generate-html`),
  
  generateAll: (id: number) =>
    api.post<Article>(`/articles/${id}/generate-all`),
}
