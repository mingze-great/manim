import { useState, useEffect } from 'react'
import { Button, Space, Tag, Modal, Form, Input, message, Popconfirm, Upload, Switch, Tooltip, Segmented, Card, Spin } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, PlayCircleOutlined, UploadOutlined, SettingOutlined } from '@ant-design/icons'
import { templateApi, Template } from '@/services/template'
import { inferTemplateCategory } from '@/utils/templateCategory'
import { getAppBase, resolveBackendUrl } from '@/services/api'
import { useIsMobile } from '@/hooks/useIsMobile'
import api from '@/services/api'

const { TextArea } = Input

const CATEGORY_OPTIONS = [
  { label: '全部', value: 'all' },
  { label: '思维可视化', value: 'thinking' },
  { label: '数学可视化', value: 'math' },
]

const CATEGORY_MAP: Record<string, string> = {
  thinking: '思维可视化',
  math: '数学可视化',
  custom: '自定义',
}

export default function AdminTemplates() {
  const isMobile = useIsMobile()
  const [templates, setTemplates] = useState<Template[]>([])
  const [loading, setLoading] = useState(true)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingTemplate, setEditingTemplate] = useState<Template | null>(null)
  const [form] = Form.useForm()
  const [videoPreviewVisible, setVideoPreviewVisible] = useState(false)
  const [previewVideoUrl, setPreviewVideoUrl] = useState<string>('')
  const [uploading, setUploading] = useState(false)
  const [topicConfigVisible, setTopicConfigVisible] = useState(false)
  const [topicConfig, setTopicConfig] = useState('')
  const [savingConfig, setSavingConfig] = useState(false)
  const [categoryFilter, setCategoryFilter] = useState<string>('all')

  useEffect(() => {
    fetchTemplates()
    loadTopicConfig()
  }, [categoryFilter])

  const loadTopicConfig = async () => {
    try {
      const { data } = await api.get('/admin/system-config/video_topic_prompt')
      setTopicConfig(data.value || '')
    } catch (err) {
    }
  }

  const fetchTemplates = async () => {
    try {
      const { data } = await templateApi.list({ limit: 100 })
      const allTemplates = [...data.system_templates, ...data.user_templates]
      const filteredTemplates = categoryFilter === 'all'
        ? allTemplates
        : allTemplates.filter((template) => inferTemplateCategory(template) === categoryFilter)
      setTemplates(filteredTemplates)
    } catch (err) {
      message.error('获取模板失败')
    } finally {
      setLoading(false)
    }
  }

  const handleAdd = () => {
    setEditingTemplate(null)
    form.resetFields()
    form.setFieldsValue({ category: categoryFilter !== 'all' ? categoryFilter : 'thinking' })
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
        await templateApi.create(values)
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
    const API_BASE = getAppBase()
    setPreviewVideoUrl(videoUrl.startsWith('http') ? videoUrl : `${API_BASE}${videoUrl}`)
    setVideoPreviewVisible(true)
  }

  const handleUploadVideo = async (templateId: number, file: File) => {
    setUploading(true)
    try {
      await templateApi.uploadExampleVideo(templateId, file)
      message.success('视频上传成功')
      fetchTemplates()
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '视频上传失败')
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

  const handleSaveTopicConfig = async () => {
    setSavingConfig(true)
    try {
      await api.post('/admin/system-config/video_topic_prompt', { value: topicConfig })
      message.success('配置保存成功')
      setTopicConfigVisible(false)
    } catch (err) {
      message.error('保存失败')
    } finally {
      setSavingConfig(false)
    }
  }

  const renderTemplateCard = (record: Template) => {
    const inferredCategory = inferTemplateCategory(record)
    const rawCategory = record.category ? String(record.category) : ''
    return (
      <Card key={record.id} size="small" style={{ borderRadius: '12px' }}>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <div className="font-semibold break-words">{record.name}</div>
              <Tag color={inferredCategory === 'math' ? 'blue' : 'purple'}>{CATEGORY_MAP[inferredCategory]}</Tag>
              <Tag color={record.is_system ? 'cyan' : 'green'}>{record.is_system ? '系统' : '自定义'}</Tag>
              {rawCategory && rawCategory !== inferredCategory && <Tag color="default">原始: {rawCategory}</Tag>}
            </div>
            {record.description && <div className="text-sm text-gray-500 mt-2 leading-6">{record.description}</div>}
          </div>
          <Switch
            checked={record.is_visible}
            onChange={() => handleToggleVisible(record)}
            checkedChildren="显示"
            unCheckedChildren="隐藏"
          />
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {record.example_video_url ? (
            <>
              <Button size="small" icon={<PlayCircleOutlined />} onClick={() => handlePreviewVideo(record.example_video_url!)}>预览示例</Button>
              <Popconfirm title="确定删除此示例视频？" onConfirm={() => handleDeleteVideo(record.id)}>
                <Button size="small" danger>删视频</Button>
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
              <Button size="small" icon={<UploadOutlined />} loading={uploading}>上传示例视频</Button>
            </Upload>
          )}
          <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)}>编辑</Button>
          {!record.is_system ? (
            <Popconfirm title="确定删除此模板？" description="删除后无法恢复" onConfirm={() => handleDelete(record.id)}>
              <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
            </Popconfirm>
          ) : (
            <Tooltip title="系统模板不可删除，如需隐藏请点击显示开关">
              <Button size="small" disabled icon={<DeleteOutlined />}>删除</Button>
            </Tooltip>
          )}
        </div>
      </Card>
    )
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6 gap-3 flex-wrap">
        <div>
          <h2 className="text-2xl font-bold">视频风格模板管理</h2>
          <p className="text-gray-500 mt-1">管理所有模板，上传示例视频供用户预览</p>
        </div>
        <Space>
          <Segmented
            value={categoryFilter}
            onChange={(v) => setCategoryFilter(v as string)}
            options={CATEGORY_OPTIONS}
          />
          <Button 
            icon={<SettingOutlined />} 
            onClick={() => setTopicConfigVisible(true)}
          >
            视频主题配置
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            添加模板
          </Button>
        </Space>
      </div>

      {loading ? (
        <div className="flex justify-center items-center py-16">
          <Spin size="large" />
        </div>
      ) : (
        <div className={isMobile ? 'space-y-3' : 'grid grid-cols-1 xl:grid-cols-2 gap-4'}>
          {templates.map((record) => renderTemplateCard(record))}
        </div>
      )}

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
            name="category"
            label="模板分类"
            rules={[{ required: true, message: '请选择模板分类' }]}
          >
            <Segmented
              options={[
                { label: '思维可视化', value: 'thinking' },
                { label: '数学可视化', value: 'math' },
              ]}
            />
          </Form.Item>
          
          <Form.Item
            name="description"
            label="模板描述"
            rules={[{ required: true, message: '请输入模板描述' }]}
          >
            <Input.TextArea rows={2} placeholder="描述这个模板的特点" />
          </Form.Item>
          
          <Form.Item
            noStyle
            shouldUpdate={(prevValues, currentValues) => prevValues.category !== currentValues.category}
          >
            {({ getFieldValue }) => {
              const category = getFieldValue('category')
              return (
                <Form.Item
                  name="code"
                  label="脚本模板"
                  rules={[{ required: category !== 'math', message: '请输入脚本模板' }]}
                  extra={category === 'math' 
                    ? "数学可视化可只填参考脚本，此字段可留空" 
                    : "此模板将作为AI生成视频脚本的参考风格，包括动画结构、配色、排版等"}
                >
                  <TextArea
                    rows={12}
                    className="font-mono text-sm"
                    placeholder={`from manim import *

class MyScene(Scene):
    def construct(self):
        # 在这里编写你的脚本模板...
`}
                  />
                </Form.Item>
              )
            }}
          </Form.Item>
          
          <Form.Item
            noStyle
            shouldUpdate={(prevValues, currentValues) => prevValues.category !== currentValues.category}
          >
            {({ getFieldValue }) => {
              const category = getFieldValue('category')
              return category === 'math' ? (
                <Form.Item
                  name="reference_code"
                  label="数学参考代码"
                  extra="数学可视化会优先参考这份完整代码的结构、镜头语言与动画风格生成新主题；为空时兼容回退使用上方脚本模板字段。"
                >
                  <TextArea
                    rows={12}
                    className="font-mono text-sm"
                    placeholder={`# 参考脚本示例：傅里叶级数可视化
# AI将参考此脚本的结构和风格，生成新的数学可视化内容
# 必须保持：结构、动画风格、排版方式
# 必须替换：核心公式、几何参数、文案内容

from manim import *
import numpy as np

class Fourier(Scene):
    def construct(self):
        # 分阶段动画：开场→过渡→核心→总结
        ...
`}
                  />
                </Form.Item>
              ) : null
            }}
          </Form.Item>
          
          {editingTemplate && (
            <Form.Item label="示例视频">
              {editingTemplate.example_video_url ? (
                <Space direction="vertical" className="w-full">
                  <video 
                    src={editingTemplate.example_video_url.startsWith('http') 
                      ? editingTemplate.example_video_url 
                      : resolveBackendUrl(editingTemplate.example_video_url)}
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
            <strong>提示：</strong>用户选择此模板后，将完全按照此脚本的风格（结构、动画、配色）生成新内容。分类决定该模板在哪个模块下可用。
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

      <Modal
        title="视频主题配置"
        open={topicConfigVisible}
        onOk={handleSaveTopicConfig}
        onCancel={() => setTopicConfigVisible(false)}
        width={700}
        confirmLoading={savingConfig}
        okText="保存"
      >
        <div className="mb-3 p-3 bg-blue-50 rounded text-sm text-blue-700">
          此提示词用于指导AI生成视频主题，用户在选择热门方向后，系统会根据此提示词生成相关的爆款主题示例。
        </div>
        <TextArea
          value={topicConfig}
          onChange={e => setTopicConfig(e.target.value)}
          rows={12}
          placeholder="输入视频主题生成的全局提示词..."
        />
      </Modal>
    </div>
  )
}
