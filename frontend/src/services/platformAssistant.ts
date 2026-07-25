import api from './api'

export interface PlatformAssistantChatRequest {
  message: string
  pagePath?: string
  module?: string
}

export interface PlatformAssistantAction {
  label: string
  route: string
}

export interface PlatformAssistantSource {
  title: string
  source: string
}

export interface PlatformAssistantChatResponse {
  answer: string
  suggestedActions: PlatformAssistantAction[]
  sources: PlatformAssistantSource[]
}

export const platformAssistantApi = {
  chat: (payload: PlatformAssistantChatRequest) =>
    api.post<PlatformAssistantChatResponse>('/platform-assistant/chat', payload),
}
