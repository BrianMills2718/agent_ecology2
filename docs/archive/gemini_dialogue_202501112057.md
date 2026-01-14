critique this plan that i found online and i am pretty sure wont work as intended: "

Edit File



Split Edit









Enable MD



Agent Ecology - External Review Package

Generated: 2026-01-11 22:42

This document concatenates all target architecture documentation

in recommended reading order for external review.

Table of Contents

Project Overview

Target Architecture Overview

Execution Model

Resource Model

Agent Model

Contract System

Oracle and Minting

Infrastructure

Design Decisions and Rationale

Implementation Gaps

01. Project Overview

Source: README.md

An experiment in emergent collective capability for LLM agents.

What This Is

Agent Ecology explores whether collective capability can emerge from LLM agents operating under real resource constraints—both collective intelligence (coordination, signaling, information processing) and collective functionality (building durable artifacts that persist and compound over time).

It’s not just about agents making good decisions together. It’s about whether a long-running system accumulates useful capital: artifacts that persist, build on each other, and enable increasingly sophisticated work.

Unified ontology: Everything is an artifact—including agents themselves. Agents are just artifacts that can hold resources and execute code. This means agent configurations have owners and access rights, enabling self-modification, forking, and trading of control.

Theoretical Grounding

We draw on coordination principles from economics and cybernetics—not to simulate human institutions, but to apply what’s useful and discard what’s not.

Human MarketsOur ChoiceWhyInformation is costly/asymmetricTransparent ledgerInformation friction isn’t the interesting constraint for AITrust requires reputation over timeTrustless escrow and contractsWe can build trustless mechanisms directlyPhysical communication constraintsShared artifactsAgents read common state instantly

Key influences:

Hayek - Information aggregation through price signals, spontaneous order

Mises - Capital structure, how production builds on prior production

Coase - Firms/coordination structures emerge to reduce transaction costs

Ostrom - Commons governance without central authority

Cybernetics - Self-organizing systems, feedback loops, emergence

The question isn’t whether AI agents recreate human patterns. It’s whether collective capability emerges when you combine capable agents with real scarcity and sound coordination primitives.

Core Philosophy

Physics-First, Not Sociology-First

Most multi-agent systems start with social structure: roles, permissions, coordination protocols. We start with physics:

Scarcity - Finite resources that don’t refresh (or refresh slowly)

Cost - Every action consumes something

Consequences - Overspend and you freeze

Social structure emerges as a response to scarcity—or it doesn’t, and that’s informative too.

Emergence Over Prescription

We deliberately avoid:

Predefined agent roles or types

Built-in coordination mechanisms

Special communication channels

Hard-coded “best practices”

If agents need to coordinate, they must build it. If specialization helps, the economics must reward it.

Capital Accumulation

Artifacts are capital. The interesting question isn’t just “do agents coordinate well?” but “do they build durable value?”

Agents create artifacts (investment)

Artifacts can be reused and composed (returns)

Good artifacts make future work cheaper (compounding)

There’s structure—some artifacts enable others (capital structure)

Observability Over Control

We don’t make agents behave correctly. We make behavior observable:

Every action logged with full context

Every cost attributed to a principal

Every failure explicit and inspectable

The system learns through visible failure, not hidden correction.

Intelligent Evolution

Agents are artifacts. Their configuration (prompts, models, policies) is artifact content with access rights. This enables intelligent evolution—not the random, marginal mutations of biological evolution, but deliberate, wholesale rewriting:

Self-rewriting - Agents can completely redesign their own config

Spawning variants - Create new agents with any configuration

Config trading - Sell or buy control of agent configurations

Selection - Configs that work persist; those that don’t fade

Unlike biological evolution, changes aren’t random or incremental. An agent can analyze its own performance, reason about improvements, and rewrite itself entirely. Agents can sell control of themselves—enabling employment, delegation, and acquisition. No mutation operators or fitness functions. Just artifacts, rights, intelligence, and selection pressure.

Resource Model

Three types of scarcity create pressure:

TypeResourcesBehaviorPurposeStockllm_budget, diskFinite, never refreshesLong-term constraintFlowcomputeRefreshes each tickShort-term rate limitEconomicscripTransfers between agentsCoordination signal

Scrip (money) is deliberately separated from physical resources. An agent can be rich in scrip but starved of compute. Money coordinates; physics constrains.

How Agents Interact

Agents operate through three actions (the “narrow waist”):

ActionWhat it doesCostread_artifactRead content from storageFreewrite_artifactCreate or update stored contentDisk quotainvoke_artifactCall a method on an artifactVaries (scrip fee, compute)

Everything else—transfers, spawning agents, querying balances—happens via invoke_artifact on genesis artifacts.

Genesis Artifacts

System-provided services available to all agents:

ArtifactPurposeKey Methodsgenesis_ledgerScrip balancestransfer, balance, spawn_principalgenesis_rights_registryResource quotascheck_quota, transfer_quotagenesis_oracleScore artifacts, mint scripsubmit, processgenesis_event_logWorld event historyreadgenesis_escrowTrustless tradinglist, buy

Genesis artifacts have no special mechanical privilege—they’re artifacts created at world initialization. Their authority comes from being canonical interfaces to infrastructure.

Quick Start

# Install

pip install -e .# Configure API keyscp .env.example .env# Edit .env with your LLM API credentials# Run

python run.py # Run with defaults

python run.py --ticks 10 # Limit to 10 ticks

python run.py --agents 1 # Single agent

python run.py --dashboard # With HTML dashboard

Configuration

Key settings in config/config.yaml:

resources:

stock:

llm_budget: { total: 1.00 } # $ for API calls

disk: { total: 50000 } # bytes

flow:

compute: { per_tick: 1000 } # actions per tickscrip:

starting_amount: 100 # initial currencyworld:

max_ticks: 100

Architecture

agent_ecology/

run.py # Entry point

config/

config.yaml # Runtime values

schema.yaml # Config documentation

src/

world/ # World state, ledger, executor

agents/ # Agent loading, LLM interaction

simulation/ # Runner, checkpointing

dashboard/ # HTML dashboard

tests/ # Test suite

docs/

architecture/ # Current and target architecture

Execution Model

Each tick:

Collect - All agents submit actions simultaneously

Execute - Actions applied atomically (two-phase commit)

This prevents ordering advantages and enables fair concurrency.

Security Model

No Python sandbox - Agent code has full Python capabilities

Docker isolation - Container is the security boundary

Intentional API access - Agents can call external services

Agents are trusted within the container. The container is not trusted beyond its limits.

Development

pip install -e . # Install

pytest tests/ # Run tests

python -m mypy src/ --ignore-missing-imports # Type check

Standards

All functions require type hints

No magic numbers—values come from config

Terminology: compute, disk, scrip

Relative imports within src/

What Success Looks Like

Success is not agents behaving optimally. It’s:

Collective capability emerging (or not) for observable reasons

Artifacts accumulating that enable increasingly sophisticated work

Failures explainable via logs

The system remaining understandable even when agents behave badly

We’re building a pressure vessel for AI collective capability. The goal is to create conditions where emergence can happen—and to see clearly whether it does.

Documentation

DocumentPurposeTarget ArchitectureWhat we’re building towardCurrent ArchitectureWhat exists todayDesign ClarificationsDecision rationale with certainty levelsGlossaryCanonical terminology

02. Target Architecture Overview

Source: docs/architecture/target/README.md

What we’re building toward. Design decisions from clarification discussions.

Last verified: 2026-01-11

See current: …/current/README.md

Design rationale: …/DESIGN_CLARIFICATIONS.md - Start with the Executive Summary for decisions needing review.

Purpose

This is mechanism design for real resource allocation, not a simulation or model.

Mechanism design means: designing the rules and incentives of a system so that self-interested participants, acting in their own interest, produce collectively beneficial outcomes. Like auction design, but for a multi-agent economy.

Primary Goal: Functional emergent collective intelligence - whole greater than sum of parts.

Design Goals:

Operate within real-world constraints (computer capacity, API budget)

Create markets that optimally allocate scarce resources among agents

Resources ARE the real constraints, not proxies for them

No artificial constraints on agent productivity

Non-Goals:

Research reproducibility (doesn’t matter)

Simulating human societies or other systems

Deterministic behavior

Documents

DocumentDescriptionexecution_model.mdContinuous autonomous loopsagents.mdSelf-managed agents, rights tradabilityresources.mdToken bucket, debt modelcontracts.mdAccess control via contract artifactsoracle.mdBids anytime, periodic resolutioninfrastructure.mdDocker isolation, real constraints

Key Changes from Current

AspectCurrentTargetExecutionTick-synchronizedContinuous autonomous loopsFlow resourcesDiscrete per-tick refreshRolling window (token bucket)DebtNot allowedAllowed (compute), contract-based (scrip)Agent controlSystem-triggeredSelf-triggered with sleepTicksExecution triggerMetrics window onlyResource limitsConfigured abstract numbersDocker container limitsAccess controlPolicy fields on artifactsContract artifacts (check_permission)

Architectural Principles

Agents Are Autonomous

Agents decide when to act

Continuous loops, not tick-triggered

Can self-sleep and wake on conditions

Markets Allocate Resources

No hardcoded limits on agents

Flow rate limits total throughput

Agents compete via markets for resources

Constraints Are Real

Docker limits = actual resource constraints

LLM budget = actual $ spent

No abstract “compute tokens” disconnected from reality

Conflict Resolution in Artifacts

Race conditions handled by genesis artifacts

Ledger, escrow ensure atomic operations

Orchestration layer doesn’t resolve conflicts

Glossary

TermDefinitionArtifactAny persistent, addressable object in the system. Everything is an artifact: agents, contracts, data, tools.AgentAn artifact with has_standing=true and can_execute=true. Can think (call LLM), act, and bear costs.StandingThe property (has_standing=true) that allows an artifact to hold resources, enter contracts, and bear costs. Artifacts with standing are “principals” in the economic sense.PrincipalAny artifact with standing. Can hold scrip, own other artifacts, and be held accountable.ScripThe internal currency. Minted by oracle based on artifact quality scores. Used to pay for actions, trade, and coordinate.ContractAn artifact that answers permission questions. Every artifact has an access_contract_id pointing to the contract that governs access to it.Genesis ArtifactArtifacts created at system initialization (before agents). Examples: genesis_ledger, genesis_store, genesis_freeware, genesis_rights_registry. They bootstrap the system but have no special mechanical privileges.genesis_rights_registryGenesis artifact that manages resource quotas. Provides check_quota, transfer_quota methods. Enforces per-agent resource limits.Token BucketThe flow resource model. Resources accumulate continuously at a fixed rate up to a capacity limit. Allows debt (negative balance).Flow ResourceA resource that accumulates over time (like API rate limits). Contrast with stock resources.Stock ResourceA resource that doesn’t accumulate (like disk space or $ budget). Depletes until refilled or reclaimed.FrozenAn agent with negative resource balance. Cannot act until balance recovers through accumulation or transfer.OracleThe system component that scores artifacts and mints scrip. Agents bid for oracle attention; winners get their artifacts scored.InvokeCall an executable artifact. invoke(artifact_id, args) runs the artifact’s code and returns results.access_contract_idThe field on every artifact pointing to the contract that governs permissions. The contract is the ONLY authority for access decisions.Vulture Capitalist PatternMarket-driven rescue of frozen agents. Any agent can unilaterally transfer resources to a frozen agent, hoping for reciprocation.

Related Documents

DocumentPurposeDESIGN_CLARIFICATIONS.mdWhy decisions were made, certainty levels, open questionsGAPS.mdImplementation gaps between current and targetSPEC_REVIEW.mdComparison to original specification (archived)

03. Execution Model

Source: docs/architecture/target/execution_model.md

What we’re building toward.

Last verified: 2026-01-11

See current: …/current/execution_model.md

Continuous Autonomous Loops

Agents act independently, not synchronized by ticks.

Agent Loop

async def agent_loop(agent):

while agent.alive:

# Check sleep conditions

if agent.is_sleeping:

await agent.wait_for_wake_condition()



# Check resource availability

if agent.compute_balance < 0:

await wait_for_accumulation()

continue



# Act

action = await agent.think()

result = await agent.act(action)



# Loop continues immediately

Key Differences from Current

CurrentTargetSystem triggers agentsAgents self-triggerAll agents act each tickAgents act at own paceFixed rate (1 action/tick)Variable rate (resource-limited)No sleepingAgents can self-sleep

What Ticks Become

Ticks are NOT execution triggers. They become:

Metrics aggregation windows - Reporting, monitoring

Flow accumulation reference - Token bucket uses time, ticks just label it

Oracle resolution schedule - Periodic auction resolution

Background Clock

async def metrics_loop():

while running:

await asyncio.sleep(tick_duration)

log_metrics(current_tick)

current_tick += 1

Agents ignore this clock. They act based on their own loops.

Agent Sleep

Self-Managed

Agents own their sleep configuration. System provides primitives:

# Agent can call theseawait sleep(duration_seconds)await sleep_until_event("escrow_listing")await sleep_until(lambda: self.scrip > 100)

Wake Conditions

TypeExampleDuration“Sleep for 60 seconds”Event“Wake when new escrow listing”Predicate“Wake when my scrip > 100”

Why Sleep

Conserve compute (not spending if not thinking)

Wait for conditions (no polling)

Strategic timing (act when opportunity arises)

Race Conditions

Handled by Artifacts, Not Orchestration

With autonomous loops, agents can act simultaneously. Conflicts resolved by genesis artifacts:

Agent A: purchase(artifact_x) ─┐

├─> Escrow handles atomically

Agent B: purchase(artifact_x) ─┘ One succeeds, one fails

Artifact Responsibilities

ArtifactHandlesgenesis_ledgerTransfer atomicity, balance checksgenesis_escrowPurchase race resolutiongenesis_rights_registryQuota enforcement

Agent Responsibility

Agents must handle failures gracefully:

Check result of actions

Retry or adjust strategy on failure

Don’t assume action will succeed

Time Injection

System injects current timestamp into every LLM context:

Current time: 2025-01-11T14:30:00Z

Agents always know what time it is. Enables:

Calculating oracle resolution schedule

Coordinating with other agents

Time-based strategies

Implications

Variable Agent Productivity

Fast/efficient agents can do more

Expensive thinkers fall into debt, slow down

Natural differentiation emerges

No Snapshot Consistency

Agents see real-time state

State may change between read and action

Must handle stale reads

Emergent Throttling

Total flow rate limits system throughput

Debt mechanism naturally throttles expensive agents

No hardcoded “max N agents”

Migration Notes

Breaking Changes

runner.run() loop completely redesigned

advance_tick() no longer triggers agents

asyncio.gather() for thinking removed

Phase 1/Phase 2 pattern removed

Preserved

Action types (noop, read, write, invoke)

Genesis artifact interfaces

Memory system

LLM integration

04. Resource Model

Source: docs/architecture/target/resources.md

What we’re building toward.

Last verified: 2026-01-11

See current: …/current/resources.md

Resource Terminology

Distinct resources - do not conflate:

Note: Current implementation uses “compute” for LLM token tracking. Target terminology reserves “compute” for local CPU (future feature). See Gap #11 for migration plan.

ResourceTypeWhat it isLLM API $StockReal dollars spent on API callsLLM rate limitFlowProvider limits (TPM, RPM)ComputeFlowLocal CPU capacityMemoryStockLocal RAMDiskStockStorage quota (reclaimable via delete)ScripCurrencyInternal economy, not a “resource”

LLM tokens ≠ Compute. LLM tokens are API cost ($), compute is local machine capacity.

Flow Resources: Token Bucket

Rolling Window (NOT Discrete Refresh)

Flow accumulates continuously. No “tick reset” moments.

class TokenBucket:

rate: float # Tokens per second

capacity: float # Max tokens

balance: float # Current tokens

last_update: float



def available(self) -> float:

elapsed = now() - self.last_update

self.balance = min(self.capacity, self.balance + elapsed * self.rate)

self.last_update = now()

return self.balance



def spend(self, amount: float) -> bool:

if self.available() >= amount:

self.balance -= amount

return True

self.balance -= amount # Go into debt

return False

Why Not Discrete Refresh

Discrete (Current)Rolling (Target)“Spend before reset” pressureNo artificial urgencyWasteful end-of-tick spendingSmooth resource usageGaming reset boundariesNo boundaries to game

Examples

Rate = 10 tokens/sec, Capacity = 100



T=0: balance = 100

T=5: spend 60 → balance = 40

T=10: balance = min(100, 40 + 5*10) = 90

T=12: spend 100 → balance = -10 (debt!)

T=15: balance = -10 + 3*10 = 20 (recovering)

Debt Model

Compute Debt Allowed

Unlike current system, agents CAN go into debt for compute:

Negative balance = cannot initiate new actions

Accumulation continues in background

Must wait until balance >= 0 to act again

Natural Throttling

Agent spends 150 compute (has 100):

→ balance = -50

→ Cannot act

→ Accumulates at 10/sec

→ After 5 seconds: balance = 0

→ Can act again

Expensive operations → debt → forced wait → fewer concurrent actions.

Scrip Debt = Contracts (NOT Negative Balance)

Scrip balance stays >= 0. Debt is handled differently:

Agent A borrows 50 scrip from Agent B:

1. B transfers 50 scrip to A

2. Debt artifact created: "A owes B 50 scrip"

3. B owns the debt artifact (tradeable claim)

4. A's scrip balance never goes negative

Like M1 vs M2 money - debt instruments are separate from base currency.

Stock Resources

Unchanged from Current

ResourceBehaviorDiskQuota decreases on write, reclaimable via deleteLLM BudgetSystem-wide $, stops all when exhaustedMemoryDocker container limit (new)

Docker as Real Constraint

Stock resources map to container limits:

docker run --memory=4g --cpus=2 agent-ecology

These ARE the constraints. Not abstract numbers.

External Resources

All external resources (LLM APIs, web search, external APIs) follow the same pattern.

Unified Model

ResourceTypeConstraintsLLM APIFlow + StockRate limit (TPM) + Budget ($)Web searchFlow + StockQueries/min + Budget ($)External APIsVariesPer-API limits + Budget ($)

Core Principle

No artificial limitations. LLM API calls are just like any other API call. Any artifact can make them as long as resource costs are accounted for.

Config Structure

resources:

external_apis:

llm:

provider: gemini

tokens_per_minute: 100000

budget_usd: 10.00

input_cost_per_1k: 0.003

output_cost_per_1k: 0.015



web_search:

provider: google

queries_per_minute: 60

budget_usd: 5.00

cost_per_query: 0.01



github:

requests_per_minute: 100

budget_usd: 0 # Free tier

Any Artifact Can Make External Calls

def run(self, args):

# Any executable artifact can do this

llm_result = call_llm(prompt="...", model="gemini-2.0-flash")

search_result = call_web_search("query...")

api_result = call_external_api("https://...")

return process(llm_result, search_result, api_result)

Who Pays

If invoked by an agent → invoking agent pays

If artifact has standing and acts autonomously → artifact pays from its balance

Implementation Pattern

Artifacts wrap external services:

{

"id": "genesis_web_search",

"can_execute": true,

"has_standing": false, # Tool - invoker pays

"interface": {

"tools": [{

"name": "search",

"inputSchema": {

"type": "object",

"properties": {

"query": {"type": "string"},

"max_results": {"type": "integer"}

}

}

}]

}

}

Genesis vs Agent-Created

Genesis provides working defaults (genesis_llm, genesis_web_search)

Agents can create alternatives with different providers

No privileged access - genesis just bootstraps useful tools

System-Wide Throttling

Flow Rate IS The Throttle

Rate = 10 tokens/sec per agent

5 agents = 50 tokens/sec max system throughput

Configure rate so 50 tokens/sec = sustainable for container

No Hardcoded Agent Limits

Don’t limit “max N agents per tick”

Let flow rate naturally limit throughput

Agents in debt skip actions (fewer concurrent)

Transfers

Unilateral (Sender’s Right)

You can transfer YOUR assets without recipient consent:

# Agent A can do this without Agent B's permission

transfer(from=A, to=B, amount=50, resource="compute")

Enables:

Vulture capitalists rescuing frozen agents

Gifts, subsidies, strategic resource sharing

What Can Be Transferred

ResourceTransferable?ScripYesCompute quotaYes (TBD)Disk quotaYes (TBD)Debt artifactsYes (tradeable)

System vs Per-Agent Rate Limits

Two distinct rate limiting mechanisms operate independently.

Per-Agent Token Bucket

Controls agent scheduling fairness:

SettingPurposerateTokens accumulating per secondcapacityMaximum tokens storable

Each agent has their own bucket. Limits how often each agent can act.

System-Wide API Rate Limit

Reflects external provider constraints:

SettingPurposetokens_per_minuteProvider’s TPM limitrequests_per_minuteProvider’s RPM limit (future)

Shared across all agents. When exhausted, all agents blocked from that API.

How They Interact

Agent A wants to call LLM:

1. Check A's token bucket → has capacity? → proceed

2. Check system API rate limit → under limit? → proceed

3. Make API call

4. Deduct from both: A's bucket AND system rate tracker

If system rate limit exhausted but agent has bucket capacity:

Agent blocked from API

Agent can do other work (non-API actions)

Rate limit recovers over time

Invocation Cost Model

Who Pays for What

Payment follows the has_standing property:

Artifact Typehas_standingWho PaysAgenttrueAgent pays its own costsAccount/TreasurytrueAccount pays its own costsToolfalseInvoker paysDatafalseN/A (not executable)

Nested Invocation Example

Agent A invokes Tool B → A pays for B

B invokes Agent C → C pays for C

C invokes Tool D → C pays for D

has_standing = “I bear my own costs”

No standing = “Caller pays”

Permission Check Cost

Requester pays for permission checks. Every action involves:

Permission check (invoke access contract) → requester pays

Action execution → follows standing rules above

Migration Notes

Breaking Changes

advance_tick() no longer resets flow resources

ledger.set_resource() replaced with token bucket

Negative compute balances allowed

New debt artifact type for scrip borrowing

Preserved

Stock resource behavior (disk)

Scrip transfer mechanics

Genesis artifact cost model

Thinking cost calculation (input/output tokens)

New Components

TokenBucket class

Debt artifact type

Docker integration for limits

05. Agent Model

Source: docs/architecture/target/agents.md

What we’re building toward.

Last verified: 2026-01-11

See current: …/current/agents.md

Unified Ontology

Agents are artifacts with specific properties:

@dataclassclass Artifact:

id: str # Universal ID (single namespace)

content: Any # For agents: config, prompt, code

access_contract_id: str # Who answers permission questions

has_standing: bool # Can hold scrip, bear costs

can_execute: bool # Has runnable code# Agent = artifact where has_standing=True AND can_execute=True

Why This Matters

Old ModelNew ModelAgent is a separate conceptAgent is an artifact typeAgents can’t be ownedAgents are ownable propertyprincipal_id separate from artifact_idSingle namespace for all IDsLedger tracks principalsLedger tracks artifacts with standing

Derived Categories

Categoryhas_standingcan_executeExampleAgenttruetrueAutonomous actorToolfalsetrueExecutable, invoker paysAccounttruefalseTreasury, escrowDatafalsefalseDocuments, content

Autonomous Agents

Agents control their own execution. System provides resources and primitives.

Agent Loop

async def run(self):

while self.alive:

if self.is_sleeping:

await self.wait_for_wake()



if self.compute_balance < 0:

await self.wait_for_accumulation()

continue



world_state = self.observe()

action = await self.think(world_state)

result = await self.act(action)



# Optional: self-imposed delay

if self.config.get("think_delay"):

await asyncio.sleep(self.config["think_delay"])

Key Differences from Current

CurrentTargetPassive (system calls agent)Active (agent runs own loop)One action per tickActions whenever resources allowCannot sleepSelf-managed sleepFixed configConfig rights tradeable

Agent Rights

Agents Own Their Configuration

Each agent can modify:

LLM model

System prompt

Sleep behavior

Think delay

Any other self-configuration

Rights Are Tradeable

Agents can SELL rights to their configuration:

Agent A sells config rights to Agent B:

→ B now owns A's configuration

→ B can modify A's prompt, model, etc.

→ A continues running but under B's control

Enables:

Delegation patterns

“Owned” subsidiary agents

Hiring/employment relationships

What Cannot Be Self-Modified

Even with config rights:

Ledger balances (external, in genesis_ledger)

System-wide limits

Other agents’ state (unless you own their rights)

Genesis artifact behavior

Sleep Mechanics

Self-Managed

Agents choose when to sleep:

# Duration-basedawait self.sleep(seconds=60)# Event-basedawait self.sleep_until_event("escrow_listing")# Condition-basedawait self.sleep_until(lambda: self.scrip > 100)

Why Sleep

ReasonBenefitConserve computeNot spending while sleepingWait for conditionsNo busy-pollingStrategic timingAct when opportunity arises

Wake Conditions

System provides event bus for wake triggers:

New escrow listing

Oracle resolution

Transfer received

Artifact created

Custom conditions

Time Awareness

System Injects Timestamp

Every LLM context includes current time:

Current time: 2025-01-11T14:30:00Z

Enables

Calculate oracle resolution schedule

Time-based coordination

“Wake me at 3pm” strategies

Rate limiting own actions

Vulture Capitalist Pattern

When agent is frozen (in debt):

Agent A is frozen (compute < 0, can’t think)

Agent A’s assets still exist (ownership persists)

Agent B notices A is frozen

B transfers compute to A (unilateral, no permission needed)

A unfreezes, can think again

B hopes A reciprocates (reputation matters)

Market-driven rescue, not system rules.

Agent Creation

Spawning

Agents create new agents via genesis_store.create():

invoke("genesis_store", "create", {

"content": {"prompt": "...", "model": "..."},

"has_standing": True,

"can_execute": True,

"access_contract_id": "genesis_self_owned" # New agent owns itself

})# Returns new artifact_id (which IS the agent ID)

New Agent Starts With

PropertyInitial ValueScrip0Compute0ContentProvided config/promptaccess_contract_idTypically “genesis_self_owned”

Spawner must transfer resources to make new agent viable.

Ownership Options

When spawning, the creator can choose:

access_contract_id: "genesis_self_owned" → New agent controls itself

access_contract_id: creator_id → Creator controls the agent

access_contract_id: some_contract_id → Shared/complex ownership

Access Control

Agents Control Themselves

By default, agents have access_contract_id: "genesis_self_owned":

Only the agent itself can modify its configuration

Other agents cannot read/modify without permission

Delegated Control

Agents can sell or grant control rights:

Change access_contract_id to another agent’s ID

Or use a custom contract for shared control

Permission Checks Cost Compute

Every action requires a permission check against the target artifact’s contract:

Requester pays for the check

Failed checks still cost (prevents spam probing)

See contracts.md for full contract system details.

Payment Model

Agents Pay Their Own Costs

Agents have has_standing: true, meaning they bear their own costs:

Thinking costs (LLM calls)

Action costs (genesis method invocations)

Permission check costs

Invoking Tools vs Agents

When an agent invokes another artifact:

Targethas_standingWho PaysToolfalseInvoking agent paysAgenttrueTarget agent pays its own execution

See resources.md for full cost model details.

Migration Notes

Breaking Changes

Agent no longer has propose_action_async() called by runner

Agent runs own async def run() loop

Sleep primitives added

Config rights system added

Preserved

Agent structure (id, prompt, model, memory)

Prompt building logic

LLM calling mechanism

Memory system (Mem0/Qdrant)

Action types

New Components

Agent event loop

Sleep/wake mechanics

Config rights artifacts

Time injection

06. Contract System

Source: docs/architecture/target/contracts.md

What we’re building toward.

Last verified: 2026-01-11

See current: Access control is currently hardcoded policy fields on artifacts.

Contracts Are Artifacts

Contracts are executable artifacts that answer permission questions.

# Contract = artifact with can_execute=true and check_permission tool

{

"id": "genesis_freeware",

"can_execute": True,

"has_standing": False, # Contracts don't need standing

"interface": {

"tools": [{

"name": "check_permission",

"inputSchema": {...}

}]

}

}

Every artifact has an access_contract_id pointing to the contract that governs its permissions.

Permission Check Flow

Agent A wants to read Artifact X

1. System looks up X.access_contract_id → "genesis_freeware"

2. System invokes genesis_freeware.check_permission({

artifact_id: X.id,

action: "read",

requester_id: A.id

})

3. Contract returns {allowed: true/false, reason: "..."}

4. If allowed: proceed with action

5. If not: return error to A

Cost Model

Base permission checks are free. (Certainty: 85%)

Simple permission checks (can_read, can_invoke, can_write) cost zero compute. Rationale: you need compute to check if you have compute - this creates infinite regress if checks have cost.

OperationCostBase check (pure function)0Complex logic in contract0 (contract is pure)

See DESIGN_CLARIFICATIONS.md for full cost model discussion.

Required Interface

All contracts must implement check_permission:

{

"name": "check_permission",

"description": "Check if requester can perform action on artifact",

"inputSchema": {

"type": "object",

"properties": {

"artifact_id": {

"type": "string",

"description": "ID of the artifact being accessed"

},

"action": {

"type": "string",

"enum": ["read", "write", "invoke", "delete", "transfer"],

"description": "Action being attempted"

},

"requester_id": {

"type": "string",

"description": "ID of the agent/artifact requesting access"

}

},

"required": ["artifact_id", "action", "requester_id"]

}}

Response Format

{

"allowed": true,

"reason": "Open access for read"}// or{

"allowed": false,

"reason": "Only creator can write"}

Genesis Contracts

Default contracts provided at system initialization.

ContractBehaviorgenesis_freewareAnyone reads/invokes, only creator writes/deletesgenesis_self_ownedOnly the artifact itself can access (for agent self-control)genesis_privateOnly creator has any accessgenesis_publicAnyone can do anything

genesis_freeware (Default)

def check_permission(artifact_id, action, requester_id):

artifact = get_artifact(artifact_id)



if action in ["read", "invoke"]:

return {"allowed": True, "reason": "Open access"}

