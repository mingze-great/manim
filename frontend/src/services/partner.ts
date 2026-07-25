import api from './api'

export interface PartnerProfile {
  id: number
  display_name: string
  commission_rate_bps: number
  status: string
  referral_code?: string
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

export const partnerApi = {
  getProfile: () => api.get<PartnerProfile>('/partner/profile'),
  getReferrals: () => api.get<PartnerReferral[]>('/partner/referrals'),
  getOrders: () => api.get<PartnerOrder[]>('/partner/orders'),
  getCommissions: () => api.get<PartnerCommission[]>('/partner/commissions'),
  createInviteCode: (payload: { plan_key: string; quota_limit: number; quota_period: string; max_video_seconds: number; max_uses: number; allowed_libraries?: string[] }) =>
    api.post<{ code: string; plan_key: string; material_mode: string; allowed_libraries?: string[]; status: string }>('/partner/invite-codes', payload),
}
