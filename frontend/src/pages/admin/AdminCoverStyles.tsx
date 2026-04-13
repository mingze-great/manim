import { useEffect, useState } from 'react'
import {
  Card, Table, Button, Space, Modal, Form, Input, Select, Switch, message, Image, Typography
} from 'antd'
import {
  PlusOutlined, EditOutlined, DeleteOutlined, PictureOutlined
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import api from '@/services/api'

const { TextArea } = Input
const { Text } = Typography

interface CoverStyle {
  id: number
  name: string
  description: string | null
  base_prompt: string
  example_image_url: string | null
  font_recommendation: string | null
  color_recommendation: string | null
  is_active: boolean
}

export default function AdminCoverStyles() {
  const [styles, setStyles] = useState<CoverStyle[]>([])
  const [loading, setLoading] = useState(true)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingStyle, setEditingStyle] = useState<CoverStyle | null>(null)
  const [form] = Form.useForm()

  useEffect(() => {
    loadStyles()
  }, [])

  const loadStyles = async () => {
    setLoading(true)
    try {
      const { data } = await api.get('/admin/cover-styles')
      setStyles(data)
    } catch (err: any) {
      message.error(err.response?.data?.detail || '加载失败')
    } finally {
      setLoading(false)
    }
  }

  const handleAdd = () => {
    setEditingStyle(null)
    form.resetFields()
    form.setFieldsValue({
      name: '',
      description: '',
      base_prompt: '公众号封面，主题：{topic}，简约商务风格，专业感，高质量，无文字，9:16比例',
      font_recommendation: '黑体',
      color_recommendation: '#333333',
      is_active: true,
    })
    setModalVisible(true)
  }

  const handleEdit = (record: CoverStyle) => {
    setEditingStyle(record)
    form.setFieldsValue(record)
    setModalVisible(true)
  }

  const handleDelete = async (id: number) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个封面风格吗？',
      onOk: async () => {
        try {
          await api.delete(`/admin/cover-styles/${id}`)
          message.success('删除成功')
          loadStyles()
        } catch (err: any) {
          message.error(err.response?.data?.detail || '删除失败')
        }
      },
    })
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      if (editingStyle) {
        await api.put(`/admin/cover-styles/${editingStyle.id}`, values)
        message.success('更新成功')
      } else {
        await api.post('/admin/cover-styles', values)
        message.success('创建成功')
      }
      setModalVisible(false)
      loadStyles()
    } catch (err: any) {
      message.error(err.response?.data?.detail || '操作失败')
    }
  }

  const columns: ColumnsType<CoverStyle> = [
    {
      title: 'ID',
      dataIndex: 'id',
      width: 60,
    },
    {
      title: '风格名称',
      dataIndex: 'name',
      width: 150,
    },
    {
      title: '描述',
      dataIndex: 'description',
      ellipsis: true,
    },
    {
      title: '母 Prompt',
      dataIndex: 'base_prompt',
      ellipsis: true,
      width: 300,
    },
    {
      title: '示例图片',
      dataIndex: 'example_image_url',
      width: 120,
      render: (url: string | null) => 
        url ? <Image src={url} width={80} height={80} style={{ borderRadius: 8 }} /> : <Text type="secondary">无</Text>,
    },
    {
      title: '推荐字体',
      dataIndex: 'font_recommendation',
      width: 100,
    },
    {
      title: '推荐颜色',
      dataIndex: 'color_recommendation',
      width: 100,
    },
    {
      title: '启用',
      dataIndex: 'is_active',
      width: 80,
      render: (active: boolean, record) => (
        <Switch checked={active} onChange={(checked) => {
          api.put(`/admin/cover-styles/${record.id}`, { is_active: checked })
            .then(() => loadStyles())
            .catch(() => message.error('操作失败'))
        }} />
      ),
    },
    {
      title: '操作',
      width: 150,
      render: (_, record) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)}>编辑</Button>
          <Button size="small" danger icon={<DeleteOutlined />} onClick={() => handleDelete(record.id)}>删除</Button>
        </Space>
      ),
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Card 
        title={<><PictureOutlined /> 封面风格管理</>}
        extra={<Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>新增风格</Button>}
      >
        <Table 
          columns={columns}
          dataSource={styles}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      <Modal
        title={editingStyle ? '编辑封面风格' : '新增封面风格'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={handleSubmit}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="风格名称" rules={[{ required: true, message: '请输入风格名称' }]}>
            <Input placeholder="如：简约商务" />
          </Form.Item>
          <Form.Item name="description" label="风格描述">
            <TextArea rows={2} placeholder="风格特点说明" />
          </Form.Item>
          <Form.Item name="base_prompt" label="封面母 Prompt" rules={[{ required: true, message: '请输入 Prompt' }]}>
            <TextArea 
              rows={4} 
              placeholder="公众号封面，主题：{topic}，简约商务风格，专业感，高质量，无文字，9:16比例"
            />
            <Text type="secondary">使用 {'{topic}'} 作为主题占位符</Text>
          </Form.Item>
          <Form.Item name="font_recommendation" label="推荐字体">
            <Select>
              <Select.Option value="黑体">黑体</Select.Option>
              <Select.Option value="宋体">宋体</Select.Option>
              <Select.Option value="微软雅黑">微软雅黑</Select.Option>
              <Select.Option value="楷体">楷体</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="color_recommendation" label="推荐颜色">
            <Select>
              <Select.Option value="#333333">黑色</Select.Option>
              <Select.Option value="#FFFFFF">白色</Select.Option>
              <Select.Option value="#1E90FF">蓝色</Select.Option>
              <Select.Option value="#FF6B6B">红色</Select.Option>
              <Select.Option value="#2C3E50">深灰</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="example_image_url" label="示例图片URL">
            <Input placeholder="可选，示例图片URL" />
          </Form.Item>
          <Form.Item name="is_active" label="启用" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}