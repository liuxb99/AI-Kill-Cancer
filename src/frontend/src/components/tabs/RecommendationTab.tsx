import { useEffect, useState, useCallback, type ReactNode } from 'react'
import { getRecommendation, type TreatmentRecommendation } from '../../api/workbench'

// ─── Simple Markdown renderer ────────────────────────────────────────────────

function simpleMarkdown(md: string): string {
  // Escape HTML to prevent injection
  const escaped = md
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  // Split into lines and process block-level elements
  const lines = escaped.split('\n')
  const htmlLines: string[] = []
  let inList = false

  for (let i = 0; i < lines.length; i++) {
    let line = lines[i]

    // Headings
    const headingMatch = line.match(/^(#{1,6})\s+(.*)/)
    if (headingMatch) {
      if (inList) { htmlLines.push('</ul>'); inList = false }
      const level = headingMatch[1].length
      htmlLines.push(`<h${level} class="text-sm font-semibold text-gray-700 mt-3 mb-1">${headingMatch[2]}</h${level}>`)
      continue
    }

    // Horizontal rule
    if (/^(-{3,}|\*{3,})$/.test(line.trim())) {
      if (inList) { htmlLines.push('</ul>'); inList = false }
      htmlLines.push('<hr class="my-3 border-gray-200" />')
      continue
    }

    // Unordered list item
    const ulMatch = line.match(/^[-*+]\s+(.*)/)
    if (ulMatch) {
      if (!inList) { htmlLines.push('<ul class="list-disc list-inside space-y-0.5 text-sm text-gray-700 mb-2">'); inList = true }
      htmlLines.push(`<li>${inlineMarkdown(ulMatch[1])}</li>`)
      continue
    }

    // Ordered list item
    const olMatch = line.match(/^\d+\.\s+(.*)/)
    if (olMatch) {
      if (!inList) { htmlLines.push('<ol class="list-decimal list-inside space-y-0.5 text-sm text-gray-700 mb-2">'); inList = true }
      htmlLines.push(`<li>${inlineMarkdown(olMatch[1])}</li>`)
      continue
    }

    // Code block (fenced)
    if (line.trimStart().startsWith('```')) {
      if (inList) { htmlLines.push('</ul>'); inList = false }
      const lang = line.trim().slice(3).trim()
      // Collect code lines until closing ```
      const codeLines: string[] = []
      i++
      while (i < lines.length && !lines[i].trimStart().startsWith('```')) {
        codeLines.push(lines[i])
        i++
      }
      // i now points at closing ``` or past end
      htmlLines.push(`<pre class="bg-gray-100 rounded-lg p-3 text-xs text-gray-700 overflow-x-auto mb-3"><code${lang ? ` class="language-${lang}"` : ''}>${codeLines.join('\n')}</code></pre>`)
      continue
    }

    // Empty line — close any open list
    if (line.trim() === '') {
      if (inList) { htmlLines.push('</ul>'); inList = false }
      continue
    }

    // Paragraph (default)
    if (inList) { htmlLines.push('</ul>'); inList = false }
    htmlLines.push(`<p class="text-sm text-gray-700 mb-2">${inlineMarkdown(line)}</p>`)
  }

  // Close any open list
  if (inList) htmlLines.push('</ul>')

  return htmlLines.join('\n')
}

/** Inline markdown: bold, italic, code, links */
function inlineMarkdown(text: string): string {
  // Inline code (must escape first)
  let result = text
    // Bold **text** or __text__
    .replace(/\*\*(.+?)\*\*/g, '<strong class="font-semibold">$1</strong>')
    .replace(/__(.+?)__/g, '<strong class="font-semibold">$1</strong>')
    // Italic *text* or _text_
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/_(.+?)_/g, '<em>$1</em>')
    // Inline code
    .replace(/`(.+?)`/g, '<code class="bg-gray-100 px-1 py-0.5 rounded text-xs text-pink-600">$1</code>')
    // Links [text](url)
    .replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" class="text-primary-600 hover:text-primary-800 underline" target="_blank" rel="noopener noreferrer">$1</a>')
  return result
}

// ─── Sub-components ──────────────────────────────────────────────────────────

function LoadingSkeleton() {
  return (
    <div className="animate-pulse space-y-4 p-4">
      <div className="h-5 w-36 bg-gray-200 rounded" />
      <div className="h-4 w-full bg-gray-200 rounded" />
      <div className="h-4 w-3/4 bg-gray-200 rounded" />
      <div className="h-4 w-1/2 bg-gray-200 rounded" />
      <div className="h-24 w-full bg-gray-100 rounded" />
      <div className="h-4 w-2/3 bg-gray-200 rounded" />
      <div className="h-4 w-full bg-gray-200 rounded" />
    </div>
  )
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="p-8 text-center">
      <p className="text-red-500 text-sm font-medium mb-1">⚠ 加载失败</p>
      <p className="text-xs text-gray-400">{message}</p>
    </div>
  )
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="p-8 text-center">
      <p className="text-sm text-gray-400">{message}</p>
    </div>
  )
}

// ─── Section helper ──────────────────────────────────────────────────────────

function Section({ title, icon, children }: { title: string; icon?: string; children: ReactNode }) {
  return (
    <section className="bg-white rounded-lg border border-gray-100 shadow-sm">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-50">
        {icon && <span className="text-base">{icon}</span>}
        <h4 className="text-sm font-semibold text-gray-700">{title}</h4>
      </div>
      <div className="p-4">
        {children}
      </div>
    </section>
  )
}

