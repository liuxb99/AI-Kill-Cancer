import { useEffect, useMemo, useRef, useState } from 'react'

import type { PTCProteinStructure } from '../api/ptcVisualization'
import type { PTCVariant } from '../api/ptcResearch'
import { loadThree } from './threeRuntime'

interface Props {
  structure: PTCProteinStructure | null
  variants?: PTCVariant[]
  loading?: boolean
}

interface MutationResidue {
  key: string
  label: string
  residue: number
}

interface ParsedAtom {
  atomName: string
  residueName: string
  residue: number
  chain: string
  x: number
  y: number
  z: number
  element: string
  confidence: number
}

interface StructureSource {
  key: string
  label: string
  urls: string[]
  alphafold: boolean
}

const ELEMENT_COLORS: Record<string, number> = {
  C: 0x94a3b8,
  N: 0x3b82f6,
  O: 0xef4444,
  S: 0xfacc15,
  P: 0xf97316,
  H: 0xf8fafc,
  FE: 0xb45309,
  MG: 0x22c55e,
  ZN: 0x8b5cf6,
}

const ELEMENT_RADII: Record<string, number> = {
  H: 0.22,
  C: 0.36,
  N: 0.34,
  O: 0.33,
  S: 0.44,
  P: 0.42,
  FE: 0.46,
  MG: 0.45,
  ZN: 0.45,
}

function residueNumber(proteinChange?: string): number | null {
  if (!proteinChange) return null
  const match = proteinChange.match(/(?:p\.)?[A-Za-z*]+(\d+)/)
  return match ? Number(match[1]) : null
}

export function parsePdb(text: string): ParsedAtom[] {
  const atoms: ParsedAtom[] = []
  for (const line of text.split(/\r?\n/)) {
    if (!line.startsWith('ATOM  ') && !line.startsWith('HETATM')) continue
    const x = Number(line.slice(30, 38).trim())
    const y = Number(line.slice(38, 46).trim())
    const z = Number(line.slice(46, 54).trim())
    const residue = Number(line.slice(22, 26).trim())
    if (![x, y, z, residue].every(Number.isFinite)) continue
    const atomName = line.slice(12, 16).trim()
    const inferredElement = atomName.replace(/[0-9]/g, '').slice(0, 2).trim().toUpperCase()
    const element = (line.slice(76, 78).trim() || inferredElement || 'C').toUpperCase()
    atoms.push({
      atomName,
      residueName: line.slice(17, 20).trim(),
      residue,
      chain: line.slice(21, 22).trim() || 'A',
      x,
      y,
      z,
      element,
      confidence: Number(line.slice(60, 66).trim()) || 0,
    })
  }
  return atoms
}

function confidenceColor(confidence: number): number {
  if (confidence >= 90) return 0x0053d6
  if (confidence >= 70) return 0x65cbf3
  if (confidence >= 50) return 0xffdb13
  return 0xff7d45
}

function centerOfAtoms(atoms: ParsedAtom[]): { x: number; y: number; z: number } {
  if (atoms.length === 0) return { x: 0, y: 0, z: 0 }
  const sum = atoms.reduce(
    (value, atom) => ({ x: value.x + atom.x, y: value.y + atom.y, z: value.z + atom.z }),
    { x: 0, y: 0, z: 0 },
  )
  return { x: sum.x / atoms.length, y: sum.y / atoms.length, z: sum.z / atoms.length }
}

async function fetchFirstStructure(urls: string[], signal: AbortSignal): Promise<{ text: string; url: string }> {
  const failures: string[] = []
  for (const url of urls) {
    try {
      const response = await fetch(url, { signal })
      if (response.ok) return { text: await response.text(), url }
      failures.push(`${url} (HTTP ${response.status})`)
    } catch (reason) {
      if ((reason as Error)?.name === 'AbortError') throw reason
      failures.push(`${url} (${reason instanceof Error ? reason.message : 'network error'})`)
    }
  }
  throw new Error(`所有静态结构文件均无法下载：${failures.join('；')}`)
}

