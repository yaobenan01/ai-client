import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './index.css'

// 桌面端（Tauri）由内嵌资源提供前端，必须禁用 Service Worker：
// 旧 SW 会缓存上一版 index.html，而它引用的 hash 资源在新版本里已不存在，
// 结果就是升级后窗口一片空白（“卡住不显示”）。这里主动注销并清空缓存做自愈。
const isTauriRuntime =
  typeof window !== 'undefined' &&
  ('__TAURI_INTERNALS__' in window ||
    '__TAURI__' in window ||
    window.location.protocol === 'tauri:' ||
    window.location.hostname === 'tauri.localhost')

if ('serviceWorker' in navigator) {
  if (isTauriRuntime) {
    navigator.serviceWorker
      .getRegistrations()
      .then((regs) => Promise.all(regs.map((r) => r.unregister())))
      .catch(() => {})
    if ('caches' in window) {
      caches
        .keys()
        .then((keys) => Promise.all(keys.map((k) => caches.delete(k))))
        .catch(() => {})
    }
  } else {
    // Web/PWA（含鸿蒙浏览器）保留离线能力
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/sw.js').catch(() => {})
    })
  }
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
)
