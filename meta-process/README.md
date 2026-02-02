# Meta-Process: AI-Assisted Development Framework

A portable framework for coordinating AI coding assistants (Claude Code, etc.) on shared codebases.

## What This Solves

When multiple AI instances work on the same codebase:
- **Drift** - AI forgets constraints mid-implementation
- **Cheating** - AI writes weak tests that pass but don't verify requirements
- **Big-bang integration** - Days of work, hope it integrates at the end
- **Conflicts** - Two instances start same work, neither knows
- **No traceability** - Can't answer "what tests cover this feature?"

## Core Idea

**Move human review upstream.** Humans can't review code at AI speed, but CAN:
- Review requirements in plain English (Given/When/Then)
- See green/red CI
- Approve specs before implementation

If you trust the spec (human-reviewed) and trust CI (automated), you can trust implementation (green = done) without reading code.

## Quick Start

```bash
# 1. Install into your project
./meta-process/install.sh /path/to/your/project

# 2. Configure what patterns to enable
vim meta-process.yaml

# 3. Start using
make worktree              # Create isolated workspace
# ... do work ...
make pr-ready && make pr   # Ship it
```

## Patterns (Pick What You Need)

### Always Recommended (Low Overhead)
| Pattern | What It Does |
|---------|--------------|
| Plans | Track work with `[Plan #N]` commits |
| Claims | Prevent parallel work conflicts |
| Worktrees | Isolate work from main branch |
| Trivial Exemption | Skip plans for tiny changes |

### Add When Needed (More Setup)
| Pattern | What It Does |
|---------|--------------|
| Doc-Code Coupling | Fail CI when docs drift from code |
| ADR Governance | Link architecture decisions to code |
| Mock Policy | Enforce real tests over mocked tests |
| Acceptance Gates | Lock specs before implementation |

### Heavyweight (Opt-In)
| Pattern | What It Does |
|---------|--------------|
| Locked Specs | Prevent AI from weakening tests |
| Planning Modes | guided/detailed/iterative workflows |
| Inter-CC Messaging | Async communication between AI instances |

## Configuration

All patterns are configured in `meta-process.yaml`:

```yaml
meta_process:
  plans:
    enabled: true
    require_tests: true
  claims:
    enabled: true
  acceptance_gates:
    enabled: false  # Start simple, enable when ready
```

See `templates/meta-process.yaml.example` for all options.

## Directory Structure (After Install)

```
your-project/
├── meta-process.yaml        # Your configuration
├── meta-process/            # Portable framework (copy this to new projects)
│   ├── scripts/             # Baseline scripts (portable)
│   ├── patterns/            # Pattern documentation
│   └── hooks/               # Hook templates
├── scripts/                 # Project-specific scripts (may extend meta-process/)
├── docs/
│   └── plans/               # Implementation plans
├── acceptance_gates/        # Feature definitions (if enabled)
├── hooks/                   # Git hooks
└── .claude/
    └── hooks/               # Claude Code hooks
```

## Portable vs. Project-Specific Scripts

The framework separates **portable** scripts from **project-specific** extensions:

| Directory | Purpose | When to Modify |
|-----------|---------|----------------|
| `meta-process/scripts/` | Baseline scripts that work in any project | Never (modify upstream in meta-process repo) |
| `scripts/` | Project-specific scripts that extend the baseline | Add features specific to your project |

**Example:** `meta-process/scripts/check_doc_coupling.py` is a 283-line baseline. A project might
extend it in `scripts/check_doc_coupling.py` (770 lines) with project-specific checks like
`--bidirectional` or `--check-orphans`.

**When adopting meta-process:**
1. Copy `meta-process/` directory to your project
2. Create project-specific scripts in `scripts/` as needed
3. Project scripts can import from meta-process or replace them entirely

## Full Documentation

See `patterns/` directory for detailed documentation of each pattern:
- `patterns/01_README.md` - Pattern index
- `patterns/15_plan-workflow.md` - How plans work
- `patterns/18_claim-system.md` - How claims work
- `patterns/13_acceptance-gate-driven-development.md` - Full acceptance gate system

## Customizing for Your Project

The patterns are generic but examples come from [agent_ecology2](https://github.com/BrianMills2718/agent_ecology2), the project where this framework was developed. When adopting, replace these project-specific terms in pattern documentation:

| agent_ecology2 term | Replace with |
|----------------------|--------------|
| `scrip` | Your currency/points system (or remove) |
| `principal` | Your user/account concept |
| `artifact` | Your entity/object concept |
| `kernel` | Your core/engine module |
| `ledger` | Your transaction/state store |
| `escrow` | Your holding/pending mechanism (or remove) |
| `genesis` | Your bootstrap/seed data |
| `mint` | Your creation/issuance process (or remove) |

**Most affected patterns** (>20 project-specific terms each): Pattern 13 (Acceptance Gates), Pattern 18 (Claims), Pattern 03 (Testing), Pattern 14 (Gate Linkage). The core concepts in these patterns are fully generic — only the examples need customization.

## Origin

Emerged from the [agent_ecology](https://github.com/BrianMills2718/agent_ecology2) project while coordinating multiple Claude Code instances.

## License

MIT
