import { useEffect, useState } from 'react'
import { Alert, Spin } from 'antd'
import { useParams } from 'react-router-dom'
import StickmanProjectTaskLegacy from './StickmanProjectTask'
import StickmanProjectTaskV2 from './StickmanProjectTaskV2'
import { projectApi, Project } from '@/services/project'

export default function StickmanProjectTaskEntry() {
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
        <div className="max-w-5xl mx-auto px-6 pt-6">
          <Alert type="success" message="当前为火柴人优化版任务流" description="这里展示新版火柴人生成/合成任务，不影响经典版任务流。" />
        </div>
        <StickmanProjectTaskV2 />
      </>
    )
  }

  return (
    <>
      <div className="max-w-5xl mx-auto px-6 pt-6">
        <Alert type="info" message="当前为火柴人经典版任务流" description="这里保留基线火柴人任务流，便于与优化版并存使用。" />
      </div>
      <StickmanProjectTaskLegacy />
    </>
  )
}
