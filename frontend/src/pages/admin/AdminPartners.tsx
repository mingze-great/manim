import { useEffect, useMemo, useState } from 'react'
import { Button, Card, Col, Form, Input, InputNumber, Modal, Row, Select, Space, Statistic, Switch, Table, Tabs, Tag, Typography, message } from 'antd'
import { GiftOutlined, PlusOutlined, ReloadOutlined, TeamOutlined, WalletOutlined } from '@ant-design/icons'
import { adminApi, AdminCommission, AdminPartner, AdminReferral, StickmanWorkflowMaterialLibrary, StickmanWorkflowPlan, User } from '@/services/admin'

const formatMoney = (value?: number | null) => `¥${(((value || 0) as number) / 100).toFixed(2)}`

const formatDate = (value?: string | null) => {
  if (!value) return '-'
  try {
    return new Date(value).toLocaleString('zh-CN')
  } catch {
    return '-'
  }
}

const getErrorMessage = (error: any, fallback: string) => {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((item) => item?.msg || item?.message || JSON.stringify(item)).join('；') || fallback
  if (detail && typeof detail === 'object') return detail.msg || detail.message || JSON.stringify(detail)
  return fallback
}

const quotaModeOptions = [
  { label: '月卡/周期卡', value: 'period' },
  { label: '次数包不限时', value: 'count_package' },
]

const materialModeOptions = [
  { label: '素材库模式', value: 'material_only' },
  { label: '实时生图模式', value: 'ai_image' },
  { label: '混合补图模式', value: 'hybrid' },
]

