import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu, Avatar, Dropdown, Space, Badge, Button, Drawer } from 'antd'
import type { MenuProps } from 'antd'
import {
  DashboardOutlined, UserOutlined, LogoutOutlined, SafetyOutlined,
  TeamOutlined, FileTextOutlined, BarChartOutlined, SettingOutlined, MenuOutlined
} from '@ant-design/icons'
import { useAuthStore } from '@/stores/authStore'
import { useState } from 'react'
import './AdminLayout.css'

const { Header, Sider, Content } = Layout

export default function AdminLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuthStore()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const menuItems: MenuProps['items'] = [
    { key: '/admin', icon: <DashboardOutlined />, label: '仪表盘' },
    { key: '/admin/users', icon: <TeamOutlined />, label: '用户管理' },
    { key: '/admin/logs', icon: <FileTextOutlined />, label: '操作日志' },
    { key: '/admin/stats', icon: <BarChartOutlined />, label: '数据统计' },
    { type: 'divider' as const },
    { key: '/admin/settings', icon: <SettingOutlined />, label: '系统设置' },
  ]

  const userMenu: MenuProps = {
    items: [
      {
        key: 'username',
        icon: <UserOutlined />,
        label: user?.username,
        disabled: true,
      },
      {
        key: 'exit-admin',
        icon: <SafetyOutlined />,
        label: '退出管理',
        disabled: true,
      },
      { type: 'divider' },
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

  const getPageTitle = () => {
    const item = menuItems.find(m => m && 'key' in m && m.key === location.pathname)
    if (item && 'label' in item) return item.label
    return '管理后台'
  }

  return (
    <Layout className="admin-layout">
      <Sider width={240} className="admin-sider" theme="dark">
        <div className="admin-logo">
          <SafetyOutlined className="admin-logo-icon" />
          <span className="admin-logo-text">Manim 管理后台</span>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => handleMenuClick(key)}
          className="admin-menu"
        />
        <div className="admin-version">
          <span>v2.0.0</span>
        </div>
      </Sider>

      <Drawer
        title={
          <Space>
            <SafetyOutlined />
            <span>Manim 管理后台</span>
          </Space>
        }
        placement="left"
        onClose={() => setMobileMenuOpen(false)}
        open={mobileMenuOpen}
        width={280}
        className="admin-mobile-drawer"
        styles={{ body: { padding: 0 } }}
      >
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => handleMenuClick(key)}
        />
      </Drawer>

      <Layout>
        <Header className="admin-header">
          <div className="admin-header-left">
            <Button 
              type="text" 
              icon={<MenuOutlined />} 
              onClick={() => setMobileMenuOpen(true)}
              className="admin-mobile-menu-btn"
              size="large"
            />
            <h2 className="admin-page-title">{getPageTitle()}</h2>
          </div>
          <div className="admin-header-right">
            <Dropdown menu={userMenu} placement="bottomRight">
              <Space className="admin-user">
                <Badge dot status="processing" color="#52c41a">
                  <Avatar icon={<UserOutlined />} className="admin-avatar" />
                </Badge>
                <span className="admin-username">{user?.username}</span>
                <span className="admin-role">管理员</span>
              </Space>
            </Dropdown>
          </div>
        </Header>
        <Content className="admin-content">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
