import { Card, Descriptions, Tag, Row, Col, Divider } from 'antd'
import { SafetyOutlined, LockOutlined, GlobalOutlined, CheckCircleOutlined, DatabaseOutlined, ApiOutlined, CodeOutlined, SecurityScanOutlined } from '@ant-design/icons'

export default function AdminSettings() {
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
      </Row>
    </div>
  )
}
