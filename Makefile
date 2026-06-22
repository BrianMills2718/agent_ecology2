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
	@python scripts/safe_worktree_remove.py worktrees/$(BRANCH)

# === META-PROCESS TARGETS ===
# Added by meta-process install.sh

# Configuration
SCRIPTS_META := scripts/meta
PLANS_DIR := docs/plans
GITHUB_ACCOUNT ?= BrianMills2718
PR_AUTO_EXPECTED_REPO ?= $(notdir $(CURDIR))

# --- Session Start ---
.PHONY: status

status:  ## Show git status
	@git status --short --branch

# --- During Implementation ---
.PHONY: test test-quick check

test:  ## Run pytest
	pytest tests/ -v

test-quick:  ## Run pytest (no traceback)
	pytest tests/ -q --tb=no

check:  ## Run all checks (test, mypy, lint)
	@echo "Running tests..."
	@pytest tests/ -q --tb=short
	@echo ""
	@echo "Running mypy..."
	@mypy src/ --ignore-missing-imports
	@echo ""
	@echo "All checks passed!"

# --- PR Workflow ---
.PHONY: pr-ready pr merge finish pr-auto-check pr-auto

pr-ready:  ## Rebase on main and push
	@git fetch origin main
	@git rebase origin/main
	@git push -u origin HEAD

pr:  ## Create PR (opens browser)
	@gh pr create --fill --web

pr-auto-check:  ## Autonomous PR preflight (branch/clean tree/origin/account)
	@python $(SCRIPTS_META)/pr_auto.py --preflight-only --expected-origin-repo $(PR_AUTO_EXPECTED_REPO) --account $(GITHUB_ACCOUNT)

pr-auto:  ## Autonomous PR create + auto-merge request (non-interactive)
	@python $(SCRIPTS_META)/pr_auto.py --expected-origin-repo $(PR_AUTO_EXPECTED_REPO) --account $(GITHUB_ACCOUNT) --fill --auto-merge

merge:  ## Merge PR (PR=number required)
ifndef PR
	$(error PR is required. Usage: make merge PR=123)
endif
	@python $(SCRIPTS_META)/merge_pr.py $(PR)

finish:  ## Merge PR + cleanup branch (BRANCH=name PR=number required)
ifndef BRANCH
	$(error BRANCH is required. Usage: make finish BRANCH=plan-42-feature PR=123)
endif
ifndef PR
	$(error PR is required. Usage: make finish BRANCH=plan-42-feature PR=123)
endif
	@gh pr merge $(PR) --squash --delete-branch
	@git checkout main && git pull --ff-only
	@git branch -d $(BRANCH) 2>/dev/null || true

# --- Plans ---
.PHONY: plan-tests plan-complete

plan-tests:  ## Check plan's required tests (PLAN=N required)
ifndef PLAN
	$(error PLAN is required. Usage: make plan-tests PLAN=42)
endif
	@python $(SCRIPTS_META)/check_plan_tests.py --plan $(PLAN)

plan-complete:  ## Mark plan complete with verification (PLAN=N required)
ifndef PLAN
	$(error PLAN is required. Usage: make plan-complete PLAN=42)
endif
	@python $(SCRIPTS_META)/complete_plan.py --plan $(PLAN)

# --- Quality ---
.PHONY: dead-code

dead-code:  ## Run dead code detection
	@python $(SCRIPTS_META)/check_dead_code.py

# --- Help ---
.PHONY: help-meta

help-meta:  ## Show meta-process targets
	@echo "Meta-Process Targets:"
	@echo ""
	@echo "  Session:"
	@echo "    status          Show git status"
	@echo ""
	@echo "  Development:"
	@echo "    test            Run tests"
	@echo "    check           Run all checks"
	@echo ""
	@echo "  PR Workflow:"
	@echo "    pr-ready        Rebase + push"
	@echo "    pr              Create PR"
	@echo "    pr-auto-check   Preflight autonomous PR flow"
	@echo "    pr-auto         Non-interactive PR + auto-merge request"
	@echo "    merge           Merge PR (PR=number)"
	@echo "    finish          Merge + cleanup (BRANCH=name PR=number)"
	@echo ""
	@echo "  Quality:"
	@echo "    dead-code       Run dead code detection"
	@echo ""
	@echo "  Plans:"
	@echo "    plan-tests      Check plan tests (PLAN=N)"
	@echo "    plan-complete   Complete plan (PLAN=N)"
