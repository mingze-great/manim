import { useEffect, useState } from 'react'
import { Alert, Button, Card, Col, Input, InputNumber, Progress, Row, Space, Switch, Tag, Typography, Upload, message } from 'antd'
import { CheckOutlined, FolderOpenOutlined, PictureOutlined, PlusOutlined, ReloadOutlined, SaveOutlined, UploadOutlined } from '@ant-design/icons'
import { adminApi, StickmanWorkflowMaterialGeneration, StickmanWorkflowMaterialLibrary } from '@/services/admin'
import { resolveBackendUrl } from '@/services/api'

const emptyLibrary = (): StickmanWorkflowMaterialLibrary => ({
  key: `workflow_library_${Date.now()}`,
  name: '',
  description: '',
  is_active: true,
  is_visible: true,
  sort_order: 10,
  base_path: '',
  material_json_path: '',
  image_count: 0,
  material_count: 0,
  source: 'uploaded_package',
})

export default function AdminStickmanWorkflowLibraries() {
  const [libraries, setLibraries] = useState<StickmanWorkflowMaterialLibrary[]>([])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [uploadingKeys, setUploadingKeys] = useState<Record<string, boolean>>({})
  const [generationKey, setGenerationKey] = useState(`reference_library_${Date.now()}`)
  const [generationName, setGenerationName] = useState('参考图素材库')
  const [generationCount, setGenerationCount] = useState(100)
  const [generation, setGeneration] = useState<StickmanWorkflowMaterialGeneration | null>(null)
  const [generationLoading, setGenerationLoading] = useState(false)
  const [sampleImageUrls, setSampleImageUrls] = useState<string[]>([])
  const sampleImageKey = generation?.sample_images?.join('|') || ''

  const loadLibraries = async () => {
    setLoading(true)
    try {
      const { data } = await adminApi.getStickmanWorkflowMaterialLibraries()
      setLibraries(data.libraries || [])
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '加载火柴人工作流素材库失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadLibraries()
  }, [])

  useEffect(() => {
    if (!generation?.id || ['samples_ready', 'completed', 'failed'].includes(generation.status)) return
    const timer = window.setInterval(async () => {
      try {
        const { data } = await adminApi.getStickmanWorkflowMaterialGeneration(generation.id)
        setGeneration(data)
        if (data.status === 'completed') await loadLibraries()
      } catch {
        window.clearInterval(timer)
      }
    }, 3000)
    return () => window.clearInterval(timer)
  }, [generation?.id, generation?.status])

  useEffect(() => {
    if (!sampleImageKey) {
      setSampleImageUrls([])
      return
    }
    let active = true
    const objectUrls: string[] = []
    Promise.all(sampleImageKey.split('|').map(async (assetUrl) => {
      const { data } = await adminApi.getStickmanWorkflowMaterialGenerationAsset(assetUrl)
      const objectUrl = URL.createObjectURL(data)
      objectUrls.push(objectUrl)
      return objectUrl
    }))
      .then((urls) => {
        if (active) {
          setSampleImageUrls(urls)
        } else {
          urls.forEach((url) => URL.revokeObjectURL(url))
        }
      })
      .catch(() => {
        if (active) message.error('加载样图失败')
      })
    return () => {
      active = false
      objectUrls.forEach((url) => URL.revokeObjectURL(url))
    }
  }, [sampleImageKey])

  const updateLibrary = (index: number, patch: Partial<StickmanWorkflowMaterialLibrary>) => {
    setLibraries((prev) => prev.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item))
  }

  const saveLibraries = async () => {
    setSaving(true)
    try {
      const payload = libraries.map((item, index) => ({
        ...item,
        key: String(item.key || '').trim(),
        name: String(item.name || '').trim(),
        sort_order: item.sort_order || index + 1,
      }))
      const { data } = await adminApi.saveStickmanWorkflowMaterialLibraries(payload)
      setLibraries(data.libraries || [])
      message.success('火柴人工作流素材库配置已保存')
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '保存素材库失败')
    } finally {
      setSaving(false)
    }
  }

  const uploadPackage = async (libraryKey: string, file: File) => {
    const key = String(libraryKey || '').trim()
    if (!key) {
      message.warning('请先填写素材库 key 并保存')
      return false
    }
    setUploadingKeys((prev) => ({ ...prev, [key]: true }))
    try {
      await saveLibraries()
      const { data } = await adminApi.uploadStickmanWorkflowMaterialLibraryPackage(key, file)
      message.success(data.message || '素材库 zip 已上传')
      await loadLibraries()
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '上传素材库 zip 失败')
    } finally {
      setUploadingKeys((prev) => ({ ...prev, [key]: false }))
    }
    return false
  }

  const createSamples = async (file: File) => {
    if (!generationKey.trim() || !generationName.trim()) {
      message.warning('请先填写素材库 Key 和名称')
      return false
    }
    setGenerationLoading(true)
    try {
      const { data } = await adminApi.createStickmanWorkflowMaterialSamples({
        libraryKey: generationKey.trim().toLowerCase(),
        libraryName: generationName.trim(),
        targetCount: generationCount,
        referenceImage: file,
      })
      setGeneration(data)
      message.success('已开始生成两张风格样图')
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '创建样图任务失败')
    } finally {
      setGenerationLoading(false)
    }
    return false
  }

  const confirmSamples = async () => {
    if (!generation) return
    setGenerationLoading(true)
    try {
      const { data } = await adminApi.confirmStickmanWorkflowMaterialGeneration(generation.id)
      setGeneration(data)
      message.success('已确认样图，开始批量生成')
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '确认样图失败')
    } finally {
      setGenerationLoading(false)
    }
  }

  const regenerateSamples = async () => {
    if (!generation) return
    setGenerationLoading(true)
    try {
      const { data } = await adminApi.regenerateStickmanWorkflowMaterialSamples(generation.id)
      setGeneration(data)
      message.success('正在重新生成样图')
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '重新生成样图失败')
    } finally {
      setGenerationLoading(false)
    }
  }

  return (
    <div>
      <div className="mb-6">
        <Typography.Title level={2}>火柴人工作流素材库</Typography.Title>
        <Typography.Paragraph type="secondary">
          这里管理的是 `/stickman-workflow` 专用素材库，不是增强讲解 `stickman-v2` 的场景图风格库。
        </Typography.Paragraph>
      </div>

      <Card className="mb-4">
        <Space wrap>
          <Button icon={<ReloadOutlined />} loading={loading} onClick={loadLibraries}>刷新</Button>
          <Button icon={<PlusOutlined />} onClick={() => setLibraries((prev) => [...prev, emptyLibrary()])}>新增素材库</Button>
          <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={saveLibraries}>保存配置</Button>
        </Space>
      </Card>

      <section className="mb-4" style={{ border: '1px solid #e5e7eb', padding: 20, background: '#fff' }}>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div>
            <Typography.Title level={4} style={{ margin: 0 }}>参考图生成素材库</Typography.Title>
            <Typography.Text type="secondary">先生成两张样图确认画风，再批量生成并自动建立匹配 JSON。</Typography.Text>
          </div>
          <Row gutter={[12, 12]}>
            <Col xs={24} md={8}>
              <div className="text-gray-500 mb-1">素材库 Key</div>
              <Input value={generationKey} onChange={(event) => setGenerationKey(event.target.value)} disabled={!!generation && generation.status !== 'failed'} />
            </Col>
            <Col xs={24} md={8}>
              <div className="text-gray-500 mb-1">素材库名称</div>
              <Input value={generationName} onChange={(event) => setGenerationName(event.target.value)} disabled={!!generation && generation.status !== 'failed'} />
            </Col>
            <Col xs={24} md={8}>
              <div className="text-gray-500 mb-1">图片数量</div>
              <InputNumber min={6} max={120} value={generationCount} onChange={(value) => setGenerationCount(value || 100)} style={{ width: '100%' }} disabled={!!generation && generation.status !== 'failed'} />
            </Col>
          </Row>
          <Upload beforeUpload={createSamples} showUploadList={false} accept=".png,.jpg,.jpeg,.webp">
            <Button icon={<PictureOutlined />} loading={generationLoading}>上传参考图并生成两张样图</Button>
          </Upload>
          {generation ? (
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
              <div>
                <Space wrap><Tag color="blue">任务 #{generation.id}</Tag><strong>{generation.message || generation.status}</strong></Space>
                <Progress percent={generation.progress || 0} status={generation.status === 'failed' ? 'exception' : generation.status === 'completed' ? 'success' : 'active'} />
              </div>
              {generation.error ? <Alert type="error" showIcon message={generation.error} /> : null}
              {sampleImageUrls.length ? (
                <Row gutter={[16, 16]}>
                  {sampleImageUrls.map((url, index) => (
                    <Col xs={24} md={12} key={url}>
                      <img src={resolveBackendUrl(url)} alt={`风格样图 ${index + 1}`} style={{ width: '100%', aspectRatio: '1 / 1', objectFit: 'contain', border: '1px solid #e5e7eb', background: '#fafafa' }} />
                    </Col>
                  ))}
                </Row>
              ) : null}
              {generation.status === 'samples_ready' ? (
                <Space wrap>
                  <Button icon={<ReloadOutlined />} onClick={regenerateSamples} loading={generationLoading}>重新生成样图</Button>
                  <Button type="primary" icon={<CheckOutlined />} onClick={confirmSamples} loading={generationLoading}>确认画风并批量生成</Button>
                </Space>
              ) : null}
              {generation.status === 'completed' ? <Alert type="success" showIcon message="素材库已生成并启用，用户现在可以在火柴人工作流中选择。" /> : null}
            </Space>
          ) : null}
        </Space>
      </section>

      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        {libraries.map((item, index) => {
          const key = item.key || `library_${index}`
          const imageUrl = resolveBackendUrl(item.image_url)
          const isDefault = item.key === 'sc1_outputs'
          return (
            <Card
              key={`${key}_${index}`}
              title={
                <Space>
                  <FolderOpenOutlined />
                  <span>{item.name || `素材库 ${index + 1}`}</span>
                  {isDefault ? <Tag color="blue">默认 SC1</Tag> : <Tag>{item.source || 'uploaded_package'}</Tag>}
                  {item.is_active ? <Tag color="green">启用</Tag> : <Tag>停用</Tag>}
                </Space>
              }
            >
              <Row gutter={[16, 16]}>
                <Col xs={24} lg={16}>
                  <Space direction="vertical" style={{ width: '100%' }} size="middle">
                    <Row gutter={12}>
                      <Col xs={24} md={8}>
                        <div className="text-gray-500 mb-1">素材库 Key</div>
                        <Input value={item.key} disabled={isDefault} onChange={(event) => updateLibrary(index, { key: event.target.value })} />
                      </Col>
                      <Col xs={24} md={8}>
                        <div className="text-gray-500 mb-1">名称</div>
                        <Input value={item.name} onChange={(event) => updateLibrary(index, { name: event.target.value })} />
                      </Col>
                      <Col xs={24} md={8}>
                        <div className="text-gray-500 mb-1">排序</div>
                        <InputNumber value={item.sort_order || index + 1} min={1} max={999} style={{ width: '100%' }} onChange={(value) => updateLibrary(index, { sort_order: value || index + 1 })} />
                      </Col>
                    </Row>
                    <div>
                      <div className="text-gray-500 mb-1">说明</div>
                      <Input.TextArea value={item.description || ''} rows={2} onChange={(event) => updateLibrary(index, { description: event.target.value })} />
                    </div>
                    <Row gutter={12}>
                      <Col xs={24} md={12}>
                        <div className="text-gray-500 mb-1">素材目录</div>
                        <Input value={item.base_path || ''} onChange={(event) => updateLibrary(index, { base_path: event.target.value })} placeholder="上传 zip 后自动生成，也可填写已有目录" />
                      </Col>
                      <Col xs={24} md={12}>
                        <div className="text-gray-500 mb-1">JSON 清单</div>
                        <Input value={item.material_json_path || ''} onChange={(event) => updateLibrary(index, { material_json_path: event.target.value })} placeholder="material.json 或 materials.normalized.json" />
                      </Col>
                    </Row>
                    <Space wrap>
                      <span>启用</span>
                      <Switch checked={item.is_active !== false} onChange={(checked) => updateLibrary(index, { is_active: checked })} />
                      <span>前台可见</span>
                      <Switch checked={item.is_visible !== false} onChange={(checked) => updateLibrary(index, { is_visible: checked })} />
                      <Tag color="purple">图片 {item.image_count || 0}</Tag>
                      <Tag color="geekblue">条目 {item.material_count || 0}</Tag>
                    </Space>
                  </Space>
                </Col>
                <Col xs={24} lg={8}>
                  <Space direction="vertical" style={{ width: '100%' }}>
                    {imageUrl ? (
                      <img src={imageUrl} alt={item.name || item.key} style={{ width: '100%', maxHeight: 180, objectFit: 'contain', border: '1px solid #eee', borderRadius: 8, background: '#fafafa' }} />
                    ) : (
                      <div style={{ display: 'grid', placeItems: 'center', minHeight: 160, border: '1px dashed #d9d9d9', borderRadius: 8, color: '#999' }}>
                        暂无预览图
                      </div>
                    )}
                    <Upload beforeUpload={(file) => uploadPackage(item.key, file)} showUploadList={false} accept=".zip">
                      <Button icon={<UploadOutlined />} loading={!!uploadingKeys[item.key]} block>
                        上传素材库 zip
                      </Button>
                    </Upload>
                    <div className="text-gray-400 text-xs">
                      zip 需包含图片和 material.json / materials.json，上传后会生成规范化清单。
                    </div>
                  </Space>
                </Col>
              </Row>
            </Card>
          )
        })}
      </Space>
    </div>
  )
}
