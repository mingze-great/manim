import { useState, useEffect } from 'react'
import { Card, Table, Button, Space, Modal, Form, Input, Select, Switch, message, Popconfirm } from 'antd'
import { EditOutlined, DeleteOutlined, PlusOutlined } from '@ant-design/icons'
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'

interface Category {
  id: number
  name: string
  icon: string
  system_prompt: string
  example_topics: string
  image_prompt_template: string
  is_active: boolean
  sort_order: number
}

export default function AdminArticleCategories() {
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingCategory, setEditingCategory] = useState<Category | null>(null)
  const [form] = Form.useForm()

  useEffect(() => {
    loadCategories()
  }, [])

  const loadCategories = async () => {
    setLoading(true)
    try {
      const token = localStorage.getItem('token')
      const { data } = await axios.get(`${API_BASE}/admin/article-categories`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setCategories(data)
    } catch (error) {
      message.error('加载创作方向失败')
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = () => {
    setEditingCategory(null)
    form.resetFields()
    setModalVisible(true)
  }

  const handleEdit = (record: Category) => {
    setEditingCategory(record)
    form.setFieldsValue({
      ...record,
      example_topics: record.example_topics ? JSON.parse(record.example_topics).join('\n') : ''
    })
    setModalVisible(true)
  }

  const handleDelete = async (id: number) => {
    try {
      const token = localStorage.getItem('token')
      await axios.delete(`${API_BASE}/admin/article-categories/${id}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      message.success('删除成功')
      loadCategories()
    } catch (error) {
      message.error('删除失败')
    }
  }

  const handleSubmit = async (values: any) => {
    try {
      const token = localStorage.getItem('token')
      const data = {
        ...values,
        example_topics: values.example_topics.split('\n').filter((t: string) => t.trim())
      }

      if (editingCategory) {
        await axios.put(
          `${API_BASE}/admin/article-categories/${editingCategory.id}`,
          data,
          { headers: { Authorization: `Bearer ${token}` } }
        )
        message.success('更新成功')
      } else {
        await axios.post(
          `${API_BASE}/admin/article-categories`,
          data,
          { headers: { Authorization: `Bearer ${token}` } }
        )
        message.success('创建成功')
      }

      setModalVisible(false)
      loadCategories()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '操作失败')
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
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
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
      render: (_: any, record: Category) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定删除此创作方向吗？"
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
        title="文章创作方向管理"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            新建创作方向
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={categories}
          rowKey="id"
          loading={loading}
        />
      </Card>

      <Modal
        title={editingCategory ? '编辑创作方向' : '新建创作方向'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={() => form.submit()}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{ is_active: true, sort_order: 0 }}
        >
          <Form.Item
            name="name"
            label="方向名称"
            rules={[{ required: true, message: '请输入方向名称' }]}
          >
            <Input placeholder="例如：两性情感、育儿、体育" />
          </Form.Item>

          <Form.Item
            name="icon"
            label="图标（Emoji）"
            rules={[{ required: true, message: '请输入图标' }]}
          >
            <Input placeholder="例如：❤️、👶、⚽" />
          </Form.Item>

          <Form.Item
            name="system_prompt"
            label="系统提示词"
            rules={[{ required: true, message: '请输入系统提示词' }]}
          >
            <Input.TextArea rows={6} placeholder="输入AI生成文案时的系统提示词..." />
          </Form.Item>

          <Form.Item
            name="example_topics"
            label="示例主题（每行一个）"
          >
            <Input.TextArea rows={4} placeholder="异地恋维护&#10;情侣吵架和解&#10;如何让感情保鲜" />
          </Form.Item>

          <Form.Item
            name="image_prompt_template"
            label="图片生成提示词模板"
          >
            <Input.TextArea 
              rows={3} 
              placeholder="公众号文章配图，主题：{topic}，两性情感风格，高质量"
            />
          </Form.Item>

          <Form.Item
            name="sort_order"
            label="排序"
          >
            <Input type="number" />
          </Form.Item>

          <Form.Item
            name="is_active"
            label="启用状态"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}