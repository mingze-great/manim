import api from './api'


export interface VideoTopicCategory {
  id: number
  name: string
  icon: string
  description: string
  example_topics: string[]
}


export const videoTopicApi = {
  getCategories: () =>
    api.get<VideoTopicCategory[]>('/video-topics/categories'),
  
  generateTopics: (category: string, keyword?: string) =>
    api.post<{ topics: string[] }>('/video-topics/generate', { category, keyword })
}