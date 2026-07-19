import { useState, useEffect } from 'react'
import { Card, Table, Button, Space, Modal, Form, Input, Switch, message, Popconfirm, InputNumber } from 'antd'
import { EditOutlined, DeleteOutlined, PlusOutlined } from '@ant-design/icons'
import api from '@/services/api'

interface VideoTopicCategory {
  id: number
  name: string
  icon: string
  description: string
  example_topics: string[]
  topic_generation_prompt: string
  system_prompt: string
  is_active: boolean
  sort_order: number
  created_at: string
}

export default function AdminVideoTopics() {
  const [categories, setCategories] = useState<VideoTopicCategory[]>([])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingCategory, setEditingCategory] = useState<VideoTopicCategory | null>(null)
  const [form] = Form.useForm()

  useEffect(() => {
    loadCategories()
  }, [])

  const loadCategories = async () => {
    setLoading(true)
    try {
      const { data } = await api.get('/admin/video-topic-categories')
      setCategories(data)
    } catch (error) {
      message.error('加载失败')
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = () => {
    setEditingCategory(null)
    form.resetFields()
    setModalVisible(true)
  }

  const handleEdit = (record: VideoTopicCategory) => {
    setEditingCategory(record)
    form.setFieldsValue({
      ...record,
      example_topics: record.example_topics.join('\n')
    })
    setModalVisible(true)
  }

  const handleDelete = async (id: number) => {
    try {
      await api.delete(`/admin/video-topic-categories/${id}`)
      message.success('删除成功')
      loadCategories()
    } catch (error) {
      message.error('删除失败')
    }
  }

  const handleSubmit = async (values: any) => {
    setSaving(true)
    try {
      const data = {
        ...values,
        example_topics: values.example_topics.split('\n').filter((t: string) => t.trim())
      }

      if (editingCategory) {
        await api.put(`/admin/video-topic-categories/${editingCategory.id}`, data)
        message.success('更新成功')
      } else {
        await api.post('/admin/video-topic-categories', data)
        message.success('创建成功')
      }

      setModalVisible(false)
      loadCategories()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '操作失败')
    } finally {
      setSaving(false)
    }
  }

  const columns = [
    {
      title: '图标',
      dataIndex: 'icon',
      key: 'icon',
      width: 60,
      render: (icon: string) => <span style={{ fontSize: '24px' }}>{icon}</span>
    },
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name'
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true
    },
    {
      title: '示例数量',
      dataIndex: 'example_topics',
      key: 'example_count',
      width: 100,
      render: (topics: string[]) => topics?.length || 0
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (active: boolean) => (
        <span style={{ color: active ? '#52c41a' : '#999' }}>
          {active ? '启用' : '禁用'}
        </span>
      )
    },
    {
      title: '排序',
      dataIndex: 'sort_order',
      key: 'sort_order',
      width: 80
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_: any, record: VideoTopicCategory) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定删除此方向吗？"
            onConfirm={() => handleDelete(record.id)}
          >
            <Button type="link" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      )
    }
  ]

  return (
    <div style={{ padding: '24px' }}>
      <Card
        title="视频主题方向管理"
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleCreate}
          >
            新建方向
          </Button>
        }
      >
        <Table
          dataSource={categories}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      <Modal
        title={editingCategory ? '编辑方向' : '新建方向'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        width={700}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{ is_active: true, sort_order: 0 }}
        >
          <Form.Item
            label="方向名称"
            name="name"
            rules={[{ required: true, message: '请输入方向名称' }]}
          >
            <Input placeholder="如：思维方法论" />
          </Form.Item>

          <Form.Item
            label="图标"
            name="icon"
            rules={[{ required: true, message: '请输入图标' }]}
          >
            <Input placeholder="如：🧠" style={{ width: 100 }} />
          </Form.Item>

          <Form.Item
            label="描述"
            name="description"
          >
            <Input.TextArea rows={2} placeholder="如：认知提升、思维模型、学习方法" />
          </Form.Item>

          <Form.Item
            label="爆款主题示例（每行一个）"
            name="example_topics"
          >
            <Input.TextArea 
              rows={4} 
              placeholder="世界十大顶级思维&#10;刻意练习法则&#10;复利思维的力量" 
            />
          </Form.Item>

          <Form.Item
            label="主题生成提示词"
            name="topic_generation_prompt"
          >
            <Input.TextArea 
              rows={3} 
              placeholder="生成思维方法论相关的热门主题，如认知提升、思维模型、学习方法等" 
            />
          </Form.Item>

          <Form.Item
            label="系统提示词（用于内容生成）"
            name="system_prompt"
          >
            <Input.TextArea 
              rows={6} 
              placeholder="你是一个思维方法论和认知科学的专家..."
            />
          </Form.Item>

          <Form.Item
            label="排序"
            name="sort_order"
          >
            <InputNumber min={0} max={100} />
          </Form.Item>

          <Form.Item
            label="启用状态"
            name="is_active"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button onClick={() => setModalVisible(false)}>
                取消
              </Button>
              <Button type="primary" htmlType="submit" loading={saving}>
                保存
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}