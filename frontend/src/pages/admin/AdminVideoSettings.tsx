import { useEffect, useState } from 'react'
import { Card, Divider, Button, Input, Space, message, Upload, Switch, Tag } from 'antd'
import { EditOutlined, PlusOutlined, SaveOutlined, UploadOutlined, VideoCameraOutlined } from '@ant-design/icons'
import api, { resolveBackendUrl } from '@/services/api'
import type { StickmanV2BackgroundTemplate, StickmanV2OpeningStyle, StickmanV2SceneStyleLibrary } from '@/services/project'

type EditableSection = 'opening' | 'background' | 'scene'

export default function AdminVideoSettings() {
  const [openingStyles, setOpeningStyles] = useState<StickmanV2OpeningStyle[]>([])
  const [backgroundTemplates, setBackgroundTemplates] = useState<StickmanV2BackgroundTemplate[]>([])
  const [sceneStyleLibraries, setSceneStyleLibraries] = useState<StickmanV2SceneStyleLibrary[]>([])
  const [savingVideoConfig, setSavingVideoConfig] = useState(false)
  const [savingKeys, setSavingKeys] = useState<Record<string, boolean>>({})
  const [uploadingKeys, setUploadingKeys] = useState<Record<string, boolean>>({})
  const [editingKeys, setEditingKeys] = useState<Record<string, boolean>>({})

  const setUploading = (key: string, value: boolean) => {
    setUploadingKeys((prev) => ({ ...prev, [key]: value }))
  }

  const setSaving = (key: string, value: boolean) => {
    setSavingKeys((prev) => ({ ...prev, [key]: value }))
  }

  const setEditing = (key: string, value: boolean) => {
    setEditingKeys((prev) => ({ ...prev, [key]: value }))
  }

  const isUploading = (key: string) => !!uploadingKeys[key]
  const isSaving = (key: string) => !!savingKeys[key]
  const isEditing = (key: string) => !!editingKeys[key]

  const loadConfigs = async () => {
    try {
      const [openingRes, backgroundRes, sceneStyleRes] = await Promise.all([
        api.get('/admin/stickman-v2/opening-styles'),
        api.get('/admin/stickman-v2/background-templates'),
        api.get('/admin/stickman-v2/scene-style-libraries'),
      ])
      setOpeningStyles(openingRes.data.styles || [])
      setBackgroundTemplates(backgroundRes.data.templates || [])
      setSceneStyleLibraries(sceneStyleRes.data.libraries || [])
    } catch {
      message.error('加载视频管理配置失败')
    }
  }

  useEffect(() => {
    loadConfigs()
  }, [])

  const updateOpeningStyle = (index: number, patch: Partial<StickmanV2OpeningStyle>) => {
    setOpeningStyles((prev) => prev.map((item, i) => (i === index ? { ...item, ...patch } : item)))
  }

  const updateBackgroundTemplate = (index: number, patch: Partial<StickmanV2BackgroundTemplate>) => {
    setBackgroundTemplates((prev) => prev.map((item, i) => (i === index ? { ...item, ...patch } : item)))
  }

  const updateSceneStyleLibrary = (index: number, patch: Partial<StickmanV2SceneStyleLibrary>) => {
    setSceneStyleLibraries((prev) => prev.map((item, i) => (i === index ? { ...item, ...patch } : item)))
  }

  const handleSaveVideoConfig = async () => {
    setSavingVideoConfig(true)
    try {
      const openingPayload = openingStyles.map((item, index) => ({ ...item, sort_order: index + 1 }))
      const backgroundPayload = backgroundTemplates.map((item, index) => ({ ...item, sort_order: index + 1 }))
      const sceneStylePayload = sceneStyleLibraries.map((item, index) => ({ ...item, sort_order: index + 1 }))
      const [openingRes, backgroundRes, sceneStyleRes] = await Promise.all([
        api.post('/admin/stickman-v2/opening-styles', { styles: openingPayload }),
        api.post('/admin/stickman-v2/background-templates', { templates: backgroundPayload }),
        api.post('/admin/stickman-v2/scene-style-libraries', { libraries: sceneStylePayload }),
      ])
      setOpeningStyles(openingRes.data.styles || [])
      setBackgroundTemplates(backgroundRes.data.templates || [])
      setSceneStyleLibraries(sceneStyleRes.data.libraries || [])
      message.success('视频管理配置已保存')
    } catch {
      message.error('保存视频管理配置失败')
    } finally {
      setSavingVideoConfig(false)
    }
  }

  const saveSingleSectionItem = async (section: EditableSection, key: string) => {
    const stateKey = `${section}:${key}`
    setSaving(stateKey, true)
    try {
      if (section === 'opening') {
        const payload = openingStyles.map((item, index) => ({ ...item, sort_order: index + 1 }))
        const { data } = await api.post('/admin/stickman-v2/opening-styles', { styles: payload })
        setOpeningStyles(data.styles || [])
      } else if (section === 'background') {
        const payload = backgroundTemplates.map((item, index) => ({ ...item, sort_order: index + 1 }))
        const { data } = await api.post('/admin/stickman-v2/background-templates', { templates: payload })
        setBackgroundTemplates(data.templates || [])
      } else {
        const payload = sceneStyleLibraries.map((item, index) => ({ ...item, sort_order: index + 1 }))
        const { data } = await api.post('/admin/stickman-v2/scene-style-libraries', { libraries: payload })
        setSceneStyleLibraries(data.libraries || [])
      }
      setEditing(stateKey, false)
      message.success('当前配置已保存')
      return true
    } catch (error: any) {
      message.error(error.response?.data?.detail || '保存当前配置失败')
      return false
    } finally {
      setSaving(stateKey, false)
    }
  }

  const ensureSavedBeforeUpload = async (section: EditableSection, key: string) => {
    const saved = await saveSingleSectionItem(section, key)
    if (saved) {
      await loadConfigs()
    }
    return saved
  }

  const handleUploadOpeningSample = async (styleKey: string, file: File) => {
    const uploadKey = `opening:${styleKey}`
    setUploading(uploadKey, true)
    try {
      const ensured = await ensureSavedBeforeUpload('opening', styleKey)
      if (!ensured) return false
      const formData = new FormData()
      formData.append('file', file)
      const { data } = await api.post(`/admin/stickman-v2/opening-styles/${styleKey}/sample-image`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setOpeningStyles((prev) => prev.map((item) => item.key === styleKey ? { ...item, image_url: data.image_url } : item))
      message.success('开头风格样例图已上传')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '上传样例图失败')
    } finally {
      setUploading(uploadKey, false)
    }
    return false
  }

  const handleUploadBackgroundTemplate = async (templateKey: string, file: File) => {
    const uploadKey = `background:${templateKey}`
    setUploading(uploadKey, true)
    try {
      const ensured = await ensureSavedBeforeUpload('background', templateKey)
      if (!ensured) return false
      const formData = new FormData()
      formData.append('file', file)
      const { data } = await api.post(`/admin/stickman-v2/background-templates/${templateKey}/image`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setBackgroundTemplates((prev) => prev.map((item) => item.key === templateKey ? { ...item, image_url: data.image_url } : item))
      message.success('背景模板图已上传')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '上传背景模板失败')
    } finally {
      setUploading(uploadKey, false)
    }
    return false
  }

  const handleUploadSceneStyleLibrary = async (libraryKey: string, file: File) => {
    const uploadKey = `scene:${libraryKey}`
    setUploading(uploadKey, true)
    try {
      const ensured = await ensureSavedBeforeUpload('scene', libraryKey)
      if (!ensured) return false
      const formData = new FormData()
      formData.append('file', file)
      const { data } = await api.post(`/admin/stickman-v2/scene-style-libraries/${libraryKey}/package`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setSceneStyleLibraries((prev) => prev.map((item) => item.key === libraryKey ? {
        ...item,
        image_url: data.image_url,
        image_count: data.image_count,
        material_count: data.material_count,
      } : item))
      message.success('场景图风格包已上传')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '上传场景图风格包失败')
    } finally {
      setUploading(uploadKey, false)
    }
    return false
  }

  const renderDisplayCard = ({
    title,
    description,
    imageUrl,
    extra,
    section,
    itemKey,
  }: {
    title: string
    description?: string
    imageUrl?: string | null
    extra?: React.ReactNode
    section: EditableSection
    itemKey: string
  }) => (
    <Space direction="vertical" style={{ width: '100%' }} size="small">
      <div className="font-medium text-base">{title}</div>
      {description ? <div className="text-gray-500 text-sm whitespace-pre-wrap">{description}</div> : <div className="text-gray-400 text-sm">暂无说明</div>}
      {extra}
      {imageUrl ? <img src={resolveBackendUrl(imageUrl)} alt={title} style={{ width: 220, borderRadius: 10, border: '1px solid #eee' }} /> : <div className="text-gray-400 text-sm">暂无预览图</div>}
      <Space>
        <Button icon={<EditOutlined />} onClick={() => setEditing(`${section}:${itemKey}`, true)}>编辑</Button>
      </Space>
    </Space>
  )

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl font-bold">视频管理</h2>
        <p className="text-gray-500 mt-1">管理增强讲解的开头风格、背景模板和相关图片资源</p>
      </div>

      <Card className="hover-lift" style={{ borderRadius: '16px' }}>
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-lg bg-rose-100 flex items-center justify-center">
            <VideoCameraOutlined className="text-xl text-rose-500" />
          </div>
          <div>
            <div className="text-lg font-medium">增强讲解视频配置</div>
            <div className="text-gray-400 text-sm">更适合按卡片逐项管理，每个风格可单独保存、单独上传</div>
          </div>
        </div>
        <Divider className="my-3" />

        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="font-medium">开头图风格</div>
              <Button icon={<PlusOutlined />} onClick={() => {
                const key = `opening_style_${Date.now()}`
                setOpeningStyles((prev) => [...prev, { key, name: '', prompt: '', description: '', is_active: true }])
                setEditing(`opening:${key}`, true)
              }}>新增风格</Button>
            </div>
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              {openingStyles.map((item, index) => {
                const stateKey = `opening:${item.key}`
                return (
                  <Card key={item.key} size="small" title={item.name || `风格 ${index + 1}`} extra={<Switch checked={item.is_active !== false} onChange={(checked) => updateOpeningStyle(index, { is_active: checked })} checkedChildren="启用" unCheckedChildren="停用" />}>
                    {isEditing(stateKey) ? (
                      <Space direction="vertical" style={{ width: '100%' }} size="small">
                        <Input value={item.name} onChange={(e) => updateOpeningStyle(index, { name: e.target.value })} placeholder="风格名称，例如：柔和粉彩" />
                        <Input value={item.key} onChange={(e) => updateOpeningStyle(index, { key: e.target.value })} placeholder="风格标识 key" />
                        <Input.TextArea rows={2} value={item.description || ''} onChange={(e) => updateOpeningStyle(index, { description: e.target.value })} placeholder="风格简介，前台会展示给用户" />
                        <Input.TextArea rows={5} value={item.prompt || ''} onChange={(e) => updateOpeningStyle(index, { prompt: e.target.value })} placeholder="该风格对应的出图 prompt 要点" />
                        <Space>
                          <Button type="primary" icon={<SaveOutlined />} loading={isSaving(stateKey)} onClick={() => saveSingleSectionItem('opening', item.key)}>单独保存</Button>
                          <Upload beforeUpload={(file) => handleUploadOpeningSample(item.key, file)} showUploadList={false} accept=".png,.jpg,.jpeg,.webp">
                            <Button icon={<UploadOutlined />} loading={isUploading(stateKey)}>上传样例图</Button>
                          </Upload>
                        </Space>
                        {item.image_url && <img src={resolveBackendUrl(item.image_url)} alt={item.name || item.key} style={{ width: 180, borderRadius: 10, border: '1px solid #eee' }} />}
                      </Space>
                    ) : renderDisplayCard({ title: item.name || `风格 ${index + 1}`, description: item.description, imageUrl: item.image_url, section: 'opening', itemKey: item.key })}
                  </Card>
                )
              })}
            </Space>
          </div>

          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="font-medium">背景模板</div>
              <Button icon={<PlusOutlined />} onClick={() => {
                const key = `background_template_${Date.now()}`
                setBackgroundTemplates((prev) => [...prev, { key, name: '', description: '', is_active: true }])
                setEditing(`background:${key}`, true)
              }}>新增背景模板</Button>
            </div>
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              {backgroundTemplates.map((item, index) => {
                const stateKey = `background:${item.key}`
                return (
                  <Card key={item.key} size="small" title={item.name || `背景 ${index + 1}`} extra={<Switch checked={item.is_active !== false} onChange={(checked) => updateBackgroundTemplate(index, { is_active: checked })} checkedChildren="启用" unCheckedChildren="停用" />}>
                    {isEditing(stateKey) ? (
                      <Space direction="vertical" style={{ width: '100%' }} size="small">
                        <Input value={item.name} onChange={(e) => updateBackgroundTemplate(index, { name: e.target.value })} placeholder="背景模板名称" />
                        <Input value={item.key} onChange={(e) => updateBackgroundTemplate(index, { key: e.target.value })} placeholder="背景模板 key" />
                        <Input.TextArea rows={2} value={item.description || ''} onChange={(e) => updateBackgroundTemplate(index, { description: e.target.value })} placeholder="背景模板简介" />
                        <Space>
                          <Button type="primary" icon={<SaveOutlined />} loading={isSaving(stateKey)} onClick={() => saveSingleSectionItem('background', item.key)}>单独保存</Button>
                          <Upload beforeUpload={(file) => handleUploadBackgroundTemplate(item.key, file)} showUploadList={false} accept=".png,.jpg,.jpeg,.webp">
                            <Button icon={<UploadOutlined />} loading={isUploading(stateKey)}>上传背景图</Button>
                          </Upload>
                        </Space>
                        {item.image_url && <img src={resolveBackendUrl(item.image_url)} alt={item.name || item.key} style={{ width: 220, borderRadius: 10, border: '1px solid #eee' }} />}
                      </Space>
                    ) : renderDisplayCard({ title: item.name || `背景 ${index + 1}`, description: item.description, imageUrl: item.image_url, section: 'background', itemKey: item.key })}
                  </Card>
                )
              })}
            </Space>
          </div>

          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="font-medium">中间人物场景图风格</div>
              <Button icon={<PlusOutlined />} onClick={() => {
                const key = `scene_style_${Date.now()}`
                setSceneStyleLibraries((prev) => [...prev, { key, name: '', description: '', is_active: true, is_visible: true }])
                setEditing(`scene:${key}`, true)
              }}>新增风格</Button>
            </div>
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              {sceneStyleLibraries.map((item, index) => {
                const stateKey = `scene:${item.key}`
                return (
                  <Card key={item.key} size="small" title={item.name || `场景图风格 ${index + 1}`} extra={<Switch checked={item.is_active !== false} onChange={(checked) => updateSceneStyleLibrary(index, { is_active: checked })} checkedChildren="启用" unCheckedChildren="停用" />}>
                    {isEditing(stateKey) ? (
                      <Space direction="vertical" style={{ width: '100%' }} size="small">
                        <Input value={item.name} onChange={(e) => updateSceneStyleLibrary(index, { name: e.target.value })} placeholder="风格名称" />
                        <Input value={item.key} onChange={(e) => updateSceneStyleLibrary(index, { key: e.target.value })} placeholder="风格 key" />
                        <Input.TextArea rows={2} value={item.description || ''} onChange={(e) => updateSceneStyleLibrary(index, { description: e.target.value })} placeholder="前台展示给用户的风格说明" />
                        <Space>
                          <Button type="primary" icon={<SaveOutlined />} loading={isSaving(stateKey)} onClick={() => saveSingleSectionItem('scene', item.key)}>单独保存</Button>
                          <Upload beforeUpload={(file) => handleUploadSceneStyleLibrary(item.key, file)} showUploadList={false} accept=".zip">
                            <Button icon={<UploadOutlined />} loading={isUploading(stateKey)}>上传场景图风格包</Button>
                          </Upload>
                        </Space>
                        {(item.material_count || item.image_count) ? <div className="text-gray-500 text-sm">素材数 {item.material_count || 0}，图片数 {item.image_count || 0}</div> : null}
                        {item.image_url && <img src={resolveBackendUrl(item.image_url)} alt={item.name || item.key} style={{ width: 220, borderRadius: 10, border: '1px solid #eee' }} />}
                      </Space>
                    ) : renderDisplayCard({
                      title: item.name || `场景图风格 ${index + 1}`,
                      description: item.description,
                      imageUrl: item.image_url,
                      extra: <Space><Tag color="blue">图片 {item.image_count || 0}</Tag><Tag color="purple">条目 {item.material_count || 0}</Tag></Space>,
                      section: 'scene',
                      itemKey: item.key,
                    })}
                  </Card>
                )
              })}
            </Space>
          </div>

          <div className="bg-blue-50 p-3 rounded-lg text-sm text-blue-700">
            每个配置项都支持单独保存。新增后先保存，再上传图片或风格包；保存成功后会自动切换成卡片展示态。
          </div>

          <Button type="primary" onClick={handleSaveVideoConfig} loading={savingVideoConfig}>保存全部配置</Button>
        </Space>
      </Card>
    </div>
  )
}
