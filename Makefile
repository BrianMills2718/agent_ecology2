# Agent Ecology - Common Commands
# Usage: make <target>

# Get the main repo directory (first worktree listed is always main)
# This ensures we always use main's scripts, not potentially stale worktree copies
MAIN_DIR := $(shell git worktree list | head -1 | awk '{print $$1}')

# Plan #176: Removed worktree-quick (no bypass path for claiming)
.PHONY: help install test mypy lint check validate clean claim release gaps status rebase pr-ready pr pr-create merge finish pr-merge-admin pr-list pr-view worktree worktree-remove worktree-remove-force clean-branches clean-branches-delete clean-worktrees clean-worktrees-auto kill ci-status ci-require ci-optional run dash dash-run analyze

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

# Setup
install:  ## Install dependencies
	pip install -e .
	pip install -r requirements.txt

# Simulation control
kill:  ## Kill all running simulations
	@pkill -f "python run.py" 2>/dev/null && echo "Killed simulation processes" || echo "No simulations running"

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

worktree-list:  ## List active worktrees
	git worktree list

worktree-remove:  ## Remove a worktree safely (usage: make worktree-remove BRANCH=feature-name)
	@if [ -z "$(BRANCH)" ]; then echo "Usage: make worktree-remove BRANCH=feature-name"; exit 1; fi
	python $(MAIN_DIR)/scripts/safe_worktree_remove.py $(MAIN_DIR)/worktrees/$(BRANCH)

worktree-remove-force:  ## Force remove worktree (LOSES uncommitted changes!)
	@if [ -z "$(BRANCH)" ]; then echo "Usage: make worktree-remove-force BRANCH=feature-name"; exit 1; fi
	python $(MAIN_DIR)/scripts/safe_worktree_remove.py --force $(MAIN_DIR)/worktrees/$(BRANCH)

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

merge:  ## Merge PR (usage: make merge PR=5)
	@if [ -z "$(PR)" ]; then echo "Usage: make merge PR=5"; exit 1; fi
	python $(MAIN_DIR)/scripts/merge_pr.py $(PR)

finish:  ## Complete PR lifecycle: merge + cleanup (usage: make finish BRANCH=plan-XX PR=N) - RUN FROM MAIN!
	@if [ -z "$(BRANCH)" ] || [ -z "$(PR)" ]; then echo "Usage: make finish BRANCH=plan-XX PR=N"; exit 1; fi
	cd $(MAIN_DIR) && python $(MAIN_DIR)/scripts/finish_pr.py --branch $(BRANCH) --pr $(PR)

pr-merge-admin:  ## Merge PR bypassing checks (usage: make pr-merge-admin PR=5)
	@if [ -z "$(PR)" ]; then echo "Usage: make pr-merge-admin PR=5"; exit 1; fi
	GIT_CONFIG_NOSYSTEM=1 gh pr merge $(PR) --squash --admin --delete-branch

pr-list:  ## List open PRs
	GIT_CONFIG_NOSYSTEM=1 gh pr list

pr-view:  ## View PR details (usage: make pr-view PR=5)
	@if [ -z "$(PR)" ]; then GIT_CONFIG_NOSYSTEM=1 gh pr view; else GIT_CONFIG_NOSYSTEM=1 gh pr view $(PR); fi

# Simulation (continuous/autonomous mode)
run:  ## Run simulation (usage: make run DURATION=60 AGENTS=2)
	python run.py --duration $(or $(DURATION),60) --agents $(or $(AGENTS),1)

dash:  ## View existing run.jsonl in dashboard (no simulation)
	python run.py --dashboard-only

dash-run:  ## Run simulation with dashboard (usage: make dash-run DURATION=60)
	python run.py --dashboard --duration $(or $(DURATION),60) --agents $(or $(AGENTS),1)

# Dashboard v2 (React)
dash-v2-install:  ## Install dashboard v2 dependencies
	cd dashboard-v2 && npm install

dash-v2-dev:  ## Run dashboard v2 in dev mode (hot reload, proxies to backend)
	cd dashboard-v2 && npm run dev

dash-v2-build:  ## Build dashboard v2 for production
	cd dashboard-v2 && npm run build

dash-v2-test:  ## Run dashboard v2 tests
	cd dashboard-v2 && npm test

dash-v2-types:  ## Generate TypeScript types from API (requires backend running)
	@echo "Fetching OpenAPI spec from http://localhost:9000/openapi.json..."
	cd dashboard-v2 && curl -s http://localhost:9000/openapi.json | npx openapi-typescript /dev/stdin -o src/types/api.ts

analyze:  ## Analyze simulation run (usage: make analyze RUN=logs/latest)
	python scripts/analyze_run.py $(or $(RUN),logs/latest)

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

clean-branches:  ## List stale remote branches (PRs already merged)
	python scripts/cleanup_branches.py

clean-branches-delete:  ## Delete stale remote branches (PRs already merged)
	python scripts/cleanup_branches.py --delete

clean-worktrees:  ## Find and report orphaned worktrees (merged PRs with lingering worktrees)
	python scripts/cleanup_orphaned_worktrees.py

clean-worktrees-auto:  ## Auto-cleanup orphaned worktrees (skips those with uncommitted changes)
	python scripts/cleanup_orphaned_worktrees.py --auto

# CI Configuration
ci-status:  ## Show current CI requirement status
	@echo "Checking branch protection rules..."
	@gh api repos/BrianMills2718/agent_ecology2/rulesets/11737543 --jq '.rules | map(.type) | if any(. == "required_status_checks") then "CI: REQUIRED (blocks merges)" else "CI: OPTIONAL (informational only)" end'

ci-require:  ## Make CI required for merges (costs money when CI runs)
	@echo "Enabling required CI checks..."
	@echo '{"rules":[{"type":"deletion"},{"type":"non_fast_forward"},{"type":"pull_request","parameters":{"required_approving_review_count":0,"dismiss_stale_reviews_on_push":true,"require_code_owner_review":false,"require_last_push_approval":false,"required_review_thread_resolution":true,"allowed_merge_methods":["merge","squash","rebase"]}},{"type":"required_status_checks","parameters":{"strict_required_status_checks_policy":false,"do_not_enforce_on_create":false,"required_status_checks":[{"context":"plans"},{"context":"changes"},{"context":"fast-checks"}]}}]}' | gh api repos/BrianMills2718/agent_ecology2/rulesets/11737543 -X PUT --input - > /dev/null
	@echo "✅ CI is now REQUIRED - merges blocked until CI passes"

ci-optional:  ## Make CI optional (runs but doesn't block merges)
	@echo "Making CI optional..."
	@echo '{"rules":[{"type":"deletion"},{"type":"non_fast_forward"},{"type":"pull_request","parameters":{"required_approving_review_count":0,"dismiss_stale_reviews_on_push":true,"require_code_owner_review":false,"require_last_push_approval":false,"required_review_thread_resolution":true,"allowed_merge_methods":["merge","squash","rebase"]}}]}' | gh api repos/BrianMills2718/agent_ecology2/rulesets/11737543 -X PUT --input - > /dev/null
	@echo "✅ CI is now OPTIONAL - merges work without waiting for CI"
