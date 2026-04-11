import { useState, useEffect } from 'react'
import { Card, Table, Button, Space, Modal, Form, Input, Switch, message, Popconfirm } from 'antd'
import { EditOutlined, DeleteOutlined, PlusOutlined } from '@ant-design/icons'
import api from '@/services/api'

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
  const [saving, setSaving] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingCategory, setEditingCategory] = useState<Category | null>(null)
  const [form] = Form.useForm()

  useEffect(() => {
    loadCategories()
  }, [])

  const loadCategories = async () => {
    setLoading(true)
    try {
      const { data } = await api.get('/admin/article-categories')
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
      await api.delete(`/admin/article-categories/${id}`)
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
        await api.put(`/admin/article-categories/${editingCategory.id}`, data)
        message.success('更新成功')
      } else {
        await api.post('/admin/article-categories', data)
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
        confirmLoading={saving}
        okButtonProps={{ loading: saving }}
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
            rules={[
              { required: true, message: '请输入图标' },
              { 
                pattern: /[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F1E0}-\u{1F1FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/u,
                message: '请输入有效的Emoji表情'
              }
            ]}
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
            rules={[
              { 
                required: true,
                validator: (_, value) => {
                  if (!value || value.trim().split('\n').filter((t: string) => t.trim()).length === 0) {
                    return Promise.reject(new Error('请至少输入一个示例主题'));
                  }
                  return Promise.resolve();
                }
              }
            ]}
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