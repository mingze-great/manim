import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu, Avatar, Dropdown, Space, Badge, Button, Drawer, Tag, Tooltip } from 'antd'
import type { MenuProps } from 'antd'
import {
  DashboardOutlined, UserOutlined, LogoutOutlined, SafetyOutlined,
  TeamOutlined, FileTextOutlined, SettingOutlined, 
  MenuOutlined, SwapOutlined, HomeOutlined, CodeOutlined, BarChartOutlined, ThunderboltOutlined, EditOutlined
} from '@ant-design/icons'
import { useAuthStore } from '@/stores/authStore'
import { useEffect } from 'react'
import { useState } from 'react'
import './Layout.css'

const { Header, Sider, Content } = Layout

export default function AdminLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuthStore()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  useEffect(() => {
    if (user?.is_admin) {
      sessionStorage.setItem('admin_mode', 'true')
    }
  }, [user])

  const menuItems: MenuProps['items'] = [
    { key: '/admin', icon: <DashboardOutlined />, label: '仪表盘' },
    { key: '/admin/statistics', icon: <BarChartOutlined />, label: '数据统计' },
    { key: '/admin/token-usage', icon: <ThunderboltOutlined />, label: 'Token统计' },
    { key: '/admin/users', icon: <TeamOutlined />, label: '用户管理' },
    { key: '/admin/templates', icon: <CodeOutlined />, label: '代码模板' },
    { key: '/admin/article-categories', icon: <EditOutlined />, label: '公众号配置' },
    { key: '/admin/module-stats', icon: <BarChartOutlined />, label: '模块看板' },
    { key: '/admin/logs', icon: <FileTextOutlined />, label: '操作日志' },
    { type: 'divider' as const },
    { key: '/admin/settings', icon: <SettingOutlined />, label: '系统设置' },
  ]

  const userMenu: MenuProps = {
    items: [
      {
        key: 'username',
        icon: <UserOutlined />,
        label: (
          <div>
            <div className="font-medium">{user?.username}</div>
            <Tag color="gold" className="text-xs">管理员</Tag>
          </div>
        ),
        disabled: true,
      },
      { type: 'divider' },
      {
        key: 'switch-user',
        icon: <SwapOutlined />,
        label: '切换到用户视图',
        onClick: () => navigate('/'),
      },
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
    <Layout className="main-layout">
      <Sider 
        width={240} 
        className="main-sider admin-sider"
        breakpoint="lg"
        collapsedWidth={0}
        onBreakpoint={(broken) => !broken && setMobileMenuOpen(false)}
      >
        <div className="sider-logo admin-logo" onClick={() => navigate('/admin')}>
          <div className="logo-icon" style={{ background: 'linear-gradient(135deg, #f59e0b, #d97706)' }}>
            <SafetyOutlined />
          </div>
          <span className="logo-text admin-logo-text">管理后台</span>
        </div>
        <Menu
          theme="light"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => handleMenuClick(key)}
          className="main-menu"
        />
        <div className="sider-footer">
          <Button 
            icon={<HomeOutlined />} 
            onClick={() => navigate('/')}
            block
            className="mb-2"
          >
            返回首页
          </Button>
          <div className="user-quota">
            <div className="quota-label">当前用户</div>
            <div className="quota-value">{user?.username}</div>
          </div>
        </div>
      </Sider>

      <Drawer
        title={
          <div className="drawer-logo">
            <div className="logo-icon small" style={{ background: 'linear-gradient(135deg, #f59e0b, #d97706)' }}>
              <SafetyOutlined style={{ color: '#fff' }} />
            </div>
            <span>管理后台</span>
          </div>
        }
        placement="left"
        onClose={() => setMobileMenuOpen(false)}
        open={mobileMenuOpen}
        width={280}
        className="mobile-drawer"
      >
        <Menu
          theme="light"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => handleMenuClick(key)}
        />
      </Drawer>

      <Layout>
        <Header className="main-header admin-header">
          <div className="header-left">
            <Button
              type="text"
              icon={<MenuOutlined />}
              onClick={() => setMobileMenuOpen(true)}
              className="mobile-menu-btn"
            />
            <h1 className="page-title">{getPageTitle()}</h1>
            <Tag color="gold" className="ml-2">管理</Tag>
          </div>
          <div className="header-right">
            <Tooltip title="返回用户视图">
              <Button 
                type="text" 
                icon={<HomeOutlined />}
                onClick={() => navigate('/')}
              />
            </Tooltip>
            <Dropdown menu={userMenu} placement="bottomRight">
              <Space className="user-info">
                <Badge dot status="processing" color="#52c41a">
                  <Avatar 
                    size={36} 
                    style={{ backgroundColor: '#f59e0b' }}
                    icon={<SafetyOutlined />}
                  />
                </Badge>
                <div className="user-details">
                  <span className="user-name">{user?.username}</span>
                  <span className="user-plan">管理员</span>
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
