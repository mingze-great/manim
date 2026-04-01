import { useState, useEffect, useMemo } from 'react'
import { Table, Button, Space, Tag, Modal, Form, Input, message, Popconfirm, Card, Row, Col, Statistic } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, FileTextOutlined, AppstoreOutlined, StarOutlined, EyeOutlined } from '@ant-design/icons'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { templateApi, Template } from '@/services/template'

const { TextArea } = Input
const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']

export default function AdminTemplates() {
  const [templates, setTemplates] = useState<Template[]>([])
  const [loading, setLoading] = useState(true)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingTemplate, setEditingTemplate] = useState<Template | null>(null)
  const [form] = Form.useForm()

  useEffect(() => {
    fetchTemplates()
  }, [])

  const fetchTemplates = async () => {
    try {
      const { data } = await templateApi.list()
      setTemplates([...data.system_templates, ...data.user_templates])
    } catch (err) {
      message.error('获取模板失败')
    } finally {
      setLoading(false)
    }
  }

  const handleAdd = () => {
    setEditingTemplate(null)
    form.resetFields()
    setModalVisible(true)
  }

  const handleEdit = (template: Template) => {
    setEditingTemplate(template)
    form.setFieldsValue(template)
    setModalVisible(true)
  }

  const handleDelete = async (id: number) => {
    try {
      await templateApi.delete(id)
      message.success('删除成功')
      fetchTemplates()
    } catch (err) {
      message.error('删除失败')
    }
  }

  const stats = useMemo(() => {
    const systemCount = templates.filter(t => t.is_system).length
    const customCount = templates.filter(t => !t.is_system).length
    const totalUsage = templates.reduce((sum, t) => sum + (t.usage_count || 0), 0)
    const topTemplates = [...templates]
      .sort((a, b) => (b.usage_count || 0) - (a.usage_count || 0))
      .slice(0, 5)
      .map(t => ({ name: t.name, 使用次数: t.usage_count || 0 }))

    const categoryData = [
      { name: '系统模板', value: systemCount },
      { name: '自定义模板', value: customCount }
    ]

    return { systemCount, customCount, totalUsage, topTemplates, categoryData }
  }, [templates])

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      if (editingTemplate) {
        await templateApi.update(editingTemplate.id, values)
        message.success('更新成功')
      } else {
        await templateApi.create({
          ...values,
          category: 'custom',
        })
        message.success('创建成功')
      }
      setModalVisible(false)
      fetchTemplates()
    } catch (err) {
      message.error('操作失败')
    }
  }

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      render: (cat: string) => (
        <Tag color={cat === 'system' ? 'blue' : 'green'}>
          {cat === 'system' ? '系统' : '自定义'}
        </Tag>
      ),
    },
    {
      title: '代码',
      dataIndex: 'code',
      key: 'code',
      render: (code: string) => (
        <span className="text-xs text-gray-500">
          {code?.slice(0, 50)}...
        </span>
      ),
    },
    {
      title: '使用次数',
      dataIndex: 'usage_count',
      key: 'usage_count',
      width: 100,
      render: (count: number) => (
        <span className="font-medium text-blue-600">{count || 0}</span>
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: Template) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          {record.category !== 'system' && (
            <Popconfirm
              title="确定删除此模板？"
              onConfirm={() => handleDelete(record.id)}
            >
              <Button type="link" danger icon={<DeleteOutlined />}>
                删除
              </Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-2xl font-bold">代码模板管理</h2>
          <p className="text-gray-500 mt-1">管理前台用户可选择的代码模板</p>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
          添加模板
        </Button>
      </div>

      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24} sm={12} lg={6}>
          <Card className="hover-lift" style={{ borderRadius: '12px' }}>
            <Statistic
              title="模板总数"
              value={templates.length}
              prefix={<FileTextOutlined className="text-blue-500" />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className="hover-lift" style={{ borderRadius: '12px' }}>
            <Statistic
              title="系统模板"
              value={stats.systemCount}
              prefix={<AppstoreOutlined className="text-green-500" />}
              valueStyle={{ color: '#10b981' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className="hover-lift" style={{ borderRadius: '12px' }}>
            <Statistic
              title="自定义模板"
              value={stats.customCount}
              prefix={<StarOutlined className="text-purple-500" />}
              valueStyle={{ color: '#8b5cf6' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className="hover-lift" style={{ borderRadius: '12px' }}>
            <Statistic
              title="总使用次数"
              value={stats.totalUsage}
              prefix={<EyeOutlined className="text-orange-500" />}
              valueStyle={{ color: '#f59e0b' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24} lg={12}>
          <Card className="hover-lift" style={{ borderRadius: '16px' }}>
            <div className="text-gray-600 font-medium mb-4">热门模板（使用次数）</div>
            {stats.topTemplates.length > 0 ? (
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={stats.topTemplates}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="使用次数" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-48 text-gray-400">暂无数据</div>
            )}
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card className="hover-lift" style={{ borderRadius: '16px' }}>
            <div className="text-gray-600 font-medium mb-4">模板类型分布</div>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={stats.categoryData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                  label={({ name, percent }) => `${name} ${((percent || 0) * 100).toFixed(0)}%`}
                >
                  {stats.categoryData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>

      <Card className="hover-lift" style={{ borderRadius: '16px' }}>
        <Table
          columns={columns}
          dataSource={templates}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      <Modal
        title={editingTemplate ? '编辑模板' : '添加模板'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        width={800}
        okText="保存"
      >
        <Form form={form} layout="vertical" className="mt-4">
          <Form.Item
            name="name"
            label="模板名称"
            rules={[{ required: true, message: '请输入模板名称' }]}
          >
            <Input placeholder="如：简洁风格、动态丰富" />
          </Form.Item>
          
          <Form.Item
            name="description"
            label="模板描述"
            rules={[{ required: true, message: '请输入模板描述' }]}
          >
            <Input.TextArea rows={2} placeholder="描述这个模板的特点" />
          </Form.Item>
          
          <Form.Item
            name="prompt"
            label="生成提示词 (可选)"
            extra="选择此模板时使用的自定义 AI 提示词，留空则使用默认提示词"
          >
            <TextArea
              rows={6}
              className="font-mono text-sm"
              placeholder="输入自定义的 AI 提示词，用于指导代码生成风格..."
            />
          </Form.Item>
          
          <Form.Item
            name="code"
            label="Manim 代码模板"
            rules={[{ required: true, message: '请输入代码' }]}
          >
            <TextArea
              rows={12}
              className="font-mono text-sm"
              placeholder={`from manim import *

class MyScene(Scene):
    def construct(self):
        # 在这里编写你的代码模板...
`}
            />
          </Form.Item>
          
          <div className="bg-yellow-50 p-3 rounded-lg text-sm text-yellow-700">
            <strong>💡 提示：</strong>用户选择此模板后，将完全按照此代码的风格（结构、动画、配色）生成新内容。
          </div>
        </Form>
      </Modal>
    </div>
  )
}
