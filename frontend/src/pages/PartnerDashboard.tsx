import { useEffect, useMemo, useState } from 'react'
import { Button, Card, Col, Form, InputNumber, Row, Space, Statistic, Table, Tag, Typography, message } from 'antd'
import { CopyOutlined, GiftOutlined, ReloadOutlined, TeamOutlined, WalletOutlined } from '@ant-design/icons'
import { partnerApi, PartnerCommission, PartnerOrder, PartnerProfile, PartnerReferral } from '@/services/partner'

const formatMoney = (value?: number | null) => `¥${(((value || 0) as number) / 100).toFixed(2)}`

const formatDate = (value?: string | null) => {
  if (!value) return '-'
  try {
    return new Date(value).toLocaleString('zh-CN')
  } catch {
    return '-'
  }
}

export default function PartnerDashboard() {
  const [profile, setProfile] = useState<PartnerProfile | null>(null)
  const [referrals, setReferrals] = useState<PartnerReferral[]>([])
  const [orders, setOrders] = useState<PartnerOrder[]>([])
  const [commissions, setCommissions] = useState<PartnerCommission[]>([])
  const [loading, setLoading] = useState(false)
  const [creatingCode, setCreatingCode] = useState(false)

  const loadData = async () => {
    setLoading(true)
    try {
      const [profileRes, referralRes, orderRes, commissionRes] = await Promise.all([
        partnerApi.getProfile(),
        partnerApi.getReferrals(),
        partnerApi.getOrders(),
        partnerApi.getCommissions(),
      ])
      setProfile(profileRes.data)
      setReferrals(referralRes.data || [])
      setOrders(orderRes.data || [])
      setCommissions(commissionRes.data || [])
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '加载合作者数据失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const summary = useMemo(() => {
    const paidAmount = orders.filter((item) => item.status === 'paid').reduce((sum, item) => sum + (item.amount || 0), 0)
    const commissionAmount = commissions.reduce((sum, item) => sum + (item.commission_amount || 0), 0)
    return {
      referrals: referrals.length,
      paidOrders: orders.filter((item) => item.status === 'paid').length,
      paidAmount,
      commissionAmount,
    }
  }, [commissions, orders, referrals])

  const copyReferralLink = async () => {
    const code = profile?.referral_code || ''
    const link = `${window.location.origin}/register?ref=${code}`
    try {
      await navigator.clipboard.writeText(link)
      message.success('推广链接已复制')
    } catch {
      message.info(link)
    }
  }

  const createInviteCode = async (values: { quota_limit: number; max_video_seconds: number; max_uses: number }) => {
    setCreatingCode(true)
    try {
      const { data } = await partnerApi.createInviteCode({
        plan_key: 'basic',
        quota_period: 'daily',
        quota_limit: values.quota_limit,
        max_video_seconds: values.max_video_seconds,
        max_uses: values.max_uses,
      })
      message.success(`兑换码已生成：${data.code}`)
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '生成兑换码失败')
    } finally {
      setCreatingCode(false)
    }
  }

  return (
    <div className="partner-dashboard-page">
      <div className="mb-6">
        <Typography.Title level={2}>合作者工作台</Typography.Title>
        <Typography.Paragraph type="secondary">
          查看自己推荐来的用户、订单和佣金，必要时给已付款用户发放兑换码。
        </Typography.Paragraph>
      </div>

      <Row gutter={[16, 16]} className="mb-4">
        <Col xs={24} md={6}>
          <Card>
            <Statistic title="推荐用户" value={summary.referrals} prefix={<TeamOutlined />} />
          </Card>
        </Col>
        <Col xs={24} md={6}>
          <Card>
            <Statistic title="付费订单" value={summary.paidOrders} prefix={<GiftOutlined />} />
          </Card>
        </Col>
        <Col xs={24} md={6}>
          <Card>
            <Statistic title="推荐收入" value={formatMoney(summary.paidAmount)} />
          </Card>
        </Col>
        <Col xs={24} md={6}>
          <Card>
            <Statistic title="预计佣金" value={formatMoney(summary.commissionAmount)} prefix={<WalletOutlined />} />
          </Card>
        </Col>
      </Row>

      <Card
        title="推广信息"
        className="mb-4"
        extra={<Button icon={<ReloadOutlined />} loading={loading} onClick={loadData}>刷新</Button>}
      >
        <Space wrap>
          <Tag color="blue">{profile?.display_name || '合作者'}</Tag>
          <Tag color="green">佣金比例 {((profile?.commission_rate_bps || 0) / 100).toFixed(1)}%</Tag>
          <Button icon={<CopyOutlined />} onClick={copyReferralLink}>复制推广链接</Button>
        </Space>
      </Card>

      <Card title="生成兑换码" className="mb-4">
        <Form layout="inline" initialValues={{ quota_limit: 30, max_video_seconds: 60, max_uses: 1 }} onFinish={createInviteCode}>
          <Form.Item name="quota_limit" label="每日次数" rules={[{ required: true }]}>
            <InputNumber min={1} max={999} />
          </Form.Item>
          <Form.Item name="max_video_seconds" label="单条秒数" rules={[{ required: true }]}>
            <InputNumber min={15} max={180} step={15} />
          </Form.Item>
          <Form.Item name="max_uses" label="可用次数" rules={[{ required: true }]}>
            <InputNumber min={1} max={99} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={creatingCode}>生成</Button>
          </Form.Item>
        </Form>
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} xl={12}>
          <Card title="推荐用户">
            <Table
              loading={loading}
              dataSource={referrals}
              rowKey="id"
              pagination={{ pageSize: 8 }}
              columns={[
                { title: '用户', dataIndex: 'username' },
                { title: '手机号', dataIndex: 'phone', render: (value: string | null) => value || '-' },
                { title: '状态', dataIndex: 'is_approved', render: (value: boolean) => value ? <Tag color="green">已开通</Tag> : <Tag>待开通</Tag> },
                { title: '注册时间', dataIndex: 'created_at', render: formatDate },
              ]}
            />
          </Card>
        </Col>
        <Col xs={24} xl={12}>
          <Card title="推荐订单">
            <Table
              loading={loading}
              dataSource={orders}
              rowKey="order_id"
              pagination={{ pageSize: 8 }}
              columns={[
                { title: '订单号', dataIndex: 'order_id', ellipsis: true },
                { title: '套餐', dataIndex: 'plan' },
                { title: '金额', dataIndex: 'amount', render: formatMoney },
                { title: '佣金', dataIndex: 'commission_amount', render: formatMoney },
                { title: '状态', dataIndex: 'status', render: (value: string) => value === 'paid' ? <Tag color="green">已支付</Tag> : <Tag>{value}</Tag> },
              ]}
            />
          </Card>
        </Col>
        <Col span={24}>
          <Card title="佣金台账">
            <Table
              loading={loading}
              dataSource={commissions}
              rowKey="id"
              pagination={{ pageSize: 8 }}
              columns={[
                { title: '用户ID', dataIndex: 'user_id' },
                { title: '来源', dataIndex: 'source' },
                { title: '订单金额', dataIndex: 'amount', render: formatMoney },
                { title: '佣金', dataIndex: 'commission_amount', render: formatMoney },
                { title: '状态', dataIndex: 'status', render: (value: string) => value === 'pending' ? <Tag color="orange">待结算</Tag> : <Tag>{value}</Tag> },
                { title: '时间', dataIndex: 'created_at', render: formatDate },
              ]}
            />
          </Card>
        </Col>
      </Row>
    </div>
  )
}
