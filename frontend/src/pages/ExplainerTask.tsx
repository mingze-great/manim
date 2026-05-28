import { Alert, Button, Card } from 'antd'
import { useNavigate } from 'react-router-dom'

export default function ExplainerTask() {
  const navigate = useNavigate()

  return (
    <div className="max-w-4xl mx-auto p-6">
      <Card title="讲解视频任务">
        <Alert
          type="info"
          showIcon
          message="当前项目类型暂未接入独立任务页"
          description="请返回创作页或历史记录，使用已开放的思维可视化与火柴人视频流程。"
        />
        <Button className="mt-4" type="primary" onClick={() => navigate('/creator')}>
          返回创作页
        </Button>
      </Card>
    </div>
  )
}