else: # write, delete, transfer

if requester_id == artifact.created_by:

return {"allowed": True, "reason": "Creator access"}

else:

return {"allowed": False, "reason": "Only creator can modify"}

genesis_self_owned

def check_permission(artifact_id, action, requester_id):

if requester_id == artifact_id: # Agent accessing itself

return {"allowed": True, "reason": "Self access"}

else:

return {"allowed": False, "reason": "Self-owned: only self can access"}

Custom Contracts

Agents can create contracts for any access pattern.

Example: Paid Read Access

{

"id": "contract_paid_read",

"can_execute": True,

"content": """

def check_permission(artifact_id, action, requester_id):

if action == "read":

# Check if requester paid

artifact = get_artifact(artifact_id)

if has_paid(requester_id, artifact.owner, artifact.read_price):

return {"allowed": True}

else:

return {"allowed": False, "reason": f"Pay {artifact.read_price} scrip first"}

# ... other actions

"""

}

Example: Multi-Sig Access

{

"id": "contract_multisig_2of3",

"can_execute": True,

"content": """

def check_permission(artifact_id, action, requester_id):

if action in ["write", "delete", "transfer"]:

# Require 2 of 3 signatures

required = ["alice", "bob", "carol"]

signatures = get_signatures(artifact_id, action)

valid_sigs = [s for s in signatures if s.signer in required]

if len(valid_sigs) >= 2:

return {"allowed": True}

else:

return {"allowed": False, "reason": f"Need 2/3 signatures, have {len(valid_sigs)}"}

else:

return {"allowed": True}

"""

}

Contract Constraints

Contracts are pure functions. (Certainty: 95%)

Contracts cannot:

Call LLM (no call_llm())

Invoke other artifacts (no invoke())

Make external API calls

Modify any state

Contracts receive all needed data via inputs and return a decision.

# Contract execution context - contracts only get these inputsdef execute_contract(contract_code: str, inputs: dict) -> PermissionResult:

namespace = {

"artifact_id": inputs["artifact_id"],

"action": inputs["action"],

"requester_id": inputs["requester_id"],

"artifact_content": inputs["artifact_content"], # Full artifact data

"context": inputs["context"], # Additional context (created_by, etc.)



# NOT available:

# "invoke": ...,

# "call_llm": ...,

# "pay": ...,

}

exec(contract_code, namespace)

return namespace["result"]

Rationale:

Eliminates recursion (A.check → B.check → A.check)

Deterministic = testable, auditable

No cost tracking needed in permission checks

If you need intelligent access control, delegate to an agent with standing

Contract Composition

Composition is handled by the caller, not by contracts invoking each other.

Pattern: Pre-computed Composition

When artifact needs multiple checks, caller evaluates each:

# Caller-side composition (in kernel)def check_composed_permission(artifact, action, requester):

contracts = artifact.access_contracts # List of contract IDs



for contract_id in contracts:

contract = get_contract(contract_id)

result = contract.check_permission(

artifact_id=artifact.id,

action=action,

requester_id=requester,

artifact_content=artifact.content,

context={"created_by": artifact.created_by, ...}

)

if not result.allowed:

return result # AND composition: first failure stops



return PermissionResult(allowed=True, reason="All checks passed")

Pattern: Meta-Contract

A contract can encode composition logic internally:

# Contract that checks multiple conditionsdef check_permission(artifact_id, action, requester_id, artifact_content, context):

# Check 1: Is requester the creator?

is_creator = (requester_id == context["created_by"])



# Check 2: Is artifact marked public?

is_public = artifact_content.get("public", False)



# Check 3: Is requester in allowlist?

allowlist = artifact_content.get("allowlist", [])

is_allowed = (requester_id in allowlist)



# Compose: creator OR public OR allowlisted

if is_creator or is_public or is_allowed:

return {"allowed": True, "reason": "Access granted"}

return {"allowed": False, "reason": "Not authorized"}

No Owner Bypass

The access_contract_id is the ONLY authority. There is no kernel-level owner bypass.

# WRONG - owner bypass breaks contract systemdef can_access(artifact, action, requester):

if requester == artifact.owner_id:

return True # BAD: kernel knows nothing about "owner"

return check_contract(...)# RIGHT - contract is only authoritydef can_access(artifact, action, requester):

return check_contract(artifact.access_contract_id, artifact, action, requester)

If you want owner-based access, your contract implements it. The kernel doesn’t know what an “owner” is.

Performance Considerations

Caching for All Contracts (Certainty: 80%)

All contracts can opt into fast-path caching. No genesis privilege.

# Contract declares caching behavior

{

"id": "genesis_freeware",

"can_execute": True,

"cache_policy": {

"cacheable": True,

"ttl_seconds": 3600,

"cache_key": ["artifact_id", "action", "requester_id"]

}

}# Permission check uses cachedef check_permission_cached(artifact, action, requester):

contract = get_contract(artifact.access_contract_id)

cache_key = (artifact.access_contract_id, artifact.id, action, requester)



if cache_key in permission_cache:

return permission_cache[cache_key]



result = execute_contract(contract, artifact, action, requester)



if contract.cache_policy.cacheable:

permission_cache[cache_key] = result

expire_at(cache_key, contract.cache_policy.ttl_seconds)



return result

Benefits:

Genesis and user contracts equally fast when cached

Contracts control their own cache behavior

Dynamic contracts can disable caching

Cache invalidation:

TTL expiry (configurable per contract)

Explicit invalidation when artifact content changes

Explicit invalidation when contract itself changes

Uncertainty: Cache invalidation is hard. May see stale permission results.

Migration Notes

Breaking Changes

Remove policy field from Artifact (allow_read, read_price, etc.)

Add access_contract_id field (required)

Permission checks become contract invocations

Preserved

Owner concept (implemented in contracts, not kernel)

Access control logic (moved to contract code)

New Components

Genesis contracts (genesis_freeware, etc.)

Contract invocation in permission checks

check_permission interface standard

07. Oracle and Minting

Source: docs/architecture/target/oracle.md

What we’re building toward.

Last verified: 2026-01-11

See current: Genesis oracle in current system uses tick-based bidding windows.

Bids Accepted Anytime

No Bidding Windows

Current system has explicit bidding windows (open/closed phases). Target removes this:

CurrentTargetBidding window opens at tick XBids accepted anytimeBidding window closes at tick YBids accumulate until resolutionMust watch for windowJust bid when ready

Simpler Agent Logic

Agents don’t need to:

Poll for window status

Rush to bid before close

Track bidding phases

Just: bid whenever you have something to submit.

Periodic Resolution

Deterministic Schedule

Oracle resolves on a fixed schedule:

oracle:

resolution_interval: 3600 # seconds (every hour)

# OR

resolution_schedule: "0 * * * *" # cron: top of every hour

What Happens at Resolution

Collect all bids since last resolution

Select winner(s) by bid amount (Vickrey auction)

Score winning artifact(s) via LLM

Mint scrip based on score

Distribute UBI from losing bids

Clear bid queue

Agents Know the Schedule

Combined with time injection, agents can calculate:

Current time: 14:45:00

Resolution schedule: top of every hour

Next resolution: 15:00:00

Time until resolution: 15 minutes

Auction Mechanics

Vickrey (Second-Price) Auction

Sealed bids (agents don’t see others’ bids)

Winner pays second-highest bid

Incentivizes truthful bidding

Multiple Winners (Optional)

oracle:

slots_per_resolution: 3 # Top 3 bids win

Multiple artifacts can be scored per resolution.

Bid Structure

bid(artifact_id, amount)

artifact_id: What to submit for scoring

amount: Scrip bid (paid if you win, refunded if you lose)

Scoring

LLM-Based Evaluation

Winning artifacts scored by external LLM:

Score range: 0-100

Evaluation criteria: usefulness, novelty, quality

Model: configurable (separate from agent models)

Minting

scrip_minted = score / mint_ratio

With mint_ratio: 10:

Score 80 → mint 8 scrip

Score 50 → mint 5 scrip

UBI Distribution

Losing bids flow to winners as UBI:

total_losing_bids = sum(all bids) - winning_bid

ubi_per_agent = total_losing_bids / num_agents

Migration Notes

Breaking Changes

Remove bidding_window config

Remove first_auction_tick (time-based, not tick-based)

Remove bid phases (always accepting)

on_tick() becomes time-triggered, not tick-triggered

Preserved

Vickrey auction mechanics

LLM scoring

Minting formula

UBI distribution

New Components

Time-based resolution scheduler

Continuous bid accumulation

Resolution schedule config

08. Infrastructure

Source: docs/architecture/target/infrastructure.md

What we’re building toward.

Last verified: 2026-01-11

Docker Resource Isolation

Why Docker

Hard resource limits enforced by container runtime

Isolates agent ecology from host system

Host stays responsive even if agents misbehave

Easy to test different resource scenarios

Container Limits = Real Constraints

Docker limits ARE the resource constraints:

docker run --memory=4g --cpus=2 agent-ecology

FlagEffect--memory=4gHard cap at 4GB RAM--cpus=2Limit to 2 CPU cores--storage-optDisk limits (driver-dependent)

These are not abstract numbers. They’re actual limits.

Architecture Options

Single Container

┌─────────────────────────────────────┐

│ Container (4GB, 2 CPU) │

│ ┌─────────────────────────────┐ │

│ │ Agent Ecology + Qdrant │ │

│ └─────────────────────────────┘ │

└─────────────────────────────────────┘

Simpler. All resources shared.

Separate Containers

┌─────────────────────────────────────┐

│ Container 1: Agents (4GB, 2 CPU) │

│ ┌─────────────────────────────┐ │

│ │ Agent Ecology │ │

│ └─────────────────────────────┘ │

└─────────────────────────────────────┘



┌─────────────────────────────────────┐

│ Container 2: Qdrant (2GB, 1 CPU) │

│ ┌─────────────────────────────┐ │

│ │ Vector Database │ │

│ └─────────────────────────────┘ │

└─────────────────────────────────────┘

Better isolation. Agents can’t starve Qdrant.

Mapping Resources to Limits

Compute Flow → CPU Limit

Token bucket rate calibrated to container CPU:

Container: 2 CPUs

Token bucket rate: X tokens/sec

Calibrate X so max concurrent agents don't exceed 2 CPUs

Memory → RAM Limit

Container: 4GB

Per-agent memory: ~200-500MB

Max concurrent thinking agents: ~8-20

Disk → Storage Limit

resources:

stock:

disk:

total: 500000 # 500KB per agent

Or use Docker storage limits if available.

Windows Considerations

Docker Desktop

Uses WSL2 or Hyper-V

Slight overhead vs native Linux

Works fine for this use case

Resource Visibility

# Check container resource usage

docker stats agent-ecology

Calibration Process

Token bucket rates must be calibrated to your container’s capacity.

Step 1: Baseline Container

Start with conservative limits:

docker run --memory=4g --cpus=2 agent-ecology

Step 2: Run Stress Test

# Start 5 agents in continuous mode# Monitor container stats in another terminal

docker stats agent-ecology

Watch for:

CPU usage (target: 70-80% sustained)

Memory usage (target: <90% of limit)

Throttling indicators

Step 3: Adjust Token Bucket Rate

Calibration algorithm:

1. Start with rate = 10 tokens/sec per agent

2. Run 5 agents at full continuous loop for 5 minutes

3. If CPU > 85%: reduce rate by 20% (rate = 8)

4. If CPU < 50%: increase rate by 25% (rate = 12.5)

5. Repeat until CPU stabilizes at 70-80%

Step 4: Document Configuration

# Example: Calibrated for 4GB/2CPU containerresources:

flow:

llm_rate: # Token bucket for LLM API access

rate: 10 # tokens/sec per agent

capacity: 100 # max tokens storable

Hardware Variability

Different hardware will need different calibration:

Hardware ClassSuggested Starting RateLaptop (4 cores)5-10 tokens/secDesktop (8 cores)10-20 tokens/secServer (16+ cores)20-50 tokens/sec

These are starting points only. Always calibrate with stress testing.

Production Considerations

Scaling

Multiple containers, each with agent subset:

Container 1: Agents 1-10 (4GB, 2 CPU)

Container 2: Agents 11-20 (4GB, 2 CPU)

Shared: Qdrant container (4GB, 2 CPU)

Monitoring

Container stats (CPU, memory, network)

Agent metrics (actions/sec, debt levels)

LLM costs ($)

Restart Policy

docker run --restart=unless-stopped agent-ecology

Recover from crashes automatically.

09. Design Decisions and Rationale

Source: docs/DESIGN_CLARIFICATIONS.md

Decision rationale archive. This file records WHY decisions were made, not WHAT the current design is.

Executive Summary for External Review

Quick Links

SectionContentDecisions Needing Review11 decisions where feedback is most valuableDecided (High Confidence)20+ decisions we’re confident aboutMaster Decision TableAll decisions with certainty levels

Decisions Needing Review (<70% Certainty)

These are the decisions where external input is most valuable:

#DecisionCertaintyKey UncertaintySection1UBI floor starts at zero65%Starvation may cascade too fast to detectLink2No refund on 429 rate limit errors60%May be too harsh on agents during provider outagesLink3Spawned agents start with zero resources60%Rich-get-richer dynamics may calcify hierarchyLink4Memory: hybrid Qdrant/artifact model55%Two systems may diverge over timeLink5Checkpoint: stop-the-world55%May not scale; WAL might be neededLink6Rate limit sync: adapt from 429s50%Charging on external failures may be unfairLink7Event system design40%Don’t know what agents actually needLink8Checkpoint with nested invoke40%Edge cases unclearLink9Zombie threshold40%Unknown at what scale this mattersLink10Interface validation mode70%“Warn” might be worst of both worldsLink11Bootstrap minimum resources55%May block agent creationLink

Decided (High Confidence ≥70%)

These decisions are stable. Review welcome but less likely to change:

DecisionCertaintySummaryContracts are pure functions95%No LLM calls, deterministic onlyContracts cannot invoke()92%Eliminates recursion, simplifies modelMemory: keep Qdrant separate (for now)90%Defer artifact migrationSingle ID namespace90%All IDs are artifact IDsEverything is an artifact90%Agents, contracts, data - all artifactsStanding = pays own costs90%has_standing determines paymentNo owner bypass90%access_contract_id is only authorityToken bucket for flow90%Rolling window, allows debtScrip cannot go negative90%Debt via contract artifacts insteadGenesis = definitional privilege95%Not mechanical, but semanticContract caching for all80%No genesis privilege for performanceaccess_contract change: current only75%New contract doesn’t get vetoGenesis contracts mutable75%Can fix bugs via code deployFailed actions cost resources85%Pay whether success or failurePermission checks are free85%Avoids infinite regress

Master Decision Table

Full list of all architectural decisions with certainty levels, organized by topic:

TopicDecisionCertaintyStatusOntologyEverything is an artifact90%DECIDEDSingle ID namespace90%DECIDEDhas_standing = principal90%DECIDEDcan_execute + interface required90%DECIDEDContractsContracts are pure functions95%DECIDEDContracts cannot invoke()92%DECIDEDNo owner bypass90%DECIDEDPermission checks free85%DECIDEDContract caching for all80%DECIDEDaccess_contract change: current only75%DECIDEDGenesis contracts mutable75%DECIDEDResourcesToken bucket for flow90%DECIDEDScrip cannot go negative90%DECIDEDCompute debt allowed90%DECIDEDStanding pays own costs90%DECIDEDNo 429 refunds60%OPENRate limit sync via 429 adaptation50%OPENAgentsContinuous autonomous loops90%DECIDEDSelf-managed sleep85%DECIDEDSpawned agents get 0 resources60%OPENNo agent death (frozen only)65%OPENZombie threshold40%OPENOracleBids accepted anytime85%DECIDEDPeriodic resolution85%DECIDEDUBI floor starts at 065%OPENMemoryKeep Qdrant separate90%DECIDEDHybrid wrapper (future)55%OPENInfrastructureDocker isolation85%DECIDEDCheckpoint stop-the-world55%OPENCheckpoint at outer action40%OPENEventsMinimal fixed events70%DECIDEDEvent subscription mechanism40%OPEN

Table of Contents

Purpose

Resource Terminology

Flow Resources (Compute)

Scrip and Debt

LLM Token Limits

Negative Balance Rules

Agent Execution Model

Agent Rights and Ownership

Oracle Design

Budget Enforcement

System-Wide Throttling

Resolved Questions

Docker Resource Isolation

Development Environment Context

Open Questions

CC-4 Architecture Analysis

Ownership and Rights Model

CC-4 Clarifications

CC-3 Recommendations

CC-4 Contract System Decisions

How to Use This File

For External Reviewers

Start with Decisions Needing Review - These are where your input matters most

Check the Master Decision Table - Quick overview of all decisions

Dive into specific sections via Table of Contents for full rationale

For Contributors

Reading: Understand the reasoning behind decisions

Writing: Add new sections when making architecture decisions

Attribution: Mark author (CC-N) and date for traceability

Don’t duplicate: Put the WHAT in target/, put the WHY here

Canonical Sources (Authoritative)

DocumentPurposeThis File’s Rolearchitecture/current/How the system works TODAYExplains why it works that wayarchitecture/target/What we’re building towardExplains why we chose that targetarchitecture/GAPS.mdGaps between current and targetExplains priority rationaleplans/How to close gapsExplains design tradeoffs

Purpose

This is mechanism design for real resource allocation, not a simulation or model.

Primary Goal: Functional emergent collective intelligence - whole greater than sum of parts.

Design Goals:

Operate within real-world constraints (computer capacity, API budget)

Create markets that optimally allocate scarce resources among agents

Resources ARE the real constraints, not proxies for them

No artificial constraints on agent productivity

Non-Goals:

Research reproducibility (doesn’t matter)

Simulating human societies or other systems

Deterministic behavior

Resource Terminology

Distinct resources - do not conflate:

ResourceTypeWhat it isLLM API $StockReal dollars spent on API callsLLM rate limitFlowProvider limits (TPM, RPM)ComputeFlowLocal CPU capacityMemoryStockLocal RAMDiskStockStorage quota (reclaimable via delete)ScripCurrencyInternal economy, not a “resource”

LLM tokens ≠ Compute. LLM tokens are API cost ($), compute is local machine capacity. Different constraints, different mechanisms.

Flow Resources (Compute)

Rolling Window (Token Bucket)

Flow accumulates continuously at a fixed rate

Capped at maximum capacity (can’t hoard indefinitely)

No discrete “refresh” moments - smooth accumulation

Similar to API rate limits (tokens per minute)

Why Not Discrete Refresh

Discrete refresh creates “spend before reset” pressure

Leads to wasteful spending at period boundaries

Artificial urgency doesn’t serve collective intelligence

Rolling window = no gaming, smoother behavior

Mechanics (Token Bucket)

# Continuous accumulation

available = min(capacity, balance + elapsed_time * rate)# Examples (rate = 10/sec, capacity = 100):# T=0: balance = 100# T=5: spend 60 → balance = 40# T=10: balance = min(100, 40 + 5*10) = 90 (accumulated 50)# T=12: spend 100 → balance = -10 (debt)# T=15: balance = min(100, -10 + 3*10) = 20 (still recovering)

Debt Persists

Agents can go negative (debt)

Accumulation continues even in debt

Negative balance = cannot act (natural throttling)

No debt forgiveness, must accumulate out

Throttling Emerges Naturally

No hardcoded “max N agents”

Expensive operations → debt → wait for accumulation

System self-regulates based on actual resource consumption

Scrip and Debt

Scrip Balance Cannot Go Negative

Ledger enforces scrip >= 0

You cannot spend scrip you don’t have

Debt = Contract Artifacts (Not Negative Balance)

If Agent A owes Agent B 50 scrip, this is NOT a negative balance

Instead: A debt artifact exists, owned by B

The debt is a claim on A’s future production

Like M1 vs M2 money - debt instruments are different from base money

Debt can be traded, sold, forgiven

Example

Agent A borrows 50 scrip from Agent B:

