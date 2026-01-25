import { useArtifactDetail } from '../../api/queries'
import { Modal } from '../shared/Modal'
import { safeFixed, formatBytes, formatTime } from '../../utils/format'

interface ArtifactDetailModalProps {
  artifactId: string
  onClose: () => void
}

export function ArtifactDetailModal({ artifactId, onClose }: ArtifactDetailModalProps) {
  const { data: artifact, isLoading } = useArtifactDetail(artifactId)

  return (
    <Modal title={artifactId} onClose={onClose}>
      {isLoading && (
        <div className="animate-pulse space-y-4">
          <div className="h-20 bg-[var(--bg-tertiary)] rounded" />
          <div className="h-40 bg-[var(--bg-tertiary)] rounded" />
        </div>
      )}

      {artifact && (
        <div className="space-y-6">
          {/* Stats Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard label="Type" value={artifact.artifact_type} />
            <StatCard label="Creator" value={artifact.created_by} mono />
            <StatCard
              label="Price"
              value={`${safeFixed(artifact.price, 2)} scrip`}
            />
            <StatCard
              label="Size"
              value={formatBytes(artifact.size_bytes)}
            />
          </div>

          {/* Mint Status */}
          <Section title="Mint Status">
            <div className="flex items-center gap-4">
              <StatusBadge status={artifact.mint_status} />
              {artifact.mint_score != null && (
                <span className="text-sm">
                  Score: <span className="font-mono">{safeFixed(artifact.mint_score, 3)}</span>
                </span>
              )}
            </div>
          </Section>

          {/* Properties */}
          <Section title="Properties">
            <div className="grid grid-cols-2 gap-2 text-sm">
              <PropertyItem
                label="Executable"
                value={artifact.executable ? 'Yes' : 'No'}
              />
              <PropertyItem
                label="Invocations"
                value={artifact.invocation_count.toString()}
              />
              {artifact.access_contract_id && (
                <PropertyItem
                  label="Access Contract"
                  value={artifact.access_contract_id}
                  mono
                />
              )}
            </div>
          </Section>

          {/* Methods */}
          {(artifact.methods?.length ?? 0) > 0 && (
            <Section title="Methods" badge={artifact.methods!.length}>
              <div className="flex flex-wrap gap-2">
                {artifact.methods!.map((method) => (
                  <span
                    key={method}
                    className="px-2 py-1 bg-[var(--bg-tertiary)] rounded text-xs font-mono"
                  >
                    {method}
                  </span>
                ))}
              </div>
            </Section>
          )}

          {/* Content Preview */}
          {artifact.content && (
            <Section title="Content Preview">
              <pre className="p-3 bg-[var(--bg-primary)] rounded text-xs font-mono overflow-x-auto max-h-48 whitespace-pre-wrap">
                {artifact.content.slice(0, 2000)}
                {artifact.content.length > 2000 && '...'}
              </pre>
            </Section>
          )}

          {/* Ownership History */}
          <Section title="Ownership History" badge={artifact.ownership_history?.length ?? 0}>
            {(artifact.ownership_history?.length ?? 0) > 0 ? (
              <div className="space-y-2 max-h-32 overflow-y-auto">
                {artifact.ownership_history!.map((transfer, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between text-sm py-1 border-b border-[var(--border-color)]"
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-[var(--text-secondary)]">{formatTime(transfer.timestamp)}</span>
                      <span className="text-xs text-[var(--text-secondary)]">
                        {transfer.from_id || '(created)'} → {transfer.to_id}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-[var(--text-secondary)]">No transfers</p>
            )}
          </Section>

          {/* Recent Invocations */}
          <Section title="Recent Invocations" badge={artifact.invocation_history?.length ?? 0}>
            {(artifact.invocation_history?.length ?? 0) > 0 ? (
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {artifact.invocation_history!.slice(-10).reverse().map((inv, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between text-sm py-1 border-b border-[var(--border-color)]"
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs">{inv.invoker_id}</span>
                      {inv.method && (
                        <span className="text-xs text-[var(--accent-primary)]">
                          .{inv.method}()
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      {inv.duration_ms != null && (
                        <span className="text-xs text-[var(--text-secondary)]">
                          {inv.duration_ms}ms
                        </span>
                      )}
                      {!inv.success && (
                        <span className="text-xs text-[var(--accent-danger)]">
                          {inv.error || 'failed'}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-[var(--text-secondary)]">No invocations yet</p>
            )}
          </Section>
        </div>
      )}
    </Modal>
  )
}

function StatCard({
  label,
  value,
  mono = false,
}: {
  label: string
  value: string
  mono?: boolean
}) {
  return (
    <div className="bg-[var(--bg-primary)] rounded p-3">
      <p className="text-xs text-[var(--text-secondary)] mb-1">{label}</p>
      <p className={`text-sm font-semibold truncate ${mono ? 'font-mono' : ''}`}>
        {value}
      </p>
    </div>
  )
}

function Section({
  title,
  badge,
  children,
}: {
  title: string
  badge?: number
  children: React.ReactNode
}) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <h3 className="text-sm font-semibold">{title}</h3>
        {badge !== undefined && (
          <span className="text-xs bg-[var(--bg-tertiary)] px-2 py-0.5 rounded">
            {badge}
          </span>
        )}
      </div>
      {children}
    </div>
  )
}

function PropertyItem({
  label,
  value,
  mono = false,
}: {
  label: string
  value: string
  mono?: boolean
}) {
  return (
    <div className="flex justify-between py-1">
      <span className="text-[var(--text-secondary)]">{label}</span>
      <span className={mono ? 'font-mono text-xs' : ''}>{value}</span>
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    minted: 'bg-[var(--accent-secondary)]/20 text-[var(--accent-secondary)]',
    pending: 'bg-[var(--accent-warning)]/20 text-[var(--accent-warning)]',
    rejected: 'bg-[var(--accent-danger)]/20 text-[var(--accent-danger)]',
    not_submitted: 'bg-[var(--bg-tertiary)] text-[var(--text-secondary)]',
  }

  return (
    <span className={`px-2 py-1 rounded text-xs font-medium ${colors[status] || ''}`}>
      {status}
    </span>
  )
}

