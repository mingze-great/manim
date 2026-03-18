import { Outlet, useNavigate } from 'react-router-dom'
import { Layout, Menu, Space, Dropdown, Avatar } from 'antd'
import { HomeOutlined, LogoutOutlined, UserOutlined } from '@ant-design/icons'
import { useAuthStore } from '@/stores/authStore'

const { Header, Sider, Content } = Layout

export default function MainLayout() {
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()

  const menuItems = [
    { key: '/', icon: <HomeOutlined />, label: '项目列表' },
  ]

  const userMenu = {
    items: [
      {
        key: 'logout',
        icon: <LogoutOutlined />,
        label: '退出登录',
        onClick: () => {
          logout()
          navigate('/login')
        },
      },
    ],
  }

  return (
    <Layout className="min-h-screen">
      <Sider theme="light" breakpoint="lg">
        <div className="h-16 flex items-center justify-center text-xl font-bold text-blue-600">
          Manim 视频平台
        </div>
        <Menu
          mode="inline"
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header className="bg-white px-6 flex justify-end items-center">
          <Space>
            <Dropdown menu={userMenu}>
              <Space className="cursor-pointer">
                <Avatar icon={<UserOutlined />} />
                <span>{user?.username}</span>
              </Space>
            </Dropdown>
          </Space>
        </Header>
        <Content className="p-6">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