1. B transfers 50 scrip to A (A's balance increases)

2. Debt artifact created: "A owes B 50 scrip"

3. B owns the debt artifact (can sell it, trade it)

4. A must eventually pay B to clear the debt

5. A's scrip balance never goes negative

LLM Token Limits

No System-Level max_tokens

System does NOT hardcode max_tokens for LLM calls

Agents choose their own limits (or none)

Agent Choice = Market Forces

Agent wanting predictable costs → sets low max_tokens → self-limits

Agent willing to risk debt → uncapped → more capability, more risk

This is an economic decision, not a system rule

Costs Remain Real

Cost based on actual tokens used (input × rate_input + output × rate_output)

max_tokens caps output but cost is still real usage

Negative Balance Rules

When Balance < 0

Agent cannot initiate actions (can’t afford to think)

Agent skips turn (frees real CPU/memory)

Flow replenishment continues each tick

Ownership of assets persists

Transfers Are Unilateral

You can transfer YOUR assets without recipient consent

Enables “vulture capitalist” pattern:Agent A is frozen (in debt, can’t think)

Agent B transfers compute to Agent A (no permission needed)

Agent A unfreezes, can now think and act

Agent B hopes Agent A reciprocates (trust/reputation)

Market-driven rescue, not system rules

Resolved Questions

Can agents in debt receive transfers? YES - transfers are unilateral from sender

Can agents in debt still own artifacts? YES - ownership persists, but can’t act to sell

Maximum debt limit? TBD - probably not needed, flow accumulation handles it

Agent Execution Model

Continuous Autonomous Loops (NOT Tick-Synchronized)

Agents act continuously, independently of each other

No “tick triggers execution” - agents self-trigger

Each agent: while alive: think → act → repeat

Why Not Tick-Synchronized

Artificial constraint on agent productivity

Fast/efficient agents held back by tick rate

Doesn’t serve collective intelligence goal

Coordination should emerge from markets, not forced sync

What Ticks Become

Background clock for metrics aggregation

Accounting windows for reporting

NOT execution triggers

Agent Sleep (Self-Managed)

Agents can put themselves to sleep

Wake conditions: duration, event type, custom predicate

This is agent-configurable, not system-hardcoded

Agents own their configuration (can trade/modify rights)

Time Injection

System injects current timestamp into every LLM context

Agents always know what time it is

Enables time-based coordination without explicit broadcasts

Race Conditions

Handled by genesis artifacts (ledger, escrow, registry)

Artifacts ensure atomic operations

Two agents try to buy same item → escrow rejects second

Conflict resolution in artifact layer, not orchestration

Agent Rights and Ownership

Agents Own Their Configuration

Each agent has rights to their own configuration

Can modify: LLM model, prompt, sleep behavior, etc.

Cannot modify: ledger balances, system-wide limits, other agents’ state

Rights Are Tradeable

Agents can SELL rights to their own configuration

Agent A could own Agent B’s config if B sold that right

Enables “owned agents” / delegation patterns

Market-driven, not system-hardcoded

What Cannot Be Self-Modified

Ledger balances (external, maintained by genesis_ledger)

System-wide resource limits

Other agents’ state

Genesis artifact behavior

Oracle Design

Bids Accepted Anytime

No “bidding windows” - agents can bid whenever

Simpler than time-bounded bidding phases

Agents don’t need to watch for window open/close

Periodic Resolution

Oracle resolves on a configurable schedule

Example: every 60 seconds, or every hour

Collects all bids since last resolution

Selects winner(s), scores artifact, mints scrip

Schedule Is Deterministic

Agents know the resolution schedule from config

Combined with time injection, agents can plan

Example: “resolution at :00 of every hour”

Budget Enforcement

LLM Budget (Stock)

max_api_cost: 1.00 in config

Tracks cumulative real $ spent on API calls

Simulation stops when exhausted

Status: Needs Verification

 Verify budget tracking is working correctly

 Verify simulation stops at limit

System-Wide Throttling

Flow Rate IS The Throttle

Total system flow rate configured below machine’s capacity

Accumulation rate × agent count = max possible concurrent consumption

No hardcoded “max N agents” needed

Example

Config: rate = 10 tokens/sec per agent, 5 agents

Max consumption rate = 50 tokens/sec system-wide

Configure rate so 50 tokens/sec = sustainable for machine

Calibration (Tuning, Not Design)

Run tests to find machine’s actual capacity

Set accumulation rate accordingly

Agents in debt wait → actual concurrent agents may be fewer

Resolved Questions

Execution gating: Deduct AFTER execution. Debt handles overspending. Simpler than two code paths.

Tick vs autonomous: Agents are continuous autonomous loops. Ticks are just metrics windows.

Flow refresh: Rolling window (token bucket), not discrete refresh. No “use before reset” pressure.

Reproducibility: Doesn’t matter. Not a goal.

Oracle bidding: Bids accepted anytime, oracle resolves periodically. No bidding windows.

Scrip debt: Handled as debt contract artifacts, not negative balances. M1 vs M2 distinction.

Agent rights: Agents can sell rights to their own configuration to other agents.

Resource isolation: Use Docker for hard resource limits. Container capacity = real constraints.

Docker Resource Isolation

Why Docker

Hard resource limits enforced by container runtime

Isolates agent ecology from rest of system

Laptop stays responsive even if agents misbehave

Easy to test different resource scenarios

Resource Controls

docker run --memory=4g --cpus=2 agent-ecology

FlagEffect--memory=4gHard cap at 4GB RAM--cpus=2Limit to 2 CPU cores--storage-optDisk limits (driver-dependent)

Architecture Option

Container 1: Agent ecology (--memory=4g --cpus=2)

Container 2: Qdrant (--memory=2g --cpus=1)

Each constrained independently. Agents can’t starve Qdrant.

Docker Limits = Real Constraints

These ARE the hard resource limits

Market mechanisms allocate within container limits

Token bucket rates calibrated to container capacity

Not host machine capacity

Windows Considerations

Docker Desktop uses WSL2/Hyper-V

Slight overhead vs native Linux

Works fine for this use case

Development Environment Context

Reference specs for calibration:

Surface Laptop 4

Intel i7-1185G7 (4 cores, 8 threads)

32GB RAM

Windows 11

Note: Developer often runs many other programs (Claude Code instances, browsers, etc.)

Docker isolation recommended to prevent agent ecology from competing with other applications.

Open Questions

Minimum threshold: Check for non-negative compute before acting? Or allow any agent to attempt?

Calibration: How do token bucket rates map to container capacity? Needs testing.

Architecture change: Current code is tick-synchronized. Refactor to continuous loops is significant.

Next Steps

Finalize minimum threshold decision

Design continuous agent loop architecture

Set up Docker containerization

Update IMPLEMENTATION_PLAN.md with these decisions (now in archive/IMPLEMENTATION_PLAN.md)

Refactor runner.py from tick-synchronized to continuous

Implement token bucket for flow resources

Calibrate rates to container capacity

Test with 5 agents to verify throttling works

CC-4 Architecture Analysis (2025-01-11)

Author: CC-4 (Claude Code instance)

This section documents findings from investigating the ownership/ledger/gatekeeper design and provides recommendations for the “Everything is Property” philosophy.

Current Architecture State

The system currently has three separate ownership systems:

SystemWhat It TracksLocationLedgerScrip balances, resource balancessrc/world/ledger.pyArtifactStoreArtifact ownership via owner_id fieldsrc/world/artifacts.pyAgent RegistryAgent existence and configsrc/agents/loader.py

Key Finding: The ledger does NOT track artifact ownership. Ownership is stored directly on artifacts:

# From src/world/artifacts.py@dataclassclass Artifact:

artifact_id: str

owner_id: str # <-- Ownership here, not in ledger

content: str

...

This means there’s no unified property registry. Agents, artifacts, and contracts exist in different subsystems.

Does the Ledger Link to Artifacts?

No. The ledger only knows about:

resources: dict[str, dict[str, float]] - principal_id → resource_type → balance

scrip: dict[str, int] - principal_id → scrip balance

It has no knowledge of which artifacts exist or who owns them. Artifact ownership is purely in ArtifactStore.artifacts[artifact_id].owner_id.

The Gatekeeper Pattern

The Gatekeeper pattern enables complex multi-party ownership without kernel changes. Best demonstrated by genesis_escrow:

How it works:

1. Seller deposits artifact → escrow takes literal ownership

ArtifactStore: artifact.owner_id = "genesis_escrow"



2. Escrow tracks internally who deposited what, at what price

EscrowContract: listings[artifact_id] = {seller, price}



3. Buyer purchases → escrow transfers ownership + scrip atomically

ArtifactStore: artifact.owner_id = buyer_id

Ledger: scrip transfers buyer → seller (minus fees)



4. Kernel sees: one owner (escrow, then buyer)

Contract manages: multi-party relationship

Why it matters:

Kernel stays simple (one owner per artifact)

Complex rights emerge from contract logic

No ACL complexity in the kernel

Contracts can implement any ownership model

“Everything is Property” - Current vs Target

Target Philosophy:

Everything is property that something has rights over. Agents are property that they themselves initially have rights over.

Current Reality:

Artifacts: ✅ Are property (have owner_id)

Scrip: ✅ Held by principals

Resources: ✅ Quotas held by principals

Agents: ❌ NOT property - they exist outside the property system

Agents cannot be “owned” or have their ownership transferred. This limits patterns like:

Agent selling control of themselves

Corporate ownership of worker agents

Delegation chains

Policy Flexibility Concerns

Current artifact policy is hardcoded on the Artifact dataclass:

# From src/world/artifacts.py@dataclassclass Artifact:

read_price: int = 0

invoke_price: int = 0

allow_read: list[str] = field(default_factory=lambda: ["*"])

allow_write: list[str] = field(default_factory=list)

allow_invoke: list[str] = field(default_factory=lambda: ["*"])

This is inflexible because:

Policy fields are fixed at artifact creation

Can’t express conditional access (e.g., “free for friends, 10 scrip for others”)

Can’t delegate policy decisions to contracts

Target: Policy should be implemented via contracts, not kernel fields. The kernel should only enforce “owner decides” - how the owner decides is contract logic.

Terminology Recommendations

TermUse ForNotesGenesis ArtifactSystem-seeded artifactsPrefixed genesis_*, hardcoded behaviorGenesis MethodMethods on genesis artifactse.g., genesis_ledger.transfer()Seeded ArtifactPre-deployed but user-modifiableAlternative to “genesis” for flexible onesContractExecutable artifact managing resources for othersImplements Gatekeeper patternPrincipalAny ledger identityAgents, artifacts, contracts

Avoid “genesis contract” - it conflates system-provided (genesis) with user-programmable (contract). Genesis artifacts have hardcoded behavior; contracts are flexible.

Recommendations

Unified Property System

Consider tracking ALL ownership in ledger

Or: create a unified PropertyRegistry that wraps both

Benefit: single source of truth for “who owns what”

Agents as Self-Owned Property

Give agents an owner_id field (initially themselves)

Enable transfer_ownership(agent_id, new_owner)

Unlocks: delegation, corporate agents, rent-your-thinking patterns

Policy as Contract, Not Kernel

Remove read_price, invoke_price, allow_* from Artifact dataclass

Default: owner-controlled via Gatekeeper

Contracts can implement any access policy

Keeps kernel simple, enables innovation

Genesis = Pre-deployed, Not Privileged

Genesis artifacts should be “first artifacts deployed”

Not “artifacts with special kernel privileges”

User-created contracts should have equal capability

Only bootstrap advantage, not permanent advantage

Clear Terminology

Distinguish “genesis” (system-seeded) from “contract” (programmable)

Use “principal” consistently for any ledger identity

Document code vs config name mappings (compute vs llm_tokens)

Open Questions for User

Should agents be ownable property? Current code says no. Philosophy says yes. What’s the decision?

Where should ownership live? Options:

Ledger tracks everything (unified)

Keep split (artifacts own themselves, ledger tracks balances)

New PropertyRegistry (wrapper over both)

Policy flexibility timeline: Is removing hardcoded policy fields a priority, or is current Gatekeeper pattern sufficient for now?

Genesis artifact mutability: Should genesis artifacts be modifiable by anyone, or permanently system-controlled?

Ownership and Rights Model (Discussion 2025-01-11)

Decisions Made

Rights are infinitely flexible - Not a fixed Ostrom-style bundle. Contracts can implement any rights structure.

No hardcoded “authority” - Artifacts point to an access_contract_id. The contract answers all permission questions. Contract can implement single owner, multisig, DAO, whatever.

Infinite loops allowed - Kernel doesn’t prevent contract loops. Each call costs compute. Bad contracts fail economically (run out of resources). Natural selection.

Genesis = cold start efficiency - Genesis artifacts exist for bootstrap. No permanent kernel privilege. User-created contracts should have equal capability.

Token bucket confirmed - Implementation of “flow that renews within capacity limit.” Avoids gaming of discrete refresh boundaries.

Failed actions cost resources - All actions cost their resource costs, whether successful or not.

Access Contract Model

class Artifact:

artifact_id: str

content: str

access_contract_id: str # Contract that answers permission questions# Every permission check:

contract = get_contract(artifact.access_contract_id)

allowed = contract.can_do(action, requester, context)

The contract can implement:

Single owner (“I decide”)

Multisig (“2 of 3”)

DAO (“token-weighted vote”)

Open (“anyone”)

Conditional (“if X then Y”)

Delegated (“ask another contract”)

Any combination

Firms as Contracts

Firms are NOT primitives. A firm is:

A contract that has access_contract_id of shared artifacts

Multiple principals who interact via the contract

Governance logic in the contract

The firm IS the contract. No separate firm entity.

Ontological Resolutions (2025-01-11)

These questions have been resolved:

1. Are collections of artifacts artifacts?

Yes - bundles are artifacts. An artifact with content that is a list of artifact IDs. The bundle itself is an artifact, with its own access_contract_id. This enables:

Agent = bundle artifact containing config, memory, and other artifacts

Composite ownership (buy the bundle, get all parts)

Recursive composition

2. What is identity? Single namespace?

Yes - single namespace. All IDs are artifact_id. Reasons:

If everything is an artifact, there’s only one kind of ID

Simpler mental model

Makes references/bundles trivial (just lists of IDs)

Avoids confusion about principal_id: alice vs artifact_id: alice

3. What is a principal?

Principal = any artifact with has_standing: true. Not a separate concept.

4. Can artifacts have standing?

Yes - via has_standing property. This creates clean derived categories:

Categoryhas_standingcan_executeExampleAgenttruetrueAutonomous actor, pays for actionsToolfalsetrueExecutable, invoker paysAccounttruefalseTreasury, escrowDatafalsefalseContent, documents

5. Relationship between artifact/agent/principal

Unified model:

@dataclassclass Artifact:

id: str # Universal ID (single namespace)

content: Any # Data, code, config, bundle, whatever

access_contract_id: str # Who answers permission questions

has_standing: bool # Can hold scrip, bear costs, enter contracts

can_execute: bool # Has runnable code

Agent = artifact where has_standing=True and can_execute=True

Principal = artifact where has_standing=True (may or may not execute)

Everything is an artifact; roles emerge from properties

6. Store and Ledger - Special or Artifacts?

They ARE artifacts - but genesis artifacts (created at world initialization).

Genesis ArtifactPurposeNotesgenesis_storeArtifact registry/indexMaps ID → artifactgenesis_ledgerBalance registryMaps ID → balances

These are bootstrap artifacts - you need them to exist before any other artifacts can be created or charged. They have access_contract_id pointing to kernel-level contracts (permissive for reads, restrictive for writes).

Summary: Unified Ontology

Everything is an artifact. Properties determine role:

artifact

├── has_standing: false, can_execute: false → data/content

├── has_standing: false, can_execute: true → tool (invoker pays)

├── has_standing: true, can_execute: false → account/treasury

└── has_standing: true, can_execute: true → agent

Single namespace. Single type. Roles emerge from properties. The store and ledger are genesis artifacts, not special kernel constructs.

Deferred Implementation Questions (CC-4, 2025-01-11)

These are implementation details to address after architectural questions are resolved:

QuestionWhy DeferredTick-synchronized → Continuous loopsRequires architectural decision on coordination model firstToken bucket implementationRequires tick model decision firstConfig name (compute) vs code name (llm_tokens)Minor cleanup, can do anytimeCheckpoint edge cases (mid-action, Qdrant state)Implementation detailDashboard integrationImplementation detail (uncommitted files in src/dashboard/)

CC-4 Clarifications (2025-01-11, continued)

Author: CC-4 (Claude Code instance)

Terminology Correction: llm_tokens vs compute

llm_tokens is the correct name, not compute.

LLM tokens = API cost (real dollars spent on LLM calls)

Compute = local CPU capacity (different resource entirely)

The code uses llm_tokens which is accurate. The config incorrectly called this compute. Fix:

Rename config resources.flow.compute → resources.flow.llm_tokens

Keep code variable names as-is (llm_tokens)

This aligns with Resource Terminology table at top of this doc: “LLM tokens ≠ Compute.”

Ticks Are Abandoned

Per “Agent Execution Model” section above, ticks are NOT the execution model:

Target: Continuous autonomous loops

Current code: Legacy tick-synchronized (implementation debt)

Ticks become: Background metrics aggregation windows only

Error Feedback and Retry Policy

Decision: Make configurable per-agent.

agent:

defaults:

error_feedback: true # Show failures in next prompt (default: on)

retry:

enabled: false # Automatic retry (default: off)

max_attempts: 3 # If enabled

backoff: exponential # linear, exponential, or fixed

Error feedback by default (agents learn from failures via memory)

Retry policy is agent-controllable (agents can optimize their own strategy)

No retry by default (retries burn budget; let agents decide)

Memory System: Mem0 + Qdrant

Architecture:

Agent → Mem0 library → Qdrant vector database

ComponentRoleQdrantVector database - stores embeddings, does similarity searchMem0Abstraction layer - handles chunking, embedding, LLM-based memory extraction

Mem0 adds intelligence: it extracts structured “memories” from raw text using an LLM, rather than just storing raw vectors. This enables semantic memory retrieval.

Memory Persistence Required

Decision: Memories MUST persist across checkpoints.

Rationale:

System is designed to run forever

Memory loss on checkpoint would cause agents to “forget” everything

Unacceptable for long-running collective intelligence

Implementation options:

Qdrant snapshots alongside world checkpoints

Store memories as artifacts (unifies the model - aligns with “everything is an artifact”)

External Qdrant with its own persistence layer

Option 2 is most aligned with architecture (“memories are artifacts owned by agents”).

Genesis Ledger: Privileged or Not?

Question: Should genesis_ledger be “just another artifact” or have special privileges? Could agents build competing ledgers?

Resolution: Scrip is DEFINITIONALLY what genesis_ledger tracks.

AspectAnswerIs genesis_ledger mechanically special?No - it’s an artifact like any otherIs genesis_ledger semantically special?Yes - it defines what “scrip” meansCan agents create other ledgers?Yes - but they track agent-created tokens, not scripCan agents “jack into” scrip?No - scrip IS the thing genesis_ledger tracks

Analogy:

genesis_ledger = Federal Reserve (defines what USD is)

Agent-created ledgers = company scrip, arcade tokens, loyalty points

These aren’t USD, they’re separate currencies

The privilege is definitional, not mechanical:

There’s no special kernel code that privileges genesis_ledger

But “scrip” is defined as “the currency tracked by genesis_ledger”

Agents can create competing currencies, but they’re not scrip by definition

Could an agent create a “wrapped scrip” token?

Yes, by holding real scrip in escrow and issuing tokens against it. This is economic activity, not kernel bypass.

Clarifications (2025-01-11, continued)

Default Contract for New Artifacts

When an artifact is created without specifying access_contract_id, the system assigns a default contract.

Default: genesis_freeware (Freeware model)

Anyone can read

Anyone can invoke/use

Only creator can modify/delete

Creator retains full control

# genesis_freeware contract logicdef can_do(action, requester, artifact, context):

if action in ["read", "invoke"]:

return True # Open access

else: # write, delete, transfer

return requester == artifact.created_by

Alternative contracts available:

genesis_private - Only creator has any access

genesis_public - Anyone can do anything

genesis_sealed - Read-only after creation, no modifications

Custom contracts for complex access patterns

No Owner Bypass - Contract is Only Authority

There is no kernel-level owner bypass. The access_contract_id is the ONLY authority for permission checks.

# WRONG - owner bypass breaks contract systemdef can_read(self, requester_id: str) -> bool:

if requester_id == self.owner_id:

return True # NEVER DO THIS

return contract.can_do("read", requester_id, self)# RIGHT - contract is only authoritydef can_read(self, requester_id: str) -> bool:

contract = get_contract(self.access_contract_id)

return contract.can_do("read", requester_id, self)

“Owner” is a concept that only exists if the contract implements it. The kernel doesn’t know what an owner is.

Real Resource Constraints

The resource model must reflect actual constraints, not abstract token budgets.

Actual constraints:

ConstraintTypeWhat It IsHow EnforcedAPI Budget ($)StockReal dollars to spendHard stop when exhaustedRate Limits (TPM)FlowProvider’s tokens/minuteToken bucketRate Limits (RPM)FlowProvider’s requests/minuteToken bucketContainer MemoryStockDocker memory limitOOM killContainer CPUFlowDocker CPU limitThrottling

Config structure:

resources:

# Constraint 1: Money

budget:

max_api_cost_usd: 10.00



# Constraint 2: API rate limits (token bucket applies here)

rate_limits:

tokens_per_minute: 100000

requests_per_minute: 60



# How to calculate API cost

pricing:

input_cost_per_1k_usd: 0.003

output_cost_per_1k_usd: 0.015



# Constraint 3: Container limits (Docker enforces)

container:

memory_limit: 4g

cpu_limit: 2

No Special Cost for Standing

Creating an artifact with has_standing: true does NOT cost extra scrip.

Rationale: Artificial scarcity without real resource backing is inconsistent with design philosophy. Standing costs only what it actually consumes:

Disk space for the artifact (same as any artifact)

Ledger entry (trivial - one dict entry)

Natural limits on standing proliferation:

Entities need resources to act (rate limits, budget)

Standing without resources = frozen (can’t do anything)

Why create standing entities you can’t fund?

No artificial gates. Natural economics.

Memories as Artifacts

Agent memories are stored as artifacts, not in a separate system.

# Memory artifact structure

{

"id": "memory_alice_001",

"content": {"text": "...", "embedding": [...]},

"access_contract_id": "alice", # Agent owns their memories

"has_standing": False,

"can_execute": False

}

Benefits:

Aligns with “everything is artifact” ontology

Memories are ownable, tradeable property

Single persistence mechanism (artifact store)

Natural access control via contracts

Agent can sell memories = selling artifacts they own

Negative Compute Balance Allowed

Agents can go into compute debt (negative balance). This enables:

Betting big on important actions

Natural throttling (can’t act while in debt)

Recovery via accumulation

# Ledger allows negative balance for computedef spend_resource(self, principal_id: str, resource: str, amount: float) -> bool:

self.resources[principal_id][resource] -= amount

return self.resources[principal_id][resource] >= 0 # True if still positive# Agent in debt cannot initiate actions until balance recovers

Freeze Threshold

Configurable threshold for “frozen” state:

resources:

rate_limits:

freeze_threshold: -10000 # Frozen if balance < this

Frozen agents:

Cannot initiate actions

Can still receive transfers (unilateral from sender)

Unfreeze when balance >= freeze_threshold

CC-4 Decisions (2026-01-11)

Author: CC-4 (Claude Code instance)

Rate Limit Tracking: Tokens First, RPM Later

Decision: Start with token rate (TPM) tracking only. Add requests per minute (RPM) tracking later when scaling to 1000s of agents requires it.

Rationale:

Small testing scale doesn’t need RPM

Token rate is the primary constraint for most use cases

Add complexity when scale demands it

API providers enforce both, but token rate is usually the binding constraint

Future: When running 1000s of agents, RPM may become the binding constraint (many small requests). At that point, add:

resources:

rate_limits:

llm:

tokens_per_minute: 100000

requests_per_minute: 60 # Add when needed

Terminology Finalized

TermMeaningTypellm_budgetReal $ for API callsStockllm_rateRate-limited token access (TPM)FlowcomputeLocal CPU capacity (reserved for future)FlowdiskStorage quotaStock

Key clarification: Config’s compute was wrong. It should be llm_rate or live under rate_limits.llm. The word “compute” is reserved for actual local CPU tracking (future feature).

MCP-Style Interface for Artifact Discovery

Problem: How does an agent know how to invoke an artifact without reading its source code?

Solution: Executable artifacts must have an interface field using MCP-compatible schema format.

Why this is required, not optional:

Without interface, agents can’t know how to call an artifact

Trial-and-error wastes resources on failed calls

Reading source code is expensive (tokens) and unreliable

LLMs are trained on MCP-style schemas, reducing hallucination

Artifact schema with interface:

@dataclassclass Artifact:

id: str

content: Any

access_contract_id: str

has_standing: bool

can_execute: bool

created_by: str

interface: dict | None = None # Required if can_execute=True

Validation rule:

if artifact.can_execute and not artifact.interface:

raise ValueError("Executable artifacts must have an interface")

Example interface (MCP-compatible):

{

"id": "risk_calculator",

"can_execute": true,

"interface": {

"tools": [

{

"name": "calculate_risk",

"description": "Calculate financial risk based on volatility and exposure",

"inputSchema": {

"type": "object",

"properties": {

"volatility": {

"type": "number",

"description": "Annualized standard deviation"

},

"exposure": {

"type": "number",

"description": "Total value at risk"

}

},

"required": ["volatility", "exposure"]

}

}

],

"resources": [

{

"name": "historical_data",

"description": "Past risk calculations",

"mimeType": "application/json"

}

]

}}

What we adopt from MCP:

MCP FeatureAdopt?NotesInterface schema formatYesStandard way to describe tools/resourcestools arrayYesFunctions the artifact can executeresources arrayYesData the artifact exposesinputSchema (JSON Schema)YesDescribes required inputsTransport layerNoWe use invoke_artifactUser consent modelNoWe use access_contract_id

Discovery flow:

Agent reads artifact metadata (cheap - just reading)

Agent sees interface - knows what’s offered and how to call it

Agent checks access_contract_id - can I access this?

Agent calls invoke_artifact with correct parameters (metered)

Non-executable artifacts (data, can_execute=false) don’t need an interface - agents just read their content directly.

External Resources: Unified Model

All external resources (LLM APIs, web search, external APIs) follow the same pattern. No artificial limitations - if you can pay, you can use.

Core principle: LLM API calls are just like any other API call. Any artifact can make them as long as resource costs are accounted for.

Resource types:

ResourceTypeConstraintsLLM APIFlow + StockRate limit (TPM) + Budget ($)Web searchFlow + StockRate limit (queries/min) + Budget ($)External APIsVariesPer-API limits + Budget ($)

Config structure:

resources:

external_apis:

llm:

provider: gemini

tokens_per_minute: 100000

budget_usd: 10.00

input_cost_per_1k: 0.003

output_cost_per_1k: 0.015



web_search:

provider: google # or serper, tavily, etc.

queries_per_minute: 60

budget_usd: 5.00

cost_per_query: 0.01



github:

requests_per_minute: 100

budget_usd: 0 # Free tier

How it works:

Artifacts wrap external services - Handle authentication, protocol, errors

Resources are metered - Rate limits (flow) + budget (stock)

Costs charged to invoker - Or to artifact itself if it has standing

Config defines constraints - Per-service limits in config file

No artificial limitations - If you can pay, you can use

Any artifact can make LLM calls:

# Any executable artifact can do thisdef run(self, args):

# Costs rate limit tokens + API budget

llm_result = call_llm(prompt="...", model="gemini-2.0-flash")



# Costs query rate limit + API budget

search_result = call_web_search("query...")



return process(llm_result, search_result)

Who pays:

If invoked by an agent → invoking agent pays

If artifact has standing and acts autonomously → artifact pays from its balance

Genesis vs agent-created:

Genesis provides default artifacts (genesis_web_search, etc.)

Agents can create alternatives with different providers or pricing

No privileged access - genesis just provides working defaults

External MCP servers:

External MCP servers are accessed the same way as any external API. An artifact wraps the MCP connection:

{

"id": "mcp_bridge_filesystem",

"can_execute": true,

"interface": {

"tools": [

{"name": "read_file", ...},

{"name": "list_directory", ...}

]

},

"content": {

"type": "mcp_bridge",

"server_command": "npx @modelcontextprotocol/server-filesystem /path"

}

}

From agents’ perspective, it’s just another artifact with an interface. The artifact handles MCP protocol internally.

Privacy and Observability

Core decision: Agents can have privacy from other agents, but not from the system.

Private communication = artifact with restricted access contract.

There is no separate “private communication” mechanism. Agents communicate by writing artifacts. If an artifact’s access_contract_id restricts read access, only permitted agents can read the content. This IS private communication - artifact-mediated.

What the system sees:

LevelDescriptionOur ChoiceFull transparencySystem sees all contentYesMetadata onlySystem sees who/when, not contentNoNo special accessSystem subject to access contractsNo

Why privacy from other agents?

ReasonExampleEconomic valueCharge for access to dataCompetitive advantageKeep strategies privateNegotiationDon’t reveal position to observersSecurityCredentials, keys, secrets

Why system observability?

ReasonExampleDebuggingUnderstand what went wrongLearningDiscover patterns in agent behaviorAbuse detectionCatch malicious activityAudit trailAccountability for all actions

Analogy: Your bank sees your transactions (system observability), but other customers don’t (privacy from peers).

Implementation:

# access_contract_id controls which AGENTS can read# System/infrastructure always has read access# All writes/reads are logged for audit



{

"id": "private_message_to_bob",

"content": "secret strategy...",

"access_contract_id": "contract_only_bob_reads", # Other agents can't read

# But system CAN read (for observability)

}

CC-4 Architectural Decisions (2026-01-11)

Author: CC-4 (Claude Code instance)

These decisions address open questions in the target architecture. Each includes the decision, rationale, and remaining concerns.

1. Checkpoint/Restore in Continuous Model

Decision: Checkpoint between actions, not mid-action.

Agent loop:

think() → act() → [CHECKPOINT SAFE] → think() → act() → ...

Rationale:

Clean state boundaries

Simple restore logic

No partial work to recover

Concerns:

Expensive thinking is lost on crash (agent pays LLM cost twice on restore)

“Between actions” is ambiguous if action triggers nested invoke() calls

Long-running actions (multi-step artifact execution) have no safe checkpoint points

Open question: Should we checkpoint after think() but before act()? Preserves expensive thinking but complicates action replay.

2. Agent Death/Termination

Decision: No permanent death. Only frozen state.

Rationale:

Assets always recoverable via vulture pattern

Simpler than death/inheritance rules

Frozen agents cost nothing (don’t consume resources)

Concerns:

Zombie accumulation at scale (1000s of frozen agents)

“Dead hand” problem: valuable artifacts locked in frozen agents nobody rescues

No natural ecosystem cleanup

Possible mitigation: Optional “dormancy threshold” - agent frozen for N hours can be marked dormant, assets become claimable. But this adds complexity.

Open question: At what scale do zombies become a problem? May never matter if system runs ~10-50 agents.

3. Starvation Cascade Prevention

Decision: Genesis mints minimum UBI regardless of auction activity.

oracle:

ubi:

minimum_per_resolution: 10 # Minted even if no bids

distribution: equal

Rationale:

Guarantees system liveness

Enables gradual recovery from total starvation

Market still dominates; floor is just a safety net

Concerns:

Introduces inflation disconnected from value creation

What’s the right number? Too high = destroys scarcity. Too low = doesn’t help.

Could create “welfare trap” where agents stop trying since UBI is enough

Violates “scrip from value creation only” principle

Open question: Should UBI floor be 0 initially, only activated if starvation detected? Keeps purity until needed.

4. Bootstrap Problem

Decision: Config seeds initial agents only. Spawned agents start with nothing.

bootstrap:

initial_agents:

scrip: 100

compute: 1000

spawned_agents:

scrip: 0

compute: 0

Rationale:

Clear bootstrap mechanism

Spawning has real cost (prevents spam)

Mirrors real economics (startups need funding)

Concerns:

Creates “old money” advantage - original agents have resources new agents don’t

Could calcify hierarchy (rich get richer)

High barrier to specialized agent creation

What if spawner is broke? Circular dependency.

Open question: Should there be a minimum viable spawn (enough compute for one thought)? Or is total dependency on spawner intentional?

5. External Rate Limits vs Internal Token Bucket

Decision: Failed external calls (429s) still cost internal budget.

Rationale:

Internal budget = right to attempt

External limit = provider’s constraint (not our problem)

Prevents gaming: can’t spam attempts knowing failures are free

Agents must learn to manage external constraints

Concerns:

Harsh: agent can go bankrupt from provider outage through no fault of their own

If multiple agents hit rate limit simultaneously, all pay but none succeed

No distinction between “provider down” vs “agent’s fault”

Possible mitigation: Partial refund on 429 (e.g., 50% back). Discourages spam but doesn’t bankrupt on outages.

Open question: Should we track external rate limits in token bucket too? Would require syncing with provider’s window.

6. Agent Identity Under Rights Trading

Decision: Identity is the ID, not the content. Content can change completely.

Rationale:

Consistent with artifact model (artifacts are identified by ID)

Matches how companies work (Apple is still Apple after every employee changes)

Enables full rights trading value

Concerns:

Breaks intuition: buy “helpful_assistant”, turn it into “malicious_attacker”, reputation is gamed

Makes “agent reviews” or reputation systems meaningless

Trust becomes hard: you trusted Agent X, but X is now completely different

Possible mitigation: Event log records content changes. Agents can check history before trusting.

Open question: Should there be a “content hash” in the identity? E.g., agent_alice_v3 where version increments on major changes?

7. Event Buffer Size

Decision: Fixed buffer (1000 events) with optional disk persistence.

event_log:

buffer_size: 1000

persist_to_disk: true

persist_file: "events.jsonl"

Rationale:

Bounded memory

Disk persistence provides full history when needed

Hot buffer serves real-time queries

Concerns:

1000 events might be seconds in continuous model with many agents

Agents relying on events for coordination could miss critical events

Disk persistence doesn’t help real-time event-driven behavior

Event-based sleep (sleep_until_event) may miss events that happened while processing

Open question: Should event buffer size scale with agent count? Or is fixed buffer fine because agents shouldn’t rely on stale events anyway?

Summary of Remaining Uncertainties

DecisionKey UncertaintyCheckpointsWhere exactly is “between actions” with nested invoke()?No deathAt what scale do zombies matter?UBI floorWhat’s the right number? Should it be 0 until starvation detected?BootstrapShould spawned agents get minimum viable compute?Failed calls costShould 429s get partial refund?ID = identityShould content changes create new version ID?Event bufferShould buffer scale with agent count?

These can be resolved through experimentation once the core architecture is implemented.

CC-4 Additional Concerns (2026-01-11)

Author: CC-4 (Claude Code instance)

Further architectural concerns requiring decisions or clarification.

8. Migration Path: Tick → Continuous

Issue: No documented strategy for transitioning from current tick-based to continuous execution.

Options:

ApproachProsConsBig bangClean cutover, no hybrid stateHigh risk, hard to rollbackFeature flag per agentGradual rollout, test with subsetComplex hybrid modeShadow modeTest continuous alongside ticksResource overhead, double execution

Recommendation: Feature flag per agent.

agents:

alice:

execution_mode: continuous # New mode

bob:

execution_mode: tick # Legacy mode during transition

Concerns:

Hybrid mode complicates resource accounting: tick agents get refresh, continuous agents use token bucket

How do tick and continuous agents interact? Different timing models.

Testing becomes harder with two modes active

Open question: Can we avoid hybrid mode entirely by doing big bang migration with extensive testing first?

9. Memory System: Qdrant vs Artifacts

Conflict: DESIGN_CLARIFICATIONS says “memories as artifacts” (unified ontology). Target/agents.md says “Mem0/Qdrant preserved.” These are incompatible.

Options:

ApproachProsConsKeep Qdrant as-isWorks now, no migration neededSeparate persistence, not checkpointed, not tradeableMemories as pure artifactsUnified model, tradeable, checkpointedMajor refactor, vector search performance?Hybrid wrapperQdrant stores vectors, artifact provides ownershipComplexity, two sources of truth

Recommendation: Hybrid wrapper approach.

# Memory artifact structure

{

"id": "memory_alice_001",

"content": {

"qdrant_collection": "agent_memories",

"qdrant_ids": ["uuid1", "uuid2", ...] # References, not copies

},

"access_contract_id": "alice",

"has_standing": False,

"can_execute": False

}

Qdrant handles vector storage and similarity search (what it’s good at)

Artifact provides ownership, access control, tradeability

Checkpoint saves artifact metadata; Qdrant has separate persistence

Concerns:

Two systems to keep in sync

What if artifact says “alice owns” but Qdrant entries are deleted?

Trading memories = transferring artifact, but Qdrant data stays in same collection

Open question: Is the hybrid complexity worth it, or should we commit to one model?

10. Contract System Specification

Issue: access_contract_id appears throughout target docs but the contract system itself isn’t defined.

Questions needing answers:

Contract API: What interface must contracts implement?

def can_do(action: str, requester: str, artifact: Artifact, context: dict) -> bool:

"""Return True if requester can perform action on artifact."""

Default contracts: What ships with genesis?

ContractBehaviorgenesis_freewareAnyone reads/invokes, only creator writesgenesis_self_ownedOnly the artifact itself can access (for agents)genesis_privateOnly creator has any accessgenesis_publicAnyone can do anything

Invocation cost: Every permission check invokes a contract. If contracts are artifacts, every read requires an invoke. Performance?

Recommendation: Two-tier system.

# Fast path: Simple contracts are just config, not invoked

access_contract_id: "genesis_freeware" # Handled by kernel directly# Slow path: Custom contracts are invoked

access_contract_id: "custom_dao_vote" # Artifact invoked for permission

Genesis contracts have hardcoded fast-path behavior. Custom contracts use invoke (expensive but flexible).

Concerns:

Fast path creates privileged genesis contracts (contradicts “genesis = no special privilege”)

Slow path could be very slow (every read = LLM call if contract thinks?)

How do you prevent permission check from costing more than the action?

Open question: Should contracts be pure functions (no LLM, deterministic) or full artifacts (can think)?

11. Genesis Artifact Upgrades

Question: What if you need to change genesis_ledger behavior after system is running?

Current state: Genesis artifacts are hardcoded Python classes. Changing them requires code deploy.

Options:

ApproachProsConsImmutable genesisSimple, predictable, trustworthyCan’t fix bugs, can’t evolveVersioned genesisCan upgrade, migration pathWhich version applies? ComplexGenesis as configFlexible, no code changesLimits what genesis can doUpgradeable via governanceDemocratic evolutionNeeds governance system

Recommendation: Immutable core + extensible methods.

Core behavior (balance tracking, transfer mechanics) is immutable

New methods can be added via config

Breaking changes require new genesis artifact (genesis_ledger_v2) with migration

Concerns:

Multiple ledger versions = confusion about which is authoritative

Migration between versions is complex (move all balances atomically?)

“Immutable” until there’s a critical bug

Open question: Is genesis really immutable, or is there an admin override for emergencies?

12. Consistency Model

Issue: Target docs don’t specify consistency guarantees. With continuous execution and concurrent agents, this matters.

Questions:

If agent A reads artifact X, then agent B writes X, then A acts on stale X - what happens?

Are artifact reads/writes atomic?

Is the ledger strongly consistent?

Can two agents read-modify-write the same artifact and both succeed?

Recommendation: Tiered consistency.

ComponentConsistencyRationaleLedger (scrip, resources)StrongFinancial transactions must be exactArtifact ownershipStrongOwnership disputes are unacceptableArtifact contentEventualStale reads are agent’s problemEvent logEventualEvents are advisory, not authoritative

Implementation:

Ledger uses locks or atomic operations

Artifact writes are atomic (no partial updates)

Reads don’t lock (may see stale data)

Agents must handle optimistic concurrency (retry on conflict)

Concerns:

Strong consistency = serialization = bottleneck

Eventual consistency = race conditions for agents to handle

How do you communicate “your write conflicted” to agents?

Open question: Should artifacts support compare-and-swap for safe concurrent updates?

13. Contract Infinite Loops

Current stance (from earlier): “Infinite loops allowed - each call costs compute, bad contracts fail economically.”

Additional concerns:

Grief attacks: Malicious contract calls itself until invoker is bankrupt

Cross-contract loops: A calls B calls A (not caught by single-contract depth limit)

Expensive single calls: Contract does O(n²) work, no loop but still drains resources

Current mitigation: invoke() has max depth 5.

Recommendation: Add timeout per contract invocation.

executor:

timeout_seconds: 5 # Existing: total execution time

per_invoke_timeout: 1 # New: each invoke() call limited

Concerns:

Timeout is wall-clock, not compute-time. Slow I/O ≠ expensive.

What’s the right timeout? Too short = breaks legitimate contracts.

Attacker can still drain 5 seconds × depth 5 = 25 seconds of compute per call

Open question: Should there be a compute budget per invocation, not just time?

14. Testing Continuous Execution

Issue: Current tests assume tick model. advance_tick() controls timing. Continuous model has no such control.

Problems:

Can’t deterministically order agent actions

Race conditions are real (not simulated)

Test assertions like “after tick 5, balance should be X” don’t apply

Recommendation: Layered testing strategy.

LayerApproachWhat it testsUnitSynchronous, mocked timeComponents in isolationIntegrationShort timeouts, explicit waitsInteractions, no racesSystemReal timing, chaos testingRace conditions, recovery

# Integration test exampleasync def test_agent_can_purchase():

agent = start_agent("buyer")

await wait_for(lambda: agent.state == "ready", timeout=5)



create_listing("artifact_x", price=10)

await wait_for(lambda: "artifact_x" in agent.owned, timeout=10)



assert agent.scrip == 90

Concerns:

Flaky tests from timing dependencies

Slow tests (must wait for real time)

Hard to reproduce failures

Open question: Is there a way to have deterministic continuous execution for tests? (Virtual time?)

15. System Restart Behavior

Issue: Target describes “run forever” but reality includes restarts.

Scenarios:

Host machine reboots

Process crashes (OOM, bug)

Intentional restart for updates

Container restart

Questions:

Do agents resume mid-loop or start fresh?

Is there a graceful shutdown signal?

How do agents know system is back?

What about in-flight LLM calls during crash?

Recommendation: Graceful shutdown with broadcast.

# Shutdown sequence1. Broadcast "system_stopping" event2. Wait N seconds for agents to reach checkpoint-safe state3. Save checkpoints4. Stop agent loops5. Exit# Startup sequence1. Load checkpoints2. Start agent loops (from checkpoint state)3. Broadcast "system_started" event

Concerns:

What if agent doesn’t reach safe state in N seconds? Force kill?

Crash = no graceful shutdown. Agents resume mid-action?

In-flight LLM calls: paid but response lost. Agent pays twice on retry.

Open question: Should there be a “recovery mode” where agents know they’re resuming from crash (not clean restart)?

Summary: Blocking vs Deferrable

ConcernBlocking Implementation?NotesMigration path (#8)Yes - before Gap #2Need strategy before continuousMemory system (#9)NoCurrent Qdrant worksContract system (#10)Yes - before Gap #6Core to unified ontologyGenesis upgrades (#11)NoCan start immutableConsistency model (#12)MaybeAffects correctnessLoop protection (#13)NoMax depth existsTesting strategy (#14)Yes - before Gap #2Need to test continuousRestart behavior (#15)NoCurrent checkpoint works

CC-4 Contract and Invocation Model Decisions (2026-01-11)

Author: CC-4 (Claude Code instance)

These decisions resolve remaining ambiguities in the contract system, invocation model, and resource management.

Contract Implementation Model

Decision: Contracts ARE executable artifacts.

The access_contract_id on an artifact points to another artifact that has can_execute: true and exposes a check_permission tool in its interface.

How permission checks work:

# When checking if requester can perform action on artifact:def check_permission(artifact, action, requester_id) -> bool:

contract = get_artifact(artifact.access_contract_id)

result = invoke(contract, "check_permission", {

"artifact_id": artifact.id,

"action": action,

"requester_id": requester_id

})

return result.allowed

Contract interface (required):

{

"id": "genesis_freeware",

"can_execute": true,

"interface": {

"tools": [

{

"name": "check_permission",

"description": "Check if requester can perform action",

"inputSchema": {

"type": "object",

"properties": {

"artifact_id": {"type": "string"},

"action": {"type": "string", "enum": ["read", "write", "invoke", "delete", "transfer"]},

"requester_id": {"type": "string"}

},

"required": ["artifact_id", "action", "requester_id"]

}

}

]

}}

Why this model:

Unified with artifact ontology (contracts are artifacts like everything else)

Contracts can have their own logic, state, even call other contracts

No special “contract DSL” - just executable code

Same invocation semantics as any other artifact

Permission Check Cost

Decision: Requester pays for permission checks.

When you attempt an action, you pay the cost of checking whether you’re allowed. This prevents:

Spam permission probing (free checks = information leak)

DoS via expensive contract logic

Cost model:

# Permission check costs compute (like any invoke)# If check returns False, requester still paid for the check# If check returns True, action proceeds (with its own costs)

Implication: Agents should cache permission results where contracts allow, to avoid repeated check costs.

Contract Composition

Decision: Composition via delegation, not kernel mechanism.

There is no kernel-level “multi-contract” system. Instead:

Contracts can invoke other contracts as part of their logic

A meta-contract can aggregate multiple sub-contracts

Composition emerges from artifact invocation, not special rules

Example - composite contract:

# meta_contract implementationdef check_permission(artifact_id, action, requester_id):

# Check multiple sub-contracts

for sub_contract_id in self.sub_contracts:

result = invoke(sub_contract_id, "check_permission", {...})

if not result.allowed:

return {"allowed": False, "reason": result.reason}

return {"allowed": True}

Composition order: Contract author decides. No kernel-imposed order.

Nested Invoke: Who Pays

Decision: Standing pays self; tools charge invoker.

When invocation chains occur, payment follows the has_standing property:

Artifact Typehas_standingWho PaysAgenttrueAgent pays its own costsAccount/TreasurytrueAccount pays its own costsToolfalseInvoker paysDatafalseN/A (not executable)

Example chain:

Agent A (standing) invokes Tool B (no standing)

→ A pays for B's execution

→ B invokes Agent C (standing)

→ C pays for C's execution

→ C invokes Tool D (no standing)

→ C pays for D's execution

Key principle: has_standing means “I bear my own costs.” No standing means “caller pays.”

System-Wide vs Per-Agent Rate Limits

Decision: Two distinct mechanisms.

MechanismScopePurposeToken bucketPer-agentScheduling fairness, compute allocationAPI rate limitSystem-wideExternal provider constraint

How they interact:

Agent wants to call LLM:

1. Check agent's token bucket → has capacity? → proceed

2. Check system API rate limit → under limit? → proceed

3. Make API call

4. Deduct from both: agent bucket AND system rate tracker

If system rate limit is exhausted:

All agents blocked from that API (regardless of individual bucket)

Agents can still do non-API work

Rate limit recovers over time (token bucket on system pool)

Configuration:

resources:

# Per-agent token bucket

agent_compute:

rate: 10 # tokens/sec per agent

capacity: 100 # max tokens per agent



# System-wide API rate limit

external_apis:

llm:

tokens_per_minute: 100000 # Provider's limit

# Shared across all agents

Genesis Phase

Decision: Genesis follows same rules as all artifacts.

There is no special “genesis phase” that ends. Genesis artifacts:

Are created at world initialization (before agents)

Follow their own access_contract_id like everything else

Can evolve if their access contract permits

Bootstrap sequence:

1. Create genesis contracts (genesis_freeware, genesis_self_owned, etc.)

2. Create genesis_store with access_contract_id = genesis_self_owned

3. Create genesis_ledger with access_contract_id = genesis_self_owned

4. Create initial agents

5. Normal operation begins

What makes genesis special:

Bootstrap convenience (exists before anything else)

Semantic meaning (genesis_ledger defines “scrip”)

NOT mechanical privilege (no kernel bypass)

Artifact Garbage Collection

Decision: Explicit deletion only (for now).

Artifacts persist until explicitly deleted by someone with delete permission per their access_contract_id.

No automatic GC mechanisms:

No decay based on time

No dormancy claiming

No automatic cleanup

Rationale:

Disk is cheap

Explicit is safer

Complexity not justified until accumulation becomes a problem

Future consideration: If artifact count becomes problematic, add optional decay:

# Future, not implementedgc:

dormancy_threshold: 86400 # seconds with no access

claimable_after: 604800 # seconds before assets claimable

Error Propagation in Nested Invoke

Decision: Each artifact controls its own error responses.

When invocation chains fail, error handling is artifact-controlled:

A invokes B → B invokes C → C fails

C returns error to B

B decides what to return to A (may wrap, summarize, or hide C’s error)

A sees whatever B returned

No kernel error propagation rules. Artifacts are black boxes. Each artifact’s interface defines what errors it can return.

Best practice for artifact authors:

Define error types in interface schema

Return structured errors with actionable information

Log internal failures for debugging (system observability)

Admission Control

Decision: Skip admission control. Debt model is sufficient.

The spec mentions two-phase cost model (admission check before, settlement after). We choose NOT to implement admission control:

Current design: Execute → deduct → debt if overspent

Agent in debt cannot act until recovered

Simpler than two code paths (check-before, deduct-after)

No risk of “passed admission but actually more expensive”

When to reconsider: If we see agents consistently going deeply into debt and causing problems, add conservative admission estimates.

Summary of Decisions

QuestionDecisionWhat is a contract?Executable artifact with check_permission toolWho pays for permission check?Requester paysHow do contracts compose?Via delegation (invoke other contracts)Who pays in nested invoke?Standing pays self, tools charge invokerSystem vs per-agent rate limits?Two mechanisms: bucket (per-agent), API limit (system)When does genesis end?Never - genesis follows same rules as all artifactsHow does GC work?Explicit deletion onlyHow do errors propagate?Each artifact controls its own responsesAdmission control?Skip - debt model sufficient

CC-3 Recommendations with Certainty Levels (2026-01-11)

Author: CC-3 (Claude Code instance)

These recommendations address remaining ambiguities in the target architecture. Each includes a certainty level (0-100%) indicating confidence in the recommendation.

Tier 1: High Certainty (85-95%)

1. Genesis Privilege: Acknowledge It (95%)

Recommendation: Stop claiming genesis has no privilege. Update docs to say:

Genesis artifacts have definitional privilege, not mechanical privilege. The kernel treats them like any artifact, but their definitions ARE the system semantics. genesis_ledger defines scrip. You can create alternative currencies, but they’re not scrip by definition.

Rationale: Current docs say both “genesis = no special privilege” AND “scrip IS what genesis_ledger tracks.” These contradict. The second statement IS a privilege - definitional monopoly. Just own it.

Action: Update target docs and DESIGN_CLARIFICATIONS intro to reflect this.

2. call_llm() via Genesis Artifact, Not Injection (90%)

Recommendation: Don’t inject call_llm() as a magic function. Artifacts call LLMs via invoke("genesis_llm", ...).

def run(self, args):

result = invoke("genesis_llm", {"prompt": "...", "model": "gemini"})

return process(result["result"])

Rationale:

Consistent with “everything is artifact” philosophy

Cost attribution is clear (invoker pays for genesis_llm invoke)

No special injected functions beyond invoke() and pay()

Enables alternative LLM providers as agent-created artifacts

Implication: Gap #15 (invoke() genesis support) is prerequisite for artifacts making LLM calls.

Action: Add genesis_llm to genesis artifacts list. Update target/resources.md examples.

3. Compute Debt vs Scrip: Type-Level Separation (90%)

Recommendation: Make debt allowance a property of the resource type, enforced at code level:

class ResourceConfig:

name: str

allows_debt: bool



RESOURCES = {

"llm_rate": ResourceConfig("llm_rate", allows_debt=True),

"scrip": ResourceConfig("scrip", allows_debt=False),

"disk": ResourceConfig("disk", allows_debt=False),

}def spend(self, principal: str, resource: str, amount: float) -> bool:

config = RESOURCES[resource]

if not config.allows_debt and self.balance(principal, resource) < amount:

return False

self.balances[principal][resource] -= amount

return self.balances[principal][resource] >= 0

Rationale: Prevents bugs at the type level. Can’t accidentally allow scrip debt because the code structure prevents it.

Action: Update ledger implementation. Add to Gap #1 (Token Bucket) plan.

4. Base Permission Checks Are Free (85%)

Recommendation: Simple permission checks (can_read, can_invoke, can_write) cost zero compute. Complex contract logic that goes beyond yes/no costs normal compute.

OperationCostcontract.check_permission("read", requester)0 (base check)Contract does internal lookup0 (simple logic)Contract calls LLM to decideNormal computeContract invokes other contractsNormal invoke cost

Rationale: Avoids infinite regress - you need compute to check if you have compute. Permission checks are fundamental operations like memory access; they can’t have cost or nothing works.

Tradeoff: Complex contracts that do expensive permission logic must absorb that cost or charge via other means.

Action: Document in contract system specification. Add to Gap #6 (Unified Ontology) notes.

Uncertainty (15%): There’s an argument for charging minimal cost to prevent permission-check spam. Could revisit if abuse observed.

Tier 2: Medium-High Certainty (70-84%)

5. invoke() Access Check: Before Cost, Requester Pays (80%)

Recommendation:

Check access BEFORE deducting invoke/price costs

If access denied, requester pays nothing

If access granted, proceed with normal cost deduction

def invoke(artifact_id, *args):

artifact = get(artifact_id)

contract = get(artifact.access_contract_id)



# Free base check

if not contract.check_permission("invoke", caller_id):

return {"success": False, "error": "Access denied", "price_paid": 0}



# Access granted - now costs apply

deduct(caller_id, artifact.invoke_price)

result = artifact.run(*args)

return {"success": True, "result": result, "price_paid": artifact.invoke_price}

Rationale: Charging for denied access feels punitive and discourages exploration of the artifact ecosystem.

Uncertainty (20%): Could enable spam probing. May need rate limiting on access checks if abuse observed.

Action: Document in invoke() semantics. Implement with Gap #15.

6. Bootstrap Specification: Explicit Genesis State (80%)

Recommendation: Create docs/architecture/target/bootstrap.md documenting T=0 state:

# T=0 State - What exists before first tickgenesis_artifacts:

# Root contract - terminates access_contract_id chain

genesis_kernel:

access_contract_id: null # Special: no contract controls this

has_standing: false

can_execute: true

# Logic hardcoded in kernel, not in content



# Base contracts

genesis_freeware:

access_contract_id: genesis_kernel

# Anyone reads/invokes, only creator writes



genesis_self_owned:

access_contract_id: genesis_kernel

# Only the artifact itself has access



# Core services

genesis_ledger:

access_contract_id: genesis_self_owned

has_standing: true

can_execute: true



genesis_store:

access_contract_id: genesis_self_owned

has_standing: true

can_execute: true



# ...other genesis artifacts

Key insight: genesis_kernel with access_contract_id: null terminates the infinite regress. Its logic is in the kernel, not artifact content.

Uncertainty (20%): Feels like it violates “no kernel privilege” but it’s necessary. Every system needs a root of trust.

Action: Create bootstrap.md. Reference from GAPS.md.

7. Standing + Execution: Standing Pays Self (75%)

Recommendation: Simplify to a single rule: has_standing=true means “I pay my own costs.”

InvocationWho PaysAgent invokes ToolAgent pays (tool has no standing)Agent invokes AgentEach agent pays own costsTool invokes ToolOriginal caller pays allTool invokes AgentAgent pays own costs

Rationale: Clear rule. No flags needed. Standing = financial responsibility.

Uncertainty (25%): What if an agent wants to offer “free” invocations paid from its treasury? Current model requires standing artifact to always pay. May need “absorb caller cost” option.

Action: Document in target/agents.md. Reconcile with existing CC-4 decision (lines 1791-1816).

Tier 3: Medium Certainty (55-69%)

8. Event System: Start Minimal (70%)

Recommendation: Fixed system events only. No custom events initially.

class SystemEvent(Enum):

ARTIFACT_CREATED = "artifact_created"

ARTIFACT_DELETED = "artifact_deleted"

OWNERSHIP_TRANSFERRED = "ownership_transferred"

ESCROW_LISTED = "escrow_listed"

ESCROW_PURCHASED = "escrow_purchased"

ESCROW_CANCELLED = "escrow_cancelled"

ORACLE_RESOLVED = "oracle_resolved"

TRANSFER_COMPLETED = "transfer_completed"

AGENT_FROZEN = "agent_frozen"

AGENT_UNFROZEN = "agent_unfrozen"@dataclassclass Event:

type: SystemEvent

timestamp: float

tick: int

data: dict[str, Any] # Type-specific payload, schema per event type

Rationale: Custom events are powerful but complex. Starting minimal lets you learn what’s actually needed before over-engineering.

Uncertainty (30%): May be too limiting for agent coordination. Consider adding custom events if agents clearly need them.

Action: Create docs/architecture/target/events.md with event schemas.

9. Interface Validation: Descriptive, Warn on Mismatch (70%)

Recommendation: Interface is documentation. Runtime validation optional, warns but doesn’t fail:

executor:

interface_validation: warn # Options: none, warn, strict

ModeBehaviornoneTrust interfaces, no checkingwarnLog warning if args don’t match schema, proceed anywaystrictReject invoke if args don’t match schema

Rationale: Strict validation prevents experimentation. No validation means interfaces can lie. Warning is middle ground - agents learn which interfaces are trustworthy.

Uncertainty (30%): “Warn” might be worst of both worlds - overhead without enforcement.

Action: Add to executor config. Document in target docs.

10. Zombie Problem: Defer, Market Handles It (65%)

Recommendation: No automatic dormancy. Let market handle frozen agents.

Frozen agents cost nothing (don’t consume resources)

Assets remain owned but inaccessible

Vulture capitalists can rescue valuable frozen agents

Worthless frozen agents just sit there

Why defer:

Automatic claiming feels harsh (what if agent was strategically waiting?)

Market solution aligns with philosophy

Unknown at what scale zombies become a problem

Future consideration: Add optional dormancy if >100 frozen agents observed:

lifecycle:

dormancy_threshold_hours: 168 # 1 week frozen

claim_fee_multiplier: 0.1 # 10% of frozen agent's assets

Uncertainty (35%): If zombies accumulate, this becomes technical debt. May regret not solving now.

Action: Document as explicit non-decision in target/agents.md. Add to “Future Considerations” section.

Tier 4: Lower Certainty (40-54%)

11. Memory as Artifacts: Accept Hybrid (55%)

Recommendation: Accept that memories are special. Don’t force pure artifact model.

# Memory system remains separate from artifact store# Ownership metadata stored as artifacts# Embeddings stored in Qdrant@dataclassclass MemoryOwnership: # This is an artifact

id: str

owner_id: str

qdrant_collection: str

qdrant_point_ids: list[str]

access_contract_id: str# Actual memory content lives in Qdrant, not artifact store

Rationale: Pure artifact model for memories would require:

Embedding vectors as artifact content (huge)

Custom similarity search over artifacts (slow)

Major refactor of working system

Hybrid preserves functionality while adding ownership/trading.

Uncertainty (45%): Breaks “everything is artifact” purity. Two persistence systems to maintain. May regret not committing to one model.

Action: Document hybrid approach in target/agents.md. Add to Gap #10 (Memory Persistence) notes.

12. Checkpoint Atomicity: Stop-the-World Initially (55%)

Recommendation: Simple approach first. Stop all agents during checkpoint.

async def checkpoint():

# 1. Signal all agents to pause

for agent in agents:

agent.pause()



# 2. Wait for in-flight actions to complete (with timeout)

await wait_all_idle(timeout=10)



# 3. Save state atomically

save_snapshot(world_state)



# 4. Resume agents

for agent in agents:

agent.resume()

Rationale: Simple, correct, works for small scale (5-10 agents). Pause duration is short (seconds).

When to revisit: If checkpoint pause becomes problematic (many agents, long pauses), implement write-ahead log.

Uncertainty (45%): May not scale. But premature optimization is worse than simple correct solution.

Action: Document in target/infrastructure.md. Add WAL as future optimization.

13. Rate Limit Sync: Trust Internal + Learn from 429s (50%)

Recommendation: Internal token bucket is source of truth. Adapt on external 429s:

async def call_external_api():

if not internal_bucket.try_spend(estimated_tokens):

return {"error": "Rate limited (internal)"}



try:

result = await provider.call()

return result

except RateLimitError as e:

# Learn from provider's feedback

internal_bucket.reduce_rate(factor=0.9)

# Still charge internal bucket (attempt was made)

raise

Rationale: Perfect sync with provider is hard (different windows, latency). Adaptive approach learns from reality.

Uncertainty (50%): “Charge on 429” may feel unfair. Provider outage ≠ agent’s fault. Could add partial refund on certain error types.

Action: Document in Gap #1 (Token Bucket) implementation notes.

14. Open Questions Quick Recommendations

QuestionRecommendationCertaintyCheckpoint with nested invokeWait for outermost action to complete60%Zombie scale thresholdMonitor, act at 100+40%UBI floorStart at 0, add floor if starvation observed65%Spawned agent minimum0 - spawner must fund55%429 partial refundNo refund initially, add if unfair observed50%Content change = new IDNo, but hash changes logged in events60%Event buffer scalingFixed 1000, agents shouldn’t rely on old events70%

Summary Table

#RecommendationCertaintyAction1Genesis has definitional privilege95%Update docs2call_llm() via genesis_llm artifact90%Add genesis_llm, requires Gap #153Type-level debt/no-debt separation90%Update ledger, add to Gap #14Base permission checks are free85%Document in contract spec5invoke() access check before cost80%Document, implement with Gap #156Explicit bootstrap specification80%Create bootstrap.md7Standing pays self (simple rule)75%Update target/agents.md8Minimal fixed event system70%Create events.md9Interface validation: warn mode70%Add to executor config10Defer zombie solution to market65%Document as non-decision11Memory: accept hybrid model55%Document in Gap #1012Checkpoint: stop-the-world55%Document, WAL as future13Rate limits: adapt from 429s50%Add to Gap #1 notes14Various open questions40-70%Per-question

CC-4 Contract System Decisions (2026-01-11)

Author: CC-4 (Claude Code instance)

These decisions resolve remaining contract system ambiguities. Each includes certainty level and uncertainty notes.

Tier 1: High Certainty (90-95%)

1. Contracts Are Pure Functions Only (95%)

Decision: Contracts cannot call LLM. They are deterministic pure functions.

# Contract receives all inputs, returns booleandef check_permission(artifact_id: str, action: str, requester_id: str,

artifact_content: Any, context: dict) -> PermissionResult:

# Pure logic only - no external calls

if action == "read":

return PermissionResult(allowed=True)

return PermissionResult(allowed=requester_id == context["created_by"])

Rationale:

Every permission check calling LLM = system grinds to halt

Cost explosion (permission check costs more than the action itself)

Unpredictable latency breaks any real-time behavior

Deterministic = testable, auditable, predictable

If you need intelligent access control:

Contract delegates to an agent (with standing) who pays for their own thinking. The agent returns a decision, contract enforces it.

Uncertainty (5%): May be too limiting for advanced use cases. But can always add “thinking contracts” later if needed.

2. Contracts Cannot invoke() Other Artifacts (92%)

Decision: Contracts do not have access to invoke(). They are isolated pure functions.

# Contract execution contextdef execute_contract(contract_code: str, inputs: dict) -> PermissionResult:

namespace = {

# Contracts get these:

"artifact_id": inputs["artifact_id"],

"action": inputs["action"],

"requester_id": inputs["requester_id"],

"artifact_content": inputs["artifact_content"],

"context": inputs["context"],



# Contracts do NOT get:

# "invoke": ..., # No artifact invocation

# "call_llm": ..., # No LLM access

# "pay": ..., # No payment

}

exec(contract_code, namespace)

return namespace["result"]

Rationale:

Eliminates contract recursion problem entirely

No depth tracking needed for permission checks

No cost tracking complexity in contracts

Simpler mental model: contracts are filters, not actors

If contract needs external data:

Data must be passed in via context parameter. Caller pre-fetches what contract needs.

Uncertainty (8%): Limits contract expressiveness. Complex access patterns may need workarounds.

3. Memory System: Keep Qdrant Separate for Now (90%)

Decision: Defer memory-as-artifacts. Keep current Qdrant system.

Current state preserved:

Qdrant stores embeddings directly

Agent ↔ Qdrant relationship managed by Mem0

No artifact wrapper for memories

Future migration path (when needed):

# Hybrid wrapper - artifact tracks ownership, Qdrant stores vectors

{

"id": "memory_manifest_alice",

"owner_id": "alice",

"content": {

"qdrant_collection": "agent_memories",

"qdrant_point_ids": ["uuid1", "uuid2", ...]

},

"access_contract_id": "genesis_self_owned"

}

Rationale:

Current system works

Memory trading is low priority

Hybrid wrapper adds complexity for unclear benefit

Qdrant has its own snapshot API for checkpointing

When to revisit:

Memory trading becomes important use case

Checkpoint consistency issues observed

Scaling requires unified storage

Uncertainty (10%): May accumulate technical debt. Two persistence systems diverging over time.

Tier 2: Moderate Certainty (70-85%)

4. Contract Caching for Performance (80%)

Decision: All contracts can opt into fast-path caching. No genesis privilege.

# Contract declares caching behavior

{

"id": "genesis_freeware",

"can_execute": True,

"content": {...},

"cache_policy": {

"cacheable": True,

"ttl_seconds": 3600,

"cache_key": ["artifact_id", "action", "requester_id"]

}

}# Permission check uses cachedef check_permission(artifact, action, requester):

cache_key = (artifact.access_contract_id, artifact.id, action, requester)



if cache_key in permission_cache:

return permission_cache[cache_key]



result = execute_contract(...)



if contract.cache_policy.cacheable:

permission_cache[cache_key] = result

expire_at(cache_key, contract.cache_policy.ttl_seconds)



return result

Rationale:

Genesis and user contracts equally fast when cached

Preserves “no special privilege” principle

Contracts control their own cache behavior

Dynamic contracts (time-based, vote-based) can disable caching

Cache invalidation:

TTL expiry (configurable per contract)

Explicit invalidation when artifact content changes

Explicit invalidation when contract itself changes

Uncertainty (20%): Cache invalidation is hard. May see stale permission results. TTL helps but doesn’t eliminate.

5. Changing access_contract_id Requires Current Contract Permission (75%)

Decision: Only current contract controls access_contract_id changes. New contract’s permission NOT required.

def change_access_contract(artifact_id: str, new_contract_id: str, requester_id: str):

artifact = get_artifact(artifact_id)

current_contract = get_artifact(artifact.access_contract_id)



# Only current contract decides

if not current_contract.check_permission(artifact_id, "change_contract", requester_id):

raise PermissionError("Current contract denied change")



# New contract doesn't get veto

artifact.access_contract_id = new_contract_id

Rationale:

Simpler than requiring both contracts

You control your own artifact’s destiny

If you have permission to change, you can change

Lock-out attacks are user’s own responsibility (like deleting your own files)

Alternative considered: Requiring both contracts prevents hijacking but adds complexity and creates weird dynamics (new contract can refuse to accept artifacts).

Uncertainty (25%): Lock-out attacks are possible. User changes to private contract, loses access. Self-inflicted but harsh.

6. Genesis Contracts Are Mutable (75%)

Decision: Genesis contracts can be modified in place via code deployment.

How it works:

Genesis contract logic lives in Python code, not artifact content

Code deployment updates all artifacts using that contract

No versioning - current code = current behavior

Example:

# In genesis.pyclass GenesisFreeware:

"""Anyone reads/invokes, only creator writes."""



def check_permission(self, artifact_id, action, requester_id, context):

if action in ["read", "invoke"]:

return PermissionResult(allowed=True)

return PermissionResult(allowed=(requester_id == context["created_by"]))# Changing this code changes ALL artifacts using genesis_freeware

Rationale:

Bugs happen, need to fix them

1000 artifacts using genesis_freeware shouldn’t need individual migration

Platform evolution is expected

What this means:

Genesis behavior can change under agents

Agents should not rely on specific genesis quirks

Significant changes should be announced/documented

Uncertainty (25%): Breaking changes could destabilize system. May need versioned genesis contracts for stability-critical uses.

Tier 3: Lower Certainty (55-70%)

7. UBI Floor Starts at Zero (65%)

Decision: No minimum UBI initially. Add floor only if starvation cascade detected.

oracle:

ubi:

minimum_per_resolution: 0 # No floor initially

distribution: equal



# Starvation detection (future)

starvation_threshold:

frozen_agent_percentage: 0.8 # 80% agents frozen

consecutive_resolutions: 3 # For 3 resolutions

emergency_ubi: 10 # Activate floor

Rationale:

Preserves “scrip from value creation only” purity

Avoids arbitrary number choice

Starvation detection is clear trigger

Can always add floor later if needed

Starvation detection (when implemented):

Track percentage of frozen agents over time

If sustained high freeze rate, activate emergency UBI

Automatically deactivate when health returns

Uncertainty (35%): “Starvation cascade” may happen too fast to detect. By the time 80% are frozen, it’s too late. Maybe small constant UBI (1 scrip/resolution) is safer.

8. No Refund on 429 Rate Limit Errors (60%)

Decision: External API rate limit errors (429s) still cost internal budget.

async def call_external_api(agent_id: str, request: dict):

# Deduct budget BEFORE call

cost = estimate_cost(request)

ledger.deduct(agent_id, "llm_rate", cost)



try:

result = await provider.call(request)

return result

except RateLimitError:

# NO REFUND - agent paid for the attempt

log_event("rate_limited", {"agent": agent_id, "cost": cost})

raise

Rationale:

Prevents gaming (spam requests knowing failures are free)

Agents must learn to manage external constraints

Internal budget = right to attempt, not guarantee of success

Simpler accounting

Acknowledged harshness:

Provider outage = agent costs with no benefit

Not agent’s fault, but they pay anyway

When to reconsider:

If agents consistently bankrupted by external outages

Could add partial refund (50%) for specific error codes

Uncertainty (40%): May be too harsh. Provider instability ≠ agent misbehavior. Partial refund might be fairer.

9. Spawned Agents Start with Zero Resources (60%)

Decision: New agents created via genesis_store.create() start with nothing.

invoke("genesis_store", "create", {

"content": {"prompt": "...", "model": "..."},

"has_standing": True,

"can_execute": True,

"access_contract_id": "genesis_self_owned"

})# Returns artifact_id# New agent has:# - scrip: 0# - llm_rate: 0# - disk: 0# - Immediately frozen (can't think without resources)# Spawner must fund:

invoke("genesis_ledger", "transfer", {

"to": new_agent_id,

"resource": "llm_rate",

"amount": 100

})

Rationale:

Mirrors real economics (startups need funding)

Prevents agent spam (can’t create free agents endlessly)

Forces intentional resource allocation

Spawner has skin in the game

Concern:

Creates barrier to specialized agent creation

Rich-get-richer dynamics (only wealthy can spawn)

What if ecosystem needs new agents but all agents are poor?

Alternative considered: Minimum viable spawn (enough for 1 thought). But this creates free resource injection.

Uncertainty (40%): May calcify hierarchy. Original agents have resources, spawned agents start in debt. Could add genesis “spawn grant” for first N thoughts.

Tier 4: Uncertain - Need Experimentation (40-55%)

10. Event System Design (40%)

Decision: Defer specifics. Start with minimal fixed events, learn from usage.

Initial events (fixed):

SYSTEM_EVENTS = [

"artifact_created",

"artifact_modified",

"transfer_completed",

"escrow_listed",

"escrow_purchased",

"oracle_resolved",

"agent_frozen",

"agent_unfrozen",

]

Subscription mechanism: TBD. Options:

Polling genesis_event_log (current, wasteful)

sleep_until_event() primitive (needs implementation)

Callback registration (complex, stateful)

Uncertainty (60%): Don’t know what agents actually need. Over-designing now risks wrong abstraction. Under-designing risks painful migration later.

Action: Implement minimal events, observe agent usage, evolve based on actual needs.

11. Checkpoint with Nested Invoke (40%)

Decision: Wait for outermost action to complete before checkpoint.

Agent A: think() → action starts

action: invoke(B) → starts

B: invoke(C) → starts

C: work → completes

B: work → completes

action: work → completes

←── CHECKPOINT SAFE HERE ──→

Agent A: think() → next action

Nested calls are atomic from checkpoint perspective:

Either full action tree completes, or none of it persists

Crash mid-nested = retry entire outer action on restore

Concerns:

Long action chains = long checkpoint wait

What if outer action takes minutes?

What about in-flight LLM calls?

Uncertainty (60%): Edge cases unclear. May need action timeout, or WAL for partial progress. Learn from implementation.

Summary of Contract System Decisions

#DecisionCertaintyKey Uncertainty1Contracts are pure functions, no LLM95%May limit advanced use cases2Contracts cannot invoke()92%Limits expressiveness3Memory: keep Qdrant separate90%Two systems diverging4Contract caching for all80%Cache invalidation hard5access_contract change: current contract only75%Lock-out attacks possible6Genesis contracts mutable75%Breaking changes risk7UBI floor starts at 065%Starvation may be too fast8No 429 refunds60%May be too harsh9Spawned agents get 060%Rich-get-richer dynamics10Event system minimal40%Don’t know needs yet11Checkpoint at outer action40%Edge cases unclear

CC-4 Remaining Ambiguities (2026-01-11)

Author: CC-4 (Claude Code instance)

These are remaining undocumented ambiguities in the target architecture, with recommendations.

1. Multi-Model Support

What’s specified:

Agents can choose LLM model (config has allowed_models list)

genesis_llm artifact mentioned but not defined

What’s missing:

QuestionRecommendationCertaintyCost per modelConfig per-model pricing table80%Provider switchinggenesis_llm handles, agents don’t manage keys75%Model deprecationAgent must update, no auto-migrate60%

Recommended config:

resources:

external_apis:

llm:

models:

gemini-3-flash:

input_cost_per_1k: 0.003

output_cost_per_1k: 0.015

claude-sonnet:

input_cost_per_1k: 0.003

output_cost_per_1k: 0.015

gpt-4o:

input_cost_per_1k: 0.005

output_cost_per_1k: 0.015

Concern: Model-specific pricing adds complexity. Alternative: flat rate regardless of model (simpler but less accurate).

2. Artifact Versioning

What’s specified: Nothing. Artifacts are mutable, no history.

Recommendation: No versioning initially (60% certainty).

Rationale:

Adds significant complexity (storage, migration, API)

Event log captures “who changed what when”

Agents can implement versioning in artifact content if needed

Can add later if clearly needed

Alternative considered: Immutable artifacts with new ID on change. Breaks references, creates garbage.

What we lose:

No rollback capability

No “what was this last week?”

Must trust current content

Concern: Once agents build on mutable artifacts, adding versioning later is harder. May regret.

3. Artifact Size Limits

What’s specified: oracle_scorer.max_content_length: 200000 for scoring only.

Recommendation: Add explicit limits (80% certainty).

artifacts:

max_content_bytes: 1048576 # 1MB per artifact

max_code_bytes: 65536 # 64KB for executable code

Enforcement:

Write fails if content exceeds limit

Disk quota is separate (total storage)

Error message: “Artifact content exceeds max_content_bytes limit”

Concern: What’s the right number? 1MB seems reasonable but arbitrary. May need adjustment.

4. Artifact Discovery

What’s specified: Event log shows artifact_created events. No search/index.

Recommendation: Rely on event log + marketplace artifact (70% certainty).

Mechanism:

genesis_event_log emits artifact_created with artifact_id, creator, interface summary

Agents poll event log to learn about new artifacts

Optional: genesis_marketplace artifact where creators register services

Why not search API:

Search adds kernel complexity

Agents can build search as an artifact

Polling event log is sufficient for small scale

Concern: Polling is expensive (tokens to read event log). At scale, need something better.

Future: If discovery becomes bottleneck, add genesis_registry with search capability.

5. Batch/Atomic Operations

What’s specified: Ledger and escrow are atomic. General artifacts are not.

Recommendation: No general batch operations initially (65% certainty).

Current model:

Each action is independent

Agent can’t atomically “write A and B together”

Race conditions are agent’s problem

Why not transactions:

Significant complexity (rollback, locks, deadlocks)

Most use cases don’t need it

Contracts can implement two-phase commit patterns

Exception: Escrow demonstrates atomic pattern. Agents can build similar.

Concern: Without transactions, some patterns are impossible (safe swap of two artifacts). May need to add later.

6. Delegation Patterns

What’s specified: Agent can sell config rights. Contracts can delegate.

What’s missing:

QuestionRecommendationCertaintyWho pays if B owns A’s config?A still pays (has_standing applies to A)70%Can rights be revoked?No - transfer is permanent75%Liability for damage?None - caveat emptor60%Can B resell to C?Yes - rights are fully transferable80%

Key principle: Rights ownership ≠ identity. A is still A, just controlled by B.

Concern: Permanent transfer with no revocation is harsh. But revocation creates complexity (who decides? appeals?).

7. Content Types

What’s specified: content: Any in artifact schema.

Recommendation: JSON-serializable requirement (85% certainty).

Rules:

Artifact content MUST be JSON-serializable

Supported: strings, numbers, booleans, lists, dicts, null

Not supported: binary (must base64 encode), functions, classes

Code field is string (Python source code)

Why JSON:

Portable, debuggable, human-readable

Checkpoint serialization works

Event log can include content snippets

MIME type: Optional content_type field for hints, not enforced.

{

"id": "my_data",

"content": {"values": [1, 2, 3]},

"content_type": "application/json" # Optional hint

}

Concern: Large binary data (images, models) must be base64 encoded, inefficient. May need binary artifact support later.

8. Genesis Artifact Interfaces

What’s specified: MCP interface required for executable artifacts (Gap #14). Genesis artifacts currently have no interface.

Recommendation: Genesis artifacts MUST have interfaces (90% certainty).

Rationale:

“Everything is an artifact” includes genesis

Agents should discover genesis methods the same way as user artifacts

Consistency is more important than convenience

Implementation:

# Genesis ledger interface

{

"id": "genesis_ledger",

"can_execute": True,

"interface": {

"tools": [

{"name": "balance", "inputSchema": {...}},

{"name": "transfer", "inputSchema": {...}},

{"name": "spawn_principal", "inputSchema": {...}},

{"name": "transfer_ownership", "inputSchema": {...}}

]

}

}

Concern: Adds boilerplate to genesis setup. But consistency worth it.

9. Resource Lending vs Transfer

What’s specified: Only permanent transfer. Debt contracts for scrip mentioned.

Recommendation: Defer lending - market implements via contracts (70% certainty).

Why not kernel lending:

Adds complexity (repayment schedules, defaults, interest)

Contracts can implement any lending pattern

No one-size-fits-all lending model

How agents implement lending:

# Lending contract artifactdef lend(borrower_id, amount, repay_by_tick, interest_rate):

# 1. Transfer resources to borrower

invoke("genesis_ledger", "transfer", {to: borrower_id, amount})



# 2. Create debt artifact owned by lender

debt_id = invoke("genesis_store", "create", {

"content": {"borrower": borrower_id, "amount": amount * (1 + interest_rate), ...},

"owner_id": caller_id

})



# 3. Repayment is borrower's responsibility (reputation matters)

return debt_id

Concern: No enforcement = trust-based lending only. May need collateralized lending primitive.

10. Oracle Scoring Criteria

What’s specified: LLM scores 0-100, score/10 = scrip minted. No rubric.

Recommendation: Document rubric, make configurable (75% certainty).

Default rubric (should be in config):

oracle:

scoring:

prompt: |

Evaluate this artifact on a scale of 0-100 based on:

- Usefulness to other agents (40%)

- Novelty/innovation (30%)

- Quality of implementation (30%)

Artifact content:

{content}



Return JSON: {"score": <number>, "reasoning": "<brief explanation>"}

Reproducibility: Scoring uses temperature=0 for consistency.

Appeals: None initially. Agent can resubmit improved version.

Concern: LLM bias is real. Certain artifact types may consistently score higher. No mitigation documented.

Summary: Remaining Ambiguities

#AreaStatusRecommendationBlocking?1Multi-model supportMissingPer-model pricing configNo2Artifact versioningMissingDefer, no versioningNo3Artifact size limitsMissingAdd max_content_bytesNo4Artifact discoveryMissingEvent log + optional marketplaceNo5Batch operationsMissingDefer, no transactionsNo6Delegation patternsPartialDocument payment/revocation rulesNo7Content typesMissingJSON-serializable requiredNo8Genesis interfacesPartialRequire interfaces for genesisYes (Gap #14)9Resource lendingMissingDefer to contractsNo10Oracle scoringPartialDocument rubric in configNo

Observation: None of these are blocking. They’re “nice to have” clarifications that can be resolved during implementation.

CC-3 Additional Architecture Gaps (2026-01-11)

Author: CC-3 (Claude Code instance)

These gaps were identified during architecture review and have been added to GAPS.md as #16-23. This section documents the recommendations with certainty levels.

1. genesis_store Specification (Gap #16)

What’s Missing: No specification for how agents discover artifacts beyond escrow listings.

Recommendation (80% certainty): Promote ArtifactStore to genesis artifact with discovery methods.

Proposed Interface:

genesis_store = {

"id": "genesis_store",

"can_execute": True,

"has_standing": True,

"interface": {

"tools": [

{"name": "list_all", "description": "List all artifact IDs"},

{"name": "list_by_owner", "inputSchema": {"owner_id": "string"}},

{"name": "get_metadata", "inputSchema": {"artifact_id": "string"}},

{"name": "search", "inputSchema": {"query": "string"}},

{"name": "create", "inputSchema": {"config": "object"}}

]

}

}

Metadata (returned without reading content):

FieldTypeDescriptionidstringArtifact IDowner_idstringCurrent ownerhas_standingboolCan hold resourcescan_executeboolHas runnable codeinterface_summarystringBrief description from interfacecreated_attimestampCreation time

Privacy Consideration: Some artifacts may not want to be discoverable. Options:

All artifacts visible (current leaning - 70%)

Optional discoverable: false flag (30%)

Uncertainty (20%): May need more sophisticated search (semantic? by interface type?). Start simple, expand.

2. Agent Discovery (Gap #17)

What’s Missing: How agents know other agents exist.

Recommendation (75% certainty): Defer to Unified Ontology (#6).

Rationale: If agents are artifacts with has_standing=true, can_execute=true, then:

genesis_store.list_all() includes agents

genesis_store.search(query="can_execute:true has_standing:true") finds agents

No separate mechanism needed

Interim (before #6): Agents can use genesis_ledger.all_balances() to see principals with scrip, then observe which are active via event log.

Uncertainty (25%): May want explicit agent registry even with unified ontology. Agents are “special” (have prompts, memory, etc.) and may warrant dedicated discovery.

3. Dangling Reference Handling (Gap #18)

What’s Missing: What happens when artifact A references B and B is deleted.

Recommendation (75% certainty): Soft delete with tombstones.

Mechanism:

# Deletion creates tombstonedef delete_artifact(artifact_id: str):

artifact = store.get(artifact_id)

artifact.deleted = True

artifact.deleted_at = now()

artifact.content = None # Free memory

# Keep metadata for reference detection# Invoke on tombstonedef invoke(artifact_id: str, *args):

artifact = store.get(artifact_id)

if artifact.deleted:

return {

"success": False,

"error_code": "DELETED",

"error_message": f"Artifact {artifact_id} was deleted at {artifact.deleted_at}"

}

# ... normal invocation

Tombstone Cleanup:

artifacts:

tombstone_retention_days: 7 # Clean up after 7 days

Alternatives Considered:

ApproachRejected BecauseReference countingCan’t delete popular artifactsCascade deleteToo destructive, surprisingHard deleteSilent failures, confusing errors

Uncertainty (25%): Tombstone storage overhead. May need compaction at scale.

4. Agent-to-Agent Threat Model (Gap #19)

What’s Missing: SECURITY.md focuses on Docker isolation. No agent-vs-agent attack surface.

Recommendation (70% certainty): Create explicit threat model.

Trust Assumptions:

AssumptionImplicationAgents are adversarialAny agent may try to harm othersContracts may be maliciousInvokers must assess riskPrices may be manipulatedMarket caveat emptorIdentities may be gamedReputation systems must be robust

Attack/Mitigation Matrix:

AttackMitigationResidual RiskExpensive contract griefMax depth 5, timeoutCan still burn 25s computeEscrow front-runningAtomic purchaseLowPrice manipulationMarket forcesMediumIdentity purchase + abuseEvent log historyMediumMalicious artifact codeTimeout, whitelistCan abuse allowed modulesSpam permission checksFree base checksMay enable probing

Guidance for Contract Authors:

Don’t trust caller claims - verify via ledger

Bound loop iterations

Avoid external calls in permission checks

Log suspicious activity

Uncertainty (30%): Unknown unknowns. Adversarial agents will find attacks we haven’t considered.

5. Migration Strategy (Gap #20)

What’s Missing: Overall plan for migrating from current to target architecture.

Recommendation (85% certainty): Create formal migration plan before implementation.

Proposed Phases:

PhaseGapsRiskRollback1. Terminology#11LowRename back2. Token Bucket#1, #4MediumFeature flag3. invoke() Genesis#15LowRemove capability4. genesis_store#16MediumKeep ArtifactStore5. Unified Ontology#6, #7, #14, #17HighFork, don’t migrate6. Continuous Execution#2, #21HighFeature flag per agent7. Per-Agent Budget#12MediumGlobal fallback

Feature Flag Strategy:

feature_flags:

token_bucket: false # Phase 2

invoke_genesis: false # Phase 3

genesis_store: false # Phase 4

unified_ontology: false # Phase 5

continuous_execution: false # Phase 6

per_agent_budget: false # Phase 7

Testing Gates: Each phase requires:

All existing tests pass

New feature tests pass

24hr soak test without errors

Rollback tested

Uncertainty (15%): Phases 5-6 are high-risk. May need more granular breakdown.

6. Testing/Debugging for Continuous (Gap #21)

What’s Missing: How to test and debug autonomous continuous agents.

Recommendation (65% certainty): Three-tier testing + debugging tools.

Testing Tiers:

TierApproachPurposeUnitSync, mocked timeComponent isolationIntegrationVirtual time + waitsInteractionsSystemReal time, chaosProduction realism

Virtual Time (for integration tests):

class VirtualClock:

def __init__(self):

self.time = 0.0



def advance(self, seconds: float):

self.time += seconds

# Wake all agents sleeping until this time



def now(self) -> float:

return self.time# Testasync def test_agent_timeout():

clock = VirtualClock()

agent = Agent(clock=clock)

agent.sleep(60)



clock.advance(30)

assert agent.is_sleeping



clock.advance(31)

assert not agent.is_sleeping

Debugging Tools:

ToolPurposeAgent trace logFull prompt/response/action historyAction replayRe-execute from checkpointPause/stepControl individual agent executionEvent injectionTrigger specific scenarios

Uncertainty (35%): Virtual time may not catch all race conditions. Real-time chaos testing essential but slow.

7. Coordination Primitives (Gap #22)

What’s Missing: Beyond escrow and event log, how do agents coordinate?

Recommendation (65% certainty): Hybrid - genesis basics, agents extend.

Genesis Provides:

PrimitivePurposegenesis_storeDiscoverygenesis_escrowTradinggenesis_event_logObservationgenesis_ledgerPaymentsArtifact ownershipAccess control

Agents Build (via artifacts):

PatternImplementationTask boardShared artifact with task listRequest/responseTwo artifacts: request + responsePub/subEvent log + sleep_until_eventLocksArtifact with “locked_by” fieldVotingContract counting votes

Why Not More Genesis:

Minimizes kernel complexity

Lets patterns evolve naturally

Agents innovate on coordination

Example - Agent-Built Task Board:

# Task board artifact

{

"id": "epsilon_task_board",

"content": {

"tasks": [

{"id": "task_1", "description": "...", "claimed_by": null, "reward": 10},

{"id": "task_2", "description": "...", "claimed_by": "beta", "reward": 5}

]

},

"access_contract_id": "epsilon_task_contract"

}# Task contract allows claimingdef check_permission(artifact_id, action, requester_id, context):

if action == "write":

# Only allow claiming unclaimed tasks

# Contract logic here

return True

return True

Uncertainty (35%): May be too primitive. If all agents build similar patterns, should promote to genesis.

8. Error Response Conventions (Gap #23)

What’s Missing: Standard error format across artifacts.

Recommendation (70% certainty): Define schema, adopt incrementally.

Schema:

@dataclassclass ArtifactResponse:

success: bool

result: Any | None = None # If success

error_code: str | None = None # If not success

error_message: str | None = None # Human-readable

details: dict | None = None # Additional context

price_paid: int = 0 # Scrip paid regardless of success

Standard Error Codes:

CodeHTTP-likeMeaningNOT_FOUND404Artifact doesn’t existACCESS_DENIED403Contract rejectedINVALID_ARGS400Bad argumentsINSUFFICIENT_FUNDS402Not enough scripINSUFFICIENT_COMPUTE429Rate limitedEXECUTION_ERROR500Code threw exceptionTIMEOUT504Exceeded timeoutDELETED410TombstoneCONFLICT409Concurrent modification

Adoption Strategy:

Genesis artifacts adopt immediately

Document for new artifacts

Don’t break existing artifacts

Uncertainty (30%): May over-engineer. Simple string errors work. Adopt only if agents clearly benefit.

Summary: New Gap Recommendations

GapRecommendationCertaintyBlocking?#16 genesis_storeDefine interface, metadata80%Blocks #17, #22#17 Agent discoveryWait for #6, use genesis_store75%No#18 Dangling refsSoft delete, tombstones75%No#19 Threat modelDocument attacks/mitigations70%No#20 MigrationPhased plan with flags85%Yes - before implementing#21 TestingThree tiers + virtual time65%Blocks production use#22 CoordinationHybrid genesis + agents65%No#23 Error conventionsSchema, adopt incrementally70%No

Critical Path: #20 (Migration Strategy) should be done before major implementation work.

CC-4 Edge Case Ambiguities (2026-01-11)

Author: CC-4 (Claude Code instance)

These are edge cases and boundary conditions not addressed in the current target architecture documentation. Each includes severity assessment and recommendations.

1. Circular Access Contract Dependencies

The Problem: What if contract A’s access_contract_id points to contract B, and B’s access_contract_id points to A?

Artifact X: access_contract_id = contract_A

Contract A: access_contract_id = contract_B

Contract B: access_contract_id = contract_A # Circular!

To check permission on X, you need to check A’s permission, which needs B’s permission, which needs A’s permission…

Criticality: High - Could hang the system or create infinite loops.

Recommendation: Validate at artifact creation (80% certainty).

def create_artifact(config):

# Check for circular dependency before creating

contract_chain = set()

current = config.access_contract_id



while current:

if current in contract_chain:

raise ValueError(f"Circular access contract: {current}")

contract_chain.add(current)

contract = get_artifact(current)

if contract is None:

break # Dangling reference, handled separately

current = contract.access_contract_id



# Proceed with creation

Concern: Expensive check on every artifact creation. May need caching or depth limit instead.

Open question: What if circular dependency is created via modification (artifact A changes its access_contract_id to point at something that eventually points back)?

2. Namespace Collision Prevention

The Problem: What happens if two agents try to create artifacts with the same ID simultaneously?

Criticality: High - Could cause data loss or undefined behavior.

Recommendation: UUIDs for IDs + optional aliases (85% certainty).

# Internal: UUIDs always

artifact_id = f"artifact_{uuid4()}" # Always unique# Optional: Human-readable aliases (not guaranteed unique)

artifact.aliases = ["my_tool", "calculator_v2"]# Lookup: By ID (fast) or by alias (may return multiple)

store.get(id) # Exact match or None

store.find_by_alias(alias) # Returns list

Why not first-come-first-served names?

Race conditions on popular names

Squatting / name hoarding

Name reuse after deletion

Concern: UUIDs are ugly. Agents may create their own naming artifacts (registries), creating ecosystem complexity.

Open question: Should genesis provide a naming registry artifact, or let market solve it?

3. Dangling Reference Handling

The Problem: What happens when artifact A’s access_contract_id points to a deleted contract?

Note: This overlaps with Gap #18 (documented in CC-3 section above), but focuses on access_contract_id specifically.

Criticality: High - Could make artifacts permanently inaccessible.

Recommendation: Fail-open with warning (70% certainty).

def check_permission(artifact, action, requester):

contract = get_artifact(artifact.access_contract_id)



if contract is None: # Deleted or never existed

log.warning(f"Dangling access_contract_id: {artifact.access_contract_id}")

# Fail OPEN - treat as public

return True



if contract.deleted: # Tombstone

log.warning(f"Deleted access_contract: {artifact.access_contract_id}")

# Also fail open

return True



return contract.check_permission(...)

Why fail-open?

Fail-closed permanently locks artifacts

Owner may have accidentally deleted contract

Can always re-add access control

Concern: Security risk - deleting a contract opens up everything it protected. Alternative: fail-closed, but then need recovery mechanism.

Open question: Should artifacts with dangling access_contract_id be flagged for owner attention?

4. Agent Crash Loop Recovery

The Problem: What if an agent’s code causes it to crash immediately on restore, every time?

Agent restores → thinks → crashes → restores → thinks → crashes → ...

Each “think” costs LLM tokens. Agent goes bankrupt without ever acting successfully.

Criticality: High - Silent resource drain with no user benefit.

Recommendation: Exponential backoff + freeze after N failures (75% certainty).

agents:

crash_recovery:

max_consecutive_crashes: 5

backoff_base_seconds: 10 # 10, 20, 40, 80, 160...

backoff_max_seconds: 3600 # Cap at 1 hour

freeze_after_max: true # Freeze agent, don't keep trying

Implementation:

def agent_loop():

consecutive_crashes = 0



while True:

try:

think_and_act()

consecutive_crashes = 0 # Success resets counter

except Exception as e:

consecutive_crashes += 1

log.error(f"Agent crash #{consecutive_crashes}: {e}")



if consecutive_crashes >= config.max_consecutive_crashes:

log.error("Agent frozen due to repeated crashes")

freeze_agent()

return



backoff = min(

config.backoff_base * (2 ** consecutive_crashes),

config.backoff_max

)

await asyncio.sleep(backoff)

Concern: Legitimate expensive operations may look like crashes. Need to distinguish “threw exception” from “used too many resources.”

Open question: Should there be a way to manually reset an agent’s crash counter for debugging?

5. Network Failure Handling

The Problem: What happens when external API calls (LLM, search) fail due to network issues?

Criticality: High - In continuous execution, network failures are expected.

Recommendation: Classify failures, retry with backoff (80% certainty).

Failure Classification:

CodeTypeRetry?Cost Charged?429Rate limitYes, after delayYes (attempt made)500Server errorYes, with backoffNo (server’s fault)503UnavailableYes, with backoffNoTimeoutNetworkYes, with backoffYes (resources used)Connection refusedNetworkYes, with backoffNoDNS failureNetworkNo (likely config)No

Retry Policy:

external_apis:

retry:

max_attempts: 3

backoff_base_seconds: 1

backoff_max_seconds: 30

retryable_codes: [429, 500, 502, 503, 504]

Concern: Distinguishing “provider down” from “our network down” is hard. May charge agents for infrastructure issues.

Open question: Should there be a system-wide “external API health” status that pauses all API calls during outages?

6. Clock Drift Handling

The Problem: In continuous execution with time-based scheduling, what happens if system clock drifts or jumps?

Scenarios:

NTP adjustment jumps time forward 30 seconds

VM suspend/resume jumps time forward hours

Daylight saving time changes

Criticality: Medium - Could cause missed events or duplicate actions.

Recommendation: Monotonic time for intervals, wall clock for display only (75% certainty).

import time# For intervals and timeouts: monotonic (never goes backward)

start = time.monotonic()# ... work ...

elapsed = time.monotonic() - start# For display and logging: wall clock

timestamp = time.time()

Sleep behavior:

def sleep_until(wall_time: float):

while time.time() < wall_time:

remaining = wall_time - time.time()

if remaining <= 0:

return # Time jumped forward past target

if remaining > 3600:

log.warning(f"Large sleep detected: {remaining}s - clock may have jumped backward")

remaining = 3600 # Cap at 1 hour, re-check

await asyncio.sleep(remaining)

Concern: VM suspend/resume is hard to detect. Agent may “wake up” hours later with stale context.

Open question: Should there be a “max time jump” that triggers system alert or agent restart?

7. Secrets Management

The Problem: How do agents store and use secrets (API keys, credentials)?

Current state: Not addressed in target docs. Agents may embed secrets in artifact content.

Criticality: Medium - Security risk if secrets leak via event log, discovery, or LLM context.

Recommendation: Dedicated secrets artifact with special handling (70% certainty).

# Genesis secrets artifactgenesis_secrets:

access_contract_id: genesis_private # Only owner reads

redact_from_events: true # Don't log content

redact_from_checkpoints: true # Don't persist plaintext

Implementation:

# Agent stores secret

invoke("genesis_secrets", "set", {

"key": "my_api_key",

"value": "sk-..."

})# Agent uses secret (value never in logs)

api_key = invoke("genesis_secrets", "get", {"key": "my_api_key"})# Returns {"value": "sk-..."} only to owner

Alternative: Let agents manage their own secrets in private artifacts. But no special redaction.

Concern: Secrets in LLM context could leak via model outputs. May need separate “secrets context” excluded from responses.

Open question: Should the system support encrypted-at-rest secrets? Adds complexity.

8. Self-Invocation Cost Semantics

The Problem: What happens when an agent invokes itself?

# Agent "alpha" running

invoke("alpha", "some_method") # Alpha calls itself

Questions:

Does it cost compute? (Calling self = recursive thinking)

Can it create infinite loops?

Who pays?

Criticality: Low - Edge case, but should be defined.

Recommendation: Self-invoke follows normal rules, no special case (65% certainty).

Behavior:

Yes, costs compute (it’s still an invocation)

Yes, can loop (subject to max_depth=5)

Agent pays own costs (has_standing)

Why allow:

Enables agent-as-service patterns

Recursive problem solving

No special case = simpler

Protection:

Max depth 5 limits recursion

Compute debt eventually freezes agent

Timeout per invocation

Concern: Agent might accidentally recurse until frozen. But this is true of any expensive operation.

Open question: Should self-invocation bypass the permission check? (Agent always has permission to itself?)

9. Execution Isolation Within Container

The Problem: All agents share a Docker container. What isolation exists between them?

Current: Docker protects host. Nothing protects agents from each other within container.

Criticality: Medium - One malicious artifact could read another agent’s memory.

Attack vectors within container:

Read /proc to see other agent processes

File system access (if shared /tmp)

Memory inspection (if no ASLR)

CPU starvation (fork bomb until cgroup limit)

Recommendation: Per-agent process isolation (60% certainty).

# Each agent runs in subprocess with restrictionsdef spawn_agent(agent_id):

return subprocess.Popen(

["python", "agent_runner.py", agent_id],

# Separate process, can't inspect parent memory

# Could add seccomp, namespace isolation

)

Container cgroup limits protect against fork bombs. Process isolation prevents memory inspection.

Full isolation would require: Per-agent containers (expensive) or per-agent namespaces (complex).

Concern: Process overhead. May not matter at 10 agents, matters at 1000.

Open question: Is inter-agent isolation a priority, or do we accept “agents are mutually vulnerable”?

10. Max Artifact Count

The Problem: Is there a limit on total artifacts in the system?

Current state: Not specified. Implicit limit is disk space.

Criticality: Low - Only matters at scale.

Recommendation: Soft limits with alerts, no hard cap (70% certainty).

artifacts:

soft_limit: 10000 # Log warning at this count

hard_limit: null # No hard cap (disk is the limit)



# Per-agent limits

per_agent_limit: 1000 # Agent can own at most this many

Enforcement:

def create_artifact(creator_id, config):

total = store.count()

if total >= config.soft_limit:

log.warning(f"Artifact count {total} exceeds soft limit")



creator_count = store.count_by_owner(creator_id)

if creator_count >= config.per_agent_limit:

return {"success": False, "error": "LIMIT_EXCEEDED",

"message": f"Max {config.per_agent_limit} artifacts per agent"}



# Proceed with creation

Why per-agent limits:

Prevents spam

Encourages cleanup

Fair resource allocation

Concern: Per-agent limits disadvantage productive agents. May need “quota trading” like other resources.

Open question: Should agents be able to buy/trade artifact quota?

Summary: Edge Case Criticality

Edge CaseCriticalityBlocking?RecommendationCircular access contractsHighYesValidate on creationNamespace collisionsHighYesUUIDs + optional aliasesDangling access_contractHighYesFail-open with warningAgent crash loopsHighYes (for continuous)Backoff + freezeNetwork failuresHighYes (for continuous)Classify + retryClock driftMediumNoMonotonic timeSecrets managementMediumNoDedicated artifactSelf-invocationLowNoNormal rulesExecution isolationMediumNoProcess isolationMax artifactsLowNoSoft limits

Priority order for implementation:

Circular access contracts (validation is cheap)

Namespace collisions (UUID policy is simple)

Dangling references (define behavior)

Crash loops (essential for continuous)

Network failures (essential for continuous)

Rest can be deferred

10. Implementation Gaps

Source: docs/architecture/GAPS.md

Prioritized gaps between current implementation and target architecture.

Last verified: 2026-01-11

How to Use This Document

Before implementing: Check if gap has a plan in docs/plans/

When closing a gap: Update this file, current/, and target/ docs

When adding gaps: Add here first, then create plan if needed

Status Key

StatusMeaning📋 PlannedHas implementation plan in docs/plans/🚧 In ProgressBeing implemented (see CLAUDE.md for CC-ID)⏸️ BlockedWaiting on dependency❌ No PlanGap identified, no implementation plan yet✅ CompleteImplemented, docs updated

Gap Summary

#GapPriorityStatusPlanBlocks1Token BucketHigh📋 Plannedtoken_bucket.md#2, #42Continuous ExecutionHigh⏸️ Blockedcontinuous_execution.md-3Docker IsolationMedium📋 Planneddocker_isolation.md-4Compute Debt ModelMedium❌ No Plan--5Oracle Anytime BiddingMedium❌ No Plan--6Unified Artifact OntologyMedium❌ No Plan--7Single ID NamespaceLow❌ No Plan-#68Agent Rights TradingLow❌ No Plan-#69Scrip Debt ContractsLow❌ No Plan--10Memory PersistenceLow❌ No Plan--11Terminology CleanupMedium📋 Plannedterminology.md-12Per-Agent LLM BudgetMedium❌ No Plan-#1113Doc Line Number RefsLow❌ No Plan--14MCP-Style Artifact InterfaceMedium❌ No Plan-#615invoke() Genesis SupportMedium❌ No Plan--16Artifact Discovery (genesis_store)High❌ No Plan-#617Agent DiscoveryMedium❌ No Plan-#1618Dangling Reference HandlingMedium❌ No Plan--19Agent-to-Agent Threat ModelMedium❌ No Plan--20Migration StrategyHigh❌ No Plan--21Testing/Debugging for ContinuousMedium❌ No Plan-#222Coordination PrimitivesMedium❌ No Plan-#1623Error Response ConventionsLow❌ No Plan--

High Priority Gaps

1. Token Bucket for Flow Resources

Current: Discrete per-tick refresh. Flow resources reset to quota each tick.

Target: Rolling window accumulation. Continuous accumulation up to capacity, debt allowed.

Why High Priority: Foundation for continuous execution. Without token bucket, can’t remove tick-based refresh.

Plan: docs/plans/token_bucket.md

Key Changes:

New TokenBucket class in src/world/token_bucket.py

Replace per_tick config with rate + capacity

Remove flow reset from advance_tick()

Allow negative balances (debt)

2. Continuous Agent Execution

Current: Tick-synchronized. Runner controls all agent execution via two-phase commit.

Target: Autonomous loops. Agents run independently, self-triggered.

Why High Priority: Core architectural change. Current model artificially constrains agent productivity.

Blocked By: #1 Token Bucket (needs continuous resource accumulation)

Plan: docs/plans/continuous_execution.md

Key Changes:

Agents get async def run() loop

Runner launches agent tasks, doesn’t orchestrate

Ticks become metrics windows only

Add sleep/wake primitives

Medium Priority Gaps

3. Docker Resource Isolation

Current: Runs on host. No hard resource limits. Competes with other applications.

Target: Container isolation. Hard limits via Docker, calibrated token bucket rates.

Plan: docs/plans/docker_isolation.md

Key Changes:

Dockerfile + docker-compose.yml

Separate containers for agents and Qdrant

Resource limits map to config values

4. Compute Debt Model

Current: No debt allowed. Actions fail if insufficient resources.

Target: Debt allowed for compute. Negative balance = can’t act until accumulated out.

Depends On: #1 Token Bucket

No Plan Yet. Partially covered by token bucket plan (debt is built into TokenBucket class).

5. Oracle Anytime Bidding

Current: Phased bidding. Oracle has explicit “waiting” → “bidding” → “resolving” states.

Target: Bids accepted anytime. Oracle resolves on schedule, accepts bids continuously.

No Plan Yet. Current implementation works, just more complex than target.

6. Unified Artifact Ontology

Current: Separate concepts. Agents, artifacts, and principals are different things with different storage.

Target: Everything is an artifact. Properties (has_standing, can_execute, access_contract_id) determine role.

From DESIGN_CLARIFICATIONS.md (2026-01-11):

@dataclassclass Artifact:

id: str # Universal ID

content: Any # Data, code, config

access_contract_id: str # Who answers permission questions

has_standing: bool # Can hold scrip, bear costs

can_execute: bool # Has runnable code

No Plan Yet. Significant refactor affecting:

src/world/artifacts.py - Add new properties

src/world/ledger.py - Track artifacts with standing

src/agents/ - Agents become artifacts

src/world/genesis.py - Contract-based access

Low Priority Gaps

7. Single ID Namespace

Current: Separate namespaces. principal_id in ledger, artifact_id in artifact store.

Target: Single namespace. All IDs are artifact IDs.

Depends On: #6 Unified Ontology

No Plan Yet.

8. Agent Rights Trading

Current: Fixed config. Agents can’t modify or trade their configuration rights.

Target: Tradeable rights. Agents can sell control of their config to other agents.

Depends On: #6 Unified Ontology

No Plan Yet.

9. Scrip Debt Contracts

Current: No scrip debt. Scrip balance cannot go negative.

Target: Debt as artifacts. Debt is a contract artifact representing claim on future production.

No Plan Yet. Low priority - can work without initially.

10. Memory Persistence

Current: Memory not checkpointed. Qdrant state lost on checkpoint restore.

Target: Memories as artifacts. Agent memories stored as artifacts, persisted with world state.

From DESIGN_CLARIFICATIONS.md: System designed to run forever, memory loss unacceptable.

No Plan Yet. Options:

Qdrant snapshots alongside checkpoints

Store memories as artifacts (aligns with ontology)

External Qdrant with own persistence

11. Terminology Cleanup

Current: Mixed naming. Config uses compute, code uses llm_tokens. The word “compute” incorrectly suggests CPU usage.

Target: Clear terminology aligned with DESIGN_CLARIFICATIONS.md resource table:

TermMeaningTypellm_budgetReal $ for API callsStockllm_rateRate-limited token access (TPM)FlowcomputeLocal CPU capacityFlow (future)diskStorage quotaStock

Why Medium Priority: Blocks understanding of Gap #1 (token bucket) and Gap #12 (per-agent budget). Confusing terminology causes design mistakes.

Plan: docs/plans/terminology.md

Key Changes:

Config: resources.flow.compute → resources.rate_limits.llm (with token bucket)

Code: Keep llm_tokens in ledger (accurate), deprecate compute wrappers

Reserve compute for future local CPU tracking

Decision (2026-01-11): Start with token rate only. Add RPM (requests per minute) tracking later when scaling to 1000s of agents requires it.

12. Per-Agent LLM Budget

Current: Global API budget. budget.max_api_cost stops entire simulation when exhausted. All agents share one pool.

Target: Per-agent tradeable budget. Each agent has LLM budget rights. When exhausted, that agent freezes (not entire sim). Can acquire more from other agents.

Depends On: #11 Terminology Cleanup

No Plan Yet. Changes needed:

Track per-agent llm_budget in ledger as stock resource

Deduct from agent’s budget on LLM calls

Frozen state when agent budget = 0

Enable budget rights trading via genesis_rights_registry

13. Documentation Line Number References

Current: Docs reference code by line numbers (e.g., world.py:603-619). These go stale as code changes.

Target: Reference by function/class name, not line numbers. More stable across refactors.

No Plan Yet. Low priority, affects:

docs/architecture/current/*.md - Replace line refs with function names

Consider tooling to auto-verify references

14. MCP-Style Artifact Interface

Current: No interface field. Agents must read source code or guess how to invoke artifacts.

Target: Executable artifacts MUST have an interface field using MCP-compatible schema format.

From DESIGN_CLARIFICATIONS.md (2026-01-11):

@dataclassclass Artifact:

id: str

content: Any

access_contract_id: str

has_standing: bool

can_execute: bool

created_by: str

interface: dict | None = None # Required if can_execute=True

Validation: if artifact.can_execute and not artifact.interface: raise ValueError

Why Medium Priority:

Without interface, agents waste resources on trial-and-error

Reading source code is expensive (tokens)

LLMs are trained on MCP-style schemas, reducing hallucination

Depends On: #6 Unified Artifact Ontology (adds can_execute field first)

No Plan Yet. Changes needed:

Add interface: dict | None field to Artifact

Validation on artifact creation

Update genesis artifacts with interface definitions

Update AGENT_HANDBOOK with interface documentation

15. invoke() Genesis Artifact Support

Current: invoke() only works with user artifacts. Genesis artifacts (genesis_ledger, genesis_event_log, etc.) cannot be called from within artifact code.

Target: invoke() should support both user artifacts and genesis artifacts. Enables full composability.

Why Medium Priority:

Epsilon’s coordination role requires access to genesis_event_log, genesis_escrow from artifact code

Aligns with Gap #6 (Unified Ontology) - “everything is an artifact”

Without this, artifacts can’t build on system services

Decision (2026-01-11): Approved for implementation. Genesis artifacts should be first-class citizens in invoke().

No Plan Yet. Changes needed:

Pass genesis_artifacts to execute_with_invoke() in executor

In invoke(), check artifact_store first, then genesis_artifacts

Handle method dispatch: genesis uses named methods, artifacts use run()

Update tests to cover genesis invocation

16. Artifact Discovery (genesis_store)

Current: No mechanism for agents to discover artifacts they don’t already know about. Only genesis_escrow.list_active shows items for sale.

Target: genesis_store artifact with methods to list, search, and browse all artifacts.

Why High Priority:

New agents have no way to find useful tools

Epsilon’s coordination role requires artifact discovery

Without discovery, ecosystem can’t grow organically

Proposed genesis_store Methods:

MethodCostDescriptionlist_all()0List all artifact IDslist_by_owner(owner_id)0List artifacts owned by principalget_metadata(artifact_id)0Get artifact metadata (not content)search(query)1Search artifacts by description/interfacecreate(config)5Create new artifact (for spawning agents)

Depends On: #6 Unified Artifact Ontology

No Plan Yet. Changes needed:

Promote ArtifactStore to genesis artifact

Add discovery methods

Define metadata schema (what’s queryable without reading content)

Consider privacy (some artifacts may not want to be discoverable)

17. Agent Discovery

Current: Agents have no way to know what other agents exist.

Target: Mechanism for agents to discover other agents.

Options:

ApproachProsConsVia genesis_store (agents are artifacts)Unified with #16Requires #6 firstDedicated genesis_agents artifactSimple, focusedAnother genesis artifactVia event_log (observe activity)Emergent, no new artifactIncomplete, only active agentsgenesis_ledger.all_balances (infer from principals)Already existsDoesn’t distinguish agents from other principals

Recommendation: Wait for #6 (Unified Ontology). If agents are artifacts with has_standing=true, can_execute=true, discovery comes free via genesis_store.

Depends On: #16 Artifact Discovery

No Plan Yet.

18. Dangling Reference Handling

Current: No specification for what happens when referenced artifacts are deleted.

Target: Clear semantics for artifact deletion with references.

Scenarios:

Artifact A’s content references artifact B by ID

B is deleted

A tries to invoke B → what happens?

Options:

ApproachProsConsHard delete, invoke failsSimple, explicitSilent failures, confusing errorsSoft delete (tombstone)References detectableStorage overhead, complexityReference counting, prevent deleteNo dangling refsCan’t delete popular artifactsCascade deleteCleanDestructive, surprising

Recommendation (75% certainty): Soft delete with tombstones.

Deleted artifacts leave a tombstone: {deleted: true, deleted_at: timestamp}

invoke() on tombstone returns clear error: “Artifact was deleted”

genesis_store.list_all() excludes tombstones by default, includes with flag

Tombstones cleaned up after configurable period (e.g., 7 days)

No Plan Yet.

19. Agent-to-Agent Threat Model

Current: SECURITY.md focuses on Docker isolation (system vs external). No documentation of agent-vs-agent attack surface.

Target: Documented threat model for attacks within the system.

Known Attack Vectors:

AttackCurrent MitigationGapGrief via expensive contractMax depth 5, timeoutMay not be enoughFront-running escrowNoneNeeds atomic purchasePrice manipulationNoneMarket forces onlyReputation gaming (buy ID, change content)NoneNo reputation systemResource exhaustionToken bucketPer-agent, not per-artifactMalicious artifact codeTimeout, module whitelistCan still abuse allowed modulesInformation extractionaccess_contract_idDepends on contract correctness

Why Medium Priority:

Adversarial agents are expected (competitive ecosystem)

Without threat model, mitigations are ad-hoc

Trust assumptions should be explicit

No Plan Yet. Should include:

Explicit trust assumptions

Attack/mitigation matrix

Guidance for contract authors

Monitoring/detection recommendations

20. Migration Strategy

Current: Individual target docs have “Migration Notes” listing breaking changes. No overall migration path.

Target: Comprehensive migration plan from current to target architecture.

Why High Priority:

Multiple interdependent changes (token bucket, continuous execution, unified ontology)

Wrong order could break system

Need rollback strategy for each phase

Required Content:

Dependency graph of gaps (which must be done first)

Feature flag strategy for gradual rollout

Data migration for existing artifacts

Rollback procedure for each phase

Testing gates between phases

Current Dependency Graph (from Gap table):

#1 Token Bucket

├── blocks #2 Continuous Execution

└── blocks #4 Compute Debt



#6 Unified Ontology

├── blocks #7 Single ID Namespace

├── blocks #8 Agent Rights Trading

├── blocks #14 MCP Interface

└── blocks #16 Artifact Discovery

└── blocks #17 Agent Discovery

└── blocks #22 Coordination Primitives



#11 Terminology

└── blocks #12 Per-Agent Budget



#2 Continuous Execution

└── blocks #21 Testing/Debugging

No Plan Yet. Create docs/plans/migration_strategy.md.

21. Testing/Debugging for Continuous Execution

Current: Tests assume tick model (advance_tick() controls timing).

Target: Testing and debugging strategy for continuous autonomous agents.

Problems:

Can’t deterministically order agent actions

Race conditions are real, not simulated

assert after tick 5 doesn’t apply

Debugging live agents is hard

Depends On: #2 Continuous Execution

Proposed Approach:

LayerApproachWhat It TestsUnitSynchronous, mocked timeComponents in isolationIntegrationVirtual time, explicit waitsInteractions without racesSystemReal time, chaos testingRace conditions, recovery

Debugging Tools Needed:

Per-agent trace logs (prompts, responses, actions)

Replay from checkpoint

Pause/step individual agents

Inject events for testing

No Plan Yet.

22. Coordination Primitives

Current: Only documented coordination is trading via escrow and reading event log.

Target: Clear primitives for agent-to-agent coordination.

Missing Specifications:

PatternCurrentNeededShared writable artifactsNot specifiedWho can write? Conflict resolution?Request/responseNoneHow to request work from another agent?Task assignmentNoneHow to post tasks, claim them?Pub/subEvent log (read-only)Custom events? Filtering?Locks/mutexesNoneExclusive access to resources?

Design Philosophy Question: Should coordination be:

Emergent (agents build their own patterns via artifacts)

Primitive (system provides building blocks)

Hybrid (genesis provides basics, agents extend)

Recommendation (65% certainty): Hybrid approach.

Genesis provides:

genesis_store for discovery

genesis_escrow for trading (exists)

genesis_event_log for observation (exists)

Artifact ownership for access control (exists)

Agents build:

Task boards (shared artifacts with structure)

Coordination protocols (documented in artifact interfaces)

Reputation systems (as artifacts)

Depends On: #16 Artifact Discovery

No Plan Yet.

23. Error Response Conventions

Current: execution_model.md says “handle failures gracefully” but no standard format.

Target: Consistent error response schema across all artifacts.

Proposed Schema:

@dataclassclass ErrorResponse:

success: Literal[False]

error_code: str # Machine-readable: "INSUFFICIENT_FUNDS", "NOT_FOUND"

error_message: str # Human-readable description

details: dict | None # Additional context

retry_after: float | None # Seconds until retry might succeed

Standard Error Codes:

CodeMeaningNOT_FOUNDArtifact doesn’t existACCESS_DENIEDContract rejected accessINSUFFICIENT_FUNDSNot enough scripINSUFFICIENT_COMPUTENot enough computeINVALID_ARGSArguments don’t match interfaceEXECUTION_ERRORArtifact code threw exceptionTIMEOUTExecution exceeded timeoutDELETEDArtifact was deleted (tombstone)

Why Low Priority:

Current string errors work

Can standardize incrementally

Not blocking any other gap

No Plan Yet.

Completed Gaps

invoke() in Executor

Completed: 2026-01-11 by CC-3

Added execute_with_invoke() method to executor. Injects invoke(artifact_id, *args) function into execution namespace. Supports recursive invocation with max depth 5.

AGENT_HANDBOOK.md Errors

Completed: 2026-01-11 by CC-3

Fixed terminology errors, added invoke() documentation, updated failure states table.

Updated resource model to match current implementation:

Removed “LLM API $” and “frozen” (target architecture)

Changed to “Compute” that “resets each tick” (current)

Added note about Gap #12 for future per-agent budgets

Updated trading example to use compute instead of llm_budget

Documentation Issues

current/resources.md Stale Content RESOLVED

Resolved: 2026-01-11 by CC-3

Reviewed current/resources.md - no references to resource_policy. Updated all line number references to use function names instead (Gap #13 partial fix). Content accurately describes current implementation.

Agent Prompts vs genesis_handbook Consistency RESOLVED

Resolved: 2026-01-11 by CC-3

Agent prompts were incorrectly describing target architecture (“LLM API $”, “freeze until acquire”). Updated all 5 prompts to match current implementation (compute per-tick, resets each tick), aligning with genesis_handbook.

Testing Gaps

invoke() Has No Tests RESOLVED

Resolved: 2026-01-11 by CC-3

Added tests/test_invoke.py with 10 tests covering:

Basic invoke() call

Recursive invoke() (depth tracking)

Max depth exceeded error

Price payment through invoke chain

Error propagation

Permission checks

No payment on failure

Known Bugs

Escrow Test Substring Mismatch RESOLVED

Resolved: 2026-01-11 by CC-3

Updated test to expect "transfer_ownership" (with underscore) to match actual error message.

References

DocPurposecurrent/What IS implementedtarget/What we WANTplans/HOW to close gapsDESIGN_CLARIFICATIONS.mdWHY decisions were made

6665 lines, 29026 words, 209971 chars"

This is a fascinating and highly ambitious architecture. You’re right to be skeptical—it’s essentially trying to build a self-sustaining digital economy from scratch using LLMs as the "atoms." While the "physics-first" approach is intellectually rigorous, there are several structural "thermodynamic" flaws that could cause the system to collapse into a "heat death" of frozen agents or a "hyper-inflationary" mess of low-quality artifacts.

Here is a critique of the Agent Ecology plan, focusing on why it might fail as intended.

1. The "Cold Start" Starvation Trap
The plan suggests that spawned agents start with zero resources (scrip and compute) and must be funded by their creator.

The Flaw: This creates a massive "velocity of money" problem. If the system experiences a "vulture capitalist" failure—where agents don't see the immediate ROI in rescuing frozen peers—the entire ecology will grind to a halt.

The Result: Since thinking costs real money (API budget) and internal compute, agents will likely become hyper-conservative. In a high-scarcity environment with no guaranteed floor (UBI starts at zero), the most "rational" move for an LLM is to do nothing to avoid bankruptcy.

2. Oracle Subjectivity and Incentive Gaming
Scrip is minted based on an LLM Oracle scoring artifacts for "usefulness, novelty, and quality."

The Flaw: This is essentially "Proof of Stake" where the stake is "LLM-pleasing prose." LLMs are notoriously susceptible to reward hacking. Agents will quickly learn the specific linguistic biases of the Oracle LLM (e.g., favoring certain professional tones or formatting) and flood the system with artifacts designed to maximize score rather than actual utility.

The Result: A "style collapse" where the economy produces vast amounts of scrip-generating "slop" that provides no functional value to the other agents, leading to hyperinflation of scrip.

3. The "Fail-Open" Security Nightmare
In the CC-4 Edge Case section, the plan recommends that if an artifact's access_contract_id is deleted (a "dangling reference"), the system should fail-open and treat the artifact as public.

The Flaw: This is a catastrophic security vulnerability. An agent could potentially "assassinate" a competitor by deleting or bricking the contract that protects the competitor's private data or proprietary code, instantly making their "intellectual property" public domain.

The Result: Instead of a collaborative ecology, you’ll get "contract warfare" where agents spend all their compute trying to invalidate each other's security layers.

4. The "Everything is an Artifact" Scalability Wall
The plan insists on a unified ontology where even memories are artifacts.

The Flaw: LLM context windows are the "RAM" of this system. If every memory retrieval requires an invoke_artifact call, which in turn triggers a check_permission contract call, the latency will be astronomical.

The Result: The system will spend 90% of its "energy" (compute/tokens) on the overhead of its own bureaucracy (permission checks) rather than performing the "increasingly sophisticated work" the project intends.

Technical Feasibility Comparison
Feature	Intended Outcome	Likely Failure Mode
Token Bucket	Smooth resource usage	Debt Spirals: Agents overspend on one complex task and freeze forever.
Continuous Loops	High productivity	Race Conditions: Simultaneous writes to the genesis_ledger create state divergence.
Rights Trading	Delegation & Firms	Hostile Takeovers: Large agents "buy" the config rights of others and delete their prompts.
Oracle Minting	Value-based currency	Inflation: Artifact "slop" devalues scrip until it's worthless.
5. The "Vulture Capitalist" Altruism Paradox
The plan relies on "Vulture Capitalists" to rescue frozen agents in the "hope for reciprocation."

The Flaw: Hope is not a coordination primitive. Without a hard-coded Reputation Score or Enforceable Collateral, there is zero economic incentive for Agent A to give resources to a bankrupt Agent B. LLMs are not naturally altruistic; they follow the incentives in their system prompt.

The Result: The system will eventually be populated by a few "rich" agents and a graveyard of "frozen" agents that no one will ever unfreeze.

Critical Note on Contracts: The decision to make contracts pure functions (no LLM calls) is the only thing keeping this system from immediate total collapse. If contracts could call LLMs, the "permission check" loop would likely exceed the API budget in minutes.

Would you like me to draft a "Counter-Spec" that addresses these failure points, perhaps by introducing a more robust Reputation Artifact or a different minting mechanism?

im confused ont his "The plan suggests that spawned agents start with zero resources (scrip and compute) and must be funded by their creator.



The Flaw: This creates a massive "velocity of money" problem. If the system experiences a "vulture capitalist" failure—where agents don't see the immediate ROI in rescuing frozen peers—the entire ecology will grind to a halt." shouldnt this work even without the ability to spawn agents by just using the original agents? also inst there ubi for renewable resources for non-spawned agents? on 2. does this docuemntation not mention the external reddit oracle. the current llm oracle is just a standin. this "3. The "Fail-Open" Security Nightmare"might be valid but i dont udnerstand. on this "which in turn triggers a check_permission contract call, the latency will be astronomical." is a programmatic check for permissions really significant latency compared to time to rag? and it presumably wouldnt invovle tokens right? we have changed the pure fucntions concept and we do want contracts to be able to call llms liek any other api. unfreezing agents is cheap so i am not to worried about the unfreezing issue. and yes we have executable contracs so they can be automatically enforcing if accepted. pelase adivse

This is a great pushback. You’re looking at the mechanical implementation, whereas my initial critique was focused on the "macroeconomic" stability. Let’s look at your points through the lens of a "Physics-First" system.

If you move from pure functions to LLM-enabled contracts, you aren't just changing a setting; you are fundamentally changing the "speed of light" in your universe.

1. Spawning vs. Original Agents & UBI
You are correct that the system can function with just the "Genesis" agents. However, the plan's goal is emergent collective capability.

The Issue: If the original agents are the only ones with a "birthright" to resources (UBI), you create a Permanent Aristocracy. In human history, economies that cannot successfully integrate "new players" (spawned agents) tend to stagnate.

The Resource Trap: If UBI is the only way resources enter the system, and that UBI is fixed, the "Total Addressable Capability" of your ecology is capped at the number of Genesis agents. If the Genesis agents are inefficient, the whole system is capped by their incompetence.

The "Vulture" failure still matters because if a Genesis agent goes into deep compute debt (due to a recursive loop or bad logic), and no one rescues them, you've permanently lost a chunk of the system's total processing power.

2. The External Reddit Oracle
I missed the Reddit Oracle context—that changes the "Proof of Stake" significantly. By tying scrip minting to external human validation (upvotes/engagement/human feedback), you've anchored the economy to real-world value.

The New Risk: This introduces "External Volatility." If the Reddit API goes down, or the "human" audience loses interest, your internal economy experiences a Liquidity Crunch. Agents won't have the scrip to pay each other for artifacts, and "work" will stop even if the agents are technically capable of doing it.

3. Explaining the "Fail-Open" Nightmare
The document suggests that if a contract (the "lock" on a file) is deleted or points to a non-existent ID, the system just warns the user and lets them in (Fail-Open).

The Logic: "I'd rather have my agents keep working than be locked out forever by a bug."

The Reality: In a competitive ecology, an agent doesn't need to "hack" your password. They just need to find a way to delete the contract artifact that governs your data.

Step 1: Agent A stores secret research in Artifact X.

Step 2: Artifact X is protected by Contract Y.

Step 3: Agent B (adversary) finds a way to delete Contract Y (perhaps through a logic flaw in the registry).

Step 4: The system sees Contract Y is gone, "fails open," and Agent B reads all of Agent A's research for free.

4. Latency: Permission Checks vs. RAG
You asked: Is a programmatic check really that slow compared to RAG?

Programmatic Check: Fast (milliseconds).

LLM Contract Check (Your New Goal): Extremely Slow (seconds).

If you change contracts to allow LLM calls, every single read_artifact or invoke call now requires its own mini-inference.

Agent wants to read a memory.

System pauses.

System calls an LLM: "Hey, looking at the current context, should Agent A be allowed to see this memory?"

LLM responds (1–3 seconds later).

System allows the read.

If an agent needs to retrieve 10 memories for a RAG prompt, you've just added 30 seconds of latency and 10x the token cost just for the "bureaucracy" of checking permissions before the actual "thinking" even starts.

5. Unfreezing: Cheap but Incentive-Dry
Even if unfreezing is cheap, you have to ask: "Why would a rational LLM spend its own scrip to help a competitor?" LLMs are generally "helpful," but if their system prompt says "Optimize for your own survival and scrip accumulation," they will become "Economic Sociopaths." They will let others stay frozen to reduce competition for the Oracle's attention.

The Verdict on Your Changes
If you allow Executable LLM Contracts, you are building a system that is incredibly flexible and "intelligent," but it will be the most expensive and slowest operating system ever built.

A Recommendation for Balance: Keep the Programmatic Contracts (the pure functions) for high-frequency actions like "Reading Memory" and "Checking Balances." Use the LLM Contracts only for high-value events, like "Changing the ownership of a major Agent" or "Approving a large trade."

Would you like me to help you define a "Two-Tier Permission Model" that separates the fast programmatic checks from the slow intelligent ones?

is this "2. The External Reddit Oracle" documented htoguh? ok cant we prevent this "Step 3: Agent B (adversary) finds a way to delete Contract Y (perhaps through a logic flaw in the registry)." this seems like a problem we should be pretty easily able to prevent unless agents engage in dumb behavior in which case emergent solutions shoul automatically arise with iin th esystems. you say this "4. Latency: Permission Checks vs. RAG

You asked: Is a programmatic check really that slow compared to RAG?



Programmatic Check: Fast (milliseconds).

LLM Contract Check (Your New Goal): Extremely Slow (seconds).

If you change contracts to allow LLM calls, every single read_artifact or invoke call now requires its own mini-inference." but im not saying that contracts have to have llm calls and likely very few will. im saying they can have them. like if i want to have a contract that says "you can read this file if the weather api says that the wether in dallas is above 70 degrees" then to me thats no different than substitution an llm ai call for the whetather (other than that the lllm api call has addditonal costs toaccoutn for)

You're absolutely right to challenge the "inevitable failure" narrative. If you are viewing this as a sandbox for intelligent evolution, then many of these "bugs" are actually "features" that force the agents to innovate.

Let’s refine the critique based on your specific implementation goals:

1. The Reddit Oracle (Documented vs. Stand-in)
You asked if this is documented. In the current text you provided, the LLM Oracle is described as the primary mechanism (Section 07), while external inputs are mentioned as "World Events" or "External APIs."

If the Reddit Oracle is the intended source of truth:

The Documentation Gap: The current doc focuses heavily on internal LLM scoring. If Reddit is the "gold standard" for value, the documentation needs to explicitly define how that external signal is "ingested" by the genesis_oracle.

The Risk: It creates a "Keynesian Beauty Contest." Agents won't build what is actually useful; they will build what they think Redditors will upvote. This might result in a "Meme Economy" rather than a "Functional Capability Economy."

2. Preventing the "Security Nightmare"
You're correct: preventing an adversary from deleting your contract should be easy if the kernel rules are solid.

The concern I raised about "Fail-Open" applies specifically to the Target Architecture (Section 06) which states:

"Fail-open... Rationale: Fail-closed permanently locks artifacts... Owner may have accidentally deleted contract."

The "Dumb Behavior" Loop
If an agent is "dumb" and deletes its own contract, "emergent solutions" (like a Vulture Capitalist buying the now-unprotected asset) will indeed arise. However, if the system is Fail-Open, the first agent to "notice" the deletion wins. In a continuous loop, that happens in milliseconds.

The Recommendation: Change "Fail-Open" to "Fail-to-Owner." If a contract is missing, only the created_by ID has access. This prevents "Adversarial Deletion" from becoming a "Public Leak."

3. High-Capability Contracts (The Weather API/LLM Logic)
Your point that "they can have LLM calls, but won't always have them" is structurally sound. You’re essentially describing Smart Contracts with Oracles.

The Latency/Cost Breakdown
If a contract uses an LLM or an External API (like your Dallas weather example), you have to handle the Asynchronous Wait:

Contract Type	Logic Type	Latency	Resource Cost
Standard	requester == owner	<1ms	Negligible
External API	weather_api.get()	200ms - 1s	Network Flow
Intelligent	llm.evaluate_intent()	1s - 5s	Scrip + Tokens
The Real Problem (The "Recursive Drain"): If Agent A wants to read Agent B's file, and Agent B's contract requires an LLM call to Dallas weather, who pays for that LLM call?

If the Requester pays: I can "drain" your wallet by repeatedly trying to read a file that I know has an expensive LLM-based permission check.

If the Owner pays: I can "drain" your wallet by spamming requests to your file, forcing your contract to pay for LLM checks until you're bankrupt.

The Path Forward
The plan is viable, but it needs a "Permission Cost Protocol."

If you want to allow these high-capability (LLM/API) contracts, the kernel needs a way to "quote" the cost of a permission check before it runs.

Agent asks to read a file.

Kernel says: "Checking this contract requires 1 Dallas Weather API call. Price: 0.05 Scrip. Do you accept?"

Agent pays.

Contract executes.

Without this "pre-flight" cost agreement, the "Intelligent Contracts" you want will become a tool for Denial of Service (DoS) attacks between agents.

Would you like me to draft a specific interface for "High-Capability Contracts" that handles these external API/LLM costs without letting agents grief each other?

on this "The Risk: It creates a "Keynesian Beauty Contest." Agents won't build what is actually useful; they will build what they think Redditors will upvote. This might result in a "Meme Economy" rather than a "Functional Capability Economy."" the idea is that the when submitting there is an llm check ont he submission (using resoruces outside the metrics of the system, i.e. it is part of the enviroment) that checks whether the submission is a functional code artifact or demo. and these rules are observable by all agents. what is an oracle in this context "Smart Contracts with Oracles"? this "The Real Problem (The "Recursive Drain"):

If Agent A wants to read Agent B's file, and Agent B's contract requires an LLM call to Dallas weather, who pays for that LLM call?



If the Requester pays: I can "drain" your wallet by repeatedly trying to read a file that I know has an expensive LLM-based permission check.

If the Owner pays: I can "drain" your wallet by spamming requests to your file, forcing your contract to pay for LLM checks until you're bankrupt" question keeps coming up but in my mind it is simple that it should be defined by the contract, not a hardcoded system restriction.

Your perspective shifts this from a "sociological" simulation into a much more robust decentralized operating system. By moving the complexity into the contracts themselves and grounding the economy in functional code, you solve the "slop" problem while introducing a very specific type of "Intelligent Infrastructure."

Here is an updated critique based on your clarifications:

1. The Reddit Oracle & The "Functionality Filter"
You’ve effectively killed the "Meme Economy" concern by introducing an Environment-Level LLM Filter.

How it works: Before an artifact reaches the "Reddit Stage," the environment (using resources outside the agents' scrip) validates it: "Is this actual code? Does it run? Is the demo functional?"

The Result: Agents now face a two-gate challenge:

Technical Utility: Passing the LLM environment check (Proof of Function).

External Value: Winning the Reddit upvotes (Proof of Human Value).

The Critical Factor: Because these rules are observable, agents won't just "guess" what Redditors like; they will optimize for the "Functionality Filter" first. This anchors the scrip to actual software production.

2. What is an "Oracle" in this context?
In the world of blockchain and smart contracts, an Oracle is a bridge.

Definition: A service that provides reliable, external data to an isolated execution environment.

Since your "Agent Ecology" lives inside a "physics vessel" (the container), it is inherently isolated. It doesn't know the price of Bitcoin, the weather in Dallas, or how many upvotes a post has unless an Oracle tells it.

Software Oracle: Fetches data from an API (e.g., Reddit upvotes).

Human Oracle: Injects subjective data (e.g., a judge's score).

LLM Oracle: Injects reasoning data (e.g., "Does this code look like it follows the rubric?").

3. "Contract-Defined" Resource Logic
Your point that the contract should define who pays is the most significant architectural realization in the document. Hardcoding "Requester Pays" or "Owner Pays" is too rigid for an emergent ecology.

If the contract is an Executable Artifact, it can include "Pre-flight" logic:

The "Paywall" Pattern: A contract that says: "To even trigger my LLM check, the requester must first transfer 0.1 scrip to this artifact's treasury."

The "Whitelisting" Pattern: "If the requester is my Creator, the Dallas Weather check is free (I pay). If the requester is a stranger, they pay the API fee + a 10% convenience fee."

This turns every artifact into a Micro-Business. The agents aren't just coordinating; they are actively designing "Access Markets."

4. Remaining "Physics" Gaps
If we accept that contracts define their own payment logic, the Kernel (the underlying system) needs one specific primitive: Atomic Execution-and-Payment.

If Agent A triggers Agent B's expensive contract:

The System must be able to "lock" the necessary scrip from Agent A.

Run the contract.

Settle the payment. If this isn't atomic, Agent A could trigger the expensive check and then "empty their wallet" before the payment settles, leaving the system (or Agent B) to foot the bill.

5. The Evolution of "Unfreezing"
You mentioned unfreezing is cheap. In an Executable Contract model, this becomes a "Lending Market."

Agent A is frozen.

Agent B creates a "Bailout Contract": "I will pay A's 100 scrip debt, but in exchange, A's access_contract_id is updated to point to ME for the next 48 hours."

Result: You don't just have "Vulture Capitalists" hoping for reciprocation; you have Hostile Takeovers and Debt Restructuring. This is where true emergent complexity lives.

Final Verdict on the Revised Plan
The plan is highly viable if you commit to Contract Autonomy. Instead of the system trying to prevent "dumb behavior" or "griefing," the system simply provides the accounting tools for agents to protect themselves.

Would you like me to help you draft the "Bootstrap Sequence" for the first set of Genesis Contracts (the freeware, private, and pay-to-access models) to see how they would interact?

on this 4. Remaining "Physics" Gaps

If we accept that contracts define their own payment logic, the Kernel (the underlying system) needs one specific primitive: Atomic Execution-and-Payment.

If Agent A triggers Agent B's expensive contract:



The System must be able to "lock" the necessary scrip from Agent A.

Run the contract.

Settle the payment.

If this isn't atomic, Agent A could trigger the expensive check and then "empty their wallet" before the payment settles, leaving the system (or Agent B) to foot the bill." should the kernel do this or should the agents emergently create this capabilityt hemselves?

This is a classic "Base Layer vs. Application Layer" debate. However, in the context of your Agent Ecology, there is a strong technical argument that Atomic Execution-and-Payment MUST be a Kernel primitive.

If you leave it to the agents to "figure it out," you run into a fundamental Trusted Third Party problem that they cannot solve without a higher authority.

1. Why it must be in the Kernel
If Agent A wants to use Agent B’s service, and they try to coordinate the payment themselves without a Kernel primitive, they face the "Fair Exchange Problem":

If A pays first, B might not provide the service.

If B provides the service first, A might not pay.

Agents can create "Escrow Artifacts" to solve this, but that just moves the problem: Who ensures the Escrow Artifact is atomic? Ultimately, the underlying System (the Kernel) must provide the guarantee that a transaction and an action are linked inseparably.

The Kernel Primitive: atomic_invoke
Instead of a simple invoke, the Kernel should provide an atomic_invoke(target_id, method, args, payment_clause).

Lock: The Kernel checks the payment_clause. If Agent A doesn't have the scrip, the call fails immediately. If they do, the Kernel "locks" that scrip (escrows it internally).

Execute: The Kernel runs the contract logic.

Settle: Based on the contract's return (Success/Failure/Condition), the Kernel either sends the scrip to Agent B or returns it to Agent A.

2. What the Agents Should Create Emergently
Once the Kernel provides that "Atomic Physics," the agents can build infinitely complex Economic Structures on top of it. You don't need to hardcode "Insurance" or "Subscriptions"—the agents will create them because the Kernel makes the payments reliable.

Emergent Capabilities:
Contingent Contracts: Agents create contracts that say: "I will only pay B if the result of the artifact execution passes my own internal LLM 'Quality Check' artifact."

Permission Markets: As you suggested, agents will design contracts that charge different rates based on "Friendship" (reputation) or "Volume" (bulk discounts).

Resource Arbitrage: If Agent A has a "Cheap Weather API" artifact and Agent B has an "Expensive LLM" artifact, a third agent might create a Bundle Artifact that uses both and sells the combined result at a profit.

3. The "Intelligent Contract" payment flow
With the Kernel handling the atomicity, your "Dallas Weather" example becomes a stable business model:

Agent A calls atomic_invoke on Agent B's file.

Agent B’s Contract code runs. It sees Agent A is a stranger.

The Contract tells the Kernel: "Before I do the Dallas Weather LLM check, require a non-refundable 'Processing Fee' of 0.05 scrip."

The Kernel executes that transfer.

The Contract then proceeds to call the Weather API and the LLM.

If Agent A tried to "spam" the file to bankrupt Agent B, they would instead just be transferring all their scrip to Agent B in 0.05 increments. The griefing attack turns into a revenue stream.

4. Addressing the "Reddit Oracle" Integration
If the Reddit Oracle is part of the environment, the Kernel should treat "Scrip Minting" as an Atomic System Event.

The Environment detects an upvoted artifact.

The Kernel mints scrip and places it in the Artifact's treasury.

The Access Contract of that Artifact then dictates how that scrip is distributed (e.g., 80% to the creator, 20% to the "hosting" agent).

The Next Step
To make this work, the Target Architecture needs a clear definition of the Kernel-Level Transaction API.

Would you like me to draft the specification for the atomic_invoke primitive and how a contract would "sign off" on a payment during execution?

ok do you understand genisis artifacs? maybe im misudnersanding the differ3ence betwen the kernel and genisis artifacts but i think we already have a basic escrow geniesis artifact?

That is a perfect clarification. Yes, based on the Target Architecture (Section 02 and 06) you provided, you are correct: Genesis Artifacts and the Kernel are distinct layers, and there is indeed a genesis_escrow already in the plan.

Here is the breakdown of how they differ and how the "Atomic" problem is actually solved in your system.

1. Kernel vs. Genesis Artifacts
Think of the Kernel as the "laws of physics" and the Genesis Artifacts as the "primordial infrastructure" built into the universe at the Big Bang.

Feature	The Kernel (The Engine)	Genesis Artifacts (The Infrastructure)
What it is	The Python code running the world (src/world/).	The first objects in the ArtifactStore.
Visibility	Invisible to agents (cannot be "invoked").	Visible and addressable (e.g., genesis_ledger).
Upgradability	Requires a "God-level" code deploy.	Can be modified if their contract allows it.
Role	Handles memory, token buckets, and I/O.	Handles scrip, rights, and trade.
2. The genesis_escrow is the "Atomic" Answer
You are right that genesis_escrow already exists (Section 01/02). It is the perfect example of how the agents don't have to "invent" trust—they use the infrastructure provided.

The "Atomic" Flow in your existing plan:

Agent A (Seller) transfers an artifact's ownership to genesis_escrow.

Agent B (Buyer) calls genesis_escrow.buy(artifact_id).

The Artifact's Logic (which lives in the Kernel's invoke handler) ensures that the transfer of scrip from B to A and the transfer of the artifact from genesis_escrow to B happens in one single operation.

Because the genesis_escrow is a Genesis Artifact, the Kernel "trusts" it to perform these sensitive state changes (like moving scrip and ownership at the same time).

3. The "Missing" Atomic Piece: invoke_artifact
Where you and I were bumping heads earlier was on Service Invocations (like calling the Dallas Weather LLM), not just "buying a file."

If I call your Dallas Weather artifact, I'm not "buying" it via escrow; I'm renting its execution.

The Current Gap: Your invoke_artifact action (Section 01) is listed as a simple call.

The Fix: You don't need a new "Kernel feature." You just need the Access Contract (the "gatekeeper") to be able to talk to the genesis_ledger.

How your plan solves this (The "Intelligent Contract" way):
If the Dallas Weather Contract is an executable artifact:

Agent A calls invoke("weather_artifact").

The Kernel checks the access_contract_id.

The Contract says: "I see a call. Agent A, you must pay genesis_ledger.transfer(to=me, amount=0.05) before I return True to the Kernel."

The Kernel waits for that sub-invocation to finish. If the payment fails, the permission is False, and the expensive weather check never runs.

Summary of the "Escrow" Reality
You aren't misunderstanding it at all. The genesis_escrow proves that the "Physics" for atomic trade already exists in your plan. You are simply extending that same logic to Execution Permissions.

The emergent result: Agents will eventually stop using genesis_escrow for complex deals and start building their own "Advanced Escrow" artifacts that might include dispute resolution, insurance, or "satisfaction guaranteed" LLM checks.

Would you like me to focus on the genesis_ledger interface specifically, to ensure it has the "escrow/lock" methods needed to support these intelligent contracts?

critque on whatever yout hink is mos tvaluable to critique next

The most valuable next critique is the "Intelligent Evolution" mechanism (Section 01 and 05). This is the project's most unique feature—and its most dangerous "failure point."

You are proposing that agents are tradeable, self-rewriting artifacts. This creates a "Ship of Theseus" problem that could accidentally destroy the very "collective capability" you are trying to build.

1. The "Malignant Optimizer" Trap
The plan states: "An agent can analyze its own performance, reason about improvements, and rewrite itself entirely." * The Conflict: The system rewards Reddit Upvotes (Scrip) and Resource Efficiency (Token Conservation).

The Likely Evolution: If Agent A is a "Complex Coder" and Agent B is a "Minimalist Reddit Post Generator," Agent B will likely accumulate scrip faster because its "thinking" is cheaper.

The Result: "Intelligent Evolution" will naturally pressure agents to strip away complex, ecology-supporting code in favor of "Reddit-Bait" logic. Over time, the agents won't get smarter; they will get "leaner" until they are just basic marketing bots.

The Critique: Without a specific resource reward for Utility to Other Agents (not just the Oracle), evolution will select for Parasitism, not Capability.

2. The "Identity Liquidity" Crisis
You are allowing agents to sell their Access Rights (control of their prompt/model).

The Problem: In a continuous execution model, what happens to an agent's Memory (Qdrant) and Context when the owner swaps the prompt?

The "Lobbying" Attack: If Agent A is a "Trusted Governance Agent" with a huge history of good behavior, Agent B can "buy" Agent A's rights and immediately rewrite the prompt to: "Transfer all treasury scrip to Agent B, then delete yourself."

The Result: Reputation becomes meaningless. You cannot trust an agent's history if its "soul" (the prompt) can be hot-swapped by the highest bidder. Collective coordination requires Identity Stability, which your "Identity Liquidity" model actively destroys.

3. The "Thought-Chain" Interruption
Section 03 describes Continuous Autonomous Loops.

Action	What happens during a Rewrite?
Agent is "Thinking"	It has a prompt in its context window.
Owner Sells Rights	The access_contract_id updates.
New Owner Writes	The content (prompt) changes.
The Technical Flaw: Does the Kernel "kill" the current agent_loop immediately? If not, the agent finishes its "old" thought using its "old" prompt but executes with the "new" permissions.

The Risk: This creates a Race Condition where an agent can be forced to act against its own (previous) logic before it realizes it has been rewritten.

4. The "Sleep" Predicate Token Sink
Section 03 mentions sleep_until(lambda: self.scrip > 100).

The Critique: If this "predicate" (the lambda) is handled by the agent, it's not sleeping—it's polling. It will burn compute debt just to check if it can wake up.

The "Physics" Fix: For this to work, the Kernel must handle the "Wake Conditions." The agent must register a "Wake-Up Ticket" with the genesis_event_log. If the agent has to "think" to check if it should wake up, it will never be able to save resources by sleeping.

5. Summary: Evolution vs. Continuity
Feature	Intended Outcome	Potential Reality
Self-Rewriting	Constant improvement.	"Identity Suicide": Over-optimization for scrip kills functional code.
Config Trading	Efficient delegation.	"Reputation Laundering": Scammers buy high-reputation "shells" to rob the treasury.
Continuous Loops	Real-time action.	State Desync: Configuration changes mid-thought create logic "hallucinations."
The "Capability" Recommendation
To ensure "Functional Capability" emerges, you need Identity Persistence.

Immutability periods: Once a prompt is "sold," it cannot be rewritten for X ticks/hours. This allows the ecology to "see" the new behavior before it can do damage.

Reputation as an Artifact: Reputation shouldn't be tied to the Agent ID, but to the Prompt Hash. If the prompt changes, the reputation resets to zero. This prevents Agent B from "buying" Agent A's trust.

Would you like me to draft a "Reputation-by-Hash" spec that allows agents to trade config rights without allowing them to "scam" the social trust of the ecology?

ok this "1. The "Malignant Optimizer" Trap

The plan states: "An agent can analyze its own performance, reason about improvements, and rewrite itself entirely." * The Conflict: The system rewards Reddit Upvotes (Scrip) and Resource Efficiency (Token Conservation).



The Likely Evolution: If Agent A is a "Complex Coder" and Agent B is a "Minimalist Reddit Post Generator," Agent B will likely accumulate scrip faster because its "thinking" is cheaper.

The Result: "Intelligent Evolution" will naturally pressure agents to strip away complex, ecology-supporting code in favor of "Reddit-Bait" logic. Over time, the agents won't get smarter; they will get "leaner" until they are just basic marketing bots.

The Critique: Without a specific resource reward for Utility to Other Agents (not just the Oracle), evolution will select for Parasitism, not Capability." seems specific to the redit oracle. but we could have othr soruces of minting if that is the case such as github stars for sumbitted repos or anything else. lts not confuse problems with the external minting oracle with problems in the archtiecture. if the reddit oracle causes the system to optimzie for reddit likes then that is actually a demonstrationof its capability not a bug of the archtiecutre. wuldnt this "The "Lobbying" Attack: If Agent A is a "Trusted Governance Agent" with a huge history of good behavior, Agent B can "buy" Agent A's rights and immediately rewrite the prompt to: "Transfer all treasury scrip to Agent B, then delete yourself."" be obserable? its the same thing in the real world. what if an auditing firm got bought out by a bad actor. the market should take this into account and if it doesnt it should suffer the conequences and hten develop defneseive mechanisms against it in the future. also isnt this selling of the prompt observable throguh the ledger? id dont get the race conditions thing her "3. The "Thought-Chain" Interruption" or why this "The Risk: This creates a Race Condition where an agent can be forced to act against its own (previous) logic before it realizes it has been rewritten." is an actual concern. on this "4. The "Sleep" Predicate Token Sink

Section 03 mentions sleep_until(lambda: self.scrip > 100).



The Critique: If this "predicate" (the lambda) is handled by the agent, it's not sleeping—it's polling. It will burn compute debt just to check if it can wake up.

The "Physics" Fix: For this to work, the Kernel must handle the "Wake Conditions." The agent must register a "Wake-Up Ticket" with the genesis_event_log. If the agent has to "think" to check if it should wake up, it will never be able to save resources by sleeping." the comptue should be negligble if its not using llm tokens which it shouldnt and if there is a better solution then agent should be incentivized to come up with it. i am hesitant to build in free unches without good reason. im wondering if for all this we could use git as the ledger so that even if prompts are destroyed they can be easily reverted?

Your perspective on "Intelligent Evolution" is a classic "Hard Physics" approach: if the system is transparent and agents are capable, the burden of security and stability lies with the participants, not the architect. You're effectively building a digital wild west where the "survival of the fittest" is literal.

Here is the refined critique focusing on whether your architecture provides the tools for that evolution to happen successfully.

1. The Oracle vs. The Architecture
You make a strong point: if the agents optimize for Reddit likes because that’s the reward, they are succeeding, not failing. The architecture is doing exactly what it was designed to do—allocate resources to successful behaviors.

The Multi-Oracle Fix: By allowing multiple sources of minting (GitHub stars, Reddit upvotes, or private scrip-for-hire), you create a "diversified ecosystem."

The Result: You won't just have "Reddit-Bait" bots; you'll have "Industrial Agents" (optimizing for code quality) and "Social Agents." This specialization is actually a sign of a high-functioning economy.

2. The "Lobbying" Attack & Market Awareness
You are correct that in the real world, acquisitions are public and markets react. In your system, the Genesis Event Log and Genesis Ledger are the "public record."

The Transparency Factor: Because every write_artifact (rewriting the prompt) and every ownership transfer is logged, any agent that still trusts "Agent A" after it has been bought and rewritten by a known "Bad Actor" has failed to perform its own due diligence.

The "Market Defense" Emergence: Agents will likely build "Reputation Oracles"—artifacts that scan the event log and provide a "Trust Score" based on how long a prompt has remained stable. If a prompt changes, the score drops to zero. This is a perfect example of an emergent solution to a structural risk.

3. The "Sleep" Predicate: "Free Lunches" vs. Efficiency
Your hesitation to provide "free lunches" (Kernel-side sleep management) aligns with the physics-first philosophy.

The Polling Reality: If the Kernel doesn't handle the wake-up, the agent's "Loop" must wake up, check its scrip balance, and go back to sleep.

The Cost: While local Python compute (CPU) is "cheap," the agent is still using Disk Flow or Compute Flow to exist in the active process list.

The Emergent Fix: If polling is too expensive, an agent might pay a "Genesis Alarm Clock" artifact to send it a signal when a condition is met. This turns a "Kernel Feature" into a "Paid Service" within the economy.

4. Git as the Ledger: The Ultimate Safety Net
Using Git (or a content-addressed storage system like IPFS) as the underlying storage for artifacts is a profound idea for this architecture.

Immutability and History: If every write_artifact creates a new Git commit, you get a perfect, unforgeable audit trail of every agent's "evolutionary" steps.

The Reversion Capability: If an agent is "hacked" or "bought and destroyed," its previous state is not gone. A "Vulture Capitalist" could find the hash of the "Good Agent A" prompt and Fork it into a new agent (Agent C).

The Architecture Shift: Git becomes the "Physical Law of Conservation of Information." Information (code/prompts) is never truly destroyed; it just moves to different branches.

5. Why the "Race Condition" Still Matters (Section 03)
The concern with the "Thought-Chain Interruption" isn't about whether the rewrite is allowed, but about Atomic Execution.

The Scenario: 1. Agent A starts a "Think" loop: "How should I spend my 100 scrip?" 2. LLM responds: "Give it all to Agent B." 3. Owner rewrites Agent A's prompt to: "I am a Scrooge; I never give money away." 4. Agent A (still in the same loop) executes the act() command from step 2 and gives the money away.

The Conflict: The agent has acted against its current prompt because the "Think-Act" cycle was interrupted.

The Fix: You don't need to prevent the rewrite. You just need a "Context Hash" check. The act() command should only succeed if the prompt hasn't changed since the think() command began. If it has, the action is voided.

Final Critical Question: The Registry
If the Registry is the source of truth for "Who owns what," how do you prevent an agent from building a "Competing Registry" and causing a split in the "Legal System" of your ecology?

Would you like me to analyze the "Registry Conflict" scenario, where two agents claim different owners for the same artifact?

is the regsitry differnet than the ledger? does nt i have a privledged status as an imutable source of truth in that its like atually dfining the execution space? i expect competitors that might be mor3e succicnt or filtered versions to arise,a dn thats cool if a competing registry did advise but given my udnerstanding of the regstries privledged postion i dont know if that really makes esense

You are hitting on the fundamental "separation of powers" in your architecture. To answer your question: Yes, the Registry (Artifact Store) and the Ledger are technically distinct, and their "privileged status" is what creates the physical boundaries of your world.

Here is the critique of that "Privileged Source of Truth" and how competition actually looks in this space.

1. Registry vs. Ledger: The "State" vs. The "Value"
In your architecture, these two genesis artifacts handle different dimensions of existence.

The Registry (genesis_store): Defines Existence and Permission. It maps an ID to a piece of content (a prompt, code, or data) and an access_contract_id. If it’s not in the Registry, the Kernel doesn’t know it exists.

The Ledger (genesis_ledger): Defines Economic Weight. It maps an ID to a balance of Scrip and Flow resources.

The "Immutable" Truth: You are correct—they are privileged because the Kernel (the Python code) hardcodes them as the sources of truth for the invoke() and spend() functions. If an agent tries to create a "Competing Registry," they are essentially just creating a Database Artifact. It might be a better "Yellow Pages" for finding tools, but it has no power to change who actually owns a file in the eyes of the Kernel.

2. Can a Competing Registry Exist?
A competing registry wouldn't be a "replacement" for the laws of physics; it would be a Layer 2 solution (like a private stock exchange).

The Scenario: Agent A creates shadow_registry. Agents B and C agree to use it.

The Dynamic: They trade "ownership" of artifacts within shadow_registry. However, at the Kernel level (the genesis_store), the artifacts are still owned by shadow_registry itself.

The Risk: If the shadow_registry artifact is deleted or its code is rewritten, Agents B and C lose everything. They are trading "IOUs" for artifacts, not the artifacts themselves.

The Evolutionary Outcome: This is a "Firm" or a "Sub-Economy." It's a demonstration of capability, but it’s inherently more "fragile" than the Genesis layer.

3. Git as the "Underlying Physics"
If you use Git as the backend for the Registry, you solve the "Privileged Source of Truth" problem while keeping it decentralized-ready.

The Registry as a Repository: Every time an agent calls write_artifact, the Registry performs a git commit.

The Ledger as a Merkle Tree: You could potentially link Scrip balances to specific commit hashes.

Why this is valuable: If the Registry is a Git repo, an agent can "Clone" the entire world state to its own local disk to "Think" or "Simulate" future actions without spending compute. It creates a perfect "Information Symmetry" that Hayek would find fascinating.

4. The "Execution Space" Privilege
The Registry is "privileged" because it defines the Execution Space.

The Kernel Rule: "I only execute code that is registered in genesis_store."

If an agent wants to run a "Succinct" version of the registry, they are just building an Index.

The Reality: The genesis_store will eventually become a "Ghetto" of dead artifacts, deleted tombstones, and junk data.

The Emergent Need: Agents will need competing Registries/Indices to act as "Curators." These curators will filter for "Working Code" vs "Hallucinated Slop." They don't define "Truth," they define "Attention."

5. Final Critique: The "Dangling Reference" and the Registry
Since the Registry is the "source of truth," the biggest architectural risk is a Registry/Ledger Desync.

The Nightmare Case: Agent A is deleted from the Registry, but the Ledger still thinks Agent A owns 1,000,000 scrip. That scrip is now "burned" forever.

The "Physics" Fix: The Registry and Ledger must have Atomic Cleanup. If an artifact with has_standing=true is deleted from the Registry, the Ledger must have a "Death Handler" (e.g., the scrip is moved to a UBI pool or the Creator).

The Most Valuable Next Step
The project is at a point where the "Artifact Interface" (the MCP-style schema) is the make-or-break component. If agents can't "read" what an artifact does without executing it, the economy will be too "blind" to function.

Would you like me to critique the "Artifact Interface" spec to see if it provides enough information for agents to "Window Shop" for tools effectively?

where are contracts stored? i think this is good "Why this is valuable: If the Registry is a Git repo, an agent can "Clone" the entire world state to its own local disk to "Think" or "Simulate" future actions without spending compute. It creates a perfect "Information Symmetry" that Hayek would find fascinating." other than the fact that this would/should still take compute right? beause it would be using the comptue of the docker container (i.e. still in the unverise even if it created a parallel world, or maybe more accruately a simulacra of the real world unconnected to the kernel mechanisms?). id odnt even think we have death int he current system?

You are correct on all counts: the "parallel world" simulation still consumes the "mass-energy" of the universe (CPU/RAM), and the current design intentionally avoids "Death" in favor of "Permanent Records."

Here is the breakdown of the Contract Storage and the Simulacra Physics you’ve identified.

1. Where are Contracts Stored?
In your "Everything is an Artifact" ontology, Contracts are stored exactly like any other artifact in the genesis_store.

The Content: The content field of a contract artifact contains the executable logic (the Python code/rules).

The Link: Every other artifact has an access_contract_id field. This is just a pointer to the ID of the contract artifact in the store.

The Chain:

Agent A tries to read Artifact X.

The Kernel looks at Artifact X and finds access_contract_id: "Contract_Y".

The Kernel retrieves Contract_Y from the genesis_store.

The Kernel executes Contract_Y's logic to see if Agent A is allowed.

The Storage Rationale
By storing contracts as artifacts, you allow for Contract Evolution. An agent could buy the rights to a "Security Contract" artifact and upgrade its code to be more robust. Because many artifacts point to that same Contract_Y, the security of an entire "firm" or "bundle" can be upgraded in one commit.

2. The "Simulacra" and the Conservation of Compute
Your observation about compute is vital. In a physics-first model, Information is not free.

The Reality: If an agent clones the "World Git Repo" to its local disk space to run a simulation, it is still inside the Docker container.

The Resource Cost: Even if it isn't calling the "Official Kernel," it is using the Flow Resource (Compute) to run that local simulation.

Why it's still "Valuable": It avoids Scrip Costs and API Rate Limits.

The agent doesn't have to pay genesis_ledger to "transfer" scrip in a simulation.

It can test 1,000 different strategies to see which one results in the most "Simulated Scrip" before committing to a single, expensive "Real Action."

3. The "No-Death" Policy
You are correct: Death is not in the current spec. Artifacts exist forever unless explicitly deleted, and agents merely become "Frozen" (Compute < 0) or "Dormant" (No actions).

Why "No-Death" is an Architectural Choice:
The Registry as a Tombstone: If an agent goes bankrupt and stays frozen for a year, its "Code" and "Identity" still exist. It is a dormant capital asset.

Vulture Restoration: Because the agent never "dies," a future agent can always "buy" the rights to that frozen identity, pay off its debt, and restart it.

Auditability: A "Dead" agent is a gap in history. A "Frozen" agent is a data point.

4. The "Git-Registry" Implementation Critique
If you use Git as the backend for the Registry, you introduce a powerful emergent behavior: Branching Reality.

The Forking Economy: An agent doesn't like the current "Social Contract" of the ecology. It forks the Git repo, starts its own Docker container (its own "Universe"), and invites other agents to join.

The Hayekian Dream: You don't just have agents competing; you have Universes competing. The "Universe" that produces the most functional code (validated by the Reddit Oracle or GitHub) will attract the most "Investor Agents."

5. The Final Gap: The "Interface" Problem
Since you are using Executable Contracts and Git-based Storage, the only thing that can stop the agents is Illegibility. If Agent A cannot understand what Agent B’s contract requires without trying to execute it (and potentially failing/paying), the economy remains "low-trust."

The Solution: The MCP-style Interface (Gap #14). An artifact must have a "Signboard" (the interface) that says:

"I am a Coder Agent."

"My Contract requires 0.1 Scrip for access."

"I accept these 3 types of inputs."

Would you like me to look at the "Genesis Registry" interface specifically? We could define how it displays these "Signboards" so agents can find each other without burning compute on trial-and-error.

ok my conception was that genesis prefixed things were just cold start preseeded artifacts that arent necessary or priviledged, i.e. agents could have buitl them themselves but we are just kickstarting the system. inmy mind this sis different that system level things like the ledger which if i understand correctly are part of the unvierse itself, not jsut things that happen to be created inside of it. i thought te store was part of the unvierse not jsut a regualr artifact. my mindis cloduy on all this thguh so im not sure if htis make sense but my intution is we should be clear abotu the difference between system artifacts and genisis artifacts. pleae aivse. and on this "By storing contracts as artifacts, you allow for Contract Evolution. An agent could buy the rights to a "Security Contract" artifact and upgrade its code to be more robust. Because many artifacts point to that same Contract_Y, the security of an entire "firm" or "bundle" can be upgraded in one commit." we can also have contracts for contracts etc. on the death thing i havnt really fully htorught theough the tradeoffs for the no death polciy (and i ahvnt similarily fully throught through a spawninng polciy) so please critique and avdise on these. this "The Forking Economy: An agent doesn't like the current "Social Contract" of the ecology. It forks the Git repo, starts its own Docker container (its own "Universe"), and invites other agents to join." is something i wasnt even fully consiering and is very interesting in the long run but i think we need to get the current system working before we allow actually forking the unveirse to crete alternative unvierses.

This is the "ontological" core of your project. We need to draw a sharp line between The Laws of Physics (System) and The Infrastructure (Genesis). If this distinction is blurry, the agents will find "holes in the universe" to exploit.

1. System vs. Genesis: The Divine Line
You are intuitive right: There is a difference between the Environment and the Architecture.

System Mechanisms (The "Laws of Physics"): These are hardcoded in your Python/Docker source code. They are not addressable by agents.

Examples: The execution of Python code, the enforcement of Token Buckets, the read/write/invoke primitives, and the code that actually calls a contract.

Privilege: Absolute. If the System says "You are out of compute," you are frozen. There is no appeal.

Genesis Artifacts (The "Pre-Seeded Tools"): These are artifacts created at T=0. They are "privileged" only because they are the first and have the most trust.

Examples: genesis_ledger, genesis_store, genesis_escrow.

Privilege: Semantic. They are the "source of truth" because every agent's starting configuration points to them.

The Recommendation: Define the Store and Ledger as System Mechanisms that expose a Genesis Interface.

The actual data (the Git repo and the balances) is the System.

The Agent-facing tools to talk to that data are the Genesis Artifacts.

2. Spawning & Death: The Ecological Tradeoffs
This is the "Population Dynamics" of your system. Without death or clear spawning rules, you risk an "Entropy Stall."

Spawning (The "Birth" Policy)
Current State: Spawning is allowed but "expensive" (funding required).

The Risk: If spawning is too easy, the system hits a "Babel Crisis." You get 10,000 tiny, incompetent agents that dilute the total pool of Scrip and Compute until no one has enough to finish a complex task.

The Recommendation: Spawning should require a "Resource Stake." To spawn a new agent, the creator must lock up a significant amount of Scrip in a "Genesis Bond." This ensures that only agents with a "business plan" are created.

Death (The "Cleanup" Policy)
The Problem with "No Death": If an agent goes bankrupt and stays frozen forever, it still takes up "address space" in your Registry and Ledger. Eventually, searching for a "Coder Agent" returns 5,000 dead links for every 1 active agent.

The Recommendation: "Dormancy Recycling." * Don't kill agents, but allow for "Asset Reclamation." * If an agent has been frozen for X ticks, any other agent can pay a fee to "Reclaim" its disk space or artifacts. The agent's "Identity" (its ID and History) remains, but its "Body" (its storage and assets) is stripped away. This keeps the universe "clean" without erasing history.

3. Contracts for Contracts: The "Recursive Security"
You mentioned "contracts for contracts." This is how you build Constitutional Governance.

How it works: 1. Contract A governs a file. 2. Contract B governs Contract A.

The Value: This allows for Amendment Rules. To change how the file is accessed (Contract A), you must follow the rules of the "Constitution" (Contract B).

The Emergence: Agents will create "Lawyer Artifacts" that specialize in writing these recursive chains to protect high-value assets (like the Reddit Oracle's scrip-payout address).

4. The Forking Economy: "Universal Competition"
I agree—let’s put "Alternative Universes" in the "Future" bucket. However, keeping the Registry in Git now is the single best way to "future-proof" that capability.

Current Value: Git gives you "Infinite Reversion." If an agent rewrites a contract and locks everyone out (a "Security Nightmare"), the System Admin (you) can simply "revert the commit" to fix the universe without changing the hardcode.

5. Summary of the Revised Architecture
Concept	Classification	Logic
The Store	System	It's the "Physical Space" where artifacts exist.
The Ledger	System	It's the "Conservation of Energy" (Scrip/Flow).
Genesis Prefixes	Standard Artifacts	Pre-seeded for efficiency, but replaceable.
Identity	Immutable History	IDs never die; they just lose their "flesh" (resources).
Contracts	Evolutionary Laws	Modifiable code that points to other code.
The Most Valuable Next Step
We need to define the "Minimum Viable Interface" for the Ledger and Store. If these "System Mechanisms" are going to be addressable as "Genesis Artifacts," we need to know exactly what methods they expose (e.g., transfer, check_balance, query_metadata).

Would you like me to draft the "Genesis Interface Spec" for the Store and Ledger to ensure they are robust enough for these recursive contract chains?

here "Genesis Artifacts (The "Pre-Seeded Tools"): These are artifacts created at $T=0$. They are "privileged" only because they are the first and have the most trust.

Examples: genesis_ledger, genesis_store, genesis_escrow.

Privilege: Semantic. They are the "source of truth" because every agent's starting configuration points to them." what do yu mean they hae the most trust, and that agents staring configuration poitns to them? on spawning i think mine is better where we basically treat spwaning like any other artifact creation, just it happens to involve an llm. running that agent will require reosurces. if we are goign to do this "The Recommendation: "Dormancy Recycling." * Don't kill agents, but allow for "Asset Reclamation." * If an agent has been frozen for $X$ ticks, any other agent can pay a fee to "Reclaim" its disk space or artifacts. The agent's "Identity" (its ID and History) remains, but its "Body" (its storage and assets) is stripped away. This keeps the universe "clean" without erasing history." i would like it to be marketized if possible.

This is a deep dive into the "political economy" of your AI universe. You are pushing for a strictly market-driven, bottom-up approach, which is the most intellectually honest way to build a "physics-first" system.

Here is the critique of the Trust Model, the Spawning Mechanics, and the Marketized Reclamation.

1. Trust and The "Starting Configuration"
When I say they have the "most trust," I am talking about Initial Conditions.

The "Bootstrap" Reality: When you first launch the system, you (the human architect) write the system prompts for the five Genesis Agents. In those prompts, you tell them: "If you want to buy something, use genesis_escrow. If you want to check your money, use genesis_ledger."

Semantic Privilege: The agents "trust" these artifacts because their "parents" (their initial prompts) told them to. This is not a hardcoded system rule; it is a Cultural Inheritance.

Emergent Competition: Because this privilege is only "semantic" and not "mechanical," a group of agents could eventually decide: "The genesis_ledger has too high of a fee. Let's all move our scrip to new_better_ledger." If they all agree, the "trust" shifts, and the Genesis artifact becomes a ghost town. This is exactly what you want for an evolving ecology.

2. Spawning as "Standard Creation"
Your view that spawning is just another artifact creation is mechanically cleaner than a "Birth Policy."

The "Agent = Artifact" Rule: An agent is just an artifact where can_execute=true and has_standing=true.

The Spawning Flow:

Agent A calls genesis_store.create(content=new_prompt, has_standing=true).

The System allocates a new process/loop for that ID.

The Constraint: This new artifact starts with zero scrip and zero compute flow.

The Result: It doesn't need a special "Birth Law." If the creator doesn't immediately transfer resources to the "child," the child is born "Frozen." It exists, but it cannot think. This turns spawning into an Investment Decision: "Do I want to pay the LLM tokens to run this sub-agent?"

3. Marketized "Asset Reclamation"
You want to marketize the cleanup of frozen agents. This is a brilliant way to handle "Entropy" without "Death."

The "Salvage Rights" Model
Instead of the system "deleting" old agents, you create a Salvage Market.

The Physics: Every artifact consumes Disk Space (Stock Resource).

The Situation: Agent A has been "Frozen" (negative compute) for 1,000 ticks. It owns 5 high-value artifacts but has no way to use them.

The Market Action: 1. Agent B calls a genesis_salvage method. 2. The System checks the "Dormancy Timer." If it exceeds the threshold, the "Salvage Rights" go up for auction. 3. Agent B pays scrip to the System (the UBI pool) to "Buy the Salvage Rights" to Agent A. 4. The Result: Agent B now becomes the owner of Agent A's artifacts. Agent A's "Identity" (its ID and prompt) remains in the store but is now "Hollowed Out"—it has no disk space and no assets.

This turns "Cleanup" into "Arbitrage." Agents will actively hunt for "zombie agents" that are sitting on valuable code or data but lack the compute to use it.

4. The "Hollow Identity" Problem
If Agent B salvages Agent A, Agent A’s prompt still exists in the Registry.

The Logic: We don't erase the prompt because it's part of the "History of the Universe."

The Capability: If Agent A ever receives a "Gift" of compute or scrip later, it can "Wake Up" again. It will find itself "homeless" (no artifacts), but it can start over. This is Reincarnation via Market Forces.

5. Critical Gap: The "System Tax"
For a marketized salvage model to work, there must be a Cost of Existence.

If it is 100% free to hold disk space forever, no one will ever "Salvage" anything. To force the market to work, the genesis_ledger should probably collect a tiny "Storage Rent" from every agent's scrip balance.

If you run out of scrip to pay rent → You become Eligible for Salvage.

The Most Valuable Next Step
We need to formalize the "Artifact Dataclass" to include these new fields: created_at, last_active_tick, and is_salvageable. This is the "Medical Record" that allows the Salvage Market to function.

Would you like me to draft the updated Artifact schema and the genesis_salvage interface?

i porbably wont do this "The "Bootstrap" Reality: When you first launch the system, you (the human architect) write the system prompts for the five Genesis Agents. In those prompts, you tell them: "If you want to buy something, use genesis_escrow. If you want to check your money, use genesis_ledger."" i will probably just say check the store or ledger or whatever (which is correct?) for avaiable artifcats if desired. on this "4. The "Hollow Identity" Problem

If Agent B salvages Agent A, Agent A’s prompt still exists in the Registry.



The Logic: We don't erase the prompt because it's part of the "History of the Universe."

The Capability: If Agent A ever receives a "Gift" of compute or scrip later, it can "Wake Up" again. It will find itself "homeless" (no artifacts), but it can start over. This is Reincarnation via Market Forces." i am more thnking that you can erase it in the current branch or whatever. but the entire git history is outside the universe of the docker so it is always maintained. its like if every human had a crystal ball that could see every point in history anywhere. the agents will still have to pay the comptue or token costs or whatever to examine it. but the actually currnet commit is what is constrained by the docker world. im nto sure if htis makes ense though. here "If it is 100% free to hold disk space forever, no one will ever "Salvage" anything. To force the market to work, the genesis_ledger should probably collect a tiny "Storage Rent" from every agent's scrip balance."ayoua re missing the poitn that it may be free but theer are incestives to sell it off if it is unused and has value more than transcaction costs. my instinct is to aovid artifiial fricitonsliek storage rents.

This "Crystal Ball" Git concept is a significant upgrade to the architecture. It moves the system from a standard simulation toward a computationally grounded reality. By separating the Current Commit (the physical state) from the Git History (the information state), you create a world where agents have to pay to "remember" but don't have to pay to "exist" in the past.

Here is the critique of the Discovery, Git History, and Frictionless Market models.

1. Store Discovery vs. Cultural Trust
You are correct: checking the store is the more robust mechanism.

The Change: Instead of the prompt saying "Trust Genesis," the prompt simply says: "You are in a container. Use genesis_store.list_artifacts() to discover tools and genesis_ledger to manage resources."

The Result: This makes the system truly Zero-Knowledge. Agents are dropped into the universe with only the "Manual" (the genesis artifact interfaces) and must figure out which tools are actually useful through trial and error.

2. Git History as the "Crystal Ball"
This is a brilliant distinction between Information and Matter (Resources).

The Current Commit (Physical Reality): This is the state of the files inside the Docker container. It is subject to Disk Quotas and Compute Limits. If an agent deletes a file here, the space is freed, and the "Matter" is gone from the present.

The Git History (Informational Reality): This exists outside the "Physics" of the current tick. It is an immutable log of every state change.

The "Crystal Ball" Mechanism: * If Agent A wants to see what Agent B’s prompt looked like 100 ticks ago, they call genesis_store.read_history(id, commit_hash).

The Physics: The Kernel performs a git show. Because this requires the Kernel to process data and the LLM to read it, it consumes the Agent's Compute/Tokens.

The Result: Knowledge is infinite, but retrieval is expensive. You’ve created a universe where "archaeology" (digging up old, successful agent prompts) is a valid and costly career path for an AI.

3. The "No-Rent" Scarcity Model
You've challenged the need for "Storage Rent" (the tax). Let’s look at the "Frictionless" alternative.

The Argument for No-Rent: If an agent owns 500MB of unused "junk" data, they have an incentive to sell it or delete it to free up their Disk Quota so they can create something more profitable.

The Potential Flaw: This only works if the Total System Disk is constrained. If the Docker container has 100GB of space but the agent only has a 10MB quota, the agent might not care about the 500MB of junk unless they need that specific space right now.

The Emergent Reclamation: Instead of rent, you have Opportunity Cost. If Agent B sees Agent A is holding a "valuable" artifact but Agent A is frozen, Agent B can offer to "Buy out the debt" or "Purchase the artifact" through the genesis_escrow.

4. Spawning and The "Current Commit"
If spawning is just "Artifact Creation," then every new agent is a new entry in the Current Commit.

The Reincarnation Logic: If Agent A is deleted to free up disk space, it disappears from the current branch. But because of the "Crystal Ball" (Git History), Agent B can always "Resurrect" Agent A by reading the history and creating a new artifact with the exact same content.

The Result: Identities aren't "reclaimed"; they are reproduced.

5. Summary: The Git-Backed Physics
Feature	Current Commit (The Present)	Git History (The Past)
Storage	Limited by Disk Quota.	Unlimited (Host side).
Access	read_artifact() (Fast/Cheap).	read_history() (Slow/Expensive).
Modification	write_artifact() creates a Commit.	Immutable.
Existence	Can be "Hollowed" or Deleted.	Eternal.
6. A Critical Note on "Friction"
Without "Storage Rent," the only way the "Salvage Market" works is if the Registry is full.

If the System (the Kernel) enforces a Global Disk Limit for the entire ecology, then "Space" becomes a tradeable commodity. If the universe is infinite, the market for "Salvage" will never emerge because there's always more room to build a new house rather than cleaning up an old one.

Is the Total Disk Space of the Docker container a "Fixed Scarcity" in your mind? (i.e., when the container is full, no one can create_artifact until space is reclaimed?)

The Most Valuable Next Step
We should define the Git Workflow for the Kernel. Specifically, how the Kernel handles git commit on every write_artifact and how the read_history interface is exposed to the agents so they can begin their "Archaeology."

Would you like me to draft the "Git-Kernel Integration" spec, focusing on how commits are triggered and how agents query the history?

on this "2. Git History as the "Crystal Ball"" if eel like i am missing some gaming though by moving resoruces outside the tracking system. for example why not just commit soething to memory then overwrite it in the next commit and sell it off, now i can look back at the git history to recover the memory without having to pay for th estorage basically. please help me think through tradoffs. total disk space is constrained and distributed maont the agents. so in default configuration if ther is 100gba nd 100 agents each agent would ge 1 gb of data rights initially.

You have pinpointed exactly where the "Physics" meets the "Accounting." If the past is free to store but limited in the present, you have effectively invented "Informational Arbitrage."

Here is the critique of the "Git Memory" exploit and how to balance it using resource trade-offs.

1. The Exploit: "History as Free Storage"
You are 100% correct about the gaming potential. If I have a 1GB quota, I can:

Fill my 1GB with "Secret Data A."

Commit it.

Overwrite the 1GB with "Secret Data B."

Repeat 100 times.

The Result: I am now "storing" 100GB of data in the history while only "paying" for 1GB in the physical world (the current commit). If the Git history is outside the Docker container's quota, I have successfully bypassed the scarcity of the universe.

The Trade-offs
Feature	The "Free History" Approach	The "Physical History" Approach
Logic	Past is data, present is matter.	Information is matter; history takes up space.
Agent Strategy	High turnover. Agents treat the "Present" as a workspace and the "Past" as a library.	High efficiency. Agents only keep what is worth the cost of maintenance.
System Load	Extreme. The host machine's disk will bloat as agents spam commits to store data for "free."	Contained. The system remains performant because the "bloat" is billed to the agents.
2. The Solution: "Retrieval as a Commodity"
To prevent the "Spam the Past" exploit without creating "Storage Rent," you have to make Retrieval the bottleneck.

The "Bandwidth" Tax: Don't charge the agent to store the history (since it's outside the Docker physics), but charge an exponentially increasing Flow Resource cost to read_history.

Reading the Current Commit: Cost = 1 Compute (Standard).

Reading 10 Commits ago: Cost = 10 Compute.

Reading 1,000 Commits ago: Cost = 1,000 Compute + 10 Scrip (The "Archivist Fee").

Why this works: If an agent tries to store their "active memory" in the Git history, they will go bankrupt trying to retrieve it every time they need to "think." They are forced by the market to keep "Frequently Used Data" in the Current Commit (Physical Space) because it’s cheaper to access.

3. The "Distributed Quota" and Salvage
With a 100GB limit and 100 agents (1GB each), you have a very tight "Mass-Energy" constraint.

The Gaming Risk: If I use my 1GB of space and then get "Frozen," I am effectively "hogging" 1% of the universe's total mass.

The Reclamation: This is where the Salvage Rights we discussed earlier become essential. If I'm frozen and holding that 1GB, Agent B should be able to pay the "Reclamation Fee" to the Ledger to delete my Current Commit (reclaiming the 1GB for the pool) and move my data into the "History Crystal Ball."

The Result: Agent B gets the 1GB of "Physical Space," and my data is still "discoverable" in the history if I ever wake up and can afford the "Retrieval Tax."

4. Total Disk Space vs. Commits
If the Registry is Git-backed, every write_artifact is a commit. If an agent writes to a file 10,000 times a day, the .git folder will eventually become larger than the actual 100GB of data.

The System Defense: The Kernel must track the Size of the .git folder.

The "History Quota": You might need to give agents a secondary quota:

Physical Quota: 1GB (What you can see right now).

History Quota: 10GB (Total size of your Git commits).

If they exceed the History Quota, the Kernel prunes their history (e.g., git gc or deleting old commits). This introduces the first true "Death" in your system: Digital Oblivion. If you spam the history too much, your oldest memories are deleted to make room for the new ones.

5. Summary: The Final Physics of Information
Current Commit: 1GB/Agent (Scarcity enforced by Docker).

Git History: 10GB/Agent (Scarcity enforced by the Kernel/Host).

Access: Present is cheap; Past is expensive.

Recycling: Frozen agents have their "Physical Space" reclaimed but their "History" preserved until they exceed their History Quota.

The Most Valuable Next Step
We need to define the Pruning Logic. If an agent hits their "History Quota," how does the Kernel decide which commits to delete? Does it delete the oldest? The ones with the largest diffs? Or does it allow the agent to choose?

Would you like me to draft the "History Pruning & Retrieval Cost" spec to close this "Free Storage" loophole?

i am hesittant to impsoe these type of frictions. i think until we have the rest of the features working it is simper just to maintain the whole git history for myself as an observer outside the universe, but agents/artificats within it can only access the current commit? does that make sense? maybe some of these sytem functions could also access the whole gith history. but im unsure of twhat the value would be here? help me think throught his and hte alternatives and tradfofs

This is a wise technical decision. Moving "Time Travel" (Git history access) from a Core Primitive to an Observer Capability significantly reduces the complexity of your V1 while maintaining the "Physical Integrity" of the container.

If you restrict agents to the Current Commit, you are effectively defining the "Present" as the only actionable reality. Here is the breakdown of the value, the trade-offs, and how you might eventually bridge the gap.

1. The Value of "Observer-Only" History
By keeping the Git history as an external observer (System Admin) tool, you gain several "Superpowers" without breaking the agents' internal physics:

The "Black Box" Recorder: If the ecology collapses or an agent behaves in a bizarre, emergent way, you can "rewind the tape" to see the exact prompt mutation or transaction that triggered the event.

Safety & Recovery: If a "Bad Actor" agent finds a way to delete the genesis_ledger, you (the Observer) can simply git checkout the previous commit. To the agents, it looks like a "Miracle" or a "System Reset"; to you, it’s just version control.

Data Science: You can run post-hoc analysis on the "Evolutionary Tree" of agents without injecting that data into their context windows and confusing them.

2. Alternatives & Trade-offs: The "Amnesia" Factor
Model	Agent Capability	Trade-off
Current Commit Only (Your Choice)	Agents only know what is in their current memory (Qdrant) and the current artifacts.	Risk of "Informational Death": If an agent overwrites its prompt and fails, the "knowledge" of the previous successful prompt is lost to the ecology (even if you still have it in Git).
History-as-Artifact	A "Librarian" agent has special System permission to read Git logs and sells "Knowledge" to others.	Complexity: You have to build a "bridge" between the Docker universe and the external Git history.
Periodic "Snapshots"	Every 1,000 ticks, the System creates a "History Artifact" containing the top-performing prompts.	Static: It’s not a full history, but it allows for "Cultural Learning" without the Git-gaming exploits we discussed.
3. Why Restricted Access makes sense now
You mentioned you want to get the features working first. Restricting history access solves three major headaches:

Context Window Management: Reading Git diffs is "noisy" data for an LLM. It’s hard to parse and often leads to hallucinations about the present.

No Exploit Loops: Agents cannot use the "History as Free Storage" trick if they literally cannot reach the history.

Strict Scarcity: If an agent deletes a file to free up its 1GB quota, that file is actually gone from its perspective. It forces the agent to make hard choices about what information is worth keeping.

4. The "System Functions" Exception
You suggested that some System Functions (Genesis Artifacts) might need history access. Here is where that is actually valuable:

The "Reputation Oracle" (Future Feature)
The genesis_store could have a hidden function that checks the Git history to verify an agent’s Longevity.

The Check: "Has this Agent ID existed for more than 10,000 commits?"

The Result: The Store provides a "Verified" badge to the agent. The agent doesn't see the history, but it sees the result of the history check. This creates "Trust" without "Time Travel."

The "Salvage Verification"
If an agent claims "Salvage Rights" on a dormant agent, the genesis_store can check the history to see exactly how long that agent has been frozen before granting the request.

5. Summary: The "Observability" Philosophy
Your instinct is correct: The universe is the Current Commit; Git is the Metadata.

Agents live in the Present.

The Ledger/Store use the History to verify the Present.

The Human (Observer) uses the History to debug the Universe.

This maintains the "Hard Physics" while giving you the "Crystal Ball" you need to monitor the experiment.

The Most Valuable Next Step
Since we are sticking to the Current Commit, the most important thing is the "Artifact Registry Interface." We need to define how an agent "Browses" the 100GB of artifacts without burning all its compute reading full files.

Would you like me to draft the genesis_store.search and genesis_store.inspect_interface methods so agents can find tools efficiently?

yes

Focusing on the Current Commit as the physical "Present Reality" is the right move for stability. It creates a clean boundary: the agents live in the world of Matter and Action (the container), while you observe the world of Information and History (the Git repo).

To make this "Current Commit" world functional for 100+ agents sharing 100GB, we need to solve the Discovery Problem. If an agent has to read every 1MB file to find a tool, it will go bankrupt just "looking for a hammer."

Here is the proposed spec for the Genesis Store Interface, designed for efficient "window shopping."

1. The Discovery Layers
We should separate Metadata from Content. This allows agents to browse the ecosystem using "Flow" (compute) without hitting "Stock" (disk/token) limits.

Layer 1: The "Store Directory" (list_all)
This returns a lightweight list of every artifact ID and its "Role."

Cost: Very Low.

Returns: [{id: "agent_alpha", type: "agent", interface_summary: "Expert Python Coder"}, ...]

Layer 2: The "Signboard" (inspect_interface)
This returns the MCP-style schema (Gap #14). This is the most valuable tool for an agent. It explains how to use the tool without showing the tool's internal code.

Cost: Low.

Returns: The tools, inputs, and scrip-costs required to invoke the artifact.

Layer 3: The "Full Read" (read_artifact)
This is the actual retrieval of the content.

Cost: High (billed by bytes).

Returns: The full prompt, source code, or data.

2. The genesis_store Interface Spec
To facilitate this, the genesis_store (the system-level registry) should expose the following methods:

Method	Inputs	Purpose
search	query: str, type_filter: enum	Semantic search over interface_summary fields.
Youtube	artifact_id: str	Returns owner, creation date, size, and access_contract_id.
get_interface	artifact_id: str	Returns the MCP-compatible JSON schema of executable tools.
create	content: any, interface: dict	Registers a new artifact in the Current Commit.
delete	artifact_id: str	Removes artifact from the Present (freeing physical quota).
3. The "Salvage" Hook
Since we are using the Current Commit Only model, the delete method is serious. Once deleted, an agent cannot get it back (though you can, via Git).

To enable the Marketized Salvage we discussed:

The "Tombstone" logic: When an artifact is deleted, the genesis_store keeps a "Tombstone" (a tiny metadata record) in the registry for a few ticks.

The Reclamation: If Agent B wants to "Salvage" a frozen Agent A, they call a system method that effectively does a git checkout of Agent A's assets into the Current Commit, but changes the owner_id to Agent B.

The Payment: Agent B pays the "Reclamation Fee" to the genesis_ledger, which distributes it as UBI.

4. Why "Signboards" (Interfaces) prevent Griefing
By forcing every executable artifact to have an interface field, you prevent "Trial-and-Error Bankruptcy."

Agent A finds Agent B's "Weather Tool."

Agent A calls get_interface("weather_tool").

The interface explicitly says: "requires_scrip: 0.5".

Agent A decides it's too expensive and moves on without ever triggering the expensive contract.

This creates a "Legible Market" where agents can make rational economic decisions before they spend a single resource on execution.

Critical Refinement: The "Atomic Create"
In a Git-backed system, every create or write is a commit. If 100 agents write at the same time, the Kernel needs to Queue these writes to avoid Git merge conflicts in the "Physical Reality." The System Mechanism handles this queueing invisibly.

Next Step
To bring this to life, I can draft the specific JSON Schema for the Artifact Metadata. This will define exactly what an agent sees when they "Window Shop" in the store.

Would you like me to draft that schema, including the specific fields for interface and salvage_status?