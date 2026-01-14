# Agent Ecology - Common Commands
# Usage: make <target>

.PHONY: help install test mypy lint check validate clean claim release gaps status rebase pr-ready pr pr-create pr-merge pr-merge-admin pr-list pr-view worktree worktree-quick

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

gaps-check:  ## Check plan status consistency
	python scripts/sync_plan_status.py --check

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

worktree:  ## Create worktree with mandatory claim (interactive)
	@./scripts/create_worktree.sh

worktree-quick:  ## Create worktree without claim (usage: make worktree-quick BRANCH=name) - use only if already claimed
	@if [ -z "$(BRANCH)" ]; then echo "Usage: make worktree-quick BRANCH=feature-name"; exit 1; fi
	@echo "WARNING: Ensure you have already claimed this work!"
	@python scripts/check_claims.py --list
	@echo ""
	@mkdir -p worktrees
	git fetch origin
	git worktree add worktrees/$(BRANCH) -b $(BRANCH) origin/main
	@echo ""
	@echo "Worktree created at worktrees/$(BRANCH) (based on latest origin/main)"
	@echo "To use: cd worktrees/$(BRANCH) && claude"

worktree-list:  ## List active worktrees
	git worktree list

worktree-remove:  ## Remove a worktree (usage: make worktree-remove BRANCH=feature-name)
	@if [ -z "$(BRANCH)" ]; then echo "Usage: make worktree-remove BRANCH=feature-name"; exit 1; fi
	git worktree remove worktrees/$(BRANCH)

rebase:  ## Rebase current branch onto latest origin/main
	git fetch origin
	git rebase origin/main

pr-ready:  ## Rebase and push (run before creating PR)
	git fetch origin
	git rebase origin/main
	git push --force-with-lease

pr:  ## Create PR (opens browser)
	GIT_CONFIG_NOSYSTEM=1 gh pr create --web

pr-create:  ## Create PR from CLI (usage: make pr-create TITLE="Fix bug" BODY="Description")
	GIT_CONFIG_NOSYSTEM=1 gh pr create --title "$(TITLE)" --body "$(BODY)"

pr-merge:  ## Merge PR (usage: make pr-merge PR=5)
	@if [ -z "$(PR)" ]; then echo "Usage: make pr-merge PR=5"; exit 1; fi
	GIT_CONFIG_NOSYSTEM=1 gh pr merge $(PR) --squash --delete-branch

pr-merge-admin:  ## Merge PR bypassing checks (usage: make pr-merge-admin PR=5)
	@if [ -z "$(PR)" ]; then echo "Usage: make pr-merge-admin PR=5"; exit 1; fi
	GIT_CONFIG_NOSYSTEM=1 gh pr merge $(PR) --squash --admin --delete-branch

pr-list:  ## List open PRs
	GIT_CONFIG_NOSYSTEM=1 gh pr list

pr-view:  ## View PR details (usage: make pr-view PR=5)
	@if [ -z "$(PR)" ]; then GIT_CONFIG_NOSYSTEM=1 gh pr view; else GIT_CONFIG_NOSYSTEM=1 gh pr view $(PR); fi

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

# Install git hooks for worktree enforcement
install-hooks:
	@cp scripts/git-hooks/pre-commit .git/hooks/pre-commit
	@chmod +x .git/hooks/pre-commit
	@echo "Git hooks installed"
