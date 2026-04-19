import { useState, useEffect } from 'react'
import { Table, Button, Space, Modal, Form, Input, InputNumber, Switch, message, Popconfirm } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import api from '@/services/api'

interface TemplateCategory {
  id: number
  name: string
  code: string
  description: string | null
  icon: string | null
  sort_order: number
  is_active: boolean
  skip_chat: boolean
  created_at: string
}

export default function AdminTemplateCategories() {
  const [categories, setCategories] = useState<TemplateCategory[]>([])
  const [loading, setLoading] = useState(true)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingCategory, setEditingCategory] = useState<TemplateCategory | null>(null)
  const [form] = Form.useForm()

  useEffect(() => {
    fetchCategories()
  }, [])

  const fetchCategories = async () => {
    setLoading(true)
    try {
      const { data } = await api.get('/admin/template-categories')
      setCategories(data.categories || [])
    } catch (err) {
      message.error('获取分类失败')
    } finally {
      setLoading(false)
    }
  }

  const handleAdd = () => {
    setEditingCategory(null)
    form.resetFields()
    form.setFieldsValue({ sort_order: 0, is_active: true })
    setModalVisible(true)
  }

  const handleEdit = (category: TemplateCategory) => {
    setEditingCategory(category)
    form.setFieldsValue(category)
    setModalVisible(true)
  }

  const handleDelete = async (id: number) => {
    try {
      await api.delete(`/admin/template-categories/${id}`)
      message.success('删除成功')
      fetchCategories()
    } catch (err: any) {
      message.error(err.response?.data?.detail || '删除失败')
    }
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      if (editingCategory) {
        await api.put(`/admin/template-categories/${editingCategory.id}`, values)
        message.success('更新成功')
      } else {
        await api.post('/admin/template-categories', values)
        message.success('创建成功')
      }
      setModalVisible(false)
      fetchCategories()
    } catch (err: any) {
      message.error(err.response?.data?.detail || '操作失败')
    }
  }

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 60,
    },
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      width: 150,
    },
    {
      title: '代码',
      dataIndex: 'code',
      key: 'code',
      width: 120,
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '排序',
      dataIndex: 'sort_order',
      key: 'sort_order',
      width: 80,
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (isActive: boolean) => (
        <span style={{ color: isActive ? '#52c41a' : '#999' }}>
          {isActive ? '启用' : '禁用'}
        </span>
      ),
    },
    {
      title: '跳过对话',
      dataIndex: 'skip_chat',
      key: 'skip_chat',
      width: 100,
      render: (skipChat: boolean) => (
        <span style={{ color: skipChat ? '#1890ff' : '#999' }}>
          {skipChat ? '是' : '否'}
        </span>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_: any, record: TemplateCategory) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定删除此分类？"
            description="删除后无法恢复，已关联的模板将失去分类"
            onConfirm={() => handleDelete(record.id)}
          >
            <Button type="link" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 style={{ margin: 0 }}>模板分类管理</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
          添加分类
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={categories}
        rowKey="id"
        loading={loading}
        pagination={false}
      />

      <Modal
        title={editingCategory ? '编辑分类' : '添加分类'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="分类名称"
            rules={[{ required: true, message: '请输入分类名称' }]}
          >
            <Input placeholder="如：数学可视化" />
          </Form.Item>
          <Form.Item
            name="code"
            label="分类代码"
            rules={[
              { required: true, message: '请输入分类代码' },
              { pattern: /^[a-z_]+$/, message: '只能使用小写字母和下划线' },
            ]}
          >
            <Input placeholder="如：math" disabled={!!editingCategory} />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} placeholder="分类用途说明" />
          </Form.Item>
          <Form.Item name="icon" label="图标名称">
            <Input placeholder="Ant Design 图标名称，如：CalculatorOutlined" />
          </Form.Item>
          <Form.Item name="sort_order" label="排序" valuePropName="value">
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="is_active" label="启用状态" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>
          <Form.Item name="skip_chat" label="跳过对话" valuePropName="checked" tooltip="开启后，该分类的项目将跳过对话打磨，直接生成脚本">
            <Switch checkedChildren="是" unCheckedChildren="否" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
