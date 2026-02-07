# Meta-Process Framework - Claude Code Context

This is the **meta-process framework**, a portable toolkit for coordinating AI coding assistants on shared codebases. It is designed to be copied into other projects via `install.sh`.

---

## What This Is

A collection of **patterns**, **scripts**, **hooks**, and **templates** that solve coordination problems when AI assistants (Claude Code, Cursor, etc.) work on code. Core problems addressed:

| Problem | Solution | Key Files |
|---------|----------|-----------|
| AI forgets project constraints | CLAUDE.md authoring (Pattern 02) | `templates/CLAUDE.md.*` |
| Docs drift from code | Doc-code coupling (Pattern 10) | `scripts/check_doc_coupling.py` |
| Work is untracked | Plan workflow (Pattern 15) | `scripts/parse_plan.py`, `scripts/complete_plan.py` |
| AI guesses instead of investigating | Question-driven planning (Pattern 28) | Plan templates |
| Commit quality degrades | Git hooks (Pattern 06) | `hooks/git/*` |
| Parallel AI instances conflict | Worktree coordination (opt-in) | `*/worktree-coordination/` |

---

## Design Principles

1. **Portable** - Framework must work in any git project. No hardcoded paths, project names, or tool assumptions. Scripts degrade gracefully when dependencies are missing.
2. **Modular** - Core patterns (branch-based workflow) work alone. Worktree coordination is opt-in. Each pattern is independent unless it declares a dependency.
3. **Graceful degradation** - Hooks skip checks when their scripts aren't installed rather than blocking. A minimal install should never break basic git operations.
4. **Human review upstream** - Humans review specs and plans (plain English), not code. If specs are reviewed and CI is green, implementation is trusted.
5. **Configurable weight** - From `minimal` (almost nothing) to `heavy` (full enforcement). Projects choose their overhead level via `meta-process.yaml`.

---

## Architecture

```
meta-process/
├── CLAUDE.md              # THIS FILE - AI context for the framework itself
├── README.md              # Human-facing overview
├── GETTING_STARTED.md     # Adoption guide
├── ISSUES.md              # Framework-level issues tracker
├── install.sh             # Installation script (--minimal or --full)
├── patterns/              # Pattern documentation (26 core patterns)
│   ├── 01_README.md       # Pattern index with dependency graph
│   ├── 02-34_*.md         # Individual patterns
│   ├── TEMPLATE.md        # Template for new patterns
│   └── worktree-coordination/  # Opt-in multi-CC module (5 patterns)
├── scripts/               # Portable Python scripts
│   ├── (13 core scripts)
│   └── worktree-coordination/  # Opt-in multi-CC scripts (6 scripts)
├── hooks/
│   ├── README.md          # Hook reference
│   ├── git/               # Git hook templates (pre-commit, commit-msg, post-commit)
│   └── claude/            # Claude Code hook templates
│       ├── (3 core hooks)
│       └── worktree-coordination/  # Opt-in multi-CC hooks (9 hooks)
├── templates/             # File templates for installed projects
│   ├── CLAUDE.md.*        # CLAUDE.md templates for different directories
│   ├── Makefile.meta      # Make targets to append
│   ├── *.yaml.example     # Config file templates
│   └── worktree-coordination/  # Opt-in templates
└── adr/                   # Framework-level architecture decisions (4 ADRs)
```

### Core vs Opt-In

The framework has two layers:

| Layer | Purpose | Installed by |
|-------|---------|-------------|
| **Core** | Branch-based workflow, plans, hooks, doc-coupling | `install.sh --minimal` |
| **Worktree Coordination** | Multi-CC file isolation, claims, messaging | `install.sh --full` |

Everything in `*/worktree-coordination/` subdirectories is opt-in. Core patterns must never depend on worktree coordination.

### Installation Flow

`install.sh` copies framework files into a target project:

| Source (framework) | Destination (target project) |
|--------------------|------------------------------|
| `scripts/*.py` | `scripts/meta/*.py` |
| `hooks/git/*` | `hooks/*` |
| `hooks/claude/*` | `.claude/hooks/*` |
| `templates/*.yaml.example` | Root config files |
| `templates/CLAUDE.md.*` | Various `CLAUDE.md` files |
| `patterns/*.md` | `docs/meta-patterns/*.md` |

Scripts are installed to `scripts/meta/` in the target project. This means hooks must check **both** `scripts/meta/X` and `scripts/X` paths (the `find_script()` pattern in `hooks/git/pre-commit`).

---

## Key Terminology

| Term | Meaning |
|------|---------|
| **Pattern** | A documented solution to a coordination problem. Lives in `patterns/NN_name.md`. |
| **Plan** | A markdown file tracking a unit of work. `[Plan #N]` in commit messages. |
| **Weight** | Process overhead level: `minimal`, `light`, `medium`, `heavy`. Set in `meta-process.yaml`. |
| **Hook** | Script that runs on git or Claude Code events. Git hooks block/allow; CC hooks can block, warn, or inject info. |
| **Coupling** | A declared relationship between source files and documentation. Enforced by `check_doc_coupling.py`. |
| **Gate** | A specification (Given/When/Then) that locks before implementation. Full acceptance gate system (Patterns 13/14). |
| **Core** | Patterns/scripts that work with simple branch-based workflow. Always installed. |
| **Opt-in module** | Patterns/scripts in `worktree-coordination/` subdirectories. Only installed with `--full`. |

---

## Rules for Editing This Framework

### Portability Is Sacred

- **No hardcoded project names** - Never reference `agent_ecology`, specific repo paths, or project-specific terms in templates, hooks, or scripts
- **No hardcoded tool paths** - Use `command -v` to check if tools exist. Use `find_script()` pattern to locate scripts at either `scripts/meta/` or `scripts/`
- **Graceful degradation** - If a dependency is missing, skip the check (don't fail). Example: pre-commit hook skips mypy if not installed

### Keep Layers Clean

- Core patterns must NOT reference worktree-coordination concepts (claims, worktrees, CWD rules, inter-CC messaging)
- Worktree-coordination patterns CAN reference core patterns (they build on them)
- The `01_README.md` index separates core and opt-in tables clearly

### Pattern Conventions

- Patterns are numbered `NN_name.md` (01-34 currently)
- Each pattern has: Problem, Solution, Files, Setup, Usage, Customization, Limitations
- Dependencies are declared in `01_README.md` Requires column
- New patterns use `TEMPLATE.md`

### Script Conventions

- All scripts are Python, designed to run standalone (`python scripts/meta/X.py`)
- Scripts should work whether run from repo root or via absolute path
- Exit codes: 0 = success/pass, 1 = failure/violation, 2 = error

### Hook Conventions

- Git hooks: exit 0 = allow, exit 1 = block
- Claude Code hooks: exit 0 = allow (may print warnings to stderr), exit 1 = block
- Hooks read tool input from stdin as JSON (for Claude Code hooks)
- Use `check-hook-enabled.sh` to check if a hook is enabled in `meta-process.yaml`

---

## References

| Document | What It Covers |
|----------|----------------|
| `README.md` | Human-facing overview, quick start, pattern tiers |
| `GETTING_STARTED.md` | Step-by-step adoption guide, first week path |
| `patterns/01_README.md` | Full pattern index with dependencies |
| `hooks/README.md` | Hook reference with debugging guide |
| `ISSUES.md` | Framework-level issues and tech debt |
| `adr/` | Architecture decisions (acceptance gates, enforcement) |
| `TRAYCER_COMPARISON.md` | Comparison with Traycer.ai approach |
