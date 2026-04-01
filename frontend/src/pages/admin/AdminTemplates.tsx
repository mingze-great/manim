import { useState, useEffect, useRef } from 'react'
import { Table, Button, Space, Tag, Modal, Form, Input, message, Popconfirm, Upload, Switch, Tooltip, Progress } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, PlayCircleOutlined, UploadOutlined, VideoCameraOutlined, SyncOutlined } from '@ant-design/icons'
import { templateApi, Template } from '@/services/template'

const { TextArea } = Input

interface RenderTask {
  taskId: number
  templateId: number
  templateName: string
  status: string
  progress: number
  message: string
}

export default function AdminTemplates() {
  const [templates, setTemplates] = useState<Template[]>([])
  const [loading, setLoading] = useState(true)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingTemplate, setEditingTemplate] = useState<Template | null>(null)
  const [form] = Form.useForm()
  const [videoPreviewVisible, setVideoPreviewVisible] = useState(false)
  const [previewVideoUrl, setPreviewVideoUrl] = useState<string>('')
  const [uploading, setUploading] = useState(false)
  const [renderTasks, setRenderTasks] = useState<Map<number, RenderTask>>(new Map())
  const [batchRendering, setBatchRendering] = useState(false)
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    fetchTemplates()
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
      }
    }
  }, [])

  useEffect(() => {
    if (renderTasks.size > 0) {
      if (!pollingRef.current) {
        pollingRef.current = setInterval(pollRenderTasks, 2000)
      }
    } else {
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
        pollingRef.current = null
      }
    }
  }, [renderTasks.size])

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

  const pollRenderTasks = async () => {
    const updatedTasks = new Map<number, RenderTask>()
    let hasActiveTask = false
    
    for (const [templateId, task] of renderTasks) {
      if (task.status === 'processing' || task.status === 'pending') {
        hasActiveTask = true
        try {
          const { data } = await templateApi.getRenderStatus(task.taskId)
          updatedTasks.set(templateId, {
            ...task,
            status: data.status,
            progress: data.progress,
            message: data.message
          })
          
          if (data.status === 'completed') {
            message.success(`模板 "${task.templateName}" 预览视频渲染完成`)
            fetchTemplates()
          } else if (data.status === 'failed') {
            message.error(`模板 "${task.templateName}" 渲染失败: ${data.error || data.message}`)
          }
        } catch (err) {
          console.error('Failed to poll task status:', err)
        }
      } else {
        updatedTasks.set(templateId, task)
      }
    }
    
    setRenderTasks(updatedTasks)
    
    if (!hasActiveTask && pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
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

  const handleRenderPreview = async (template: Template) => {
    try {
      const { data } = await templateApi.renderPreview(template.id)
      setRenderTasks(prev => {
        const newMap = new Map(prev)
        newMap.set(template.id, {
          taskId: data.task_id,
          templateId: template.id,
          templateName: template.name,
          status: 'pending',
          progress: 0,
          message: '渲染任务已启动'
        })
        return newMap
      })
      message.info(`模板 "${template.name}" 预览渲染已启动`)
    } catch (err: any) {
      message.error(err.response?.data?.detail || '启动渲染失败')
    }
  }

  const handleBatchRender = async () => {
    setBatchRendering(true)
    try {
      const { data } = await templateApi.renderAllPreviews()
      if (data.tasks.length === 0) {
        message.info('没有需要渲染的系统模板')
        return
      }
      
      const newTasks = new Map(renderTasks)
      data.tasks.forEach((task: any) => {
        newTasks.set(task.template_id, {
          taskId: task.task_id,
          templateId: task.template_id,
          templateName: task.template_name,
          status: 'pending',
          progress: 0,
          message: '渲染任务已启动'
        })
      })
      setRenderTasks(newTasks)
      message.success(`已启动 ${data.tasks.length} 个渲染任务`)
    } catch (err: any) {
      message.error(err.response?.data?.detail || '批量渲染失败')
    } finally {
      setBatchRendering(false)
    }
  }

  const getRenderStatus = (templateId: number): RenderTask | undefined => {
    return renderTasks.get(templateId)
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
      width: 250,
      render: (videoUrl: string | null, record: Template) => {
        const task = getRenderStatus(record.id)
        
        if (task && (task.status === 'processing' || task.status === 'pending')) {
          return (
            <Space direction="vertical" size="small" className="w-full">
              <Progress percent={task.progress} size="small" status="active" />
              <span className="text-xs text-gray-500">{task.message}</span>
            </Space>
          )
        }
        
        return (
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
                {record.is_system && (
                  <Tooltip title="重新渲染预览视频">
                    <Button
                      type="link"
                      size="small"
                      icon={<SyncOutlined />}
                      onClick={() => handleRenderPreview(record)}
                    />
                  </Tooltip>
                )}
              </>
            ) : (
              <>
                {record.is_system ? (
                  <Tooltip title="渲染模板代码生成预览视频">
                    <Button
                      type="link"
                      size="small"
                      icon={<VideoCameraOutlined />}
                      onClick={() => handleRenderPreview(record)}
                    >
                      渲染预览
                    </Button>
                  </Tooltip>
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
              </>
            )}
          </Space>
        )
      },
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
          {!record.is_system && (
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
          <p className="text-gray-500 mt-1">管理所有模板，渲染或上传示例视频供用户预览</p>
        </div>
        <Space>
          <Button
            icon={<SyncOutlined />}
            onClick={handleBatchRender}
            loading={batchRendering}
          >
            批量渲染预览
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            添加模板
          </Button>
        </Space>
      </div>

      {renderTasks.size > 0 && (
        <div className="mb-4 p-4 bg-blue-50 rounded-lg">
          <div className="flex items-center gap-2 mb-2">
            <SyncOutlined spin className="text-blue-500" />
            <span className="font-medium">渲染任务进度</span>
          </div>
          <div className="space-y-2">
            {Array.from(renderTasks.values()).map(task => (
              <div key={task.taskId} className="flex items-center gap-4">
                <span className="text-sm text-gray-600 w-32 truncate">{task.templateName}</span>
                <Progress 
                  percent={task.progress} 
                  size="small" 
                  className="flex-1"
                  status={task.status === 'failed' ? 'exception' : task.status === 'completed' ? 'success' : 'active'}
                />
                <span className="text-xs text-gray-500 w-20">
                  {task.status === 'completed' ? '完成' : task.status === 'failed' ? '失败' : task.message}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <Table
        columns={columns}
        dataSource={templates}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 10 }}
        scroll={{ x: 1200 }}
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