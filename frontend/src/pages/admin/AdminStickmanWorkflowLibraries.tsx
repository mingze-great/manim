import { useEffect, useState } from 'react'
import { Button, Card, Col, Input, InputNumber, Row, Space, Switch, Tag, Typography, Upload, message } from 'antd'
import { FolderOpenOutlined, PlusOutlined, ReloadOutlined, SaveOutlined, UploadOutlined } from '@ant-design/icons'
import { adminApi, StickmanWorkflowMaterialLibrary } from '@/services/admin'
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
