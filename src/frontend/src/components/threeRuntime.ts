declare global {
  interface Window {
    THREE?: any
  }
}

const THREE_CDN = 'https://cdn.jsdelivr.net/npm/three@0.160.1/build/three.min.js'
let loader: Promise<any> | null = null

function normalizeRuntime(THREE: any): any {
  if (!THREE.CapsuleGeometry) {
    THREE.CapsuleGeometry = class CapsuleGeometry extends THREE.SphereGeometry {
      constructor(radius = 1, length = 1, capSegments = 8, radialSegments = 16) {
        super(radius, Math.max(8, radialSegments), Math.max(8, capSegments * 2))
        const fullHeight = length + radius * 2
        this.scale(1, fullHeight / (radius * 2), 1)
      }
    }
  }
  return THREE
}

export function loadThree(): Promise<any> {
  if (window.THREE) return Promise.resolve(normalizeRuntime(window.THREE))
  if (loader) return loader
  loader = new Promise((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(`script[src="${THREE_CDN}"]`)
    const script = existing || document.createElement('script')
    const onLoad = () => window.THREE
      ? resolve(normalizeRuntime(window.THREE))
      : reject(new Error('Three.js 未正确加载'))
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
