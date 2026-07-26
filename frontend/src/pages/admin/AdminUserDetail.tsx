import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  Avatar,
  Badge,
  Button,
  Card,
  Col,
  Descriptions,
  Divider,
  Input,
  InputNumber,
  message,
  Modal,
  Radio,
  Row,
  Select,
  Space,
  Statistic,
  Switch,
  Tag,
} from 'antd'
import {
  ArrowLeftOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  LockOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
  TeamOutlined,
  UnlockOutlined,
  UserOutlined,
} from '@ant-design/icons'
import { adminApi, User, UserPartnerProfile } from '@/services/admin'

const moduleLabels: Record<string, string> = {
  visual: '思维可视化',
  stickman: '火柴人成片',
  stickman_legacy: '经典讲解',
  stickman_v2: '火柴人成片',
  explainer: 'AI 视频导演',
  article: '公众号文章',
}

const defaultModuleOrder = ['visual', 'stickman', 'stickman_v2', 'stickman_legacy', 'explainer', 'article']

const formatDateTime = (value?: string | null) => {
  if (!value) return '-'
  try {
    return new Date(value.endsWith('Z') ? value : `${value}Z`).toLocaleString('zh-CN')
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

export default function AdminUserDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const userId = Number(id)
  const [user, setUser] = useState<User | null>(null)
  const [partnerProfile, setPartnerProfile] = useState<UserPartnerProfile | null>(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [durationDays, setDurationDays] = useState(30)
  const [newPassword, setNewPassword] = useState('')
  const [passwordOpen, setPasswordOpen] = useState(false)
  const [partnerEnabled, setPartnerEnabled] = useState(false)
  const [partnerDisplayName, setPartnerDisplayName] = useState('')
  const [partnerRate, setPartnerRate] = useState(3000)
  const [partnerStatus, setPartnerStatus] = useState('active')
  const userStats = user as (User & { last_active_at?: string | null; total_projects?: number }) | null

  const modulePermissions = useMemo(() => user?.module_permissions || {}, [user?.module_permissions])
  const moduleKeys = useMemo(() => {
    const keys = new Set([...defaultModuleOrder, ...Object.keys(modulePermissions)])
    return [...keys].filter((key) => modulePermissions[key] || defaultModuleOrder.includes(key))
  }, [modulePermissions])

  const loadUser = async () => {
    if (!userId) return
    setLoading(true)
    try {
      const [detailRes, partnerRes] = await Promise.all([
        adminApi.getUserDetail(userId),
        adminApi.getUserPartnerProfile(userId),
      ])
      setUser(detailRes.data)
      setPartnerProfile(partnerRes.data)
      setPartnerEnabled(!!partnerRes.data.enabled)
      setPartnerDisplayName(partnerRes.data.display_name || detailRes.data.username)
      setPartnerRate(partnerRes.data.commission_rate_bps ?? 3000)
      setPartnerStatus(partnerRes.data.status || 'active')
    } catch (error: any) {
      message.error(getErrorMessage(error, '加载用户详情失败'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadUser()
  }, [userId])

  const reloadAfter = async (success: string) => {
    message.success(success)
    await loadUser()
  }

  const toggleActive = async () => {
    if (!user) return
    setSaving(true)
    try {
      await adminApi.toggleUserActive(user.id)
      await reloadAfter(user.is_active ? '用户已禁用' : '用户已启用')
    } catch (error: any) {
      message.error(getErrorMessage(error, '操作失败'))
    } finally {
      setSaving(false)
    }
  }

  const approveUser = async () => {
    if (!user) return
    setSaving(true)
    try {
      await adminApi.approveUser(user.id)
      await reloadAfter('用户已审核通过')
    } catch (error: any) {
      message.error(getErrorMessage(error, '审核失败'))
    } finally {
      setSaving(false)
    }
  }

  const extendUser = async () => {
    if (!user) return
    setSaving(true)
    try {
      await adminApi.extendUser(user.id, durationDays)
      await reloadAfter('有效期已更新')
    } catch (error: any) {
      message.error(getErrorMessage(error, '延长有效期失败'))
    } finally {
      setSaving(false)
    }
  }

  const updateFrontendVersion = async (frontendVersion: 'legacy' | 'v2') => {
    if (!user) return
    setSaving(true)
    try {
      await adminApi.updateUser(user.id, { frontend_version: frontendVersion })
      await reloadAfter('前端版本已更新')
    } catch (error: any) {
      message.error(getErrorMessage(error, '更新前端版本失败'))
    } finally {
      setSaving(false)
    }
  }

  const updatePermission = async (moduleKey: string, patch: Record<string, any>) => {
    if (!user || user.is_admin) return
    const current = modulePermissions[moduleKey] || { enabled: false, daily_limit: 0, used_today: 0, period: 'monthly' }
    const nextPermissions = {
      ...modulePermissions,
      [moduleKey]: { ...current, ...patch },
    }
    setSaving(true)
    try {
      await adminApi.updateUserModulePermissions(user.id, nextPermissions)
      await reloadAfter('模块权限已更新')
    } catch (error: any) {
      message.error(getErrorMessage(error, '更新模块权限失败'))
    } finally {
      setSaving(false)
    }
  }

  const resetPassword = async () => {
    if (!user || !newPassword.trim()) return
    setSaving(true)
    try {
      await adminApi.resetPassword(user.id, newPassword.trim())
      setPasswordOpen(false)
      setNewPassword('')
      message.success('密码已重置')
    } catch (error: any) {
      message.error(getErrorMessage(error, '重置密码失败'))
    } finally {
      setSaving(false)
    }
  }

  const savePartnerProfile = async () => {
    if (!user) return
    setSaving(true)
    try {
      const { data } = await adminApi.updateUserPartnerProfile(user.id, {
        enabled: partnerEnabled,
        display_name: partnerDisplayName || user.username,
        commission_rate_bps: partnerRate,
        status: partnerEnabled ? partnerStatus : 'inactive',
      })
      setPartnerProfile(data)
      await reloadAfter(partnerEnabled ? '合作者设置已保存' : '合作者身份已停用')
    } catch (error: any) {
      message.error(getErrorMessage(error, '保存合作者设置失败'))
    } finally {
      setSaving(false)
    }
  }

  if (!user) {
    return (
      <Card loading={loading}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/admin/users')}>返回用户列表</Button>
      </Card>
    )
  }

  return (
    <div>
      <Space className="mb-4" wrap>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/admin/users')}>返回用户列表</Button>
        <Button icon={<ReloadOutlined />} loading={loading} onClick={loadUser}>刷新</Button>
      </Space>

      <Card className="mb-4">
        <Space align="center" size={16} wrap>
          <Avatar size={56} icon={<UserOutlined />} style={{ background: user.is_admin ? '#f59e0b' : '#2563eb' }} />
          <div>
            <h2 style={{ margin: 0 }}>{user.username}</h2>
            <Space wrap className="mt-2">
              <Badge status={user.is_active ? 'success' : 'error'} text={user.is_active ? '正常' : '已禁用'} />
              {user.is_approved ? <Tag color="green">已审核</Tag> : <Tag color="orange">待审核</Tag>}
              {user.is_admin ? <Tag color="gold">管理员</Tag> : user.role === 'partner' ? <Tag color="blue">合作者</Tag> : <Tag>普通用户</Tag>}
            </Space>
          </div>
        </Space>
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={14}>
          <Card title="账号信息" className="mb-4">
            <Descriptions bordered column={1} size="small">
              <Descriptions.Item label="用户 ID">{user.id}</Descriptions.Item>
              <Descriptions.Item label="手机号">{user.phone || '-'}</Descriptions.Item>
              <Descriptions.Item label="邮箱">{user.email || '-'}</Descriptions.Item>
              <Descriptions.Item label="注册时间">{formatDateTime(user.created_at)}</Descriptions.Item>
              <Descriptions.Item label="最后活跃">{formatDateTime(userStats?.last_active_at)}</Descriptions.Item>
              <Descriptions.Item label="有效期">{formatDateTime(user.expires_at)}</Descriptions.Item>
            </Descriptions>
            <Divider />
            <Space wrap>
              {!user.is_approved && (
                <Button type="primary" icon={<CheckCircleOutlined />} loading={saving} onClick={approveUser}>审核通过</Button>
              )}
              <Button icon={user.is_active ? <LockOutlined /> : <UnlockOutlined />} loading={saving} onClick={toggleActive}>
                {user.is_active ? '禁用账号' : '启用账号'}
              </Button>
              <Button icon={<SafetyCertificateOutlined />} onClick={() => setPasswordOpen(true)}>重置密码</Button>
            </Space>
            <Divider />
            <Row gutter={[12, 12]}>
              <Col xs={24} md={8}>
                <div className="text-gray-500 mb-1">延长有效期</div>
                <InputNumber min={1} max={3650} value={durationDays} onChange={(value) => setDurationDays(value || 30)} addonAfter="天" style={{ width: '100%' }} />
              </Col>
              <Col xs={24} md={8}>
                <div className="text-gray-500 mb-1">前端版本</div>
                <Select
                  value={user.frontend_version || 'legacy'}
                  onChange={updateFrontendVersion}
                  options={[
                    { label: '老版本', value: 'legacy' },
                    { label: '新版本', value: 'v2' },
                  ]}
                  style={{ width: '100%' }}
                />
              </Col>
              <Col xs={24} md={8}>
                <div className="text-gray-500 mb-1">&nbsp;</div>
                <Button icon={<ClockCircleOutlined />} loading={saving} onClick={extendUser} block>保存有效期</Button>
              </Col>
            </Row>
          </Card>

          <Card title="模块权限与配额" className="mb-4">
            {user.is_admin ? (
              <Tag color="blue">管理员账号默认拥有全部模块权限</Tag>
            ) : (
              <Space direction="vertical" style={{ width: '100%' }} size="middle">
                {moduleKeys.map((moduleKey) => {
                  const permission: any = modulePermissions[moduleKey] || { enabled: false, daily_limit: 0, used_today: 0, period: moduleKey === 'visual' ? 'daily' : 'monthly' }
                  const isStickmanWorkflow = moduleKey === 'stickman_v2'
                  return (
                    <Card key={moduleKey} size="small" title={moduleLabels[moduleKey] || moduleKey}>
                      <Space wrap align="center">
                        <span>启用</span>
                        <Switch checked={!!permission.enabled} loading={saving} onChange={(checked) => updatePermission(moduleKey, { enabled: checked })} />
                        <span>额度</span>
                        <InputNumber min={0} max={999} value={permission.daily_limit} onChange={(value) => updatePermission(moduleKey, { daily_limit: value || 0 })} />
                        <span>周期</span>
                        <Select
                          value={permission.period || (moduleKey === 'visual' ? 'daily' : 'monthly')}
                          onChange={(period) => updatePermission(moduleKey, { period })}
                          options={[
                            { label: '每日', value: 'daily' },
                            { label: '每月', value: 'monthly' },
                          ]}
                          style={{ width: 96 }}
                        />
                        <Tag color="geekblue">已用 {permission.used_today || 0}</Tag>
                      </Space>
                      {isStickmanWorkflow ? (
                        <>
                          <Divider />
                          <Space direction="vertical" style={{ width: '100%' }} size="middle">
                            <Radio.Group
                              value={permission.quota_mode || 'period'}
                              onChange={(event) => updatePermission(moduleKey, { quota_mode: event.target.value })}
                              optionType="button"
                              buttonStyle="solid"
                              options={[
                                { label: '月卡/周期卡', value: 'period' },
                                { label: '次数包不限时', value: 'count_package' },
                              ]}
                            />
                            {(permission.quota_mode || 'period') === 'count_package' ? (
                              <Row gutter={[12, 12]}>
                                <Col xs={24} md={8}>
                                  <div className="text-gray-500 mb-1">总视频个数</div>
                                  <InputNumber min={0} max={9999} value={permission.total_video_limit || permission.daily_limit || 40} onChange={(value) => updatePermission(moduleKey, { total_video_limit: value || 0, daily_limit: value || 0 })} style={{ width: '100%' }} />
                                </Col>
                                <Col xs={24} md={8}>
                                  <div className="text-gray-500 mb-1">已用视频</div>
                                  <InputNumber min={0} max={9999} value={permission.used_total_videos || 0} onChange={(value) => updatePermission(moduleKey, { used_total_videos: value || 0, used_today: value || 0 })} style={{ width: '100%' }} />
                                </Col>
                                <Col xs={24} md={8}>
                                  <div className="text-gray-500 mb-1">单条最长秒数</div>
                                  <InputNumber min={15} max={1800} value={permission.max_video_seconds || 300} onChange={(value) => updatePermission(moduleKey, { max_video_seconds: value || 300, unlimited_time: true, period: 'lifetime' })} style={{ width: '100%' }} />
                                </Col>
                              </Row>
                            ) : (
                              <Row gutter={[12, 12]}>
                                <Col xs={24} md={6}>
                                  <div className="text-gray-500 mb-1">每日视频数</div>
                                  <InputNumber min={0} max={999} value={permission.daily_limit || 0} onChange={(value) => updatePermission(moduleKey, { daily_limit: value || 0, period: 'monthly' })} style={{ width: '100%' }} />
                                </Col>
                                <Col xs={24} md={6}>
                                  <div className="text-gray-500 mb-1">每日分钟</div>
                                  <InputNumber min={0} max={9999} value={permission.daily_minutes_limit || 0} onChange={(value) => updatePermission(moduleKey, { daily_minutes_limit: value || 0 })} style={{ width: '100%' }} />
                                </Col>
                                <Col xs={24} md={6}>
                                  <div className="text-gray-500 mb-1">每月分钟</div>
                                  <InputNumber min={0} max={99999} value={permission.monthly_minutes_limit || 0} onChange={(value) => updatePermission(moduleKey, { monthly_minutes_limit: value || 0 })} style={{ width: '100%' }} />
                                </Col>
                                <Col xs={24} md={6}>
                                  <div className="text-gray-500 mb-1">单条最长秒数</div>
                                  <InputNumber min={15} max={1800} value={permission.max_video_seconds || 60} onChange={(value) => updatePermission(moduleKey, { max_video_seconds: value || 60 })} style={{ width: '100%' }} />
                                </Col>
                              </Row>
                            )}
                            <Space wrap>
                              <Tag color="purple">本月已用 {permission.used_monthly_minutes || 0} 分钟</Tag>
                              <Tag color="cyan">总已用 {permission.used_total_videos || 0} 个</Tag>
                            </Space>
                          </Space>
                        </>
                      ) : null}
                    </Card>
                  )
                })}
              </Space>
            )}
          </Card>
        </Col>

        <Col xs={24} lg={10}>
          <Card title="合作者设置" className="mb-4">
            {user.is_admin ? (
              <Tag color="gold">管理员账号不能设置为合作者</Tag>
            ) : (
              <Space direction="vertical" style={{ width: '100%' }} size="middle">
                <Space>
                  <span>合作者身份</span>
                  <Switch checked={partnerEnabled} onChange={setPartnerEnabled} />
                  <Tag color={partnerProfile?.enabled ? 'blue' : 'default'}>{partnerProfile?.enabled ? '已启用' : '未启用'}</Tag>
                </Space>
                <div>
                  <div className="text-gray-500 mb-1">展示名称</div>
                  <Input value={partnerDisplayName} onChange={(event) => setPartnerDisplayName(event.target.value)} placeholder={user.username} disabled={!partnerEnabled} />
                </div>
                <Row gutter={12}>
                  <Col span={12}>
                    <div className="text-gray-500 mb-1">佣金比例</div>
                    <InputNumber min={0} max={10000} value={partnerRate} onChange={(value) => setPartnerRate(value || 0)} addonAfter="基点" style={{ width: '100%' }} disabled={!partnerEnabled} />
                  </Col>
                  <Col span={12}>
                    <div className="text-gray-500 mb-1">状态</div>
                    <Select
                      value={partnerStatus}
                      onChange={setPartnerStatus}
                      options={[
                        { label: '启用', value: 'active' },
                        { label: '停用', value: 'inactive' },
                      ]}
                      style={{ width: '100%' }}
                      disabled={!partnerEnabled}
                    />
                  </Col>
                </Row>
                <Descriptions bordered column={1} size="small">
                  <Descriptions.Item label="推荐码">{partnerProfile?.referral_code || '-'}</Descriptions.Item>
                  <Descriptions.Item label="资料 ID">{partnerProfile?.id || '-'}</Descriptions.Item>
                </Descriptions>
                <Button type="primary" icon={<TeamOutlined />} loading={saving} onClick={savePartnerProfile}>保存合作者设置</Button>
              </Space>
            )}
          </Card>

          <Row gutter={[12, 12]} className="mb-4">
            <Col span={12}><Card><Statistic title="视频项目" value={userStats?.total_projects || 0} /></Card></Col>
            <Col span={12}><Card><Statistic title="文章" value={user.total_articles || 0} /></Card></Col>
          </Row>

          <Card title="最近任务日志">
            {user.latest_task ? (
              <div>
                <div className="font-medium mb-2">{user.latest_task.project_title}</div>
                <Tag>{user.latest_task.status}</Tag>
                {user.latest_task.error_message ? <div className="text-red-500 mt-2">{user.latest_task.error_message}</div> : null}
                {user.latest_task.log ? <pre style={{ whiteSpace: 'pre-wrap', maxHeight: 220, overflow: 'auto', fontSize: 12 }}>{user.latest_task.log}</pre> : null}
              </div>
            ) : (
              <div className="text-gray-400">暂无任务日志</div>
            )}
          </Card>
        </Col>
      </Row>

      <Modal
        title="重置密码"
        open={passwordOpen}
        onCancel={() => setPasswordOpen(false)}
        onOk={resetPassword}
        confirmLoading={saving}
        okText="确认重置"
        cancelText="取消"
      >
        <Input.Password value={newPassword} onChange={(event) => setNewPassword(event.target.value)} placeholder="输入新密码，至少 8 位" minLength={8} />
      </Modal>
    </div>
  )
}
