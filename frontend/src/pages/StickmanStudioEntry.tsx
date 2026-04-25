import { useEffect, useState } from 'react'
import { Alert, Spin } from 'antd'
import { useParams } from 'react-router-dom'
import StickmanStudioLegacy from './StickmanStudio'
import StickmanStudioV2 from './StickmanStudioV2'
import { projectApi, Project } from '@/services/project'

export default function StickmanStudioEntry() {
  const { id } = useParams<{ id: string }>()
  const [project, setProject] = useState<Project | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const run = async () => {
      try {
        const { data } = await projectApi.get(Number(id))
        setProject(data)
      } finally {
        setLoading(false)
      }
    }
    run()
  }, [id])

  if (loading) {
    return <div className="flex items-center justify-center h-64"><Spin size="large" /></div>
  }

  if (project?.stickman_variant === 'v2') {
    return (
      <>
        <div className="max-w-6xl mx-auto px-6 pt-6">
          <Alert type="success" message="当前为火柴人优化版模块" description="这个项目走新版火柴人工作流，后续优化只影响优化版，不覆盖经典版。" />
        </div>
        <StickmanStudioV2 />
      </>
    )
  }

  return (
    <>
      <div className="max-w-6xl mx-auto px-6 pt-6">
        <Alert type="info" message="当前为火柴人经典版模块" description="这个项目保持基线火柴人工作流，适合继续沿用原有制作流程。" />
      </div>
      <StickmanStudioLegacy />
    </>
  )
}
