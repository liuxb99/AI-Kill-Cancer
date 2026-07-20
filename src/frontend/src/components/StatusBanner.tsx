import { useState, useEffect } from 'react'

interface StatusInfo {
  mode: string
  model_loaded: boolean
  database_connected?: boolean
  version: string
}

const API_BASE = import.meta.env.VITE_API_URL || ''

export default function StatusBanner() {
  const [info, setInfo] = useState<StatusInfo | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    let cancelled = false
    fetch(`${API_BASE}/api/v1/health`)
      .then((r) => r.json())
      .then((data) => {
        if (!cancelled) setInfo(data as StatusInfo)
      })
      .catch(() => {
        if (!cancelled) setError(true)
      })
    return () => { cancelled = true }
  }, [])

  if (error) {
    return (
      <div className="bg-red-600 text-white text-center text-xs py-1 px-4 font-medium">
        ⚠ API 服務無法連接 — 部分功能不可用
      </div>
    )
  }

  if (!info) return null

  if (info.mode === 'demo') {
    return (
      <div className="bg-amber-500 text-white text-center text-xs py-1 px-4 font-medium">
        ⓘ 演示模式（Demo）— 所有資料為模擬數據，<strong>不可用於診斷或治療</strong>
        {info.model_loaded ? ' | 模型已載入' : ' | 模型未載入'}
      </div>
    )
  }

  if (info.mode === 'production' || info.mode === 'research') {
    if (!info.model_loaded) {
      return (
        <div className="bg-red-600 text-white text-center text-xs py-1 px-4 font-medium">
          ⚠ 系統未就緒 — 模型未載入，預測功能不可用
        </div>
      )
    }
    return null
  }

  return null
}
