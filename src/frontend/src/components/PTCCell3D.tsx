import { useEffect, useRef, useState } from 'react'

import type { PTCLatestCase } from '../api/ptcVisualization'
import { loadThree } from './threeRuntime'

interface Props {
  selectedCase: PTCLatestCase | null
  onSelectGene: (gene: string) => void
}

const GENE_COLORS: Record<string, number> = {
  BRAF: 0xf97316,
  RET: 0x38bdf8,
  NTRK1: 0xa78bfa,
  NTRK2: 0x8b5cf6,
  NTRK3: 0x7c3aed,
  TERT: 0xf43f5e,
  NRAS: 0x34d399,
  HRAS: 0x10b981,
  KRAS: 0x059669,
  TP53: 0xfacc15,
  AKT1: 0x22d3ee,
  PIK3CA: 0xe879f9,
  EGFR: 0xfb7185,
}

export default function PTCCell3D({ selectedCase, onSelectGene }: Props) {
  const hostRef = useRef<HTMLDivElement | null>(null)
  const [selectedPart, setSelectedPart] = useState('癌细胞整体')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const host = hostRef.current
    if (!host) return
    let disposed = false
    let cleanup = () => undefined

    void loadThree().then((THREE) => {
      if (disposed || !hostRef.current) return
      setError(null)
      const container = hostRef.current
      const width = Math.max(container.clientWidth, 320)
      const height = Math.max(container.clientHeight, 560)
      const scene = new THREE.Scene()
      scene.background = new THREE.Color(0x030712)
      scene.fog = new THREE.FogExp2(0x030712, 0.018)

      const camera = new THREE.PerspectiveCamera(48, width / height, 0.1, 1000)
      camera.position.set(0, 0, 34)
      const renderer = new THREE.WebGLRenderer({ antialias: true })
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
      renderer.setSize(width, height)
      container.replaceChildren(renderer.domElement)

      scene.add(new THREE.AmbientLight(0xffffff, 1.25))
      const light = new THREE.PointLight(0x67e8f9, 95, 120)
      light.position.set(14, 18, 28)
      scene.add(light)

      const cell = new THREE.Group()
      scene.add(cell)
      const interactive: any[] = []

      const membrane = new THREE.Mesh(
        new THREE.SphereGeometry(10.8, 64, 48),
        new THREE.MeshPhysicalMaterial({
          color: 0x0891b2,
          transparent: true,
          opacity: 0.2,
          roughness: 0.22,
          transmission: 0.35,
          side: THREE.DoubleSide,
        }),
      )
      membrane.scale.set(1.14, 0.92, 1)
      membrane.userData = { label: '癌细胞膜', kind: 'organelle' }
      cell.add(membrane)
      interactive.push(membrane)

      const nucleus = new THREE.Mesh(
        new THREE.SphereGeometry(4.5, 48, 36),
        new THREE.MeshStandardMaterial({ color: 0x7c3aed, emissive: 0x4c1d95, emissiveIntensity: 0.36, roughness: 0.4 }),
      )
      nucleus.position.set(-0.8, 0.2, 0)
      nucleus.scale.set(1, 0.92, 1.08)
      nucleus.userData = { label: '细胞核／基因组', kind: 'organelle' }
      cell.add(nucleus)
      interactive.push(nucleus)

      const nucleolus = new THREE.Mesh(
        new THREE.SphereGeometry(1.2, 32, 24),
        new THREE.MeshStandardMaterial({ color: 0xf472b6, emissive: 0x831843, emissiveIntensity: 0.4 }),
      )
      nucleolus.position.set(-1.5, 0.7, 1.2)
      nucleolus.userData = { label: '核仁', kind: 'organelle' }
      cell.add(nucleolus)
      interactive.push(nucleolus)

      const mitochondrialMaterial = new THREE.MeshStandardMaterial({ color: 0xf59e0b, emissive: 0x92400e, emissiveIntensity: 0.28 })
      for (let i = 0; i < 8; i += 1) {
        const angle = (i / 8) * Math.PI * 2
        const mitochondrion = new THREE.Mesh(new THREE.CapsuleGeometry(0.55, 2.2, 8, 18), mitochondrialMaterial)
        mitochondrion.position.set(Math.cos(angle) * 7.1, Math.sin(angle) * 5.6, (i % 3 - 1) * 2.4)
        mitochondrion.rotation.z = angle + Math.PI / 2
        mitochondrion.userData = { label: `粒线体 ${i + 1}`, kind: 'organelle' }
        cell.add(mitochondrion)
        interactive.push(mitochondrion)
      }

      const erMaterial = new THREE.MeshStandardMaterial({ color: 0x60a5fa, transparent: true, opacity: 0.58 })
      for (let i = 0; i < 4; i += 1) {
        const er = new THREE.Mesh(new THREE.TorusGeometry(5.2 + i * 0.55, 0.09, 12, 96), erMaterial)
        er.rotation.set(Math.PI / 2.8 + i * 0.18, i * 0.4, i * 0.2)
        er.userData = { label: '内质网', kind: 'organelle' }
        cell.add(er)
        interactive.push(er)
      }

      const microtubuleMaterial = new THREE.LineBasicMaterial({ color: 0x22d3ee, transparent: true, opacity: 0.45 })
      for (let i = 0; i < 18; i += 1) {
        const angle = (i / 18) * Math.PI * 2
        const points = [
          new THREE.Vector3(0, 0, 0),
          new THREE.Vector3(Math.cos(angle) * 9, Math.sin(angle) * 7, (i % 5 - 2) * 1.4),
        ]
        cell.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(points), microtubuleMaterial))
      }

      const genes = Array.from(new Set((selectedCase?.variants || []).map((item) => item.gene.toUpperCase()))).slice(0, 18)
      genes.forEach((gene, index) => {
        const angle = (index / Math.max(genes.length, 1)) * Math.PI * 2
        const radius = 5.8 + (index % 2) * 1.4
        const beacon = new THREE.Mesh(
          new THREE.SphereGeometry(0.46, 24, 18),
          new THREE.MeshStandardMaterial({
            color: GENE_COLORS[gene] ?? 0xf8fafc,
            emissive: GENE_COLORS[gene] ?? 0xf8fafc,
            emissiveIntensity: 1.25,
          }),
        )
        beacon.position.set(Math.cos(angle) * radius, Math.sin(angle) * radius * 0.72, (index % 4 - 1.5) * 1.5)
        beacon.userData = { label: `${gene} 突变讯号`, kind: 'gene', gene }
        cell.add(beacon)
        interactive.push(beacon)
      })

      const raycaster = new THREE.Raycaster()
      const pointer = new THREE.Vector2()
      let dragging = false
      let previousX = 0
      let previousY = 0
      let animation = 0

      const down = (event: PointerEvent) => {
        dragging = true
        previousX = event.clientX
        previousY = event.clientY
        renderer.domElement.setPointerCapture(event.pointerId)
      }
      const move = (event: PointerEvent) => {
        if (!dragging) return
        cell.rotation.y += (event.clientX - previousX) * 0.006
        cell.rotation.x += (event.clientY - previousY) * 0.004
        previousX = event.clientX
        previousY = event.clientY
      }
      const up = (event: PointerEvent) => {
        dragging = false
        renderer.domElement.releasePointerCapture(event.pointerId)
      }
      const wheel = (event: WheelEvent) => {
        event.preventDefault()
        camera.position.z = Math.min(62, Math.max(17, camera.position.z + event.deltaY * 0.025))
      }
      const click = (event: MouseEvent) => {
        const rect = renderer.domElement.getBoundingClientRect()
        pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
        pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1
        raycaster.setFromCamera(pointer, camera)
        const hit = raycaster.intersectObjects(interactive, false)[0]
        if (!hit?.object?.userData) return
        const data = hit.object.userData
        setSelectedPart(data.label)
        if (data.kind === 'gene' && data.gene) onSelectGene(data.gene)
      }
      const resize = () => {
        const nextWidth = Math.max(container.clientWidth, 320)
        const nextHeight = Math.max(container.clientHeight, 560)
        camera.aspect = nextWidth / nextHeight
        camera.updateProjectionMatrix()
        renderer.setSize(nextWidth, nextHeight)
      }

      renderer.domElement.addEventListener('pointerdown', down)
      renderer.domElement.addEventListener('pointermove', move)
      renderer.domElement.addEventListener('pointerup', up)
      renderer.domElement.addEventListener('wheel', wheel, { passive: false })
      renderer.domElement.addEventListener('click', click)
      window.addEventListener('resize', resize)

      const animate = () => {
        animation = requestAnimationFrame(animate)
        if (!dragging) cell.rotation.y += 0.0012
        renderer.render(scene, camera)
      }
      animate()

      cleanup = () => {
        cancelAnimationFrame(animation)
        window.removeEventListener('resize', resize)
        renderer.domElement.removeEventListener('pointerdown', down)
        renderer.domElement.removeEventListener('pointermove', move)
        renderer.domElement.removeEventListener('pointerup', up)
        renderer.domElement.removeEventListener('wheel', wheel)
        renderer.domElement.removeEventListener('click', click)
        cell.traverse((object: any) => {
          object.geometry?.dispose?.()
          if (Array.isArray(object.material)) object.material.forEach((item: any) => item.dispose?.())
          else object.material?.dispose?.()
        })
        renderer.dispose()
        container.replaceChildren()
      }
    }).catch((reason) => {
      if (!disposed) setError(reason instanceof Error ? reason.message : '无法建立癌细胞 3D 模型')
    })

    return () => {
      disposed = true
      cleanup()
    }
  }, [selectedCase, onSelectGene])

  return (
    <div className="relative overflow-hidden rounded-xl border border-slate-700 bg-slate-950 shadow-xl">
      <div ref={hostRef} className="h-[620px] w-full" aria-label="PTC cancer cell multiscale 3D model" />
      <div className="pointer-events-none absolute left-3 top-3 max-w-sm rounded bg-slate-900/85 px-3 py-2 text-xs text-slate-200 backdrop-blur">
        科学示意模型：细胞膜、细胞核、粒线体、内质网、微管与病例突变讯号。拖曳旋转、滚轮缩放、点击发光突变点进入蛋白结构。
      </div>
      <div className="absolute bottom-3 left-3 rounded bg-slate-900/85 px-3 py-2 text-sm text-white backdrop-blur">
        当前：{selectedPart}
      </div>
      {error && <div className="absolute inset-0 grid place-items-center bg-slate-950/90 p-8 text-center text-red-300">{error}</div>}
    </div>
  )
}
