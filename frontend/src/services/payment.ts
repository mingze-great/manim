import api from './api'

export interface SubscriptionPlan {
  name: string
  price: number
  daily_quota: number
  max_projects: number
  features: string[]
}

export interface Subscription {
  plan: string
  daily_quota: number
  max_projects: number
  expires_at: string | null
  features: string[]
}

export interface Order {
  order_id: string
  plan: string
  amount: number
  status: string
  created_at: string
  paid_at: string | null
}

export const paymentApi = {
  getPlans: () => api.get<Record<string, SubscriptionPlan>>('/payment/plans'),
  
  getMySubscription: () => api.get<Subscription>('/payment/my-subscription'),
  
  createOrder: (plan: string) => api.post<{ 
    order_id: string
    plan: string
    amount: number
    status: string
    code_url: string | null
  }>('/payment/create', { plan }),
  
  queryOrder: (orderId: string) => api.post<{ 
    status: string
    message: string 
  }>(`/payment/query/${orderId}`),
  
  getOrders: () => api.get<Order[]>('/payment/orders'),
}
