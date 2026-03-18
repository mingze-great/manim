import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Button, Modal, Form, Input, message, Popconfirm, Empty } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, PlayCircleOutlined, RocketOutlined, SunOutlined, MoonOutlined } from '@ant-design/icons'
import { projectApi, Project } from '@/services/project'
import { useThemeStore } from '@/stores/themeStore'
import { motion, AnimatePresence } from 'framer-motion'

const statusMap: Record<string, { text: string; className: string }> = {
  draft: { text: '草稿', className: 'status-badge status-badge-draft' },
  chatting: { text: '对话中', className: 'status-badge status-badge-processing' },
  pending: { text: '等待中', className: 'status-badge status-badge-processing' },
  rendering: { text: '渲染中', className: 'status-badge status-badge-processing' },
  completed: { text: '已完成', className: 'status-badge status-badge-completed' },
  failed: { text: '失败', className: 'status-badge status-badge-failed' },
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [projects, setProjects] = useState<Project[]>([])
  const [modalVisible, setModalVisible] = useState(false)
  const [form] = Form.useForm()
  const { mode, toggleTheme } = useThemeStore()

  const fetchProjects = async () => {
    try {
      const { data } = await projectApi.list()
      setProjects(data)
    } catch (error) {
      message.error('获取项目列表失败')
    }
  }

  useEffect(() => {
    fetchProjects()
  }, [])

  const handleCreate = async (values: { title: string; theme: string }) => {
    try {
      const { data } = await projectApi.create(values)
      message.success('创建成功')
      setModalVisible(false)
      form.resetFields()
      navigate(`/project/${data.id}/chat`)
    } catch (error) {
      message.error('创建失败')
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await projectApi.delete(id)
      message.success('删除成功')
      fetchProjects()
    } catch (error) {
      message.error('删除失败')
    }
  }

  return (
    <div className="min-h-screen p-6">
      {/* 头部 */}
      <motion.div 
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex justify-between items-center mb-8"
      >
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#0066FF] to-[#00CCFF] flex items-center justify-center">
            <RocketOutlined className="text-2xl text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-800 dark:text-white">
              我的项目
            </h1>
            <p className="text-gray-500 dark:text-gray-400 text-sm">
              管理您的动画视频项目
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-4">
          {/* 主题切换按钮 */}
          <Button
            type="default"
            shape="circle"
            icon={mode === 'dark' ? <SunOutlined /> : <MoonOutlined />}
            onClick={toggleTheme}
            className="flex items-center justify-center"
          />
          
          <Button 
            type="primary" 
            icon={<PlusOutlined />} 
            onClick={() => setModalVisible(true)}
            className="btn-gradient h-10 px-6"
          >
            新建项目
          </Button>
        </div>
      </motion.div>

      {/* 项目列表 */}
      <AnimatePresence mode="wait">
        {projects.length === 0 ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex flex-col items-center justify-center py-20"
          >
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description={
                <span className="text-gray-500 dark:text-gray-400">
                  暂无项目，点击右上角创建第一个项目
                </span>
              }
            >
              <Button 
                type="primary" 
                icon={<PlusOutlined />}
                onClick={() => setModalVisible(true)}
                className="btn-gradient"
              >
                创建项目
              </Button>
            </Empty>
          </motion.div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            <AnimatePresence>
              {projects.map((project, index) => (
                <motion.div
                  key={project.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.9 }}
                  transition={{ delay: index * 0.1 }}
                >
                  <Card
                    hoverable
                    className="project-card hover-lift dark:bg-gray-800 dark:border-gray-700"
                    onClick={() => navigate(`/project/${project.id}/chat`)}
                  >
                    {/* 封面区域 */}
                    <div className="h-32 -mx-4 -mt-4 mb-4 rounded-t-lg bg-gradient-to-br from-[#0066FF]/10 to-[#00CCFF]/10 dark:from-[#00CCFF]/10 dark:to-[#0066FF]/10 flex items-center justify-center">
                      <RocketOutlined className="text-4xl text-[#0066FF]/30 dark:text-[#00CCFF]/30" />
                    </div>
                    
                    {/* 项目信息 */}
                    <h3 className="font-bold text-lg text-gray-800 dark:text-white mb-2 truncate">
                      {project.title}
                    </h3>
                    
                    <p className="text-gray-500 dark:text-gray-400 text-sm mb-3 line-clamp-2">
                      {project.theme}
                    </p>
                    
                    <div className="flex items-center justify-between">
                      <span className={statusMap[project.status]?.className}>
                        {statusMap[project.status]?.text || project.status}
                      </span>
                      <span className="text-gray-400 text-xs">
                        {new Date(project.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    
                    {/* 操作按钮 */}
                    <div 
                      className="flex gap-2 mt-4 pt-4 border-t border-gray-100 dark:border-gray-700"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <Button 
                        size="small" 
                        icon={<EditOutlined />}
                        onClick={() => navigate(`/project/${project.id}/chat`)}
                        className="flex-1"
                      >
                        编辑
                      </Button>
                      {project.status === 'completed' && (
                        <Button 
                          size="small" 
                          type="primary"
                          icon={<PlayCircleOutlined />}
                          onClick={() => navigate(`/project/${project.id}/task`)}
                          className="flex-1"
                        >
                          视频
                        </Button>
                      )}
                      <Popconfirm
                        title="确定删除此项目？"
                        onConfirm={() => handleDelete(project.id)}
                      >
                        <Button size="small" danger icon={<DeleteOutlined />} />
                      </Popconfirm>
                    </div>
                  </Card>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </AnimatePresence>

      {/* 新建项目弹窗 */}
      <Modal
        title={
          <div className="flex items-center gap-2">
            <RocketOutlined className="text-[#0066FF]" />
            <span>新建项目</span>
          </div>
        }
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        width={500}
      >
        <Form 
          form={form} 
          onFinish={handleCreate} 
          layout="vertical"
          className="mt-4"
        >
          <Form.Item
            name="title"
            rules={[{ required: true, message: '请输入项目标题' }]}
          >
            <Input 
              placeholder="例如：勾股定理讲解" 
              size="large"
              className="rounded-lg"
            />
          </Form.Item>
          <Form.Item
            name="theme"
            rules={[{ required: true, message: '请输入视频主题' }]}
          >
            <Input.TextArea
              placeholder="描述你想要制作的数学动画内容..."
              rows={4}
              className="rounded-lg"
            />
          </Form.Item>
          <Form.Item className="mb-0">
            <Button 
              type="primary" 
              htmlType="submit" 
              block
              className="btn-gradient h-12 text-base"
            >
              开始创建
            </Button>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
