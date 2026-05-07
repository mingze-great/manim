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
          <Alert type="success" message="当前为增强讲解生成页面" description="这里显示增强讲解的生成进度和结果，你也可以随时返回继续编辑。" />
        </div>
        <StickmanProjectTaskV2 />
      </>
    )
  }

  return (
    <>
      <div className="max-w-5xl mx-auto px-6 pt-6">
        <Alert type="info" message="当前为标准讲解生成页面" description="这里显示标准讲解的生成进度和结果。" />
      </div>
      <StickmanProjectTaskLegacy />
    </>
  )
}
