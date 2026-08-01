declare global {
  interface Window {
    THREE?: any
  }
}

const THREE_CDN = 'https://cdn.jsdelivr.net/npm/three@0.160.1/build/three.min.js'
let loader: Promise<any> | null = null

export function loadThree(): Promise<any> {
  if (window.THREE) return Promise.resolve(window.THREE)
  if (loader) return loader
  loader = new Promise((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(`script[src="${THREE_CDN}"]`)
    const script = existing || document.createElement('script')
    const onLoad = () => window.THREE ? resolve(window.THREE) : reject(new Error('Three.js 未正确加载'))
    const onError = () => reject(new Error('Three.js CDN 加载失败'))
    script.addEventListener('load', onLoad, { once: true })
    script.addEventListener('error', onError, { once: true })
    if (!existing) {
      script.src = THREE_CDN
      script.async = true
      script.crossOrigin = 'anonymous'
      document.head.appendChild(script)
    }
  })
  return loader
}
