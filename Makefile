# Agent Ecology - Common Commands
# Usage: make <target>

.PHONY: help status test check pr-ready pr finish clean run dash dash-run kill analyze branches branches-delete

# --- Core workflow ---

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

status:  ## Show git status
	@git status -sb

test: ensure-hooks  ## Run pytest
	pytest tests/ -v --tb=short

check: ensure-hooks  ## Run all CI checks locally
	./check

pr-ready:  ## Rebase and push (run before creating PR)
	git fetch origin
	git rebase origin/main
	git push --force-with-lease

pr:  ## Create PR (opens browser)
	GIT_CONFIG_NOSYSTEM=1 gh pr create --web

finish:  ## Merge PR + cleanup (usage: make finish BRANCH=name PR=N)
	@if [ -z "$(BRANCH)" ] || [ -z "$(PR)" ]; then echo "Usage: make finish BRANCH=name PR=N"; exit 1; fi
	python scripts/merge_and_cleanup.py --branch $(BRANCH) --pr $(PR)

clean:  ## Remove generated files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	rm -f run.jsonl checkpoint.json 2>/dev/null || true

# --- Branch management ---

branches:  ## List stale remote branches (merged PRs, abandoned, etc.)
	python scripts/cleanup_branches.py

branches-delete:  ## Delete stale remote branches with merged PRs
	python scripts/cleanup_branches.py --delete

# --- Simulation ---

run:  ## Run simulation (usage: make run DURATION=60 AGENTS=2)
	python run.py --duration $(or $(DURATION),60) --agents $(or $(AGENTS),1)

dash:  ## View existing run.jsonl in dashboard (no simulation)
	python run.py --dashboard-only

dash-run:  ## Run simulation with dashboard (usage: make dash-run DURATION=60)
	python run.py --dashboard --duration $(or $(DURATION),60) --agents $(or $(AGENTS),1)

kill:  ## Kill all running simulations
	@pkill -f "python run.py" 2>/dev/null && echo "Killed simulation processes" || echo "No simulations running"

analyze:  ## Analyze simulation run (usage: make analyze RUN=logs/latest)
	python scripts/analyze_run.py $(or $(RUN),logs/latest)

# --- Internal (not shown in help) ---

install-hooks:
	@mkdir -p .git/hooks
	@for hook in pre-commit commit-msg post-commit; do \
		if [ -f hooks/$$hook ]; then \
			ln -sf ../../hooks/$$hook .git/hooks/$$hook 2>/dev/null || true; \
		fi; \
	done
	@echo "Git hooks installed (symlinks to hooks/)"

.PHONY: ensure-hooks
ensure-hooks:
	@if [ ! -L .git/hooks/pre-commit ]; then \
		$(MAKE) install-hooks --no-print-directory; \
	fi

# --- Worktree Coordination (parallel CC isolation) ---

worktree:  ## Create worktree (usage: make worktree BRANCH=plan-42-feature)
	@if [ -z "$(BRANCH)" ]; then echo "Usage: make worktree BRANCH=plan-42-feature"; exit 1; fi
	@mkdir -p worktrees
	@git worktree add worktrees/$(BRANCH) -b $(BRANCH) 2>/dev/null || git worktree add worktrees/$(BRANCH) $(BRANCH)
	@echo ""
	@echo "Worktree created: worktrees/$(BRANCH)"
	@echo ""
	@echo "IMPORTANT: Do NOT cd into the worktree."
	@echo "Use absolute paths for file operations."
	@echo "Use git -C worktrees/$(BRANCH) for git commands."

worktree-list:  ## List active worktrees
	@git worktree list

worktree-remove:  ## Safely remove worktree (usage: make worktree-remove BRANCH=plan-42-feature)
	@if [ -z "$(BRANCH)" ]; then echo "Usage: make worktree-remove BRANCH=plan-42-feature"; exit 1; fi
	@python scripts/safe_worktree_remove.py --branch $(BRANCH)
