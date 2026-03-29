import { useState, useEffect } from 'react'
import { Table, Button, Space, Tag, Modal, Form, Input, message, Popconfirm, Switch } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, EyeOutlined, EyeInvisibleOutlined } from '@ant-design/icons'
import { templateApi, Template } from '@/services/template'

const { TextArea } = Input

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
    form.setFieldsValue({
      ...template,
      is_visible: template.is_visible ?? true
    })
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

  const handleToggleVisible = async (template: Template) => {
    try {
      await templateApi.update(template.id, { is_visible: !template.is_visible })
      message.success(template.is_visible ? '已对用户隐藏' : '已对用户显示')
      fetchTemplates()
    } catch (err) {
      message.error('操作失败')
    }
  }

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
      title: '用户可见',
      dataIndex: 'is_visible',
      key: 'is_visible',
      render: (isVisible: boolean, record: Template) => (
        <Space>
          <Tag color={isVisible ? 'green' : 'default'} icon={isVisible ? <EyeOutlined /> : <EyeInvisibleOutlined />}>
            {isVisible ? '可见' : '隐藏'}
          </Tag>
          <Switch
            size="small"
            checked={isVisible}
            onChange={() => handleToggleVisible(record)}
          />
        </Space>
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

      <Table
        columns={columns}
        dataSource={templates}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 10 }}
      />

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
            name="is_visible"
            label="用户可见"
            valuePropName="checked"
            extra="开启后，普通用户可以在模板列表中看到此模板"
          >
            <Switch checkedChildren="可见" unCheckedChildren="隐藏" />
          </Form.Item>
          
          <Form.Item
            name="prompt"
            label="生成提示词"
            rules={[{ required: true, message: '请输入生成提示词' }]}
            extra="包含 AI 指令和代码模板，用户选择此模板后将按照此内容生成视频代码"
          >
            <TextArea
              rows={20}
              className="font-mono text-sm"
              placeholder={`角色与任务：
你是一个精通自媒体爆款文案的创作者...

步骤 1：生成文案与匹配图形
...

步骤 2：填入代码模板
...

from manim import *

class MyScene(Scene):
    def construct(self):
        # 代码模板...
`}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
