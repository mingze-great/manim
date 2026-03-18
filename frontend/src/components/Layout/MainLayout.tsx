import { Outlet, useNavigate } from 'react-router-dom'
import { Layout, Menu, Space, Dropdown, Avatar, Tag, Button, Drawer } from 'antd'
import type { MenuProps } from 'antd'
import { HomeOutlined, LogoutOutlined, UserOutlined, SafetyOutlined, MenuOutlined } from '@ant-design/icons'
import { useAuthStore } from '@/stores/authStore'
import { useState } from 'react'

const { Header, Sider, Content } = Layout

export default function MainLayout() {
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const menuItems: MenuProps['items'] = [
    { key: '/', icon: <HomeOutlined />, label: '项目列表' },
  ]
  
  if (user?.is_admin) {
    menuItems.push({ key: '/admin', icon: <SafetyOutlined />, label: '管理后台' })
  }

  const userMenu: MenuProps = {
    items: [
      {
        key: 'email',
        icon: <UserOutlined />,
        label: user?.email,
        disabled: true,
      },
      { type: 'divider' as const },
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

  const handleMenuClick = (key: string) => {
    navigate(key)
    setMobileMenuOpen(false)
  }

  return (
    <Layout className="min-h-screen mobile-layout">
      <Sider 
        theme="light" 
        breakpoint="lg" 
        collapsedWidth={0}
        onBreakpoint={(broken) => {
          if (!broken) setMobileMenuOpen(false)
        }}
        className="main-sider md:block hidden"
      >
        <div className="h-16 flex items-center justify-center text-xl font-bold text-blue-600">
          Manim 视频平台
        </div>
        <Menu
          mode="inline"
          items={menuItems}
          onClick={({ key }) => handleMenuClick(key)}
        />
      </Sider>

      <Drawer
        title={
          <span className="text-xl font-bold text-blue-600">Manim 视频平台</span>
        }
        placement="left"
        onClose={() => setMobileMenuOpen(false)}
        open={mobileMenuOpen}
        width={280}
        className="mobile-drawer"
        styles={{ body: { padding: 0 } }}
      >
        <Menu
          mode="inline"
          items={menuItems}
          onClick={({ key }) => handleMenuClick(key)}
          selectedKeys={[window.location.pathname]}
        />
      </Drawer>

      <Layout>
        <Header className="bg-white px-4 md:px-6 flex items-center justify-between mobile-header">
          <div className="flex items-center gap-3 md:hidden">
            <Button 
              type="text" 
              icon={<MenuOutlined />} 
              onClick={() => setMobileMenuOpen(true)}
              size="large"
            />
          </div>
          <div className="flex-1" />
          <Space>
            <Dropdown menu={userMenu} placement="bottomRight">
              <Space className="cursor-pointer py-2 px-3 hover:bg-gray-100 rounded-lg transition-colors">
                <Avatar icon={<UserOutlined />} size="small" />
                <span className="hidden sm:inline">{user?.username}</span>
                {user?.is_admin && <Tag color="gold" className="hidden sm:inline">管理员</Tag>}
              </Space>
            </Dropdown>
          </Space>
        </Header>
        <Content className="p-4 md:p-6 mobile-content">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
