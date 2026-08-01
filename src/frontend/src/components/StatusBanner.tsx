import { useEffect, useState } from 'react'

import { apiRequest } from '../api/client'

interface StatusInfo {
  mode: string
  model_loaded: boolean
  database_connected?: boolean
  version: string
}

export default function StatusBanner() {
  const [info, setInfo] = useState<StatusInfo | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    let cancelled = false
    void apiRequest<StatusInfo>('/health')
      .then((data) => {
        if (!cancelled) setInfo(data)
      })
      .catch(() => {
        if (!cancelled) setError(true)
      })
    return () => { cancelled = true }
  }, [])

  if (error) {
    return (
      <div className="bg-red-600 px-4 py-1 text-center text-xs font-medium text-white">
        ⚠ API 服務無法連接 — 部分功能不可用
      </div>
    )
  }

  if (!info) return null

  if (info.mode === 'demo') {
    return (
      <div className="bg-amber-500 px-4 py-1 text-center text-xs font-medium text-white">
        ⓘ 演示模式（Demo）— 所有資料為模擬數據，<strong>不可用於診斷或治療</strong>
        {info.model_loaded ? ' | 模型已載入' : ' | 模型未載入'}
      </div>
    )
  }

  if ((info.mode === 'production' || info.mode === 'research') && !info.model_loaded) {
    return (
      <div className="bg-red-600 px-4 py-1 text-center text-xs font-medium text-white">
        ⚠ 系統未就緒 — 模型未載入，預測功能不可用
      </div>
    )
  }

  return null
}
