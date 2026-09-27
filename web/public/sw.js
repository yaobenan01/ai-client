/* 离线 PWA：缓存应用壳，使 Web 版可在鸿蒙浏览器等环境离线安装运行 */
const CACHE = 'ai-client-shell-v1'
const ASSETS = ['/', '/index.html', '/manifest.webmanifest', '/icon-192.png', '/icon-512.png']

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(ASSETS)).then(() => self.skipWaiting()))
})

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim())
  )
})

self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url)
  if (url.origin !== location.origin) return
  if (e.request.method !== 'GET') return
  // API 请求不缓存，直接放行
  if (url.pathname.startsWith('/api') || url.pathname.startsWith('/health')) return
  e.respondWith(
    caches.match(e.request).then((hit) => hit || fetch(e.request).then((resp) => {
      const copy = resp.clone()
      caches.open(CACHE).then((c) => c.put(e.request, copy)).catch(() => {})
      return resp
    }))
  )
})
