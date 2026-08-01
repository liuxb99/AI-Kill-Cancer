import { useEffect, useRef, useState } from 'react'

import type { PTCLatestCase } from '../api/ptcVisualization'
import { loadThree } from './threeRuntime'

interface Props {
  selectedCase: PTCLatestCase | null
  onSelectGene: (gene: string) => void
}

type LayerKey = 'membrane' | 'nucleus' | 'mitochondria' | 'endoplasmic' | 'golgi' | 'lysosomes' | 'ribosomes' | 'cytoskeleton' | 'mutations'

const LAYERS: Array<{ key: LayerKey; label: string }> = [
  { key: 'membrane', label: '细胞膜' },
  { key: 'nucleus', label: '细胞核／染色质' },
  { key: 'mitochondria', label: '粒线体' },
  { key: 'endoplasmic', label: '内质网' },
  { key: 'golgi', label: '高尔基体' },
  { key: 'lysosomes', label: '溶酶体' },
  { key: 'ribosomes', label: '核糖体' },
  { key: 'cytoskeleton', label: '细胞骨架' },
  { key: 'mutations', label: '突变讯号' },
]

const GENE_COLORS: Record<string, number> = {
  BRAF: 0xf97316, RET: 0x38bdf8, NTRK1: 0xa78bfa, NTRK2: 0x8b5cf6, NTRK3: 0x7c3aed,
  TERT: 0xf43f5e, NRAS: 0x34d399, HRAS: 0x10b981, KRAS: 0x059669, TP53: 0xfacc15,
  AKT1: 0x22d3ee, PIK3CA: 0xe879f9, EGFR: 0xfb7185,
}

function allVisible(): Record<LayerKey, boolean> {
  return Object.fromEntries(LAYERS.map(({ key }) => [key, true])) as Record<LayerKey, boolean>
}

