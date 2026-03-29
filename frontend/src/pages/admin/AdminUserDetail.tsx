import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, Descriptions, Tag, Button, Spin, Table, Collapse, Badge, Empty } from 'antd'
import { ArrowLeftOutlined, SyncOutlined, CloseCircleOutlined, MessageOutlined, CodeOutlined, PlayCircleOutlined, VideoCameraOutlined } from '@ant-design/icons'
import { adminApi, UserDetail } from '@/services/admin'

const { Panel } = Collapse

const formatDateTime = (dateStr: string | null | undefined) => {
  if (!dateStr) return '-'
  try {
    const date = new Date(dateStr.endsWith('Z') ? dateStr : dateStr + 'Z')
    return date.toLocaleString('zh-CN', { hour12: false })
  } catch {
    return '-'
  }
}

const formatNumber = (num: number) => {
  return num.toLocaleString('zh-CN')
}

const getStatusTag = (status: string) => {
  const statusConfig: Record<string, { color: string; icon: React.ReactNode; text: string }> = {
    chatting: { color: 'blue', icon: <MessageOutlined />, text: '对话中' },
    code_generating: { color: 'orange', icon: <SyncOutlined spin />, text: '生成代码中' },
    code_generated: { color: 'cyan', icon: <CodeOutlined />, text: '代码生成完成' },
    processing: { color: 'purple', icon: <PlayCircleOutlined />, text: '渲染中' },
    completed: { color: 'green', icon: <VideoCameraOutlined />, text: '视频生成成功' },
    failed: { color: 'red', icon: <CloseCircleOutlined />, text: '生成失败' }
  }
  const config = statusConfig[status] || { color: 'default', icon: null, text: status }
  return <Tag color={config.color} icon={config.icon}>{config.text}</Tag>
}

export default function AdminUserDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [userDetail, setUserDetail] = useState<UserDetail | null>(null)

  const fetchUserDetail = async () => {
    if (!id) return
    setLoading(true)
    try {
      const { data } = await adminApi.getUserDetail(Number(id))
      setUserDetail(data)
    } catch (error) {
      console.error('获取用户详情失败:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchUserDetail()
  }, [id])

  if (loading) {
    return (
      <div className="flex justify-center items-center h-96">
        <Spin size="large" />
      </div>
    )
  }

  if (!userDetail) {
    return (
      <div className="p-6">
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/admin/users')}>返回用户列表</Button>
        <Empty description="用户不存在" className="mt-10" />
      </div>
    )
  }

  const projectColumns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 60
    },
    {
      title: '项目名称',
      dataIndex: 'title',
      key: 'title'
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => getStatusTag(status)
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => formatDateTime(date)
    }
  ]

  return (
    <div className="p-6">
      <div className="mb-4">
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/admin/users')}>返回用户列表</Button>
      </div>

      <Card title={`用户详情 - ${userDetail.username}`} className="mb-4">
        <Descriptions column={2} bordered size="small">
          <Descriptions.Item label="用户名">{userDetail.username}</Descriptions.Item>
          <Descriptions.Item label="邮箱">{userDetail.email}</Descriptions.Item>
          <Descriptions.Item label="状态">
            {userDetail.is_active 
              ? <Badge status="success" text="正常" />
              : <Badge status="error" text="已禁用" />
            }
          </Descriptions.Item>
          <Descriptions.Item label="角色">
            {userDetail.is_admin ? <Tag color="gold">管理员</Tag> : <Tag>普通用户</Tag>}
          </Descriptions.Item>
          <Descriptions.Item label="审核状态">
            {userDetail.is_approved 
              ? <Tag color="green">已通过</Tag>
              : <Tag color="orange">待审核</Tag>
            }
          </Descriptions.Item>
          <Descriptions.Item label="过期时间">{formatDateTime(userDetail.expires_at)}</Descriptions.Item>
          <Descriptions.Item label="注册时间">{formatDateTime(userDetail.created_at)}</Descriptions.Item>
          <Descriptions.Item label="最后活跃">{formatDateTime(userDetail.last_active_at)}</Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title="使用统计" className="mb-4">
        <div className="grid grid-cols-3 gap-4 text-center">
          <div className="p-4 bg-blue-50 rounded-lg">
            <div className="text-3xl font-bold text-blue-600">{formatNumber(userDetail.total_projects)}</div>
            <div className="text-gray-500 mt-1">项目数</div>
          </div>
          <div className="p-4 bg-green-50 rounded-lg">
            <div className="text-3xl font-bold text-green-600">{formatNumber(userDetail.videos_count)}</div>
            <div className="text-gray-500 mt-1">视频数</div>
          </div>
          <div className="p-4 bg-purple-50 rounded-lg">
            <div className="text-3xl font-bold text-purple-600">{formatNumber(userDetail.token_usage)}</div>
            <div className="text-gray-500 mt-1">Token 使用量</div>
          </div>
        </div>
      </Card>

      {userDetail.current_status && (
        <Card title="当前状态" className="mb-4">
          <div className="flex items-center gap-4">
            {getStatusTag(userDetail.current_status.status)}
            <div>
              <div className="font-medium">{userDetail.current_status.project_title}</div>
              <div className="text-gray-500 text-sm">更新于 {formatDateTime(userDetail.current_status.updated_at)}</div>
            </div>
          </div>
        </Card>
      )}

      <Card title="最近项目（3个）" className="mb-4">
        <Table
          dataSource={userDetail.recent_projects}
          columns={projectColumns}
          rowKey="id"
          pagination={false}
          size="small"
          locale={{ emptyText: '暂无项目' }}
        />
      </Card>

      {userDetail.latest_task && (
        <Card title="最近任务日志">
          <Descriptions column={2} size="small" className="mb-4">
            <Descriptions.Item label="项目">{userDetail.latest_task.project_title}</Descriptions.Item>
            <Descriptions.Item label="状态">{getStatusTag(userDetail.latest_task.status)}</Descriptions.Item>
            <Descriptions.Item label="创建时间">{formatDateTime(userDetail.latest_task.created_at)}</Descriptions.Item>
            <Descriptions.Item label="错误信息">
              {userDetail.latest_task.error_message ? (
                <span className="text-red-500">{userDetail.latest_task.error_message}</span>
              ) : '-'}
            </Descriptions.Item>
          </Descriptions>
          
          {userDetail.latest_task.log && (
            <Collapse>
              <Panel header="查看完整日志" key="log">
                <pre className="bg-gray-900 text-green-400 p-4 rounded overflow-auto max-h-96 text-xs">
                  {userDetail.latest_task.log}
                </pre>
              </Panel>
            </Collapse>
          )}
        </Card>
      )}
    </div>
  )
}