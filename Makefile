# Agent Ecology - Common Commands
# Usage: make <target>

# Get the main repo directory (first worktree listed is always main)
# This ensures we always use main's scripts, not potentially stale worktree copies
MAIN_DIR := $(shell git worktree list | head -1 | awk '{print $$1}')

.PHONY: help status worktree worktree-remove test check pr-ready pr finish clean run dash dash-run kill analyze

# --- Core workflow ---

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

status:  ## Show git and claim status
	@echo "=== Git Status ==="
	@git status -sb
	@echo ""
	@echo "=== Active Claims ==="
	@python scripts/check_claims.py --list 2>/dev/null || true

worktree:  ## Create worktree with mandatory claim (interactive)
	@./scripts/create_worktree.sh

worktree-remove:  ## Remove a worktree safely (usage: make worktree-remove BRANCH=name [FORCE=1])
	@if [ -z "$(BRANCH)" ]; then echo "Usage: make worktree-remove BRANCH=feature-name [FORCE=1]"; exit 1; fi
	python $(MAIN_DIR)/scripts/safe_worktree_remove.py $(if $(FORCE),--force,) $(MAIN_DIR)/worktrees/$(BRANCH)

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

finish:  ## Complete PR lifecycle: merge + cleanup (usage: make finish BRANCH=plan-XX PR=N [SKIP_COMPLETE=1]) - RUN FROM MAIN!
	@if [ -z "$(BRANCH)" ] || [ -z "$(PR)" ]; then echo "Usage: make finish BRANCH=plan-XX PR=N [SKIP_COMPLETE=1]"; exit 1; fi
	cd $(MAIN_DIR) && python $(MAIN_DIR)/scripts/finish_pr.py --branch $(BRANCH) --pr $(PR) $(if $(SKIP_COMPLETE),--skip-complete,)

clean:  ## Remove generated files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	rm -f run.jsonl checkpoint.json 2>/dev/null || true

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
	@for hook in pre-commit commit-msg pre-push post-commit; do \
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
