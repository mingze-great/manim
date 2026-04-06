import { useState, useEffect } from 'react'
import { Table, Button, Space, Tag, Modal, Form, Input, message, Popconfirm, Upload, Switch, Tooltip } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, PlayCircleOutlined, UploadOutlined } from '@ant-design/icons'
import { templateApi, Template } from '@/services/template'

const { TextArea } = Input

export default function AdminTemplates() {
  const [templates, setTemplates] = useState<Template[]>([])
  const [loading, setLoading] = useState(true)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingTemplate, setEditingTemplate] = useState<Template | null>(null)
  const [form] = Form.useForm()
  const [videoPreviewVisible, setVideoPreviewVisible] = useState(false)
  const [previewVideoUrl, setPreviewVideoUrl] = useState<string>('')
  const [uploading, setUploading] = useState(false)

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

  const handleToggleVisible = async (template: Template) => {
    try {
      await templateApi.update(template.id, { is_visible: !template.is_visible })
      message.success(template.is_visible ? '已隐藏' : '已显示')
      fetchTemplates()
    } catch (err) {
      message.error('操作失败')
    }
  }

  const handlePreviewVideo = (videoUrl: string) => {
    const API_BASE = import.meta.env.VITE_API_BASE_URL || ''
    setPreviewVideoUrl(videoUrl.startsWith('http') ? videoUrl : `${API_BASE}${videoUrl}`)
    setVideoPreviewVisible(true)
  }

  const handleUploadVideo = async (templateId: number, file: File) => {
    setUploading(true)
    try {
      await templateApi.uploadExampleVideo(templateId, file)
      message.success('视频上传成功')
      fetchTemplates()
    } catch (err) {
      message.error('视频上传失败')
    } finally {
      setUploading(false)
    }
  }

  const handleDeleteVideo = async (templateId: number) => {
    try {
      await templateApi.deleteExampleVideo(templateId)
      message.success('视频删除成功')
      fetchTemplates()
    } catch (err) {
      message.error('视频删除失败')
    }
  }

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 50,
    },
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      width: 200,
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '类型',
      dataIndex: 'is_system',
      key: 'is_system',
      width: 80,
      render: (isSystem: boolean) => (
        <Tag color={isSystem ? 'blue' : 'green'}>
          {isSystem ? '系统' : '自定义'}
        </Tag>
      ),
    },
    {
      title: '用户可见',
      dataIndex: 'is_visible',
      key: 'is_visible',
      width: 100,
      render: (isVisible: boolean, record: Template) => (
        <Switch
          checked={isVisible}
          onChange={() => handleToggleVisible(record)}
          checkedChildren="显示"
          unCheckedChildren="隐藏"
        />
      ),
    },
    {
      title: '示例视频',
      dataIndex: 'example_video_url',
      key: 'example_video_url',
      width: 180,
      render: (videoUrl: string | null, record: Template) => (
        <Space>
          {videoUrl ? (
            <>
              <Button
                type="link"
                size="small"
                icon={<PlayCircleOutlined />}
                onClick={() => handlePreviewVideo(videoUrl)}
              >
                预览
              </Button>
              <Popconfirm
                title="确定删除此示例视频？"
                onConfirm={() => handleDeleteVideo(record.id)}
              >
                <Button type="link" size="small" danger>
                  删除
                </Button>
              </Popconfirm>
            </>
          ) : (
            <Upload
              accept=".mp4"
              showUploadList={false}
              beforeUpload={(file) => {
                handleUploadVideo(record.id, file)
                return false
              }}
            >
              <Button type="link" size="small" icon={<UploadOutlined />} loading={uploading}>
                上传
              </Button>
            </Upload>
          )}
        </Space>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_: any, record: Template) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          {!record.is_system ? (
            <Popconfirm
              title="确定删除此模板？"
              description="删除后无法恢复"
              onConfirm={() => handleDelete(record.id)}
            >
              <Button type="link" danger icon={<DeleteOutlined />}>
                删除
              </Button>
            </Popconfirm>
          ) : (
            <Tooltip title="系统模板不可删除，如需隐藏请点击「隐藏」按钮">
              <Button type="link" disabled icon={<DeleteOutlined />}>
                删除
              </Button>
            </Tooltip>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-2xl font-bold">视频风格模板管理</h2>
          <p className="text-gray-500 mt-1">管理所有模板，上传示例视频供用户预览</p>
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
        scroll={{ x: 1000 }}
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
            label="代码模板"
            rules={[{ required: true, message: '请输入代码模板' }]}
            extra="此模板将作为AI生成视频脚本的参考风格，包括动画结构、配色、排版等"
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
          
          {editingTemplate && (
            <Form.Item label="示例视频">
              {editingTemplate.example_video_url ? (
                <Space direction="vertical" className="w-full">
                  <video 
                    src={editingTemplate.example_video_url.startsWith('http') 
                      ? editingTemplate.example_video_url 
                      : `${import.meta.env.VITE_API_BASE_URL || ''}${editingTemplate.example_video_url}`}
                    controls
                    className="w-full max-h-48 rounded-lg"
                  />
                  <Button 
                    danger 
                    onClick={() => {
                      handleDeleteVideo(editingTemplate.id)
                      setModalVisible(false)
                    }}
                  >
                    删除视频
                  </Button>
                </Space>
              ) : (
                <Upload
                  accept=".mp4"
                  showUploadList={false}
                  beforeUpload={(file) => {
                    handleUploadVideo(editingTemplate.id, file)
                    return false
                  }}
                >
                  <Button icon={<UploadOutlined />} loading={uploading}>
                    上传示例视频 (MP4)
                  </Button>
                </Upload>
              )}
            </Form.Item>
          )}
          
          <div className="bg-yellow-50 p-3 rounded-lg text-sm text-yellow-700">
            <strong>提示：</strong>用户选择此模板后，将完全按照此代码的风格（结构、动画、配色）生成新内容。
          </div>
        </Form>
      </Modal>

      <Modal
        title="视频预览"
        open={videoPreviewVisible}
        onCancel={() => setVideoPreviewVisible(false)}
        footer={null}
        width={800}
        centered
      >
        <video
          src={previewVideoUrl}
          controls
          className="w-full rounded-lg"
          autoPlay
        />
      </Modal>
    </div>
  )
}