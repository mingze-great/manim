import { Card, Descriptions, Tag } from 'antd'
import { SafetyOutlined, LockOutlined, GlobalOutlined } from '@ant-design/icons'

export default function AdminSettings() {
  return (
    <div>
      <Card className="admin-card mb-4">
        <div className="flex items-center gap-3 mb-4">
          <SafetyOutlined className="text-2xl text-blue" />
          <div>
            <div className="text-lg font-medium">安全设置</div>
            <div className="text-gray text-sm">系统安全配置信息</div>
          </div>
        </div>
        <Descriptions column={2}>
          <Descriptions.Item label="JWT 令牌有效期">24 小时</Descriptions.Item>
          <Descriptions.Item label="登录失败锁定">
            <Tag color="green">已启用</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="登录限流">
            <Tag color="green">10 次/分钟</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="注册限流">
            <Tag color="green">5 次/小时</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="密码强度">
            <Tag color="green">8位以上 + 字母 + 数字</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="Token 黑名单">
            <Tag color="green">已启用</Tag>
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Card className="admin-card mb-4">
        <div className="flex items-center gap-3 mb-4">
          <GlobalOutlined className="text-2xl text-green" />
          <div>
            <div className="text-lg font-medium">系统信息</div>
            <div className="text-gray text-sm">当前运行的系统版本</div>
          </div>
        </div>
        <Descriptions column={2}>
          <Descriptions.Item label="系统版本">v2.0.0</Descriptions.Item>
          <Descriptions.Item label="API 版本">v2.0.0</Descriptions.Item>
          <Descriptions.Item label="前端版本">v2.0.0</Descriptions.Item>
          <Descriptions.Item label="数据库">SQLite</Descriptions.Item>
        </Descriptions>
      </Card>

      <Card className="admin-card">
        <div className="flex items-center gap-3 mb-4">
          <LockOutlined className="text-2xl text-orange" />
          <div>
            <div className="text-lg font-medium">操作日志</div>
            <div className="text-gray text-sm">所有敏感操作都会被记录</div>
          </div>
        </div>
        <Descriptions column={1}>
          <Descriptions.Item label="登录日志">
            <Tag color="green">已记录</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="用户操作日志">
            <Tag color="green">已记录</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="项目操作日志">
            <Tag color="green">已记录</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="任务操作日志">
            <Tag color="green">已记录</Tag>
          </Descriptions.Item>
        </Descriptions>
      </Card>
    </div>
  )
}
