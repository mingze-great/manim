import { useEffect, useState } from 'react'
import { Card, Descriptions, Tag, Row, Col, Divider, Button, Input, Space, message, Upload, Switch } from 'antd'
import { PlusOutlined, SafetyOutlined, LockOutlined, GlobalOutlined, CheckCircleOutlined, DatabaseOutlined, ApiOutlined, CodeOutlined, SecurityScanOutlined, UploadOutlined } from '@ant-design/icons'
import api from '@/services/api'
import { resolveBackendUrl } from '@/services/api'
import type { StickmanV2BackgroundTemplate, StickmanV2OpeningStyle } from '@/services/project'

export default function AdminSettings() {
  const [explainerPromptTemplate, setExplainerPromptTemplate] = useState('')
  const [savingPrompt, setSavingPrompt] = useState(false)
  const [openingStyles, setOpeningStyles] = useState<StickmanV2OpeningStyle[]>([])
  const [backgroundTemplates, setBackgroundTemplates] = useState<StickmanV2BackgroundTemplate[]>([])
  const [savingVideoConfig, setSavingVideoConfig] = useState(false)
  const [uploadingKeys, setUploadingKeys] = useState<Record<string, boolean>>({})

  const setUploading = (key: string, value: boolean) => {
    setUploadingKeys((prev) => ({ ...prev, [key]: value }))
  }

  const isUploading = (key: string) => !!uploadingKeys[key]

  useEffect(() => {
    const loadConfigs = async () => {
      try {
        const { data } = await api.get('/admin/system-config/explainer_scene_image_prompt_template')
        setExplainerPromptTemplate(data.value || '')
        const openingRes = await api.get('/admin/stickman-v2/opening-styles')
        const backgroundRes = await api.get('/admin/stickman-v2/background-templates')
        setOpeningStyles(openingRes.data.styles || [])
        setBackgroundTemplates(backgroundRes.data.templates || [])
      } catch {
      }
    }
    loadConfigs()
  }, [])

  const handleSavePromptTemplate = async () => {
    setSavingPrompt(true)
    try {
      await api.post('/admin/system-config/explainer_scene_image_prompt_template', { value: explainerPromptTemplate })
      message.success('讲解型视频出图 prompt 模板已保存')
    } catch {
      message.error('保存 prompt 模板失败')
    } finally {
      setSavingPrompt(false)
    }
  }

  const updateOpeningStyle = (index: number, patch: Partial<StickmanV2OpeningStyle>) => {
    setOpeningStyles((prev) => prev.map((item, i) => (i === index ? { ...item, ...patch } : item)))
  }

  const updateBackgroundTemplate = (index: number, patch: Partial<StickmanV2BackgroundTemplate>) => {
    setBackgroundTemplates((prev) => prev.map((item, i) => (i === index ? { ...item, ...patch } : item)))
  }

  const handleSaveVideoConfig = async () => {
    setSavingVideoConfig(true)
    try {
      const openingPayload = openingStyles.map((item, index) => ({ ...item, sort_order: index + 1 }))
      const backgroundPayload = backgroundTemplates.map((item, index) => ({ ...item, sort_order: index + 1 }))
      const [openingRes, backgroundRes] = await Promise.all([
        api.post('/admin/stickman-v2/opening-styles', { styles: openingPayload }),
        api.post('/admin/stickman-v2/background-templates', { templates: backgroundPayload }),
      ])
      setOpeningStyles(openingRes.data.styles || [])
      setBackgroundTemplates(backgroundRes.data.templates || [])
      message.success('视频管理配置已保存')
    } catch {
      message.error('保存视频管理配置失败')
    } finally {
      setSavingVideoConfig(false)
    }
  }

  const handleUploadOpeningSample = async (styleKey: string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    setUploading(`opening:${styleKey}`, true)
    try {
      const { data } = await api.post(`/admin/stickman-v2/opening-styles/${styleKey}/sample-image`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setOpeningStyles((prev) => prev.map((item) => item.key === styleKey ? { ...item, image_url: data.image_url } : item))
      message.success('开头风格样例图已上传')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '上传样例图失败')
    } finally {
      setUploading(`opening:${styleKey}`, false)
    }
    return false
  }

  const handleUploadBackgroundTemplate = async (templateKey: string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    setUploading(`background:${templateKey}`, true)
    try {
      const { data } = await api.post(`/admin/stickman-v2/background-templates/${templateKey}/image`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setBackgroundTemplates((prev) => prev.map((item) => item.key === templateKey ? { ...item, image_url: data.image_url } : item))
      message.success('背景模板图已上传')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '上传背景模板失败')
    } finally {
      setUploading(`background:${templateKey}`, false)
    }
    return false
  }

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl font-bold">系统设置</h2>
        <p className="text-gray-500 mt-1">查看系统配置信息</p>
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card 
            className="hover-lift h-full" 
            style={{ borderRadius: '16px' }}
          >
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
                <SafetyOutlined className="text-xl text-blue-500" />
              </div>
              <div>
                <div className="text-lg font-medium">安全设置</div>
                <div className="text-gray-400 text-sm">系统安全配置信息</div>
              </div>
            </div>
            <Divider className="my-3" />
            <Descriptions column={1} labelStyle={{ fontWeight: 500 }}>
              <Descriptions.Item label="JWT 令牌有效期">
                <Tag color="blue">24 小时</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="登录失败锁定">
                <Tag color="green" icon={<CheckCircleOutlined />}>已启用</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="登录限流">
                <Tag color="cyan">10 次/分钟</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="注册限流">
                <Tag color="cyan">5 次/小时</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="密码强度">
                <Tag color="orange">8位以上 + 字母 + 数字</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Token 黑名单">
                <Tag color="green" icon={<CheckCircleOutlined />}>已启用</Tag>
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card 
            className="hover-lift h-full" 
            style={{ borderRadius: '16px' }}
          >
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center">
                <GlobalOutlined className="text-xl text-green-500" />
              </div>
              <div>
                <div className="text-lg font-medium">系统信息</div>
                <div className="text-gray-400 text-sm">当前运行的系统版本</div>
              </div>
            </div>
            <Divider className="my-3" />
            <Descriptions column={1} labelStyle={{ fontWeight: 500 }}>
              <Descriptions.Item label={<><DatabaseOutlined className="mr-1" /> 数据库</>}>
                <Tag color="purple">SQLite</Tag>
              </Descriptions.Item>
              <Descriptions.Item label={<><CodeOutlined className="mr-1" /> 系统版本</>}>
                <Tag color="blue">v2.0.0</Tag>
              </Descriptions.Item>
              <Descriptions.Item label={<><ApiOutlined className="mr-1" /> API 版本</>}>
                <Tag color="blue">v2.0.0</Tag>
              </Descriptions.Item>
              <Descriptions.Item label={<><CodeOutlined className="mr-1" /> 前端版本</>}>
                <Tag color="blue">v2.0.0</Tag>
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card 
            className="hover-lift h-full" 
            style={{ borderRadius: '16px' }}
          >
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-lg bg-orange-100 flex items-center justify-center">
                <LockOutlined className="text-xl text-orange-500" />
              </div>
              <div>
                <div className="text-lg font-medium">操作日志</div>
                <div className="text-gray-400 text-sm">所有敏感操作都会被记录</div>
              </div>
            </div>
            <Divider className="my-3" />
            <Descriptions column={1} labelStyle={{ fontWeight: 500 }}>
              <Descriptions.Item label="登录日志">
                <Tag color="green" icon={<CheckCircleOutlined />}>已记录</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="用户操作日志">
                <Tag color="green" icon={<CheckCircleOutlined />}>已记录</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="项目操作日志">
                <Tag color="green" icon={<CheckCircleOutlined />}>已记录</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="任务操作日志">
                <Tag color="green" icon={<CheckCircleOutlined />}>已记录</Tag>
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card 
            className="hover-lift h-full" 
            style={{ borderRadius: '16px' }}
          >
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-lg bg-purple-100 flex items-center justify-center">
                <SecurityScanOutlined className="text-xl text-purple-500" />
              </div>
              <div>
                <div className="text-lg font-medium">数据保护</div>
                <div className="text-gray-400 text-sm">数据安全与备份策略</div>
              </div>
            </div>
            <Divider className="my-3" />
            <Descriptions column={1} labelStyle={{ fontWeight: 500 }}>
              <Descriptions.Item label="数据加密">
                <Tag color="green" icon={<CheckCircleOutlined />}>已启用</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="敏感信息保护">
                <Tag color="green" icon={<CheckCircleOutlined />}>已启用</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="访问控制">
                <Tag color="green" icon={<CheckCircleOutlined />}>已启用</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="审计追踪">
                <Tag color="green" icon={<CheckCircleOutlined />}>已启用</Tag>
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>

        <Col xs={24}>
          <Card className="hover-lift" style={{ borderRadius: '16px' }}>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-lg bg-indigo-100 flex items-center justify-center">
                <CodeOutlined className="text-xl text-indigo-500" />
              </div>
              <div>
                <div className="text-lg font-medium">讲解型视频图片 Prompt</div>
                <div className="text-gray-400 text-sm">控制讲解型视频模块分镜图的模型出图提示词模板</div>
              </div>
            </div>
            <Divider className="my-3" />
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              <div className="text-sm text-gray-500 leading-6">
                可用变量：<code>{'{frame_instruction}'}</code>、<code>{'{style_key}'}</code>、<code>{'{beat}'}</code>、<code>{'{emotion}'}</code>、<code>{'{topic}'}</code>、<code>{'{focus}'}</code>、<code>{'{visual}'}</code>、<code>{'{total}'}</code>
              </div>
              <Input.TextArea
                rows={12}
                value={explainerPromptTemplate}
                onChange={(e) => setExplainerPromptTemplate(e.target.value)}
                placeholder="留空时使用系统默认 prompt。你也可以在这里写完整模板，例如：Create a Chinese explainer scene illustration... Style key: {style_key}. Visual description: {visual}."
              />
              <Button type="primary" onClick={handleSavePromptTemplate} loading={savingPrompt}>保存讲解型视频 Prompt 模板</Button>
            </Space>
          </Card>
        </Col>

        <Col xs={24}>
          <Card className="hover-lift" style={{ borderRadius: '16px' }}>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-lg bg-rose-100 flex items-center justify-center">
                <CodeOutlined className="text-xl text-rose-500" />
              </div>
              <div>
                <div className="text-lg font-medium">视频管理</div>
                <div className="text-gray-400 text-sm">管理增强讲解的开头风格和背景模板</div>
              </div>
            </div>
            <Divider className="my-3" />
            <Space direction="vertical" style={{ width: '100%' }} size="large">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className="font-medium">开头图风格</div>
                  <Button icon={<PlusOutlined />} onClick={() => setOpeningStyles((prev) => [...prev, { key: `opening_style_${Date.now()}`, name: '', prompt: '', description: '', is_active: true }])}>新增风格</Button>
                </div>
                <Space direction="vertical" style={{ width: '100%' }} size="middle">
                  {openingStyles.map((item, index) => (
                    <Card key={item.key} size="small" title={item.name || `风格 ${index + 1}`} extra={<Switch checked={item.is_active !== false} onChange={(checked) => updateOpeningStyle(index, { is_active: checked })} checkedChildren="启用" unCheckedChildren="停用" />}>
                      <Space direction="vertical" style={{ width: '100%' }} size="small">
                        <Input value={item.name} onChange={(e) => updateOpeningStyle(index, { name: e.target.value })} placeholder="风格名称，例如：柔和粉彩" />
                        <Input value={item.key} onChange={(e) => updateOpeningStyle(index, { key: e.target.value })} placeholder="风格标识 key" />
                        <Input.TextArea rows={2} value={item.description || ''} onChange={(e) => updateOpeningStyle(index, { description: e.target.value })} placeholder="风格简介，前台会展示给用户" />
                        <Input.TextArea rows={5} value={item.prompt || ''} onChange={(e) => updateOpeningStyle(index, { prompt: e.target.value })} placeholder="该风格对应的出图 prompt 要点" />
                        <Upload beforeUpload={(file) => handleUploadOpeningSample(item.key, file)} showUploadList={false} accept=".png,.jpg,.jpeg,.webp">
                          <Button icon={<UploadOutlined />} loading={isUploading(`opening:${item.key}`)}>上传样例图</Button>
                        </Upload>
                        {item.image_url && <img src={resolveBackendUrl(item.image_url)} alt={item.name || item.key} style={{ width: 180, borderRadius: 10, border: '1px solid #eee' }} />}
                      </Space>
                    </Card>
                  ))}
                </Space>
              </div>

              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className="font-medium">背景模板</div>
                  <Button icon={<PlusOutlined />} onClick={() => setBackgroundTemplates((prev) => [...prev, { key: `background_template_${Date.now()}`, name: '', description: '', is_active: true }])}>新增背景模板</Button>
                </div>
                <Space direction="vertical" style={{ width: '100%' }} size="middle">
                  {backgroundTemplates.map((item, index) => (
                    <Card key={item.key} size="small" title={item.name || `背景 ${index + 1}`} extra={<Switch checked={item.is_active !== false} onChange={(checked) => updateBackgroundTemplate(index, { is_active: checked })} checkedChildren="启用" unCheckedChildren="停用" />}>
                      <Space direction="vertical" style={{ width: '100%' }} size="small">
                        <Input value={item.name} onChange={(e) => updateBackgroundTemplate(index, { name: e.target.value })} placeholder="背景模板名称" />
                        <Input value={item.key} onChange={(e) => updateBackgroundTemplate(index, { key: e.target.value })} placeholder="背景模板 key" />
                        <Input.TextArea rows={2} value={item.description || ''} onChange={(e) => updateBackgroundTemplate(index, { description: e.target.value })} placeholder="背景模板简介" />
                        <Upload beforeUpload={(file) => handleUploadBackgroundTemplate(item.key, file)} showUploadList={false} accept=".png,.jpg,.jpeg,.webp">
                          <Button icon={<UploadOutlined />} loading={isUploading(`background:${item.key}`)}>上传背景图</Button>
                        </Upload>
                        {item.image_url && <img src={resolveBackendUrl(item.image_url)} alt={item.name || item.key} style={{ width: 220, borderRadius: 10, border: '1px solid #eee' }} />}
                      </Space>
                    </Card>
                  ))}
                </Space>
              </div>

              <Button type="primary" onClick={handleSaveVideoConfig} loading={savingVideoConfig}>保存视频管理配置</Button>
            </Space>
          </Card>
        </Col>
      </Row>
    </div>
  )
}
