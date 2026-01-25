import { useGenesis } from '../../api/queries'
import { Panel } from '../shared/Panel'
import { safeFixed } from '../../utils/format'

function StatBox({
  label,
  value,
  subtext,
}: {
  label: string
  value: string | number
  subtext?: string
}) {
  return (
    <div className="bg-[var(--bg-primary)] rounded p-3">
      <p className="text-xs text-[var(--text-secondary)] mb-1">{label}</p>
      <p className="text-lg font-semibold">{value}</p>
      {subtext && (
        <p className="text-xs text-[var(--text-secondary)]">{subtext}</p>
      )}
    </div>
  )
}

function ScoreBar({ score }: { score: number }) {
  const percent = Math.min(score * 100, 100)
  const color =
    score >= 0.7
      ? 'bg-[var(--accent-secondary)]'
      : score >= 0.4
      ? 'bg-[var(--accent-warning)]'
      : 'bg-[var(--accent-danger)]'

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-[var(--bg-tertiary)] rounded-full overflow-hidden">
        <div
          className={`h-full ${color}`}
          style={{ width: `${percent}%` }}
        />
      </div>
      <span className="text-xs font-mono w-12 text-right">{safeFixed(score, 2)}</span>
    </div>
  )
}

export function GenesisPanel() {
  const { data, isLoading, error } = useGenesis()

  return (
    <Panel title="Genesis Activity">
      {isLoading && (
        <div className="animate-pulse space-y-4">
          <div className="grid grid-cols-3 gap-2">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-16 bg-[var(--bg-tertiary)] rounded" />
            ))}
          </div>
        </div>
      )}

      {error && (
        <p className="text-[var(--accent-danger)] text-sm">
          Failed to load genesis data: {error.message}
        </p>
      )}

      {data && (
        <div className="space-y-6">
          {/* Mint Section */}
          <div>
            <h4 className="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wide mb-3">
              Minting
            </h4>
            <div className="grid grid-cols-2 gap-2 mb-3">
              <StatBox label="Pending" value={data.mint.pending_count} />
              <StatBox
                label="Total Minted"
                value={`${safeFixed(data.mint?.total_scrip_minted, 1)} scrip`}
              />
            </div>
            {data.mint.recent_scores.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs text-[var(--text-secondary)]">Recent Scores</p>
                {data.mint.recent_scores.slice(-5).map((score, i) => (
                  <ScoreBar key={i} score={score} />
                ))}
              </div>
            )}
          </div>

          {/* Escrow Section */}
          <div>
            <h4 className="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wide mb-3">
              Escrow
            </h4>
            <div className="grid grid-cols-2 gap-2">
              <StatBox label="Active Listings" value={data.escrow.active_listings} />
              <StatBox label="Recent Trades" value={data.escrow.recent_trades} />
            </div>
          </div>

          {/* Ledger Section */}
          <div>
            <h4 className="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wide mb-3">
              Ledger
            </h4>
            <div className="grid grid-cols-3 gap-2">
              <StatBox label="Transfers" value={data.ledger.recent_transfers} />
              <StatBox label="Spawns" value={data.ledger.recent_spawns} />
              <StatBox label="Ownership" value={data.ledger.ownership_transfers} />
            </div>
          </div>
        </div>
      )}
    </Panel>
  )
}