export default function AdminPartners() {
  const [partners, setPartners] = useState<AdminPartner[]>([])
  const [referrals, setReferrals] = useState<AdminReferral[]>([])
  const [commissions, setCommissions] = useState<AdminCommission[]>([])
  const [users, setUsers] = useState<User[]>([])
  const [materialLibraries, setMaterialLibraries] = useState<StickmanWorkflowMaterialLibrary[]>([])
  const [plans, setPlans] = useState<StickmanWorkflowPlan[]>([])
  const [selectedPartnerId, setSelectedPartnerId] = useState<number | undefined>()
  const [loading, setLoading] = useState(false)
  const [createPartnerOpen, setCreatePartnerOpen] = useState(false)
  const [inviteOpen, setInviteOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [userSearchLoading, setUserSearchLoading] = useState(false)
  const [inviteForm] = Form.useForm()
  const [planForm] = Form.useForm()
  const watchedInviteAmount = Form.useWatch('amount', inviteForm)
  const watchedInvitePartnerId = Form.useWatch('partner_id', inviteForm)

  const partnerNameMap = useMemo(() => Object.fromEntries(partners.map((item) => [item.id, item.display_name])), [partners])
  const selectedInvitePartner = partners.find((item) => item.id === watchedInvitePartnerId)
  const commissionPreview = Math.round(Number(watchedInviteAmount || 0) * Number(selectedInvitePartner?.commission_rate_bps || 0) / 10000)

  const summary = useMemo(() => {
    const filteredCommissions = selectedPartnerId ? commissions.filter((item) => item.partner_id === selectedPartnerId) : commissions
    return {
      partners: partners.length,
      referrals: referrals.length,
      commissions: filteredCommissions.reduce((sum, item) => sum + (item.commission_amount || 0), 0),
    }
  }, [commissions, partners, referrals, selectedPartnerId])

  const loadData = async (partnerId = selectedPartnerId) => {
    setLoading(true)
    try {
      const [partnerRes, referralRes, commissionRes, userRes, libraryRes, planRes] = await Promise.all([
        adminApi.getPartners(),
        adminApi.getReferrals(partnerId),
        adminApi.getCommissions(partnerId),
        adminApi.getUsers({ limit: 100 }),
        adminApi.getStickmanWorkflowMaterialLibraries(),
        adminApi.getStickmanWorkflowPlans(),
      ])
      setPartners(partnerRes.data || [])
      setReferrals(referralRes.data || [])
      setCommissions(commissionRes.data || [])
      const userPayload: any = userRes.data
      setUsers(Array.isArray(userPayload) ? userPayload : (userPayload?.users || []))
      setMaterialLibraries(libraryRes.data?.libraries || [])
      const nextPlans = planRes.data?.plans || []
      setPlans(nextPlans)
      planForm.setFieldsValue({ plans: nextPlans })
    } catch (error: any) {
      message.error(getErrorMessage(error, '加载合作者数据失败'))
    } finally {
      setLoading(false)
    }
  }

  const loadPartnerCandidateUsers = async (search = '') => {
    setUserSearchLoading(true)
    try {
      const { data } = await adminApi.getUsers({ limit: 50, search: search.trim() || undefined })
      const payload: any = data
      setUsers(Array.isArray(payload) ? payload : (payload?.users || []))
    } catch (error: any) {
      message.error(getErrorMessage(error, '搜索用户失败'))
    } finally {
      setUserSearchLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const handlePartnerFilter = (partnerId?: number) => {
    setSelectedPartnerId(partnerId)
    loadData(partnerId)
  }

  const createPartner = async (values: { user_id: number; display_name: string; commission_rate_bps: number }) => {
    setSubmitting(true)
    try {
      const { data } = await adminApi.createPartner(values)
      message.success(`合作者已创建，推荐码：${data.referral_code || '-'}`)
      setCreatePartnerOpen(false)
      loadData()
    } catch (error: any) {
      message.error(getErrorMessage(error, '创建合作者失败'))
    } finally {
      setSubmitting(false)
    }
  }

  const createInviteCode = async (values: any) => {
    setSubmitting(true)
    try {
      const { data } = await adminApi.createInviteCode(values)
      message.success(`兑换码已生成：${data.code}，预计佣金 ${formatMoney(data.commission_amount)}`)
      setInviteOpen(false)
      inviteForm.resetFields()
      loadData()
    } catch (error: any) {
      message.error(getErrorMessage(error, '生成兑换码失败'))
    } finally {
      setSubmitting(false)
    }
  }

  const savePlans = async (values: { plans: StickmanWorkflowPlan[] }) => {
    setSubmitting(true)
    try {
      const { data } = await adminApi.saveStickmanWorkflowPlans(values.plans || [])
      setPlans(data.plans || [])
      planForm.setFieldsValue({ plans: data.plans || [] })
      message.success('火柴人套餐已保存')
    } catch (error: any) {
      message.error(getErrorMessage(error, '保存套餐失败'))
    } finally {
      setSubmitting(false)
    }
  }

  const applyPlanToInvite = (planKey: string) => {
    const plan = plans.find((item) => item.key === planKey)
    if (!plan) return
    inviteForm.setFieldsValue({
      plan_key: plan.key,
      material_mode: plan.material_mode,
      quota_limit: plan.quota_mode === 'count_package' ? plan.total_video_limit : plan.daily_limit,
      quota_period: plan.quota_mode === 'count_package' ? 'lifetime' : 'daily',
      max_video_seconds: plan.max_video_seconds,
      allowed_libraries: plan.allowed_libraries || [],
      amount: plan.amount || 0,
    })
  }

  const partnerOptions = partners.map((item) => ({ label: item.display_name, value: item.id }))
  const planOptions = plans.filter((item) => item.is_active !== false).map((item) => ({ label: `${item.name} · ${formatMoney(item.amount)}`, value: item.key }))
  const materialLibraryOptions = materialLibraries
    .filter((item) => item.is_active !== false && item.is_visible !== false)
    .map((item) => ({ label: item.name || item.key, value: item.key }))
  const userOptions = users
    .filter((user) => !user.is_admin)
    .map((user) => ({ label: `${user.username} · ${user.phone || user.email || user.id}`, value: user.id }))

  return (
    <div>
      <div className="mb-6">
        <Typography.Title level={2}>合作者管理</Typography.Title>
        <Typography.Paragraph type="secondary">
          管理合作者、推荐用户、兑换码套餐和佣金台账。合作者只能看到自己的非敏感数据。
        </Typography.Paragraph>
      </div>

      <Row gutter={[16, 16]} className="mb-4">
        <Col xs={24} md={8}><Card><Statistic title="合作者" value={summary.partners} prefix={<TeamOutlined />} /></Card></Col>
        <Col xs={24} md={8}><Card><Statistic title="推荐用户" value={summary.referrals} prefix={<GiftOutlined />} /></Card></Col>
        <Col xs={24} md={8}><Card><Statistic title="预计佣金" value={formatMoney(summary.commissions)} prefix={<WalletOutlined />} /></Card></Col>
      </Row>

      <Card className="mb-4">
        <Space wrap>
          <Select allowClear placeholder="按合作者筛选" value={selectedPartnerId} onChange={handlePartnerFilter} options={partnerOptions} style={{ width: 220 }} />
          <Button icon={<ReloadOutlined />} loading={loading} onClick={() => loadData()}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => { setCreatePartnerOpen(true); loadPartnerCandidateUsers() }}>创建合作者</Button>
          <Button icon={<GiftOutlined />} onClick={() => { setInviteOpen(true); inviteForm.setFieldsValue({ partner_id: selectedPartnerId, max_uses: 1 }); if (plans[0]) applyPlanToInvite(plans[0].key) }}>生成兑换码</Button>
        </Space>
      </Card>

      <Tabs
        items={[
          {
            key: 'partners',
            label: '合作者',
            children: (
              <Card>
                <Table
                  loading={loading}
                  dataSource={partners}
                  rowKey="id"
                  columns={[
                    { title: '名称', dataIndex: 'display_name' },
                    { title: '用户ID', dataIndex: 'user_id' },
                    { title: '佣金比例', dataIndex: 'commission_rate_bps', render: (value: number) => `${((value || 0) / 100).toFixed(1)}%` },
                    { title: '状态', dataIndex: 'status', render: (value: string) => value === 'active' ? <Tag color="green">启用</Tag> : <Tag>{value}</Tag> },
                    { title: '创建时间', dataIndex: 'created_at', render: formatDate },
                  ]}
                />
              </Card>
            ),
          },
          {
            key: 'plans',
            label: '火柴人套餐',
            children: (
              <Card>
                <Form form={planForm} layout="vertical" onFinish={savePlans} initialValues={{ plans }}>
                  <Form.List name="plans">
                    {(fields, { add, remove }) => (
                      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                        {fields.map((field) => (
                          <Card key={field.key} size="small" title={`套餐 ${field.name + 1}`} extra={<Button danger onClick={() => remove(field.name)}>删除</Button>}>
                            <Row gutter={12}>
                              <Col xs={24} md={6}><Form.Item name={[field.name, 'key']} label="套餐 key" rules={[{ required: true }]}><Input /></Form.Item></Col>
                              <Col xs={24} md={6}><Form.Item name={[field.name, 'name']} label="套餐名称" rules={[{ required: true }]}><Input /></Form.Item></Col>
                              <Col xs={24} md={6}><Form.Item name={[field.name, 'quota_mode']} label="套餐类型"><Select options={quotaModeOptions} /></Form.Item></Col>
                              <Col xs={24} md={6}><Form.Item name={[field.name, 'amount']} label="金额（分）"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item></Col>
                              <Col xs={24} md={6}><Form.Item name={[field.name, 'daily_limit']} label="每日视频数"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item></Col>
                              <Col xs={24} md={6}><Form.Item name={[field.name, 'daily_minutes_limit']} label="每日分钟数"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item></Col>
                              <Col xs={24} md={6}><Form.Item name={[field.name, 'monthly_minutes_limit']} label="每月分钟数"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item></Col>
                              <Col xs={24} md={6}><Form.Item name={[field.name, 'total_video_limit']} label="总视频数"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item></Col>
                              <Col xs={24} md={6}><Form.Item name={[field.name, 'max_video_seconds']} label="单条上限秒"><InputNumber min={15} max={1800} step={15} style={{ width: '100%' }} /></Form.Item></Col>
                              <Col xs={24} md={6}><Form.Item name={[field.name, 'material_mode']} label="底层图片模式"><Select options={materialModeOptions} /></Form.Item></Col>
                              <Col xs={24} md={8}><Form.Item name={[field.name, 'allowed_libraries']} label="可用素材库"><Select mode="multiple" allowClear options={materialLibraryOptions} /></Form.Item></Col>
                              <Col xs={24} md={4}><Form.Item name={[field.name, 'is_active']} label="启用" valuePropName="checked"><Switch /></Form.Item></Col>
                              <Col xs={24}><Form.Item name={[field.name, 'description']} label="说明"><Input /></Form.Item></Col>
                            </Row>
                          </Card>
                        ))}
                        <Button onClick={() => add({ key: `plan_${Date.now()}`, name: '新套餐', quota_mode: 'period', daily_limit: 3, max_video_seconds: 60, material_mode: 'material_only', allowed_libraries: ['sc1_outputs'], amount: 0, is_active: true })}>新增套餐</Button>
                      </Space>
                    )}
                  </Form.List>
                  <Button className="mt-4" type="primary" htmlType="submit" loading={submitting}>保存套餐配置</Button>
                </Form>
              </Card>
            ),
          },
          {
            key: 'referrals',
            label: '推荐用户',
            children: (
              <Card>
                <Table
                  loading={loading}
                  dataSource={referrals}
                  rowKey="id"
                  columns={[
                    { title: '用户', dataIndex: 'username' },
                    { title: '手机号', dataIndex: 'phone', render: (value: string | null) => value || '-' },
                    { title: '合作者', dataIndex: 'partner_id', render: (value: number) => partnerNameMap[value] || value },
                    { title: '推荐码', dataIndex: 'referral_code', render: (value: string | null) => value || '-' },
                    { title: '状态', dataIndex: 'is_approved', render: (value: boolean) => value ? <Tag color="green">已开通</Tag> : <Tag>待开通</Tag> },
                    { title: '注册时间', dataIndex: 'created_at', render: formatDate },
                  ]}
                />
              </Card>
            ),
          },
          {
            key: 'commissions',
            label: '佣金台账',
            children: (
              <Card>
                <Table
                  loading={loading}
                  dataSource={commissions}
                  rowKey="id"
                  columns={[
                    { title: '合作者', dataIndex: 'partner_id', render: (value: number) => partnerNameMap[value] || value },
                    { title: '用户ID', dataIndex: 'user_id' },
                    { title: '订单金额', dataIndex: 'amount', render: formatMoney },
                    { title: '佣金', dataIndex: 'commission_amount', render: formatMoney },
                    { title: '来源', dataIndex: 'source' },
                    { title: '状态', dataIndex: 'status', render: (value: string) => value === 'pending' ? <Tag color="orange">待结算</Tag> : <Tag>{value}</Tag> },
                    { title: '创建时间', dataIndex: 'created_at', render: formatDate },
                  ]}
                />
              </Card>
            ),
          },
        ]}
      />

      <Modal title="创建合作者" open={createPartnerOpen} onCancel={() => setCreatePartnerOpen(false)} footer={null}>
        <Form layout="vertical" onFinish={createPartner} initialValues={{ commission_rate_bps: 3000 }}>
          <Form.Item name="user_id" label="选择用户" rules={[{ required: true, message: '请选择用户' }]}>
            <Select showSearch filterOption={false} loading={userSearchLoading} onSearch={loadPartnerCandidateUsers} options={userOptions} placeholder="输入用户名或手机号搜索已有用户" />
          </Form.Item>
          <Form.Item name="display_name" label="合作者名称" rules={[{ required: true, message: '请输入合作者名称' }]}><Input /></Form.Item>
          <Form.Item name="commission_rate_bps" label="佣金比例 BP" rules={[{ required: true }]}><InputNumber min={0} max={9000} style={{ width: '100%' }} addonAfter="BP" /></Form.Item>
          <Button type="primary" htmlType="submit" loading={submitting} block>创建</Button>
        </Form>
      </Modal>

      <Modal title="生成兑换码" open={inviteOpen} onCancel={() => setInviteOpen(false)} footer={null}>
        <Form form={inviteForm} layout="vertical" onFinish={createInviteCode} initialValues={{ max_uses: 1 }}>
          <Form.Item name="partner_id" label="绑定合作者"><Select allowClear options={partnerOptions} placeholder="不绑定则为平台主管兑换码" /></Form.Item>
          <Form.Item name="plan_key" label="选择套餐" rules={[{ required: true }]}><Select options={planOptions} onChange={applyPlanToInvite} /></Form.Item>
          <Row gutter={12}>
            <Col span={12}><Form.Item name="amount" label="收款金额（分）"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={12}><Form.Item label="预计佣金"><Input value={formatMoney(commissionPreview)} disabled /></Form.Item></Col>
          </Row>
          <Form.Item name="material_mode" label="底层图片模式"><Select options={materialModeOptions} /></Form.Item>
          <Form.Item name="allowed_libraries" label="可用素材库"><Select mode="multiple" allowClear options={materialLibraryOptions} /></Form.Item>
          <Row gutter={12}>
            <Col span={8}><Form.Item name="quota_limit" label="周期/总次数"><InputNumber min={0} max={9999} style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="max_video_seconds" label="单条秒数"><InputNumber min={15} max={1800} step={15} style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="max_uses" label="可兑换次数"><InputNumber min={1} max={999} style={{ width: '100%' }} /></Form.Item></Col>
          </Row>
          <Form.Item name="quota_period" hidden><Input /></Form.Item>
          <Button type="primary" htmlType="submit" loading={submitting} block>生成兑换码</Button>
        </Form>
      </Modal>
    </div>
  )
}
