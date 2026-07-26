import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu, Avatar, Dropdown, Space, Button, Drawer } from 'antd'
import type { MenuProps } from 'antd'
import {
  PlusOutlined, HistoryOutlined, UserOutlined,
  LogoutOutlined, MenuOutlined, BookOutlined, SafetyOutlined, HomeOutlined, VideoCameraOutlined, FileProtectOutlined, TeamOutlined
} from '@ant-design/icons'
import { useAuthStore } from '@/stores/authStore'
import { clearAuthArtifacts, syncCrossSiteLogout } from '@/utils/authSync'
import { useState, useEffect } from 'react'
import PlatformAssistantWidget from '@/components/PlatformAssistant/PlatformAssistantWidget'
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
    { key: '/stickman-workflow', icon: <VideoCameraOutlined />, label: '火柴人工作流' },
    ...((user?.role === 'partner' || user?.is_admin) ? [{ key: '/partner', icon: <TeamOutlined />, label: '合作者工作台' }] : []),
    { key: '/creator', icon: <PlusOutlined />, label: '开始创作' },
    { key: '/ai-video/dashboard', icon: <VideoCameraOutlined />, label: 'AI 视频导演' },
    { key: '/knowledge-ip', icon: <FileProtectOutlined />, label: '知识IP包装' },
    { key: '/history', icon: <HistoryOutlined />, label: '我的作品' },
    { key: '/docs', icon: <BookOutlined />, label: '帮助中心' },
  ]

  const workflowMenuOrder = ['/creator', '/stickman-workflow', '/ai-video/dashboard', '/knowledge-ip', '/history', '/docs', '/partner']
  const workflowMenuLabels: Record<string, string> = {
    '/creator': '工作流中心',
    '/stickman-workflow': '心理火柴人成片',
    '/ai-video/dashboard': 'AI 视频导演',
    '/knowledge-ip': '知识 IP 包装',
    '/history': '我的作品',
    '/docs': '帮助中心',
    '/partner': '合作者工作台',
  }
  const visibleMenuItems = menuItems
    .filter((item) => {
      if (!item || !('key' in item)) return true
      if (item.key === '/partner') return user?.role === 'partner' && !user?.is_admin
      if (item.key === '/ai-video/dashboard' || item.key === '/knowledge-ip') return !!user?.is_admin
      return true
    })
    .map((item) => {
      if (!item || !('key' in item)) return item
      const key = String(item.key)
      return workflowMenuLabels[key] ? { ...item, label: workflowMenuLabels[key] } : item
    })
    .sort((a, b) => {
      const left = a && 'key' in a ? workflowMenuOrder.indexOf(String(a.key)) : 999
      const right = b && 'key' in b ? workflowMenuOrder.indexOf(String(b.key)) : 999
      return (left < 0 ? 999 : left) - (right < 0 ? 999 : right)
    })

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
        clearAuthArtifacts()
        logout()
        syncCrossSiteLogout(`${window.location.protocol}//${window.location.hostname}`)
        navigate('/login', { replace: true })
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
    if (location.pathname.startsWith('/stickman-workflow')) return '火柴人工作流'
    if (location.pathname.startsWith('/partner')) return '合作者工作台'
    const item = visibleMenuItems.find(m => m && 'key' in m && m.key === location.pathname)
    if (item && 'label' in item) return item.label as string
    if (location.pathname.startsWith('/creator')) return '创作工作台'
    if (location.pathname.startsWith('/ai-video')) return 'AI 视频导演工作台'
    if (location.pathname.startsWith('/knowledge-ip')) return '知识IP自动包装'
    if (location.pathname.includes('/explainer')) return '讲解型视频'
    if (location.pathname.startsWith('/article')) return '公众号文章'
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
          items={visibleMenuItems}
          onClick={({ key }) => handleMenuClick(key)}
          className="main-menu"
        />
        <div className="sider-footer">
          <Button icon={<HomeOutlined />} onClick={() => navigate('/')} block className="mb-2">
            返回首页
          </Button>
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
          items={visibleMenuItems}
          onClick={({ key }) => handleMenuClick(key)}
        />
        <div className="px-4 pb-4 pt-2">
          <Button icon={<HomeOutlined />} block onClick={() => handleMenuClick('/')}>
            返回首页
          </Button>
        </div>
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
            <Button type="text" icon={<HomeOutlined />} onClick={() => navigate('/')}>
              返回首页
            </Button>
            <Dropdown menu={userMenu} placement="bottomRight">
              <Space className="user-info">
                <Avatar 
                  size={36} 
                  style={{ backgroundColor: '#6366f1' }}
                  icon={<UserOutlined />}
                />
                <div className="user-details">
                  <span className="user-name">{user?.username || '用户'}</span>
                  <span className="user-plan">付费版</span>
                </div>
              </Space>
            </Dropdown>
          </div>
        </Header>
        <Content className="main-content">
          <Outlet />
        </Content>
        <PlatformAssistantWidget />
      </Layout>
    </Layout>
  )
}
