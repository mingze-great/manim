import { useState, useEffect } from 'react'
import { Table, Button, Space, Tag, Modal, Form, Input, message, Popconfirm } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
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
            name="code"
            label="AI视频 代码"
            rules={[{ required: true, message: '请输入代码' }]}
          >
            <TextArea
              rows={16}
              className="font-mono text-sm"
              placeholder={`from AI视频 import *

class MyScene(Scene):
    def construct(self):
        # 在这里编写你的代码模板...
`}
            />
          </Form.Item>
          
          <div className="bg-yellow-50 p-3 rounded-lg text-sm text-yellow-700">
            <strong>💡 提示：</strong>用户选择此模板后，AI将完全按照此代码的风格（结构、动画、配色）生成新内容。
          </div>
        </Form>
      </Modal>
    </div>
  )
}
