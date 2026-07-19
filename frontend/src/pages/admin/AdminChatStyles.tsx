import { useState, useEffect } from 'react'
import { Button, Space, Modal, Form, Input, message, Popconfirm, Tag, Card, Spin } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import api from '@/services/api'
import { useIsMobile } from '@/hooks/useIsMobile'

const { TextArea } = Input

interface ChatStyle {
  id: number
  name: string
  code: string
  description: string | null
  system_prompt_zh: string
  system_prompt_en: string | null
  is_default: boolean
  is_active: boolean
  created_at: string
}

export default function AdminChatStyles() {
  const isMobile = useIsMobile()
  const [styles, setStyles] = useState<ChatStyle[]>([])
  const [loading, setLoading] = useState(true)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingStyle, setEditingStyle] = useState<ChatStyle | null>(null)
  const [form] = Form.useForm()

  useEffect(() => {
    fetchStyles()
  }, [])

  const fetchStyles = async () => {
    try {
      const { data } = await api.get<ChatStyle[]>('/chat-styles/')
      setStyles(data || [])
    } catch (err) {
      message.error('获取风格失败')
    } finally {
      setLoading(false)
    }
  }

  const handleAdd = () => {
    setEditingStyle(null)
    form.resetFields()
    setModalVisible(true)
  }

  const handleEdit = (style: ChatStyle) => {
    setEditingStyle(style)
    form.setFieldsValue(style)
    setModalVisible(true)
  }

  const handleDelete = async (id: number) => {
    try {
      await api.delete(`/chat-styles/${id}`)
      message.success('删除成功')
      fetchStyles()
    } catch (err) {
      message.error('删除失败')
    }
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      if (editingStyle) {
        await api.put(`/chat-styles/${editingStyle.id}`, values)
        message.success('更新成功')
      } else {
        await api.post('/chat-styles/', values)
        message.success('创建成功')
      }
      setModalVisible(false)
      fetchStyles()
    } catch (err) {
      message.error('操作失败')
    }
  }

  const handleInitDefaults = async () => {
    try {
      const { data } = await api.post('/chat-styles/init-defaults')
      message.success(data.message || '初始化成功')
      fetchStyles()
    } catch (err) {
      message.error('初始化失败')
    }
  }

  const renderStyleCard = (record: ChatStyle) => (
    <Card key={record.id} size="small" style={{ borderRadius: '12px' }}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <div className="font-semibold break-words">{record.name}</div>
            <Tag color="blue">{record.code}</Tag>
            {record.is_default ? <Tag color="green">默认</Tag> : null}
          </div>
          <div className="text-sm text-gray-500 mt-2 leading-6">{record.description || '暂无风格说明'}</div>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)}>编辑</Button>
        <Popconfirm title="确定删除此风格？" onConfirm={() => handleDelete(record.id)}>
          <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
        </Popconfirm>
      </div>
    </Card>
  )

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-2xl font-bold">对话风格管理</h2>
          <p className="text-gray-500 mt-1">管理AI对话的风格，用户可在对话时选择</p>
        </div>
        <Space>
          {styles.length === 0 && (
            <Button onClick={handleInitDefaults}>
              初始化默认风格
            </Button>
          )}
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            添加风格
          </Button>
        </Space>
      </div>

      {loading ? (
        <div className="flex justify-center items-center py-16">
          <Spin size="large" />
        </div>
      ) : (
        <div className={isMobile ? 'space-y-3' : 'grid grid-cols-1 xl:grid-cols-2 gap-4'}>
          {styles.map((record) => renderStyleCard(record))}
        </div>
      )}

      <Modal
        title={editingStyle ? '编辑风格' : '添加风格'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        width={800}
        okText="保存"
      >
        <Form form={form} layout="vertical" className="mt-4">
          <Form.Item
            name="name"
            label="风格名称"
            rules={[{ required: true, message: '请输入风格名称' }]}
          >
            <Input placeholder="如：保守、犀利、激进" />
          </Form.Item>

          <Form.Item
            name="code"
            label="风格标识"
            rules={[{ required: true, message: '请输入风格标识' }]}
            extra="英文标识，如：conservative、sharp、radical"
          >
            <Input placeholder="conservative" />
          </Form.Item>

          <Form.Item
            name="description"
            label="风格描述"
          >
            <Input placeholder="简短描述此风格的特点" />
          </Form.Item>

          <Form.Item
            name="system_prompt_zh"
            label="中文提示词"
            rules={[{ required: true, message: '请输入中文提示词' }]}
            extra="AI对话时使用的系统提示词，定义AI的回复风格"
          >
            <TextArea
              rows={10}
              className="font-mono text-sm"
              placeholder="你是一个专业的动画内容策划专家..."
            />
          </Form.Item>

          <Form.Item
            name="system_prompt_en"
            label="英文提示词"
            extra="可选，用于英文内容的对话"
          >
            <TextArea
              rows={6}
              className="font-mono text-sm"
              placeholder="You are a professional animation content planning expert..."
            />
          </Form.Item>

          <Form.Item
            name="is_default"
            label="设为默认"
            valuePropName="checked"
          >
            <Space>
              <input type="checkbox" />
              <span>设为默认风格</span>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
