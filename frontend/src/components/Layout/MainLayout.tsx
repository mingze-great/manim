import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu, Avatar, Dropdown, Space, Button, Drawer } from 'antd'
import type { MenuProps } from 'antd'
import {
  PlusOutlined, HistoryOutlined, UserOutlined,
  LogoutOutlined, MenuOutlined, BookOutlined, SafetyOutlined
} from '@ant-design/icons'
import { useAuthStore } from '@/stores/authStore'
import { useState, useEffect } from 'react'
import './Layout.css'

const { Header, Sider, Content } = Layout

export default function MainLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuthStore()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [isAdminMode, setIsAdminMode] = useState(false)

  useEffect(() => {
    const isAdmin = user?.is_admin || sessionStorage.getItem('admin_mode') === 'true'
    setIsAdminMode(!!isAdmin)
  }, [user])

  const menuItems: MenuProps['items'] = [
    { key: '/creator', icon: <PlusOutlined />, label: '开始创作' },
    { key: '/history', icon: <HistoryOutlined />, label: '我的作品' },
    { key: '/docs', icon: <BookOutlined />, label: '帮助中心' },
  ]

  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '个人中心',
      onClick: () => navigate('/profile'),
    },
    { type: 'divider' as const },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      onClick: () => {
        sessionStorage.removeItem('admin_mode')
        logout()
        navigate('/login')
      },
    },
  ]

  const userMenu: MenuProps = {
    items: userMenuItems,
  }

  const handleMenuClick = (key: string) => {
    navigate(key)
    setMobileMenuOpen(false)
  }

  const getPageTitle = () => {
    const item = menuItems.find(m => m && 'key' in m && m.key === location.pathname)
    if (item && 'label' in item) return item.label as string
    if (location.pathname.startsWith('/creator')) return '创作工作台'
    return '思维可视化 视频平台'
  }

  return (
    <Layout className="main-layout">
      <Sider 
        width={240} 
        className="main-sider"
        breakpoint="lg"
        collapsedWidth={0}
        onBreakpoint={(broken) => !broken && setMobileMenuOpen(false)}
      >
        <div className="sider-logo" onClick={() => navigate('/')}>
          <div className="logo-icon">
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
            </svg>
          </div>
          <span className="logo-text">思维可视化</span>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => handleMenuClick(key)}
          className="main-menu"
        />
        <div className="sider-footer">
          {isAdminMode && user?.is_admin && (
            <Button 
              icon={<SafetyOutlined />} 
              onClick={() => navigate('/admin')}
              block
              type="primary"
              ghost
              className="mb-2"
            >
              管理后台
            </Button>
          )}
        </div>
      </Sider>

      <Drawer
        title={
          <div className="drawer-logo">
            <div className="logo-icon small">
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
              </svg>
            </div>
            <span>思维可视化</span>
          </div>
        }
        placement="left"
        onClose={() => setMobileMenuOpen(false)}
        open={mobileMenuOpen}
        width={280}
        className="mobile-drawer"
      >
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => handleMenuClick(key)}
        />
      </Drawer>

      <Layout>
        <Header className="main-header">
          <div className="header-left">
            <Button
              type="text"
              icon={<MenuOutlined />}
              onClick={() => setMobileMenuOpen(true)}
              className="mobile-menu-btn"
            />
            <h1 className="page-title">{getPageTitle()}</h1>
          </div>
          <div className="header-right">
            <Dropdown menu={userMenu} placement="bottomRight" trigger={['click']}>
              <Space className="user-info">
                <Avatar 
                  size={36} 
                  style={{ backgroundColor: '#6366f1' }}
                  icon={<UserOutlined />}
                />
                <div className="user-details">
                  <span className="user-name">{user?.username || '用户'}</span>
                  <span className="user-plan">免费版</span>
                </div>
              </Space>
            </Dropdown>
          </div>
        </Header>
        <Content className="main-content">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
