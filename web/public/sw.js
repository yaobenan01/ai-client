/* 离线 PWA：缓存应用壳，使 Web 版可在鸿蒙浏览器等环境离线安装运行。
 *
 * 重要：桌面端（Tauri）前端由内嵌资源提供，绝不能启用 SW 缓存 ——
 * 旧 SW 会一直回放上一版 index.html，而它引用的 hash 资源在新版本里已被删除，
 * 结果就是升级后窗口一片空白。这里对桌面来源做“自毁”，并保证 Web 端 HTML 走
 * network-first，避免同类问题在 PWA 上重演。
 */
const CACHE = 'ai-client-shell-v2'
const ASSETS = ['/', '/index.html', '/manifest.webmanifest', '/icon-192.png', '/icon-512.png']

const IS_DESKTOP =
  self.location.hostname === 'tauri.localhost' || self.location.protocol === 'tauri:'

if (IS_DESKTOP) {
  // 桌面端：清理所有缓存、注销自身，并强制客户端重新拉取内嵌资源。
  self.addEventListener('install', () => self.skipWaiting())
  self.addEventListener('activate', (e) => {
    e.waitUntil(
      (async () => {
        const keys = await caches.keys()
        await Promise.all(keys.map((k) => caches.delete(k)))
        await self.registration.unregister()
        const clients = await self.clients.matchAll({ type: 'window' })
        await Promise.all(clients.map((c) => c.navigate(c.url)))
      })()
    )
  })
} else {
  self.addEventListener('install', (e) => {
    e.waitUntil(caches.open(CACHE).then((c) => c.addAll(ASSETS)).then(() => self.skipWaiting()))
  })

  self.addEventListener('activate', (e) => {
    e.waitUntil(
      caches
        .keys()
        .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
        .then(() => self.clients.claim())
    )
  })

  self.addEventListener('fetch', (e) => {
    const url = new URL(e.request.url)
    if (url.origin !== location.origin) return
    if (e.request.method !== 'GET') return
    // API 请求不缓存，直接放行
    if (url.pathname.startsWith('/api') || url.pathname.startsWith('/health')) return

    // 导航与 HTML 走 network-first：即使缓存存在也优先取最新页面
    const isHTML =
      e.request.mode === 'navigate' || url.pathname === '/' || url.pathname.endsWith('.html')
    if (isHTML) {
      e.respondWith(
        fetch(e.request)
          .then((resp) => {
            const copy = resp.clone()
            caches.open(CACHE).then((c) => c.put(e.request, copy)).catch(() => {})
            return resp
          })
          .catch(() => caches.match(e.request).then((hit) => hit || caches.match('/index.html')))
      )
      return
    }

    e.respondWith(
      caches.match(e.request).then(
        (hit) =>
          hit ||
          fetch(e.request).then((resp) => {
            const copy = resp.clone()
            caches.open(CACHE).then((c) => c.put(e.request, copy)).catch(() => {})
            return resp
          })
      )
    )
  })
}
