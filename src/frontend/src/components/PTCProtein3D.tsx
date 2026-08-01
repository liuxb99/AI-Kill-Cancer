import { useEffect, useMemo, useRef, useState } from 'react'

import type { PTCProteinStructure } from '../api/ptcVisualization'
import type { PTCVariant } from '../api/ptcResearch'

const MOLSTAR_VERSION = '3.3.0'
const MOLSTAR_SCRIPT = `https://cdn.jsdelivr.net/npm/pdbe-molstar@${MOLSTAR_VERSION}/build/pdbe-molstar-plugin.js`
const MOLSTAR_STYLE = `https://cdn.jsdelivr.net/npm/pdbe-molstar@${MOLSTAR_VERSION}/build/pdbe-molstar.css`
let loader: Promise<void> | null = null

declare global {
  interface Window {
    PDBeMolstarPlugin?: new () => any
  }
}

function loadMolstarPlugin(): Promise<void> {
  if (window.PDBeMolstarPlugin) return Promise.resolve()
  if (loader) return loader
  loader = new Promise((resolve, reject) => {
    if (!document.querySelector(`link[href="${MOLSTAR_STYLE}"]`)) {
      const link = document.createElement('link')
      link.rel = 'stylesheet'
      link.href = MOLSTAR_STYLE
      link.crossOrigin = 'anonymous'
      document.head.appendChild(link)
    }
    const existing = document.querySelector<HTMLScriptElement>(`script[src="${MOLSTAR_SCRIPT}"]`)
    const script = existing || document.createElement('script')
    const loaded = () => window.PDBeMolstarPlugin ? resolve() : reject(new Error('PDBe Mol* 插件未正确初始化'))
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
  variants?: PTCVariant[]
  loading?: boolean
}

interface MutationResidue {
  key: string
  label: string
  residue: number
}

function residueNumber(proteinChange?: string): number | null {
  if (!proteinChange) return null
  const match = proteinChange.match(/(?:p\.)?[A-Za-z*]+(\d+)/)
  return match ? Number(match[1]) : null
}

export default function PTCProtein3D({ structure, variants = [], loading }: Props) {
  const hostRef = useRef<HTMLDivElement | null>(null)
  const viewerRef = useRef<any>(null)
  const [mode, setMode] = useState<'alphafold' | 'pdb'>('alphafold')
  const [pdbId, setPdbId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [viewerReady, setViewerReady] = useState(false)
  const [focusedResidue, setFocusedResidue] = useState<number | null>(null)

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

  useEffect(() => {
    setPdbId(structure?.default_pdb_id || null)
    setMode('alphafold')
    setError(null)
    setFocusedResidue(null)
  }, [structure])

  useEffect(() => {
    const host = hostRef.current
    if (!host || !structure) return
    let disposed = false
    let instance: any = null
    setViewerReady(false)

    void loadMolstarPlugin().then(async () => {
      if (disposed || !hostRef.current || !window.PDBeMolstarPlugin) return
      setError(null)
      host.replaceChildren()
      instance = new window.PDBeMolstarPlugin()
      viewerRef.current = instance
      const options: Record<string, unknown> = {
        hideControls: false,
        sequencePanel: true,
        landscape: true,
        reactive: true,
        loadingOverlay: true,
        selectInteraction: true,
        visualStyle: 'cartoon',
        bgColor: { r: 7, g: 17, b: 31 },
        selectColor: '#fb923c',
        highlightColor: '#fde047',
        granularity: 'residue',
      }
      if (mode === 'pdb' && pdbId) {
        options.moleculeId = pdbId.toLowerCase()
      } else {
        options.customData = { url: structure.cif_url, format: 'cif' }
        options.alphafoldView = true
      }
      await instance.render(host, options)
      if (disposed) return
      setViewerReady(true)

      if (mutationResidues.length > 0) {
        await instance.visual.select({
          data: mutationResidues.map((item, index) => ({
            residue_number: item.residue,
            color: index === 0 ? '#f97316' : '#facc15',
            focus: index === 0,
            sideChain: true,
            representation: 'ball-and-stick',
            representationColor: index === 0 ? '#fb923c' : '#fde047',
          })),
          nonSelectedColor: '#64748b',
        })
        setFocusedResidue(mutationResidues[0].residue)
      }
    }).catch((reason) => {
      if (!disposed) setError(reason instanceof Error ? reason.message : '无法载入蛋白质 3D 结构')
    })

    return () => {
      disposed = true
      setViewerReady(false)
      viewerRef.current = null
      if (instance?.clear) void instance.clear()
      host.replaceChildren()
    }
  }, [structure, mode, pdbId, mutationResidues])

  async function focusMutation(item: MutationResidue) {
    const viewer = viewerRef.current
    if (!viewer?.visual) return
    setFocusedResidue(item.residue)
    try {
      await viewer.visual.select({
        data: [{
          residue_number: item.residue,
          color: '#f97316',
          focus: true,
          sideChain: true,
          representation: 'ball-and-stick',
          representationColor: '#fb923c',
        }],
        nonSelectedColor: '#64748b',
      })
      await viewer.visual.highlight({
        data: [{ residue_number: item.residue }],
        color: '#fde047',
        focus: true,
      })
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : `无法聚焦 residue ${item.residue}`)
    }
  }

  async function resetStructure() {
    const viewer = viewerRef.current
    if (!viewer?.visual) return
    await viewer.visual.clearHighlight()
    await viewer.visual.clearSelection()
    await viewer.visual.reset({ camera: true, theme: true })
    setFocusedResidue(null)
  }

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
          <button className="rounded bg-slate-700 px-3 py-1.5" onClick={() => void resetStructure()} disabled={!viewerReady}>
            重置视图
          </button>
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
                onClick={() => void focusMutation(item)}
                disabled={!viewerReady}
              >
                {item.label} · residue {item.residue} · 聚焦
              </button>
            ))}
          </div>
          <p className="mt-2 text-amber-200/70">
            AlphaFold 使用 UniProt 全长残基编号；实验 PDB 可能只覆盖局部结构，若该残基不在所选 PDB 中请切回 AlphaFold。
          </p>
        </div>
      )}

      <div ref={hostRef} className="h-[620px] w-full" aria-label={`${structure.gene} protein 3D structure`} />

      {error && (
        <div className="border-t border-red-700 bg-red-950/70 p-5 text-sm text-red-100">
          <div className="font-semibold">{error}</div>
          <div className="mt-3 flex flex-wrap gap-3">
            <a className="rounded bg-cyan-500 px-3 py-2 font-semibold text-slate-950" href={structure.alphafold_entry_url} target="_blank" rel="noreferrer">打开 AlphaFold DB</a>
            <a className="rounded bg-slate-700 px-3 py-2" href={structure.cif_url} target="_blank" rel="noreferrer">下载 mmCIF</a>
            {structure.default_pdb_id && (
              <a className="rounded bg-emerald-700 px-3 py-2" href={`https://www.ebi.ac.uk/pdbe/entry/pdb/${structure.default_pdb_id.toLowerCase()}`} target="_blank" rel="noreferrer">打开 PDB {structure.default_pdb_id}</a>
            )}
          </div>
        </div>
      )}

      <div className="border-t border-slate-700 bg-slate-900 px-4 py-3 text-xs text-slate-300">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span>左键旋转 · 右键／滚轮缩放 · 点击残基聚焦 · 橙色为病例突变位点</span>
          <a className="text-cyan-300 hover:underline" href={structure.alphafold_entry_url} target="_blank" rel="noreferrer">打开 AlphaFold DB</a>
        </div>
        <p className="mt-1 text-amber-300">{structure.disclaimer}</p>
      </div>
    </section>
  )
}
