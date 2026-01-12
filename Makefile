# Agent Ecology - Common Commands
# Usage: make <target>

.PHONY: help install test mypy lint check validate clean claim release gaps status pr

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

# Setup
install:  ## Install dependencies
	pip install -e .
	pip install -r requirements.txt

# Testing
test:  ## Run pytest
	pytest tests/ -v --tb=short

test-quick:  ## Run pytest (quiet, no traceback)
	pytest tests/ -q --tb=no

# Type checking
mypy:  ## Run mypy type check
	python -m mypy --strict --ignore-missing-imports --exclude '__pycache__' --no-namespace-packages src/config.py src/world/*.py src/agents/*.py run.py

# Validation
check:  ## Run all CI checks locally
	./check

check-quick:  ## Run all CI checks (quick mode)
	./check --quick

lint:  ## Check doc-code coupling
	python scripts/check_doc_coupling.py --strict

lint-suggest:  ## Show which docs need updates
	python scripts/check_doc_coupling.py --suggest

# Plan/Gap management
gaps:  ## Show gap status summary
	@echo "=== Gap Status ==="
	@python scripts/sync_plan_status.py --list 2>/dev/null || echo "Run from project root"

gaps-sync:  ## Sync plan statuses
	python scripts/sync_plan_status.py --sync

claim:  ## Claim work (usage: make claim TASK="description" PLAN=N)
	python scripts/check_claims.py --claim --task "$(TASK)" $(if $(PLAN),--plan $(PLAN),)

release:  ## Release claim with validation
	python scripts/check_claims.py --release --validate

claims:  ## List active claims
	python scripts/check_claims.py --list

# Git workflow
status:  ## Show git and claim status
	@echo "=== Git Status ==="
	@git status -sb
	@echo ""
	@echo "=== Active Claims ==="
	@python scripts/check_claims.py --list 2>/dev/null || true

branch:  ## Create plan branch (usage: make branch PLAN=3 NAME=docker)
	git checkout -b plan-$(PLAN)-$(NAME)

worktree:  ## Create worktree for parallel CC work (usage: make worktree BRANCH=feature-name)
	@if [ -z "$(BRANCH)" ]; then echo "Usage: make worktree BRANCH=feature-name"; exit 1; fi
	git worktree add ../ecology-$(BRANCH) -b $(BRANCH)
	@echo ""
	@echo "Worktree created at ../ecology-$(BRANCH)"
	@echo "To use: cd ../ecology-$(BRANCH) && claude"
	@echo "To remove when done: git worktree remove ../ecology-$(BRANCH)"

worktree-list:  ## List active worktrees
	git worktree list

worktree-remove:  ## Remove a worktree (usage: make worktree-remove BRANCH=feature-name)
	@if [ -z "$(BRANCH)" ]; then echo "Usage: make worktree-remove BRANCH=feature-name"; exit 1; fi
	git worktree remove ../ecology-$(BRANCH)

pr:  ## Create PR (opens browser)
	gh pr create --web

# Simulation
run:  ## Run simulation (usage: make run TICKS=10 AGENTS=2)
	python run.py --ticks $(or $(TICKS),10) --agents $(or $(AGENTS),1)

# Cleanup
clean:  ## Remove generated files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	rm -f run.jsonl checkpoint.json 2>/dev/null || true

clean-claims:  ## Remove old completed claims
	python scripts/check_claims.py --cleanup