export default function PTCCell3D({ selectedCase, onSelectGene }: Props) {
  const hostRef = useRef<HTMLDivElement | null>(null)
  const callbackRef = useRef(onSelectGene)
  const groupsRef = useRef<Partial<Record<LayerKey, any>>>({})
  const [selectedPart, setSelectedPart] = useState('癌细胞整体')
  const [visibility, setVisibility] = useState<Record<LayerKey, boolean>>(allVisible)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    callbackRef.current = onSelectGene
  }, [onSelectGene])

  useEffect(() => {
    LAYERS.forEach(({ key }) => {
      const group = groupsRef.current[key]
      if (group) group.visible = visibility[key]
    })
  }, [visibility])

  useEffect(() => {
    const host = hostRef.current
    if (!host) return
    let disposed = false
    let cleanup = () => undefined

    void loadThree().then((THREE) => {
      if (disposed || !hostRef.current) return
      setError(null)
      const width = Math.max(host.clientWidth, 320)
      const height = Math.max(host.clientHeight, 560)
      const scene = new THREE.Scene()
      scene.background = new THREE.Color(0x030712)
      scene.fog = new THREE.FogExp2(0x030712, 0.015)

      const camera = new THREE.PerspectiveCamera(48, width / height, 0.1, 1000)
      camera.position.set(0, 0, 34)
      const renderer = new THREE.WebGLRenderer({ antialias: true })
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
      renderer.setSize(width, height)
      host.replaceChildren(renderer.domElement)

      scene.add(new THREE.AmbientLight(0xffffff, 1.2))
      const keyLight = new THREE.PointLight(0x67e8f9, 95, 120)
      keyLight.position.set(14, 18, 28)
      scene.add(keyLight)
      const fillLight = new THREE.PointLight(0xf472b6, 55, 100)
      fillLight.position.set(-18, -10, 16)
      scene.add(fillLight)

      const cell = new THREE.Group()
      scene.add(cell)
      const groups = {} as Record<LayerKey, any>
      LAYERS.forEach(({ key }) => {
        groups[key] = new THREE.Group()
        groups[key].visible = visibility[key]
        cell.add(groups[key])
      })
      groupsRef.current = groups
      const interactive: any[] = []

      function register(object: any, label: string, kind = 'organelle', gene?: string) {
        object.userData = { label, kind, gene }
        interactive.push(object)
        return object
      }

      const membrane = register(new THREE.Mesh(
        new THREE.SphereGeometry(10.8, 64, 48),
        new THREE.MeshPhysicalMaterial({ color: 0x0891b2, transparent: true, opacity: 0.2, roughness: 0.22, transmission: 0.35, side: THREE.DoubleSide }),
      ), '癌细胞膜')
      membrane.scale.set(1.14, 0.92, 1)
      groups.membrane.add(membrane)

      for (let i = 0; i < 28; i += 1) {
        const phi = Math.acos(1 - 2 * ((i + 0.5) / 28))
        const theta = Math.PI * (1 + Math.sqrt(5)) * i
        const receptor = new THREE.Mesh(new THREE.ConeGeometry(0.14, 0.85, 8), new THREE.MeshStandardMaterial({ color: 0x22d3ee }))
        receptor.position.set(Math.sin(phi) * Math.cos(theta) * 11.4, Math.cos(phi) * 9.8, Math.sin(phi) * Math.sin(theta) * 10.8)
        receptor.lookAt(0, 0, 0)
        receptor.rotateX(Math.PI / 2)
        groups.membrane.add(receptor)
      }

      const nucleus = register(new THREE.Mesh(
        new THREE.SphereGeometry(4.5, 48, 36),
        new THREE.MeshPhysicalMaterial({ color: 0x7c3aed, emissive: 0x4c1d95, emissiveIntensity: 0.3, transparent: true, opacity: 0.78, roughness: 0.38 }),
      ), '细胞核／基因组')
      nucleus.position.set(-0.8, 0.2, 0)
      nucleus.scale.set(1, 0.92, 1.08)
      groups.nucleus.add(nucleus)

      const nucleolus = register(new THREE.Mesh(
        new THREE.SphereGeometry(1.2, 32, 24),
        new THREE.MeshStandardMaterial({ color: 0xf472b6, emissive: 0x831843, emissiveIntensity: 0.5 }),
      ), '核仁')
      nucleolus.position.set(-1.5, 0.7, 1.2)
      groups.nucleus.add(nucleolus)

      const chromatinMaterial = new THREE.LineBasicMaterial({ color: 0xf9a8d4, transparent: true, opacity: 0.48 })
      for (let strand = 0; strand < 10; strand += 1) {
        const points = Array.from({ length: 70 }, (_, index) => {
          const t = index / 69
          const angle = t * Math.PI * 5 + strand * 0.62
          const radius = 2.3 + 0.55 * Math.sin(t * Math.PI * 3 + strand)
          return new THREE.Vector3(-0.8 + Math.cos(angle) * radius, 0.2 + (t - 0.5) * 5.8, Math.sin(angle) * radius * 0.72)
        })
        groups.nucleus.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(points), chromatinMaterial))
      }

      const mitoMaterial = new THREE.MeshStandardMaterial({ color: 0xf59e0b, emissive: 0x92400e, emissiveIntensity: 0.3 })
      for (let i = 0; i < 10; i += 1) {
        const angle = (i / 10) * Math.PI * 2
        const mito = register(new THREE.Mesh(new THREE.SphereGeometry(0.85, 24, 16), mitoMaterial), `粒线体 ${i + 1}`)
        mito.scale.set(2.35, 0.72, 0.9)
        mito.position.set(Math.cos(angle) * 7.1, Math.sin(angle) * 5.5, (i % 4 - 1.5) * 2.25)
        mito.rotation.z = angle + Math.PI / 2
        groups.mitochondria.add(mito)
      }

      const erMaterial = new THREE.MeshStandardMaterial({ color: 0x60a5fa, transparent: true, opacity: 0.58 })
      for (let i = 0; i < 6; i += 1) {
        const er = register(new THREE.Mesh(new THREE.TorusGeometry(5 + i * 0.45, 0.09, 12, 96), erMaterial), '内质网')
        er.rotation.set(Math.PI / 2.8 + i * 0.14, i * 0.38, i * 0.18)
        groups.endoplasmic.add(er)
      }

      const golgiMaterial = new THREE.MeshStandardMaterial({ color: 0xfb7185, transparent: true, opacity: 0.82 })
      for (let i = 0; i < 6; i += 1) {
        const cisterna = register(new THREE.Mesh(new THREE.TorusGeometry(2.1 + i * 0.18, 0.16, 10, 48, Math.PI * 1.45), golgiMaterial), '高尔基体')
        cisterna.position.set(4.8, -1.2 + i * 0.42, 1.4)
        cisterna.rotation.set(0.4, 0.45, -0.35)
        groups.golgi.add(cisterna)
      }

      const lysosomeMaterial = new THREE.MeshStandardMaterial({ color: 0x84cc16, emissive: 0x365314, emissiveIntensity: 0.38 })
      for (let i = 0; i < 14; i += 1) {
        const angle = i * 2.39996
        const lysosome = register(new THREE.Mesh(new THREE.SphereGeometry(0.34 + (i % 3) * 0.08, 18, 14), lysosomeMaterial), `溶酶体 ${i + 1}`)
        lysosome.position.set(Math.cos(angle) * (5.8 + (i % 4)), Math.sin(angle) * (4 + (i % 3)), (i % 5 - 2) * 1.45)
        groups.lysosomes.add(lysosome)
      }

      const ribosomes = register(new THREE.InstancedMesh(
        new THREE.SphereGeometry(0.105, 8, 6),
        new THREE.MeshBasicMaterial({ color: 0xe2e8f0 }),
        120,
      ), '核糖体群')
      const dummy = new THREE.Object3D()
      for (let i = 0; i < 120; i += 1) {
        const phi = Math.acos(1 - 2 * ((i + 0.5) / 120))
        const theta = Math.PI * (1 + Math.sqrt(5)) * i
        const radius = 5.2 + (i % 7) * 0.55
        dummy.position.set(Math.sin(phi) * Math.cos(theta) * radius, Math.cos(phi) * radius * 0.78, Math.sin(phi) * Math.sin(theta) * radius)
        dummy.updateMatrix()
        ribosomes.setMatrixAt(i, dummy.matrix)
      }
      groups.ribosomes.add(ribosomes)

      const microtubuleMaterial = new THREE.LineBasicMaterial({ color: 0x22d3ee, transparent: true, opacity: 0.45 })
      for (let i = 0; i < 22; i += 1) {
        const angle = (i / 22) * Math.PI * 2
        groups.cytoskeleton.add(new THREE.Line(
          new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, 0, 0), new THREE.Vector3(Math.cos(angle) * 9.2, Math.sin(angle) * 7.1, (i % 5 - 2) * 1.4)]),
          microtubuleMaterial,
        ))
      }

      const genes = Array.from(new Set((selectedCase?.variants || []).map((item) => item.gene.toUpperCase()))).slice(0, 18)
      genes.forEach((gene, index) => {
        const angle = (index / Math.max(genes.length, 1)) * Math.PI * 2
        const radius = 5.8 + (index % 2) * 1.4
        const beacon = register(new THREE.Mesh(
          new THREE.SphereGeometry(0.46, 24, 18),
          new THREE.MeshStandardMaterial({ color: GENE_COLORS[gene] ?? 0xf8fafc, emissive: GENE_COLORS[gene] ?? 0xf8fafc, emissiveIntensity: 1.35 }),
        ), `${gene} 突变讯号`, 'gene', gene)
        beacon.position.set(Math.cos(angle) * radius, Math.sin(angle) * radius * 0.72, (index % 4 - 1.5) * 1.5)
        groups.mutations.add(beacon)
      })

      const raycaster = new THREE.Raycaster()
      const pointer = new THREE.Vector2()
      let dragging = false
      let previousX = 0
      let previousY = 0
      let frame = 0

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
        if (renderer.domElement.hasPointerCapture(event.pointerId)) renderer.domElement.releasePointerCapture(event.pointerId)
      }
      const wheel = (event: WheelEvent) => {
        event.preventDefault()
        camera.position.z = Math.min(62, Math.max(14, camera.position.z + event.deltaY * 0.025))
      }
      const click = (event: MouseEvent) => {
        const rect = renderer.domElement.getBoundingClientRect()
        pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
        pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1
        raycaster.setFromCamera(pointer, camera)
        const hit = raycaster.intersectObjects(interactive, false)[0]
        if (!hit?.object?.userData) return
        setSelectedPart(hit.object.userData.label)
        if (hit.object.userData.kind === 'gene' && hit.object.userData.gene) callbackRef.current(hit.object.userData.gene)
        else camera.position.z = Math.max(15, camera.position.z - 4)
      }
      const resize = () => {
        const nextWidth = Math.max(host.clientWidth, 320)
        const nextHeight = Math.max(host.clientHeight, 560)
        camera.aspect = nextWidth / nextHeight
        camera.updateProjectionMatrix()
        renderer.setSize(nextWidth, nextHeight)
      }

      renderer.domElement.addEventListener('pointerdown', down)
      renderer.domElement.addEventListener('pointermove', move)
      renderer.domElement.addEventListener('pointerup', up)
      renderer.domElement.addEventListener('pointercancel', up)
      renderer.domElement.addEventListener('wheel', wheel, { passive: false })
      renderer.domElement.addEventListener('click', click)
      window.addEventListener('resize', resize)

      const animate = () => {
        frame = requestAnimationFrame(animate)
        if (!dragging) cell.rotation.y += 0.0012
        groups.mutations.scale.setScalar(1 + Math.sin(performance.now() * 0.004) * 0.06)
        renderer.render(scene, camera)
      }
      animate()

      cleanup = () => {
        cancelAnimationFrame(frame)
        window.removeEventListener('resize', resize)
        renderer.domElement.removeEventListener('pointerdown', down)
        renderer.domElement.removeEventListener('pointermove', move)
        renderer.domElement.removeEventListener('pointerup', up)
        renderer.domElement.removeEventListener('pointercancel', up)
        renderer.domElement.removeEventListener('wheel', wheel)
        renderer.domElement.removeEventListener('click', click)
        cell.traverse((object: any) => {
          object.geometry?.dispose?.()
          if (Array.isArray(object.material)) object.material.forEach((item: any) => item.dispose?.())
          else object.material?.dispose?.()
        })
        renderer.dispose()
        groupsRef.current = {}
        host.replaceChildren()
      }
    }).catch((reason) => {
      if (!disposed) setError(reason instanceof Error ? reason.message : '无法建立癌细胞 3D 模型')
    })

    return () => {
      disposed = true
      cleanup()
    }
  }, [selectedCase])

  return (
    <div className="relative overflow-hidden rounded-xl border border-slate-700 bg-slate-950 shadow-xl">
      <div ref={hostRef} className="h-[680px] w-full" aria-label="PTC cancer cell multiscale 3D model" />
      <div className="absolute left-3 top-3 max-w-md rounded bg-slate-900/90 p-3 text-xs text-slate-200 backdrop-blur">
        <div className="font-semibold text-cyan-200">癌细胞多尺度超微结构</div>
        <p className="mt-1 text-slate-300">拖曳旋转、滚轮缩放、点击细胞器；点击发光突变点进入蛋白结构。</p>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {LAYERS.map((layer) => (
            <button
              key={layer.key}
              className={`rounded px-2 py-1 transition ${visibility[layer.key] ? 'bg-cyan-500 text-slate-950' : 'bg-slate-700 text-slate-300'}`}
              onClick={() => setVisibility((current) => ({ ...current, [layer.key]: !current[layer.key] }))}
            >
              {layer.label}
            </button>
          ))}
          <button className="rounded bg-white px-2 py-1 text-slate-900" onClick={() => { setVisibility(allVisible()); setSelectedPart('癌细胞整体') }}>全部显示</button>
        </div>
      </div>
      <div className="absolute bottom-3 left-3 rounded bg-slate-900/90 px-3 py-2 text-sm text-white backdrop-blur">当前：{selectedPart}</div>
      <div className="pointer-events-none absolute bottom-3 right-3 max-w-sm rounded bg-amber-950/80 px-3 py-2 text-xs text-amber-100 backdrop-blur">
        科学示意模型，不是患者真实细胞的显微或原子级重建；病例资料只用于驱动突变讯号层。
      </div>
      {error && <div className="absolute inset-0 grid place-items-center bg-slate-950/90 p-8 text-center text-red-300">{error}</div>}
    </div>
  )
}
