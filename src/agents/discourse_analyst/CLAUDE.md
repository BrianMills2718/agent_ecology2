# discourse_analyst Agent (Plan #277)

Research-focused agent for discourse analysis experiments.

## Files

| File | Purpose |
|------|---------|
| `agent.yaml` | Agent configuration with motivation_profile reference |
| `system_prompt.md` | Base system prompt for the agent |

## Key Configuration

- **Motivation profile:** `discourse_analyst` (from `config/motivation_profiles/`)
- **State machine:** questioning → investigating → building → analyzing → reflecting
- **Genotype:** HIGH collaboration, LONG time horizon, BUILD strategy

## The PhD Cycle

This agent follows the researcher pattern:
1. Question - Identify what to understand about discourse
2. Investigate - Gather information, explore existing tools
3. Build - Create new analysis tools when needed
4. Analyze - Apply tools to understand patterns
5. Reflect - Synthesize learnings, generate deeper questions

## Related

- `config/motivation_profiles/discourse_analyst.yaml` - Motivation configuration
- `docs/architecture/current/motivation.md` - Architecture documentation
- Plan #277 - Motivation/emergence configuration
