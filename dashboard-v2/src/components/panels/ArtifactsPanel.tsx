import { useState } from 'react'
import { useArtifacts } from '../../api/queries'
import { Panel } from '../shared/Panel'
import { Pagination } from '../shared/Pagination'
import { ArtifactDetailModal } from './ArtifactDetailModal'
import { safeFixed } from '../../utils/format'
import type { ArtifactInfo } from '../../types/api'

function TypeBadge({ type }: { type: string }) {
  const isGenesis = type.startsWith('genesis_')
  const displayType = isGenesis ? type.replace('genesis_', '') : type

  return (
    <span
      className={`px-2 py-0.5 rounded text-xs font-medium ${
        isGenesis
          ? 'bg-[var(--accent-primary)]/20 text-[var(--accent-primary)]'
          : 'bg-[var(--bg-tertiary)] text-[var(--text-secondary)]'
      }`}
    >
      {displayType}
    </span>
  )
}

function MintStatus({ status, score }: { status: string; score: number | null }) {
  const colors: Record<string, string> = {
    minted: 'text-[var(--accent-secondary)]',
    pending: 'text-[var(--accent-warning)]',
    rejected: 'text-[var(--accent-danger)]',
    not_submitted: 'text-[var(--text-secondary)]',
  }

  return (
    <div className="flex items-center gap-2">
      <span className={`text-xs ${colors[status] || ''}`}>{status}</span>
      {score != null && (
        <span className="text-xs text-[var(--text-secondary)]">
          ({safeFixed(score, 2)})
        </span>
      )}
    </div>
  )
}

export function ArtifactsPanel() {
  const [page, setPage] = useState(0)
  const [search, setSearch] = useState('')
  const [selectedArtifact, setSelectedArtifact] = useState<string | null>(null)
  const limit = 25

  const { data, isLoading, error } = useArtifacts(page, limit, search || undefined)

  const handleExport = () => {
    if (!data?.artifacts) return
    const csv = [
      ['ID', 'Type', 'Created By', 'Price', 'Size', 'Mint Status', 'Invocations'].join(','),
      ...data.artifacts.map((a) =>
        [
          a.artifact_id,
          a.artifact_type,
          a.created_by,
          a.price,
          a.size_bytes,
          a.mint_status,
          a.invocation_count,
        ].join(',')
      ),
    ].join('\n')

    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'artifacts.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <>
      <Panel title="Artifacts" badge={data?.total} onExport={handleExport}>
        {/* Search input */}
        <div className="mb-4">
          <input
            type="text"
            placeholder="Search artifacts..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setPage(0)
            }}
            className="w-full px-3 py-2 text-sm bg-[var(--bg-primary)] border border-[var(--border-color)] rounded focus:outline-none focus:ring-1 focus:ring-[var(--accent-primary)]"
          />
        </div>

        {isLoading && (
          <div className="animate-pulse space-y-2">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-8 bg-[var(--bg-tertiary)] rounded" />
            ))}
          </div>
        )}

        {error && (
          <p className="text-[var(--accent-danger)] text-sm">
            Failed to load artifacts: {error.message}
          </p>
        )}

        {data && (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-[var(--text-secondary)] border-b border-[var(--border-color)]">
                    <th className="pb-2 font-medium">ID</th>
                    <th className="pb-2 font-medium">Type</th>
                    <th className="pb-2 font-medium">Creator</th>
                    <th className="pb-2 font-medium">Mint</th>
                    <th className="pb-2 font-medium">Uses</th>
                  </tr>
                </thead>
                <tbody>
                  {data.artifacts.map((artifact) => (
                    <tr
                      key={artifact.artifact_id}
                      className="border-b border-[var(--border-color)] hover:bg-[var(--bg-tertiary)] cursor-pointer"
                      onClick={() => setSelectedArtifact(artifact.artifact_id)}
                    >
                      <td className="py-2 font-mono text-[var(--accent-primary)] truncate max-w-32">
                        {artifact.artifact_id}
                      </td>
                      <td className="py-2">
                        <TypeBadge type={artifact.artifact_type} />
                      </td>
                      <td className="py-2 text-xs text-[var(--text-secondary)] truncate max-w-24">
                        {artifact.created_by}
                      </td>
                      <td className="py-2">
                        <MintStatus
                          status={artifact.mint_status}
                          score={artifact.mint_score}
                        />
                      </td>
                      <td className="py-2">{artifact.invocation_count}</td>
                    </tr>
                  ))}
                  {data.artifacts.length === 0 && (
                    <tr>
                      <td
                        colSpan={5}
                        className="py-4 text-center text-[var(--text-secondary)]"
                      >
                        {search ? 'No matching artifacts' : 'No artifacts yet'}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {data.total > limit && (
              <div className="mt-4">
                <Pagination
                  page={page}
                  total={data.total}
                  perPage={limit}
                  onPageChange={setPage}
                />
              </div>
            )}
          </>
        )}
      </Panel>

      {selectedArtifact && (
        <ArtifactDetailModal
          artifactId={selectedArtifact}
          onClose={() => setSelectedArtifact(null)}
        />
      )}
    </>
  )
}
