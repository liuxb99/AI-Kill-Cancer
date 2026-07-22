import { useEffect, useState, useCallback } from 'react'
import { getDecisionThread, type DecisionNode } from '../../api/workbench'

// ─── Node type Chinese labels ────────────────────────────────────────────────

const NODE_TYPE_LABELS: Record<string, string> = {
  context_built: '上下文构建',
  evidence_collected: '证据收集',
  agent_opinion: '智能体意见',
  consensus_reached: '达成共识',
  recommendation_generated: '生成建议',
}

function nodeTypeLabel(nodeType: string): string {
  return NODE_TYPE_LABELS[nodeType] || nodeType
}

// ─── Tree helpers ────────────────────────────────────────────────────────────

interface TreeNode extends DecisionNode {
  children: TreeNode[]
}

function buildTree(nodes: DecisionNode[]): TreeNode[] {
  const map = new Map<string, TreeNode>()
  const roots: TreeNode[] = []

  for (const n of nodes) {
    map.set(n.id, { ...n, children: [] })
  }
  for (const n of nodes) {
    const node = map.get(n.id)!
    if (n.parent_id && map.has(n.parent_id)) {
      map.get(n.parent_id)!.children.push(node)
    } else {
      roots.push(node)
    }
  }
  return roots
}

// ─── Sub-components ──────────────────────────────────────────────────────────

function LoadingSkeleton() {
  return (
    <div className="animate-pulse space-y-3 p-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="h-4 bg-gray-200 rounded w-full" />
      ))}
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

// ─── Node card ───────────────────────────────────────────────────────────────

function DecisionNodeCard({
  node,
  depth,
}: {
  node: TreeNode
  depth: number
}) {
  const [expanded, setExpanded] = useState(false)
  const hasChildren = node.children.length > 0

  const typeColor = (t: string): string => {
    switch (t) {
      case 'context_built':
        return 'border-l-blue-400 bg-blue-50'
      case 'evidence_collected':
        return 'border-l-green-400 bg-green-50'
      case 'agent_opinion':
        return 'border-l-yellow-400 bg-yellow-50'
      case 'consensus_reached':
        return 'border-l-purple-400 bg-purple-50'
      case 'recommendation_generated':
        return 'border-l-rose-400 bg-rose-50'
      default:
        return 'border-l-gray-300 bg-gray-50'
    }
  }

  const typeBadgeColor = (t: string): string => {
    switch (t) {
      case 'context_built':
        return 'bg-blue-100 text-blue-700'
      case 'evidence_collected':
        return 'bg-green-100 text-green-700'
      case 'agent_opinion':
        return 'bg-yellow-100 text-yellow-700'
      case 'consensus_reached':
        return 'bg-purple-100 text-purple-700'
      case 'recommendation_generated':
        return 'bg-rose-100 text-rose-700'
      default:
        return 'bg-gray-100 text-gray-600'
    }
  }

  return (
    <div style={{ marginLeft: depth * 24 }}>
      {/* Connection line */}
      {depth > 0 && (
        <div className="ml-0.5 w-px h-4 bg-gray-200" />
      )}

      {/* Node card */}
      <div
        className={`rounded-r-lg border-l-4 border border-gray-200 p-3 mb-2 cursor-pointer transition-shadow hover:shadow-sm ${typeColor(node.node_type)}`}
        onClick={() => setExpanded(!expanded)}
      >
        {/* Header row */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${typeBadgeColor(node.node_type)}`}>
              {nodeTypeLabel(node.node_type)}
            </span>
            {node.decision_label && (
              <span className="text-xs text-gray-500 font-medium">
                {node.decision_label}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-400">
              {new Date(node.timestamp).toLocaleString('zh-CN')}
            </span>
            <span className="text-xs text-gray-300">
              {expanded ? '▲' : '▼'}
            </span>
          </div>
        </div>

        {/* Expanded details */}
        {expanded && (
          <div className="mt-3 space-y-2 border-t border-gray-200 pt-2">
            {node.reasoning && (
              <div>
                <p className="text-xs font-medium text-gray-500 mb-0.5">推理过程</p>
                <p className="text-sm text-gray-700 whitespace-pre-wrap">{node.reasoning}</p>
              </div>
            )}
            {node.confidence && (
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-gray-500">置信度</span>
                <span className={`text-xs font-semibold ${
                  parseFloat(node.confidence) >= 0.7
                    ? 'text-green-600'
                    : parseFloat(node.confidence) >= 0.4
                      ? 'text-yellow-600'
                      : 'text-red-600'
                }`}>
                  {(parseFloat(node.confidence) * 100).toFixed(0)}%
                </span>
              </div>
            )}
            <div className="flex flex-wrap gap-2 text-xs text-gray-400">
              <span>节点 ID: {node.id.slice(0, 8)}...</span>
              {node.parent_id && <span>父节点: {node.parent_id.slice(0, 8)}...</span>}
            </div>
          </div>
        )}
      </div>

      {/* Children */}
      {hasChildren && expanded && (
        <div className="border-l border-gray-200 ml-3 pl-3">
          {node.children.map((child) => (
            <DecisionNodeCard key={child.id} node={child} depth={depth + 1} />
          ))}
        </div>
      )}

      {/* Collapsed children indicator */}
      {hasChildren && !expanded && (
        <div
          className="ml-0.5 mb-1 text-xs text-gray-400 cursor-pointer hover:text-gray-600"
          onClick={() => setExpanded(true)}
        >
          {node.children.length} 个子节点...
        </div>
      )}
    </div>
  )
}

// ─── Main component ──────────────────────────────────────────────────────────

interface DecisionThreadTabProps {
  caseId: string
}

export function DecisionThreadTab({ caseId }: DecisionThreadTabProps) {
  const [tree, setTree] = useState<TreeNode[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const nodes = await getDecisionThread(caseId)
      setTree(buildTree(nodes))
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载决策线程失败')
    } finally {
      setLoading(false)
    }
  }, [caseId])

  useEffect(() => {
    loadData()
  }, [loadData])

  if (loading) return <LoadingSkeleton />
  if (error) return <ErrorState message={error} />

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700">决策线程</h3>
        <button
          onClick={loadData}
          className="text-xs text-primary-500 hover:text-primary-700 transition"
          disabled={loading}
        >
          刷新
        </button>
      </div>

      {tree.length === 0 ? (
        <EmptyState message="暂无决策数据" />
      ) : (
        <div className="space-y-1">
          {tree.map((node) => (
            <DecisionNodeCard key={node.id} node={node} depth={0} />
          ))}
        </div>
      )}
    </div>
  )
}
