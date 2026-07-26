import api from './api'

export interface PartnerProfile {
  id: number
  display_name: string
  commission_rate_bps: number
  status: string
  referral_code?: string
  stickman_entitlement?: {
    material_mode: 'material_only' | 'ai_image'
    visible_image_modes?: Array<'material_only' | 'ai_image'>
    can_choose_image_mode?: boolean
  }
}

export interface PartnerReferral {
  id: number
  username: string
  phone?: string | null
  is_approved: boolean
  created_at?: string | null
}

export interface PartnerOrder {
  order_id: string
  plan: string
  amount: number
  status: string
  commission_amount: number
  commission_status: string
  created_at?: string | null
}

export interface PartnerCommission {
  id: number
  user_id: number
  amount: number
  commission_amount: number
  status: string
  source: string
  created_at?: string | null
}

export interface PartnerStickmanPlan {
  key: string
  name: string
  description?: string
  quota_mode: 'period' | 'count_package'
  daily_limit: number
  total_video_limit?: number
  max_video_seconds: number
  material_mode: 'material_only' | 'ai_image' | 'hybrid'
  amount: number
}

export const partnerApi = {
  getProfile: () => api.get<PartnerProfile>('/partner/profile'),
  getReferrals: () => api.get<PartnerReferral[]>('/partner/referrals'),
  getOrders: () => api.get<PartnerOrder[]>('/partner/orders'),
  getCommissions: () => api.get<PartnerCommission[]>('/partner/commissions'),
  getStickmanPlans: () => api.get<{ plans: PartnerStickmanPlan[]; entitlement?: PartnerProfile['stickman_entitlement'] }>('/partner/stickman-plans'),
  createInviteCode: (payload: { plan_key: string; quota_limit: number; quota_period: string; max_video_seconds: number; max_uses: number; allowed_libraries?: string[]; amount?: number; material_mode?: 'material_only' | 'ai_image' }) =>
    api.post<{ code: string; plan_key: string; material_mode: string; allowed_libraries?: string[]; amount?: number; commission_amount?: number; status: string }>('/partner/invite-codes', payload),
}