export default function PTCProtein3D({ structure, variants = [], loading }: Props) {
  const hostRef = useRef<HTMLDivElement | null>(null)
  const focusRef = useRef<(residue: number | null) => void>(() => undefined)
  const [sourceKey, setSourceKey] = useState('alphafold')
  const [activeFileUrl, setActiveFileUrl] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [viewerReady, setViewerReady] = useState(false)
  const [focusedResidue, setFocusedResidue] = useState<number | null>(null)
  const [atomCount, setAtomCount] = useState(0)
  const [residueCount, setResidueCount] = useState(0)
  const [downloadProgress, setDownloadProgress] = useState('')

  const geneVariants = useMemo(
    () => structure
      ? variants.filter((item) => item.gene.toUpperCase() === structure.gene.toUpperCase())
      : [],
    [structure, variants],
  )

  const mutationResidues = useMemo<MutationResidue[]>(() => {
    const seen = new Set<number>()
    return geneVariants.flatMap((variant) => {
      const residue = residueNumber(variant.protein_change)
      if (!residue || seen.has(residue)) return []
      seen.add(residue)
      return [{
        key: variant.variant_id || `${variant.gene}:${residue}`,
        label: variant.protein_change || `${variant.gene} residue ${residue}`,
        residue,
      }]
    })
  }, [geneVariants])

  const sources = useMemo<StructureSource[]>(() => {
    if (!structure) return []
    return [
      { key: 'alphafold', label: 'AlphaFold 全长预测', urls: structure.pdb_urls, alphafold: true },
      ...structure.experimental_structures.map((item) => ({
        key: item.pdb_id,
        label: `PDB ${item.pdb_id}`,
        urls: [item.pdb_url],
        alphafold: false,
      })),
    ]
  }, [structure])

  const selectedSource = sources.find((item) => item.key === sourceKey) || sources[0]

  useEffect(() => {
    setSourceKey('alphafold')
    setFocusedResidue(null)
    setActiveFileUrl(null)
    setError(null)
  }, [structure])

  useEffect(() => {
    const host = hostRef.current
    if (!host || !structure || !selectedSource) return
    const controller = new AbortController()
    let disposed = false
    let cleanup = () => undefined
    setViewerReady(false)
    setError(null)
    setActiveFileUrl(null)
    setDownloadProgress('下载静态结构坐标…')

    void Promise.all([
      loadThree(),
      fetchFirstStructure(selectedSource.urls, controller.signal),
    ]).then(([THREE, structureFile]) => {
      if (disposed || !hostRef.current) return
      const atoms = parsePdb(structureFile.text)
      if (atoms.length === 0) throw new Error('结构文件中没有可显示的原子坐标')
      setActiveFileUrl(structureFile.url)
      setDownloadProgress('')
      setAtomCount(atoms.length)
      setResidueCount(new Set(atoms.map((atom) => `${atom.chain}:${atom.residue}`)).size)

      const width = Math.max(host.clientWidth, 320)
      const height = Math.max(host.clientHeight, 560)
      const scene = new THREE.Scene()
      scene.background = new THREE.Color(0x020617)
      scene.fog = new THREE.FogExp2(0x020617, 0.008)
      const camera = new THREE.PerspectiveCamera(44, width / height, 0.1, 3000)
      camera.position.set(0, 0, 95)
      const renderer = new THREE.WebGLRenderer({ antialias: true })
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
      renderer.setSize(width, height)
      host.replaceChildren(renderer.domElement)

      scene.add(new THREE.AmbientLight(0xffffff, 1.15))
      const keyLight = new THREE.DirectionalLight(0xffffff, 2.2)
      keyLight.position.set(30, 40, 60)
      scene.add(keyLight)
      const fillLight = new THREE.PointLight(0x38bdf8, 80, 250)
      fillLight.position.set(-40, -30, 50)
      scene.add(fillLight)

      const model = new THREE.Group()
      scene.add(model)
      const center = centerOfAtoms(atoms)
      const centered = atoms.map((atom) => ({ ...atom, x: atom.x - center.x, y: atom.y - center.y, z: atom.z - center.z }))
      const mutationSet = new Set(mutationResidues.map((item) => item.residue))

      const sphere = new THREE.SphereGeometry(1, 10, 8)
      const material = new THREE.MeshPhongMaterial({ vertexColors: true, shininess: 38 })
      const atomMesh = new THREE.InstancedMesh(sphere, material, centered.length)
      const dummy = new THREE.Object3D()
      const color = new THREE.Color()
      centered.forEach((atom, index) => {
        const highlighted = mutationSet.has(atom.residue)
        const radius = (ELEMENT_RADII[atom.element] || 0.36) * (highlighted ? 2.1 : 1)
        dummy.position.set(atom.x, atom.y, atom.z)
        dummy.scale.setScalar(radius)
        dummy.updateMatrix()
        atomMesh.setMatrixAt(index, dummy.matrix)
        color.setHex(highlighted
          ? 0xf97316
          : selectedSource.alphafold
            ? confidenceColor(atom.confidence)
            : (ELEMENT_COLORS[atom.element] || 0xa8a29e))
        atomMesh.setColorAt(index, color)
      })
      atomMesh.instanceMatrix.needsUpdate = true
      if (atomMesh.instanceColor) atomMesh.instanceColor.needsUpdate = true
      model.add(atomMesh)

      const caByChain = new Map<string, ParsedAtom[]>()
      centered.filter((atom) => atom.atomName === 'CA').forEach((atom) => {
        const values = caByChain.get(atom.chain) || []
        values.push(atom)
        caByChain.set(atom.chain, values)
      })
      caByChain.forEach((chainAtoms) => {
        chainAtoms.sort((a, b) => a.residue - b.residue)
        const points = chainAtoms.map((atom) => new THREE.Vector3(atom.x, atom.y, atom.z))
        if (points.length > 1) {
          model.add(new THREE.Line(
            new THREE.BufferGeometry().setFromPoints(points),
            new THREE.LineBasicMaterial({ color: selectedSource.alphafold ? 0xe2e8f0 : 0x67e8f9, transparent: true, opacity: 0.72 }),
          ))
        }
      })

      const focusResidue = (residue: number | null) => {
        const targets = residue === null ? centered : centered.filter((atom) => atom.residue === residue)
        if (targets.length === 0) {
          setError(`当前结构不包含 residue ${residue}；请切换到 AlphaFold 全长结构。`)
          return
        }
        setError(null)
        const target = centerOfAtoms(targets)
        model.position.set(-target.x, -target.y, -target.z)
        camera.position.set(0, 0, residue === null ? 95 : 24)
        camera.lookAt(0, 0, 0)
        setFocusedResidue(residue)
      }
      focusRef.current = focusResidue
      focusResidue(mutationResidues[0]?.residue ?? null)

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
        model.rotation.y += (event.clientX - previousX) * 0.006
        model.rotation.x += (event.clientY - previousY) * 0.004
        previousX = event.clientX
        previousY = event.clientY
      }
      const up = (event: PointerEvent) => {
        dragging = false
        if (renderer.domElement.hasPointerCapture(event.pointerId)) renderer.domElement.releasePointerCapture(event.pointerId)
      }
      const wheel = (event: WheelEvent) => {
        event.preventDefault()
        camera.position.z = Math.min(260, Math.max(8, camera.position.z + event.deltaY * 0.06))
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
      renderer.domElement.addEventListener('wheel', wheel, { passive: false })
      window.addEventListener('resize', resize)

      const animate = () => {
        frame = requestAnimationFrame(animate)
        if (!dragging) model.rotation.y += 0.0008
        renderer.render(scene, camera)
      }
      animate()
      setViewerReady(true)

      cleanup = () => {
        cancelAnimationFrame(frame)
        window.removeEventListener('resize', resize)
        renderer.domElement.removeEventListener('pointerdown', down)
        renderer.domElement.removeEventListener('pointermove', move)
        renderer.domElement.removeEventListener('pointerup', up)
        renderer.domElement.removeEventListener('wheel', wheel)
        model.traverse((object: any) => {
          object.geometry?.dispose?.()
          if (Array.isArray(object.material)) object.material.forEach((item: any) => item.dispose?.())
          else object.material?.dispose?.()
        })
        renderer.dispose()
        host.replaceChildren()
      }
    }).catch((reason) => {
      if (!disposed && (reason as Error)?.name !== 'AbortError') {
        setDownloadProgress('')
        setError(reason instanceof Error ? reason.message : '无法载入蛋白质结构')
      }
    })

    return () => {
      disposed = true
      controller.abort()
      setViewerReady(false)
      focusRef.current = () => undefined
      cleanup()
    }
  }, [structure, selectedSource, mutationResidues])

  if (loading) {
    return <div className="grid h-[620px] place-items-center rounded-xl border bg-slate-950 text-slate-300">蛋白结构载入中…</div>
  }
  if (!structure) {
    return <div className="grid h-[620px] place-items-center rounded-xl border bg-slate-950 p-8 text-center text-slate-300">点击病例中的基因或癌细胞发光突变点，载入内建蛋白结构查看器。</div>
  }

  return (
    <section className="overflow-hidden rounded-xl border border-slate-700 bg-slate-950 shadow-xl">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-700 bg-slate-900 px-4 py-3 text-white">
        <div>
          <h3 className="font-bold">{structure.gene} · {structure.name}</h3>
          <p className="text-xs text-slate-400">内建 Three.js PDB Renderer · UniProt {structure.uniprot}</p>
        </div>
        <div className="flex flex-wrap gap-2 text-xs">
          {sources.map((source) => (
            <button
              key={source.key}
              className={`rounded px-3 py-1.5 ${sourceKey === source.key ? 'bg-cyan-400 text-slate-950' : 'bg-slate-700'}`}
              onClick={() => setSourceKey(source.key)}
            >
              {source.label}
            </button>
          ))}
          <button className="rounded bg-slate-700 px-3 py-1.5" onClick={() => focusRef.current(null)} disabled={!viewerReady}>重置全结构</button>
        </div>
      </div>

      {mutationResidues.length > 0 && (
        <div className="border-b border-slate-700 bg-amber-950/50 px-4 py-3 text-xs text-amber-100">
          <div className="font-semibold">当前病例的 {structure.gene} 突变残基</div>
          <div className="mt-2 flex flex-wrap gap-2">
            {mutationResidues.map((item) => (
              <button
                key={item.key}
                className={`rounded-full border px-3 py-1 transition ${focusedResidue === item.residue ? 'border-orange-300 bg-orange-500 text-slate-950' : 'border-amber-500/50 bg-amber-900/50 hover:bg-amber-800/70'}`}
                onClick={() => focusRef.current(item.residue)}
                disabled={!viewerReady}
              >
                {item.label} · residue {item.residue} · 聚焦
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="relative">
        <div ref={hostRef} className="h-[620px] w-full" aria-label={`${structure.gene} built-in protein 3D structure`} />
        {downloadProgress && <div className="absolute inset-0 grid place-items-center bg-slate-950/85 text-slate-200">{downloadProgress}</div>}
        <div className="pointer-events-none absolute bottom-3 left-3 rounded bg-slate-900/85 px-3 py-2 text-xs text-slate-200">
          {atomCount.toLocaleString()} atoms · {residueCount.toLocaleString()} residues · 拖曳旋转 · 滚轮缩放
        </div>
      </div>

      {error && (
        <div className="border-t border-red-700 bg-red-950/70 p-4 text-sm text-red-100">
          {error}
          <div className="mt-2 flex flex-wrap gap-2">
            {activeFileUrl && <a className="rounded bg-slate-700 px-3 py-1.5" href={activeFileUrl} target="_blank" rel="noreferrer">下载当前 PDB 文件</a>}
            <a className="rounded bg-cyan-700 px-3 py-1.5" href={structure.alphafold_entry_url} target="_blank" rel="noreferrer">查看 AlphaFold 来源页</a>
          </div>
        </div>
      )}

      <div className="border-t border-slate-700 bg-slate-900 px-4 py-3 text-xs text-slate-300">
        <p>全部解析、原子绘制、可信度着色与突变聚焦均由项目内建代码完成；不调用 AlphaFold API，不加载 Mol*。</p>
        <p className="mt-1 text-amber-300">{structure.disclaimer}</p>
      </div>
    </section>
  )
}
