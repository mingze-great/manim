import { useEffect, useMemo, useState } from 'react'
import { Button, Card, Col, Form, Input, InputNumber, Modal, Row, Select, Space, Statistic, Table, Tabs, Tag, Typography, message } from 'antd'
import { GiftOutlined, PlusOutlined, ReloadOutlined, TeamOutlined, WalletOutlined } from '@ant-design/icons'
import { adminApi, AdminCommission, AdminPartner, AdminReferral, StickmanWorkflowMaterialLibrary, User } from '@/services/admin'

const formatMoney = (value?: number | null) => `¥${(((value || 0) as number) / 100).toFixed(2)}`

const formatDate = (value?: string | null) => {
  if (!value) return '-'
  try {
    return new Date(value).toLocaleString('zh-CN')
  } catch {
    return '-'
  }
}

export default function AdminPartners() {
  const [partners, setPartners] = useState<AdminPartner[]>([])
  const [referrals, setReferrals] = useState<AdminReferral[]>([])
  const [commissions, setCommissions] = useState<AdminCommission[]>([])
  const [users, setUsers] = useState<User[]>([])
  const [materialLibraries, setMaterialLibraries] = useState<StickmanWorkflowMaterialLibrary[]>([])
  const [selectedPartnerId, setSelectedPartnerId] = useState<number | undefined>()
  const [loading, setLoading] = useState(false)
  const [createPartnerOpen, setCreatePartnerOpen] = useState(false)
  const [inviteOpen, setInviteOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [userSearchLoading, setUserSearchLoading] = useState(false)

  const partnerNameMap = useMemo(
    () => Object.fromEntries(partners.map((item) => [item.id, item.display_name])),
    [partners],
  )

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
      const [partnerRes, referralRes, commissionRes, userRes, libraryRes] = await Promise.all([
        adminApi.getPartners(),
        adminApi.getReferrals(partnerId),
        adminApi.getCommissions(partnerId),
        adminApi.getUsers({ limit: 500 }),
        adminApi.getStickmanWorkflowMaterialLibraries(),
      ])
      setPartners(partnerRes.data || [])
      setReferrals(referralRes.data || [])
      setCommissions(commissionRes.data || [])
      const userPayload: any = userRes.data
      setUsers(Array.isArray(userPayload) ? userPayload : (userPayload?.users || []))
      setMaterialLibraries(libraryRes.data?.libraries || [])
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '加载合作者数据失败')
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
      message.error(error?.response?.data?.detail || '搜索用户失败')
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
      message.error(error?.response?.data?.detail || '创建合作者失败')
    } finally {
      setSubmitting(false)
    }
  }

  const createInviteCode = async (values: {
    partner_id?: number
    plan_key: string
    material_mode: string
    quota_limit: number
    quota_period: string
    max_video_seconds: number
    max_uses: number
    allowed_libraries?: string[]
  }) => {
    setSubmitting(true)
    try {
      const { data } = await adminApi.createInviteCode(values)
      message.success(`兑换码已生成：${data.code}`)
      setInviteOpen(false)
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '生成兑换码失败')
    } finally {
      setSubmitting(false)
    }
  }

  const partnerOptions = partners.map((item) => ({ label: item.display_name, value: item.id }))
  const materialLibraryOptions = materialLibraries
    .filter((item) => item.is_active !== false && item.is_visible !== false)
    .map((item) => ({ label: item.name || item.key, value: item.key }))
  const userOptions = users
    .filter((user) => !user.is_admin)
    .map((user) => ({
      label: `${user.username} · ${user.phone || user.email || user.id}`,
      value: user.id,
    }))

  return (
    <div>
      <div className="mb-6">
        <Typography.Title level={2}>合作者管理</Typography.Title>
        <Typography.Paragraph type="secondary">
          创建合作者、绑定推荐来源、生成兑换码，并查看推荐用户与佣金台账。
        </Typography.Paragraph>
      </div>

      <Row gutter={[16, 16]} className="mb-4">
        <Col xs={24} md={8}>
          <Card>
            <Statistic title="合作者" value={summary.partners} prefix={<TeamOutlined />} />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <Statistic title="推荐用户" value={summary.referrals} prefix={<GiftOutlined />} />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <Statistic title="预计佣金" value={formatMoney(summary.commissions)} prefix={<WalletOutlined />} />
          </Card>
        </Col>
      </Row>

      <Card className="mb-4">
        <Space wrap>
          <Select
            allowClear
            placeholder="按合作者筛选"
            value={selectedPartnerId}
            onChange={handlePartnerFilter}
            options={partnerOptions}
            style={{ width: 220 }}
          />
          <Button icon={<ReloadOutlined />} loading={loading} onClick={() => loadData()}>
            刷新
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => { setCreatePartnerOpen(true); loadPartnerCandidateUsers() }}>
            创建合作者
          </Button>
          <Button icon={<GiftOutlined />} onClick={() => setInviteOpen(true)}>
            生成兑换码
          </Button>
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
                    { title: '订单ID', dataIndex: 'order_id', render: (value: number | null) => value || '-' },
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

      <Modal
        title="创建合作者"
        open={createPartnerOpen}
        onCancel={() => setCreatePartnerOpen(false)}
        footer={null}
      >
        <Form layout="vertical" onFinish={createPartner} initialValues={{ commission_rate_bps: 3000 }}>
          <Form.Item name="user_id" label="选择用户" rules={[{ required: true, message: '请选择用户' }]}>
            <Select
              showSearch
              filterOption={false}
              loading={userSearchLoading}
              onSearch={loadPartnerCandidateUsers}
              optionFilterProp="label"
              options={userOptions}
              placeholder="输入用户名或手机号搜索已有用户"
              notFoundContent={userSearchLoading ? '搜索中...' : '暂无用户，请输入用户名或手机号搜索'}
            />
          </Form.Item>
          <Form.Item name="display_name" label="合作者名称" rules={[{ required: true, message: '请输入合作者名称' }]}>
            <Input placeholder="例如：小红书心理博主 A" />
          </Form.Item>
          <Form.Item name="commission_rate_bps" label="佣金比例 BP" rules={[{ required: true }]}>
            <InputNumber min={0} max={9000} style={{ width: '100%' }} addonAfter="BP" />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={submitting} block>
            创建
          </Button>
        </Form>
      </Modal>

      <Modal title="生成兑换码" open={inviteOpen} onCancel={() => setInviteOpen(false)} footer={null}>
        <Form
          layout="vertical"
          onFinish={createInviteCode}
          initialValues={{
            partner_id: selectedPartnerId,
            plan_key: 'basic',
            material_mode: 'material_only',
            quota_limit: 30,
            quota_period: 'daily',
            max_video_seconds: 60,
            max_uses: 1,
            allowed_libraries: ['sc1_outputs'],
          }}
        >
          <Form.Item name="partner_id" label="绑定合作者">
            <Select allowClear options={partnerOptions} placeholder="不绑定则为平台兑换码" />
          </Form.Item>
          <Form.Item name="plan_key" label="套餐">
            <Select options={[{ label: '基础套餐', value: 'basic' }, { label: '专业套餐', value: 'pro' }, { label: '企业套餐', value: 'enterprise' }]} />
          </Form.Item>
          <Form.Item name="material_mode" label="成本模式">
            <Select options={[{ label: '素材库模式', value: 'material_only' }, { label: '实时生图模式', value: 'ai_image' }, { label: '混合模式', value: 'hybrid' }]} />
          </Form.Item>
          <Form.Item name="allowed_libraries" label="可用素材库" extra="留空表示不限制；素材库套餐建议至少选择默认 SC1 素材库。">
            <Select mode="multiple" allowClear options={materialLibraryOptions} placeholder="选择用户可使用的素材库" />
          </Form.Item>
          <Row gutter={12}>
            <Col span={8}>
              <Form.Item name="quota_limit" label="每日次数">
                <InputNumber min={1} max={999} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="max_video_seconds" label="单条秒数">
                <InputNumber min={15} max={300} step={15} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="max_uses" label="可用次数">
                <InputNumber min={1} max={999} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Button type="primary" htmlType="submit" loading={submitting} block>
            生成兑换码
          </Button>
        </Form>
      </Modal>
    </div>
  )
}
