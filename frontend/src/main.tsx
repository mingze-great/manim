import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { ConfigProvider } from 'antd'
import App from './App'
import { useThemeStore, lightTheme, darkTheme } from './stores/themeStore'
import './index.css'

function ThemedApp() {
  const mode = useThemeStore((state) => state.mode)
  const theme = mode === 'dark' ? darkTheme : lightTheme
  
  // 动态设置 data-theme 属性
  React.useEffect(() => {
    document.documentElement.setAttribute('data-theme', mode)
  }, [mode])
  
  return (
    <ConfigProvider theme={theme}>
      <App />
    </ConfigProvider>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <ThemedApp />
    </BrowserRouter>
  </React.StrictMode>,
)
