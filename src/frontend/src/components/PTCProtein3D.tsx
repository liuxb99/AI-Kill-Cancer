import { useEffect, useRef, useState } from 'react'

import type { PTCProteinStructure } from '../api/ptcVisualization'

const MOLSTAR_SCRIPT = 'https://cdn.jsdelivr.net/npm/pdbe-molstar@latest/build/pdbe-molstar-component.js'
const MOLSTAR_STYLE = 'https://cdn.jsdelivr.net/npm/pdbe-molstar@latest/build/pdbe-molstar.css'
let loader: Promise<void> | null = null

function loadMolstar(): Promise<void> {
  if (customElements.get('pdbe-molstar')) return Promise.resolve()
  if (loader) return loader
  loader = new Promise((resolve, reject) => {
    if (!document.querySelector(`link[href="${MOLSTAR_STYLE}"]`)) {
      const link = document.createElement('link')
      link.rel = 'stylesheet'
      link.href = MOLSTAR_STYLE
      document.head.appendChild(link)
    }
    const existing = document.querySelector<HTMLScriptElement>(`script[src="${MOLSTAR_SCRIPT}"]`)
    const script = existing || document.createElement('script')
    const loaded = () => customElements.whenDefined('pdbe-molstar').then(() => resolve())
    const failed = () => reject(new Error('PDBe Mol* 载入失败'))
    script.addEventListener('load', loaded, { once: true })
    script.addEventListener('error', failed, { once: true })
    if (!existing) {
      script.src = MOLSTAR_SCRIPT
      script.async = true
      script.crossOrigin = 'anonymous'
      document.head.appendChild(script)
    }
  })
  return loader
}

interface Props {
  structure: PTCProteinStructure | null
  loading?: boolean
}

export default function PTCProtein3D({ structure, loading }: Props) {
  const hostRef = useRef<HTMLDivElement | null>(null)
  const [mode, setMode] = useState<'alphafold' | 'pdb'>('alphafold')
  const [pdbId, setPdbId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setPdbId(structure?.default_pdb_id || null)
    setMode('alphafold')
  }, [structure])

  useEffect(() => {
    const host = hostRef.current
    if (!host || !structure) return
    let disposed = false
    void loadMolstar().then(() => {
      if (disposed || !hostRef.current) return
      setError(null)
      const viewer = document.createElement('pdbe-molstar')
      viewer.setAttribute('hide-controls', 'false')
      viewer.setAttribute('sequence-panel', 'true')
      viewer.setAttribute('landscape', 'true')
      viewer.setAttribute('bg-color-r', '7')
      viewer.setAttribute('bg-color-g', '17')
      viewer.setAttribute('bg-color-b', '31')
      viewer.style.display = 'block'
      viewer.style.width = '100%'
      viewer.style.height = '620px'
      if (mode === 'pdb' && pdbId) {
        viewer.setAttribute('molecule-id', pdbId.toLowerCase())
      } else {
        viewer.setAttribute('custom-data-url', structure.cif_url)
        viewer.setAttribute('custom-data-format', 'cif')
        viewer.setAttribute('alphafold-view', 'true')
      }
      host.replaceChildren(viewer)
    }).catch((reason) => {
      if (!disposed) setError(reason instanceof Error ? reason.message : '无法载入蛋白质 3D 结构')
    })
    return () => {
      disposed = true
      host.replaceChildren()
    }
  }, [structure, mode, pdbId])

  if (loading) {
    return <div className="grid h-[620px] place-items-center rounded-xl border bg-slate-950 text-slate-300">蛋白结构载入中…</div>
  }
  if (!structure) {
    return <div className="grid h-[620px] place-items-center rounded-xl border bg-slate-950 p-8 text-center text-slate-300">点击病例中的基因或癌细胞发光突变点，载入 AlphaFold／PDB 蛋白结构。</div>
  }

  return (
    <section className="overflow-hidden rounded-xl border border-slate-700 bg-slate-950 shadow-xl">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-700 bg-slate-900 px-4 py-3 text-white">
        <div>
          <h3 className="font-bold">{structure.gene} · {structure.name}</h3>
          <p className="text-xs text-slate-400">UniProt {structure.uniprot} · {structure.alphafold_entry_id}</p>
        </div>
        <div className="flex flex-wrap gap-2 text-xs">
          <button
            className={`rounded px-3 py-1.5 ${mode === 'alphafold' ? 'bg-cyan-500 text-slate-950' : 'bg-slate-700'}`}
            onClick={() => setMode('alphafold')}
          >
            AlphaFold 预测
          </button>
          {structure.experimental_pdb_ids.map((id) => (
            <button
              key={id}
              className={`rounded px-3 py-1.5 ${mode === 'pdb' && pdbId === id ? 'bg-emerald-400 text-slate-950' : 'bg-slate-700'}`}
              onClick={() => {
                setPdbId(id)
                setMode('pdb')
              }}
            >
              PDB {id}
            </button>
          ))}
        </div>
      </div>
      <div ref={hostRef} className="h-[620px] w-full" aria-label={`${structure.gene} protein 3D structure`} />
      <div className="border-t border-slate-700 bg-slate-900 px-4 py-3 text-xs text-slate-300">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span>左键旋转 · 右键／滚轮缩放 · 点击原子或残基聚焦 · 可切换 AlphaFold 与实验 PDB</span>
          <a className="text-cyan-300 hover:underline" href={structure.alphafold_entry_url} target="_blank" rel="noreferrer">打开 AlphaFold DB</a>
        </div>
        <p className="mt-1 text-amber-300">{structure.disclaimer}</p>
      </div>
      {error && <div className="grid h-[620px] place-items-center p-8 text-center text-red-300">{error}</div>}
    </section>
  )
}
