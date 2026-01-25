import { useAgent, useAgentConfig } from '../../api/queries'
import { Modal } from '../shared/Modal'

interface AgentDetailModalProps {
  agentId: string
  onClose: () => void
}

export function AgentDetailModal({ agentId, onClose }: AgentDetailModalProps) {
  const { data: agent, isLoading: loadingAgent } = useAgent(agentId)
  const { data: config, isLoading: loadingConfig } = useAgentConfig(agentId)

  const isLoading = loadingAgent || loadingConfig

  return (
    <Modal title={agentId} onClose={onClose}>
      {isLoading && (
        <div className="animate-pulse space-y-4">
          <div className="h-20 bg-[var(--bg-tertiary)] rounded" />
          <div className="h-40 bg-[var(--bg-tertiary)] rounded" />
        </div>
      )}

      {agent && (
        <div className="space-y-6">
          {/* Stats Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard label="Scrip" value={agent.scrip.toFixed(2)} />
            <StatCard
              label="Budget"
              value={`$${agent.llm_budget_remaining.toFixed(3)}`}
              subtext={`of $${agent.llm_budget_initial.toFixed(2)}`}
            />
            <StatCard label="Actions" value={agent.action_count.toString()} />
            <StatCard
              label="Status"
              value={agent.status}
              valueClass={
                agent.status === 'active'
                  ? 'text-[var(--accent-secondary)]'
                  : agent.status === 'frozen'
                  ? 'text-[var(--accent-primary)]'
                  : agent.status === 'bankrupt'
                  ? 'text-[var(--accent-danger)]'
                  : ''
              }
            />
          </div>

          {/* Config Section */}
          {config?.config_found && (
            <Section title="Configuration">
              <div className="grid grid-cols-2 gap-2 text-sm">
                <ConfigItem label="LLM Model" value={config.llm_model || 'default'} />
                <ConfigItem label="Starting Scrip" value={config.starting_credits.toString()} />
                {config.temperature != null && (
                  <ConfigItem label="Temperature" value={config.temperature.toString()} />
                )}
                {config.max_tokens != null && (
                  <ConfigItem label="Max Tokens" value={config.max_tokens.toString()} />
                )}
              </div>
              {config.genotype && Object.keys(config.genotype).length > 0 && (
                <div className="mt-3">
                  <h4 className="text-xs text-[var(--text-secondary)] mb-2">Genotype</h4>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(config.genotype).map(([key, value]) => (
                      <span
                        key={key}
                        className="px-2 py-1 bg-[var(--bg-tertiary)] rounded text-xs"
                      >
                        {key}: {String(value)}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </Section>
          )}

          {/* Owned Artifacts */}
          <Section title="Artifacts Owned" badge={agent.artifacts_owned.length}>
            {agent.artifacts_owned.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {agent.artifacts_owned.map((id) => (
                  <span
                    key={id}
                    className="px-2 py-1 bg-[var(--bg-tertiary)] rounded text-xs font-mono"
                  >
                    {id}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-sm text-[var(--text-secondary)]">No artifacts owned</p>
            )}
          </Section>

          {/* Recent Actions */}
          <Section title="Recent Actions" badge={agent.actions.length}>
            {agent.actions.length > 0 ? (
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {agent.actions.slice(-10).reverse().map((action, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between text-sm py-1 border-b border-[var(--border-color)]"
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-[var(--text-secondary)]">T{action.tick}</span>
                      <span className={action.success ? '' : 'text-[var(--accent-danger)]'}>
                        {action.action_type}
                      </span>
                      {action.target_id && (
                        <span className="text-xs text-[var(--text-secondary)]">
                          → {action.target_id}
                        </span>
                      )}
                    </div>
                    {!action.success && action.error && (
                      <span className="text-xs text-[var(--accent-danger)]">
                        {action.error}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-[var(--text-secondary)]">No actions yet</p>
            )}
          </Section>

          {/* Recent Thinking */}
          <Section title="Recent Thinking" badge={agent.thinking_history.length}>
            {agent.thinking_history.length > 0 ? (
              <div className="space-y-3 max-h-64 overflow-y-auto">
                {agent.thinking_history.slice(-5).reverse().map((thought, i) => (
                  <div
                    key={i}
                    className="p-3 bg-[var(--bg-primary)] rounded text-sm"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[var(--text-secondary)]">Tick {thought.tick}</span>
                      <span className="text-xs text-[var(--text-secondary)]">
                        {thought.input_tokens}in/{thought.output_tokens}out • ${thought.thinking_cost.toFixed(4)}
                      </span>
                    </div>
                    {thought.reasoning && (
                      <p className="text-[var(--text-secondary)] text-xs line-clamp-3">
                        {thought.reasoning}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-[var(--text-secondary)]">No thinking recorded</p>
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
  subtext,
  valueClass = '',
}: {
  label: string
  value: string
  subtext?: string
  valueClass?: string
}) {
  return (
    <div className="bg-[var(--bg-primary)] rounded p-3">
      <p className="text-xs text-[var(--text-secondary)] mb-1">{label}</p>
      <p className={`text-lg font-semibold ${valueClass}`}>{value}</p>
      {subtext && (
        <p className="text-xs text-[var(--text-secondary)]">{subtext}</p>
      )}
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

function ConfigItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between py-1">
      <span className="text-[var(--text-secondary)]">{label}</span>
      <span className="font-mono">{value}</span>
    </div>
  )
}