// ─── Field renderer ──────────────────────────────────────────────────────────

function renderFields(obj: Record<string, any> | undefined | null): ReactNode {
  if (!obj || Object.keys(obj).length === 0) {
    return <p className="text-sm text-gray-400">暂无数据</p>
  }
  return (
    <div className="space-y-1.5">
      {Object.entries(obj).map(([key, value]) => (
        <div key={key} className="flex text-sm">
          <span className="text-gray-500 w-32 flex-shrink-0 font-medium">{key}:</span>
          <span className="text-gray-800">{formatValue(value)}</span>
        </div>
      ))}
    </div>
  )
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  if (Array.isArray(value)) {
    if (value.length === 0) return '—'
    return value.map(v => typeof v === 'object' ? JSON.stringify(v) : String(v)).join(', ')
  }
  if (typeof value === 'object') return JSON.stringify(value, null, 1)
  return String(value)
}

// ─── Main Component ──────────────────────────────────────────────────────────

interface RecommendationTabProps {
  caseId: string
}

export function RecommendationTab({ caseId }: RecommendationTabProps) {
  const [data, setData] = useState<TreatmentRecommendation | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await getRecommendation(caseId)
      setData(result)
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载治疗方案失败')
    } finally {
      setLoading(false)
    }
  }, [caseId])

  useEffect(() => {
    loadData()
  }, [loadData])

  // ── Loading state ──
  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <LoadingSkeleton />
      </div>
    )
  }

  // ── Error state ──
  if (error) {
    return <ErrorState message={error} />
  }

  // ── Empty state ──
  if (!data) {
    return <EmptyState message="暂无治疗方案数据" />
  }

  // ── Check if there is any real content ──
  const hasStructuredData =
    data.first_line || data.second_line || data.clinical_trial ||
    data.expected_benefit || data.potential_risk || data.monitoring_plan ||
    (data.supporting_evidence && data.supporting_evidence.length > 0)

  const hasMarkdown = !!data.markdown

  if (!hasStructuredData && !hasMarkdown) {
    return <EmptyState message="治疗方案数据为空" />
  }

  return (
    <div className="space-y-4">
      {/* Header & refresh */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700">💊 治疗方案推荐</h3>
        <div className="flex items-center gap-3">
          {data.created_at && (
            <span className="text-xs text-gray-400">
              {new Date(data.created_at).toLocaleString('zh-CN')}
            </span>
          )}
          <button
            onClick={loadData}
            className="text-xs text-primary-500 hover:text-primary-700 transition"
          >
            刷新
          </button>
        </div>
      </div>

      {/* First-line */}
      {data.first_line && Object.keys(data.first_line).length > 0 && (
        <Section title="一线治疗" icon="🟢">
          {renderFields(data.first_line)}
        </Section>
      )}

      {/* Second-line */}
      {data.second_line && Object.keys(data.second_line).length > 0 && (
        <Section title="二线治疗" icon="🟡">
          {renderFields(data.second_line)}
        </Section>
      )}

      {/* Clinical Trial */}
      {data.clinical_trial && Object.keys(data.clinical_trial).length > 0 && (
        <Section title="临床试验" icon="🔬">
          {renderFields(data.clinical_trial)}
        </Section>
      )}

      {/* Supporting Evidence */}
      {data.supporting_evidence && data.supporting_evidence.length > 0 && (
        <Section title="支持证据" icon="📚">
          <div className="space-y-3">
            {data.supporting_evidence.map((ev, i) => (
              <div key={i} className="bg-gray-50 rounded-lg p-3 border border-gray-100">
                {typeof ev === 'string' ? (
                  <p className="text-sm text-gray-700">{ev}</p>
                ) : (
                  <div className="space-y-1">
                    {Object.entries(ev).map(([key, value]) => (
                      <div key={key} className="flex text-sm">
                        <span className="text-gray-500 w-28 flex-shrink-0 font-medium">{key}:</span>
                        <span className="text-gray-800">{formatValue(value)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Expected Benefit */}
      {data.expected_benefit && Object.keys(data.expected_benefit).length > 0 && (
        <Section title="预期效益" icon="📈">
          {renderFields(data.expected_benefit)}
        </Section>
      )}

      {/* Potential Risk */}
      {data.potential_risk && Object.keys(data.potential_risk).length > 0 && (
        <Section title="潜在风险" icon="⚠️">
          {renderFields(data.potential_risk)}
        </Section>
      )}

      {/* Monitoring Plan */}
      {data.monitoring_plan && Object.keys(data.monitoring_plan).length > 0 && (
        <Section title="监测计划" icon="📋">
          {renderFields(data.monitoring_plan)}
        </Section>
      )}

      {/* Markdown rendered view */}
      {hasMarkdown && (
        <section className="bg-white rounded-lg border border-gray-100 shadow-sm">
          <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-50">
            <span className="text-base">📄</span>
            <h4 className="text-sm font-semibold text-gray-700">完整报告</h4>
          </div>
          <div
            className="p-4 prose prose-sm max-w-none text-gray-700 markdown-content"
            dangerouslySetInnerHTML={{ __html: simpleMarkdown(data.markdown) }}
          />
        </section>
      )}

      {/* Context hash footer */}
      {data.context_hash && (
        <p className="text-xs text-gray-400 text-right border-t border-gray-100 pt-3">
          上下文哈希: <code className="text-gray-500">{data.context_hash.slice(0, 16)}…</code>
        </p>
      )}
    </div>
  )
}
