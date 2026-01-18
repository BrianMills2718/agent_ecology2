"""JSONL parser for reconstructing simulation state from event log."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from .models import (
    AgentSummary,
    ArtifactInfo,
    ActionEvent,
    ThinkingEvent,
    RawEvent,
    SimulationProgress,
    GenesisMintStatus,
    GenesisEscrowStatus,
    GenesisLedgerStatus,
    GenesisActivitySummary,
    MintScore,
    EscrowListing,
    LedgerTransfer,
    OwnershipTransfer,
    ResourceBalance,
    AgentDetail,
    TickSummary,
    ChartDataPoint,
    AgentChartData,
    ResourceChartData,
    EconomicFlowData,
    FlowNode,
    FlowLink,
    Interaction,
    NetworkNode,
    NetworkEdge,
    NetworkGraphData,
    ActivityItem,
    ActivityFeed,
    ArtifactDetail,
    InvocationEvent,
    InvocationStatsResponse,
    # Temporal artifact network models
    ArtifactNode,
    ArtifactEdge,
    TemporalNetworkData,
)


@dataclass
class AgentState:
    """Internal state tracking for an agent."""
    agent_id: str
    scrip: int = 0
    llm_tokens_used: float = 0
    llm_tokens_quota: float = 0
    disk_used: float = 0
    disk_quota: float = 0
    action_count: int = 0
    last_action_tick: int | None = None
    actions: list[ActionEvent] = field(default_factory=list)
    thinking_history: list[ThinkingEvent] = field(default_factory=list)
    artifacts_owned: list[str] = field(default_factory=list)


@dataclass
class ArtifactState:
    """Internal state tracking for an artifact."""
    artifact_id: str
    artifact_type: str
    owner_id: str
    executable: bool = False
    price: int = 0
    size_bytes: int = 0
    created_at: str = ""
    updated_at: str = ""
    mint_score: float | None = None
    mint_status: Literal["pending", "scored", "none"] = "none"
    content: str | None = None
    methods: list[str] = field(default_factory=list)
    invocation_count: int = 0
    ownership_history: list[OwnershipTransfer] = field(default_factory=list)
    invocation_history: list[ActionEvent] = field(default_factory=list)
    # Interface schema for discoverability (Plan #54)
    interface: dict[str, Any] | None = None
    # Artifact dependencies (Plan #63)
    depends_on: list[str] = field(default_factory=list)


@dataclass
class SimulationState:
    """Complete reconstructed simulation state."""
    # Progress
    current_tick: int = 0
    max_ticks: int = 100
    api_cost_spent: float = 0
    api_cost_limit: float = 1.0
    start_time: str | None = None
    status: Literal["running", "paused", "completed", "budget_exhausted"] = "running"

    # Agents
    agents: dict[str, AgentState] = field(default_factory=dict)

    # Artifacts
    artifacts: dict[str, ArtifactState] = field(default_factory=dict)

    # Genesis activity
    mint_pending: list[str] = field(default_factory=list)
    mint_scores: list[MintScore] = field(default_factory=list)
    total_scrip_minted: int = 0

    escrow_listings: dict[str, EscrowListing] = field(default_factory=dict)
    escrow_trades: list[dict[str, Any]] = field(default_factory=list)

    ledger_transfers: list[LedgerTransfer] = field(default_factory=list)
    ledger_spawns: list[str] = field(default_factory=list)
    ownership_transfers: list[OwnershipTransfer] = field(default_factory=list)

    # Events
    all_events: list[RawEvent] = field(default_factory=list)
    tick_summaries: list[TickSummary] = field(default_factory=list)

    # Charts
    llm_tokens_history: dict[str, list[ChartDataPoint]] = field(default_factory=dict)
    scrip_history: dict[str, list[ChartDataPoint]] = field(default_factory=dict)

    # Flow data
    scrip_flows: list[FlowLink] = field(default_factory=list)

    # Interactions for network graph
    interactions: list[Interaction] = field(default_factory=list)

    # Activity feed items
    activity_items: list[ActivityItem] = field(default_factory=list)

    # Invocation tracking (Gap #27)
    invocation_events: list[InvocationEvent] = field(default_factory=list)


class JSONLParser:
    """Parser for JSONL event log with incremental updates."""

    def __init__(self, jsonl_path: str | Path) -> None:
        self.jsonl_path = Path(jsonl_path)
        self.file_position: int = 0
        self.state = SimulationState()
        self._current_tick_actions: int = 0
        self._current_tick_llm_tokens: float = 0
        self._current_tick_scrip_transfers: int = 0
        self._current_tick_artifacts: int = 0
        self._current_tick_mints: int = 0

    def parse_full(self) -> SimulationState:
        """Parse the entire file from the beginning."""
        self.file_position = 0
        self.state = SimulationState()
        return self.parse_incremental()

    def parse_incremental(self) -> SimulationState:
        """Parse only new events since last parse."""
        if not self.jsonl_path.exists():
            return self.state

        # Check for file truncation (simulation restart)
        file_size = self.jsonl_path.stat().st_size
        if file_size < self.file_position:
            # File was truncated, reset state and parse from beginning
            self.file_position = 0
            self.state = SimulationState()
            self._current_tick_actions = 0
            self._current_tick_llm_tokens = 0
            self._current_tick_scrip_transfers = 0
            self._current_tick_artifacts = 0
            self._current_tick_mints = 0

        with open(self.jsonl_path, 'r') as f:
            f.seek(self.file_position)
            for line in f:
                line = line.strip()
                if line:
                    try:
                        event = json.loads(line)
                        self._process_event(event)
                    except json.JSONDecodeError:
                        continue
            self.file_position = f.tell()

        return self.state

    def get_new_events(self) -> list[RawEvent]:
        """Get only the events added since last call."""
        start_count = len(self.state.all_events)
        self.parse_incremental()
        return self.state.all_events[start_count:]

    def _process_event(self, event: dict[str, Any]) -> None:
        """Process a single event and update state."""
        event_type = event.get("event_type", "")
        timestamp = event.get("timestamp", "")

        # Store raw event
        raw_event = RawEvent(
            timestamp=timestamp,
            event_type=event_type,
            data=event
        )
        self.state.all_events.append(raw_event)

        # Process by type
        handler = getattr(self, f"_handle_{event_type}", None)
        if handler:
            handler(event, timestamp)

    def _handle_world_init(self, event: dict[str, Any], timestamp: str) -> None:
        """Handle world initialization event."""
        self.state.start_time = timestamp
        self.state.max_ticks = event.get("max_ticks", 100)

        # Extract budget limit
        budget = event.get("budget", {})
        self.state.api_cost_limit = budget.get("max_api_cost", 1.0)

        # Initialize agents from principals
        principals = event.get("principals", [])
        for p in principals:
            agent_id = p.get("id", "")
            if agent_id:
                self.state.agents[agent_id] = AgentState(
                    agent_id=agent_id,
                    scrip=p.get("starting_scrip", 0),
                    llm_tokens_quota=p.get("compute_quota", 0),  # Legacy field name in events
                    disk_quota=p.get("disk_quota", 0),
                )

    def _handle_tick(self, event: dict[str, Any], timestamp: str) -> None:
        """Handle tick event - snapshot of state."""
        tick = event.get("tick", 0)
        self.state.current_tick = tick

        # Save tick summary for previous tick
        if tick > 0:
            summary = TickSummary(
                tick=tick - 1,
                timestamp=timestamp,
                agent_count=len(self.state.agents),
                action_count=self._current_tick_actions,
                total_llm_tokens_used=self._current_tick_llm_tokens,
                total_scrip_transferred=self._current_tick_scrip_transfers,
                artifacts_created=self._current_tick_artifacts,
                mint_results=self._current_tick_mints,
            )
            self.state.tick_summaries.append(summary)

        # Reset per-tick counters
        self._current_tick_actions = 0
        self._current_tick_llm_tokens = 0
        self._current_tick_scrip_transfers = 0
        self._current_tick_artifacts = 0
        self._current_tick_mints = 0

        # Update balances from tick event (legacy field name "compute" in events)
        llm_tokens = event.get("compute", {})  # Legacy field name
        scrip = event.get("scrip", {})

        for agent_id, agent in self.state.agents.items():
            if agent_id in llm_tokens:
                agent.llm_tokens_used = agent.llm_tokens_quota - llm_tokens[agent_id]
            if agent_id in scrip:
                agent.scrip = scrip[agent_id]

            # Record history for charts
            if agent_id not in self.state.llm_tokens_history:
                self.state.llm_tokens_history[agent_id] = []
            self.state.llm_tokens_history[agent_id].append(
                ChartDataPoint(tick=tick, value=agent.llm_tokens_used, label=agent_id)
            )

            if agent_id not in self.state.scrip_history:
                self.state.scrip_history[agent_id] = []
            self.state.scrip_history[agent_id].append(
                ChartDataPoint(tick=tick, value=float(agent.scrip), label=agent_id)
            )

    def _handle_thinking(self, event: dict[str, Any], timestamp: str) -> None:
        """Handle agent thinking event."""
        agent_id = event.get("principal_id", "")
        if agent_id not in self.state.agents:
            self.state.agents[agent_id] = AgentState(agent_id=agent_id)

        thought_process = event.get("thought_process", "")

        thinking = ThinkingEvent(
            tick=self.state.current_tick,
            timestamp=timestamp,
            agent_id=agent_id,
            input_tokens=event.get("input_tokens", 0),
            output_tokens=event.get("output_tokens", 0),
            thinking_cost=event.get("thinking_cost", 0),
            success=True,
            thought_process=thought_process if thought_process else None,
        )
        self.state.agents[agent_id].thinking_history.append(thinking)
        self._current_tick_llm_tokens += event.get("thinking_cost", 0)

    def _handle_thinking_failed(self, event: dict[str, Any], timestamp: str) -> None:
        """Handle failed thinking event."""
        agent_id = event.get("principal_id", "")
        if agent_id not in self.state.agents:
            self.state.agents[agent_id] = AgentState(agent_id=agent_id)

        thinking = ThinkingEvent(
            tick=self.state.current_tick,
            timestamp=timestamp,
            agent_id=agent_id,
            thinking_cost=event.get("thinking_cost", 0),
            success=False,
            error=event.get("reason", ""),
        )
        self.state.agents[agent_id].thinking_history.append(thinking)

    def _handle_action(self, event: dict[str, Any], timestamp: str) -> None:
        """Handle action execution event."""
        intent = event.get("intent", {})
        agent_id = intent.get("principal_id", "")
        action_type = intent.get("action_type", "unknown")

        if agent_id not in self.state.agents:
            self.state.agents[agent_id] = AgentState(agent_id=agent_id)

        # Determine target
        target = None
        if action_type == "read_artifact":
            target = intent.get("artifact_id")
        elif action_type == "write_artifact":
            target = intent.get("artifact_id")
            self._current_tick_artifacts += 1
            # Track artifact creation
            artifact_id = intent.get("artifact_id", "")
            content = intent.get("content", "")
            if artifact_id:
                is_new = artifact_id not in self.state.artifacts
                self.state.artifacts[artifact_id] = ArtifactState(
                    artifact_id=artifact_id,
                    artifact_type=intent.get("artifact_type", "unknown"),
                    owner_id=agent_id,
                    executable=intent.get("executable", False),
                    price=intent.get("price", 0),
                    size_bytes=len(content),
                    created_at=timestamp if is_new else self.state.artifacts.get(artifact_id, ArtifactState(artifact_id, "", "")).created_at,
                    updated_at=timestamp,
                    content=content[:10000] if content else None,  # Cap at 10KB
                    interface=intent.get("interface"),  # Plan #54: Interface for discoverability
                    depends_on=intent.get("depends_on", []),  # Plan #63: Artifact dependencies
                )
                if artifact_id not in self.state.agents[agent_id].artifacts_owned:
                    self.state.agents[agent_id].artifacts_owned.append(artifact_id)

                # Add activity item
                self.state.activity_items.append(ActivityItem(
                    tick=self.state.current_tick,
                    timestamp=timestamp,
                    activity_type="artifact_created" if is_new else "artifact_updated",
                    agent_id=agent_id,
                    artifact_id=artifact_id,
                    description=f"{agent_id} {'created' if is_new else 'updated'} artifact {artifact_id}",
                    details={"type": intent.get("artifact_type", "unknown"), "executable": intent.get("executable", False)},
                ))
        elif action_type == "invoke_artifact":
            target = intent.get("artifact_id")
            invoked_artifact_id = intent.get("artifact_id", "")
            if invoked_artifact_id and invoked_artifact_id in self.state.artifacts:
                art = self.state.artifacts[invoked_artifact_id]
                art.invocation_count += 1
                # Track interaction if invoking another agent's artifact
                if art.owner_id != agent_id and not art.owner_id.startswith("genesis_"):
                    self.state.interactions.append(Interaction(
                        tick=self.state.current_tick,
                        timestamp=timestamp,
                        from_id=agent_id,
                        to_id=art.owner_id,
                        interaction_type="artifact_invoke",
                        artifact_id=invoked_artifact_id,
                        details=f"{agent_id} invoked {invoked_artifact_id} owned by {art.owner_id}",
                    ))

        action = ActionEvent(
            tick=self.state.current_tick,
            timestamp=timestamp,
            agent_id=agent_id,
            action_type=action_type,
            target=target,
            llm_tokens_cost=event.get("compute_cost", 0),  # Legacy field name in events
            success=True,
            result=event.get("result"),
        )

        self.state.agents[agent_id].actions.append(action)
        self.state.agents[agent_id].action_count += 1
        self.state.agents[agent_id].last_action_tick = self.state.current_tick

        self._current_tick_actions += 1
        self._current_tick_llm_tokens += event.get("compute_cost", 0)  # Legacy field name

        # Track scrip changes
        if "scrip_after" in event:
            self.state.agents[agent_id].scrip = event.get("scrip_after", 0)

        # Handle genesis artifact results
        result = event.get("result", {})
        if isinstance(result, dict):
            self._process_genesis_result(result, agent_id, intent, timestamp)

    def _process_genesis_result(
        self,
        result: dict[str, Any],
        agent_id: str,
        intent: dict[str, Any],
        timestamp: str
    ) -> None:
        """Process results from genesis artifact invocations."""
        artifact_id = intent.get("artifact_id", "")
        method = intent.get("method", "")

        # Ledger transfers
        if artifact_id == "genesis_ledger" and method == "transfer":
            args = intent.get("args", [])
            if len(args) >= 3:
                from_id = str(args[0])
                to_id = str(args[1])
                amount = int(args[2])
                transfer = LedgerTransfer(
                    from_id=from_id,
                    to_id=to_id,
                    amount=amount,
                    timestamp=timestamp,
                    tick=self.state.current_tick,
                )
                self.state.ledger_transfers.append(transfer)
                self._current_tick_scrip_transfers += amount

                # Add flow link
                self.state.scrip_flows.append(FlowLink(
                    source=from_id,
                    target=to_id,
                    value=amount,
                    tick=self.state.current_tick,
                ))

                # Track interaction
                self.state.interactions.append(Interaction(
                    tick=self.state.current_tick,
                    timestamp=timestamp,
                    from_id=from_id,
                    to_id=to_id,
                    interaction_type="scrip_transfer",
                    amount=amount,
                    details=f"{from_id} sent {amount} scrip to {to_id}",
                ))

                # Add activity item
                self.state.activity_items.append(ActivityItem(
                    tick=self.state.current_tick,
                    timestamp=timestamp,
                    activity_type="scrip_transfer",
                    agent_id=from_id,
                    target_id=to_id,
                    amount=amount,
                    description=f"{from_id} transferred {amount} scrip to {to_id}",
                ))

        # Principal spawns
        elif artifact_id == "genesis_ledger" and method == "spawn_principal":
            new_id = result.get("principal_id")
            if new_id:
                self.state.ledger_spawns.append(new_id)
                if new_id not in self.state.agents:
                    self.state.agents[new_id] = AgentState(agent_id=new_id)
                # Add activity item
                self.state.activity_items.append(ActivityItem(
                    tick=self.state.current_tick,
                    timestamp=timestamp,
                    activity_type="principal_spawned",
                    agent_id=agent_id,
                    target_id=new_id,
                    description=f"{agent_id} spawned new principal {new_id}",
                ))

        # Ownership transfers
        elif artifact_id == "genesis_ledger" and method == "transfer_ownership":
            args = intent.get("args", [])
            if len(args) >= 2:
                transferred_artifact = str(args[0])
                to_id = str(args[1])
                ownership_transfer = OwnershipTransfer(
                    artifact_id=transferred_artifact,
                    from_id=agent_id,
                    to_id=to_id,
                    timestamp=timestamp,
                )
                self.state.ownership_transfers.append(ownership_transfer)
                # Update artifact owner and history
                if transferred_artifact in self.state.artifacts:
                    self.state.artifacts[transferred_artifact].owner_id = to_id
                    self.state.artifacts[transferred_artifact].ownership_history.append(ownership_transfer)

                # Track interaction
                self.state.interactions.append(Interaction(
                    tick=self.state.current_tick,
                    timestamp=timestamp,
                    from_id=agent_id,
                    to_id=to_id,
                    interaction_type="ownership_transfer",
                    artifact_id=transferred_artifact,
                    details=f"{agent_id} transferred ownership of {transferred_artifact} to {to_id}",
                ))

                # Add activity item
                self.state.activity_items.append(ActivityItem(
                    tick=self.state.current_tick,
                    timestamp=timestamp,
                    activity_type="ownership_transfer",
                    agent_id=agent_id,
                    target_id=to_id,
                    artifact_id=transferred_artifact,
                    description=f"{agent_id} transferred {transferred_artifact} to {to_id}",
                ))

        # Mint submissions
        elif artifact_id == "genesis_mint" and method == "submit":
            args = intent.get("args", [])
            if args:
                submitted_id = str(args[0])
                if submitted_id not in self.state.mint_pending:
                    self.state.mint_pending.append(submitted_id)
                if submitted_id in self.state.artifacts:
                    self.state.artifacts[submitted_id].mint_status = "pending"

        # Escrow deposits
        elif artifact_id == "genesis_escrow" and method == "deposit":
            args = intent.get("args", [])
            if len(args) >= 2:
                listed_artifact = str(args[0])
                price = int(args[1])
                listing = EscrowListing(
                    artifact_id=listed_artifact,
                    seller_id=agent_id,
                    price=price,
                    buyer_id=str(args[2]) if len(args) > 2 else None,
                    status="active",
                )
                self.state.escrow_listings[listed_artifact] = listing
                # Add activity item
                self.state.activity_items.append(ActivityItem(
                    tick=self.state.current_tick,
                    timestamp=timestamp,
                    activity_type="escrow_listed",
                    agent_id=agent_id,
                    artifact_id=listed_artifact,
                    amount=price,
                    description=f"{agent_id} listed {listed_artifact} for {price} scrip",
                ))

        # Escrow purchases
        elif artifact_id == "genesis_escrow" and method == "purchase":
            args = intent.get("args", [])
            if args:
                art_id = str(args[0])
                if art_id in self.state.escrow_listings:
                    listing = self.state.escrow_listings[art_id]
                    self.state.escrow_trades.append({
                        "artifact_id": art_id,
                        "seller_id": listing.seller_id,
                        "buyer_id": agent_id,
                        "price": listing.price,
                        "timestamp": timestamp,
                    })

                    # Track interaction (trade between buyer and seller)
                    self.state.interactions.append(Interaction(
                        tick=self.state.current_tick,
                        timestamp=timestamp,
                        from_id=agent_id,  # buyer
                        to_id=listing.seller_id,
                        interaction_type="escrow_trade",
                        amount=listing.price,
                        artifact_id=art_id,
                        details=f"{agent_id} bought {art_id} from {listing.seller_id} for {listing.price} scrip",
                    ))

                    # Add activity item
                    self.state.activity_items.append(ActivityItem(
                        tick=self.state.current_tick,
                        timestamp=timestamp,
                        activity_type="escrow_purchased",
                        agent_id=agent_id,
                        target_id=listing.seller_id,
                        artifact_id=art_id,
                        amount=listing.price,
                        description=f"{agent_id} purchased {art_id} from {listing.seller_id} for {listing.price} scrip",
                    ))

                    del self.state.escrow_listings[art_id]

        # Escrow cancellations
        elif artifact_id == "genesis_escrow" and method == "cancel":
            args = intent.get("args", [])
            if args and str(args[0]) in self.state.escrow_listings:
                cancelled_artifact = str(args[0])
                # Add activity item
                self.state.activity_items.append(ActivityItem(
                    tick=self.state.current_tick,
                    timestamp=timestamp,
                    activity_type="escrow_cancelled",
                    agent_id=agent_id,
                    artifact_id=cancelled_artifact,
                    description=f"{agent_id} cancelled listing for {cancelled_artifact}",
                ))
                del self.state.escrow_listings[cancelled_artifact]

    def _handle_mint(self, event: dict[str, Any], timestamp: str) -> None:
        """Handle mint scoring event."""
        artifact_id = event.get("artifact_id", "")
        score = event.get("score", 0)
        scrip_minted = event.get("scrip_minted", 0)
        submitter = event.get("submitter", "")

        mint_score = MintScore(
            artifact_id=artifact_id,
            submitter=submitter,
            score=score,
            scrip_minted=scrip_minted,
            timestamp=timestamp,
        )
        self.state.mint_scores.append(mint_score)
        self.state.total_scrip_minted += scrip_minted
        self._current_tick_mints += 1

        # Update artifact mint status
        if artifact_id in self.state.artifacts:
            self.state.artifacts[artifact_id].mint_score = score
            self.state.artifacts[artifact_id].mint_status = "scored"

        # Remove from pending
        if artifact_id in self.state.mint_pending:
            self.state.mint_pending.remove(artifact_id)

        # Add activity item
        self.state.activity_items.append(ActivityItem(
            tick=self.state.current_tick,
            timestamp=timestamp,
            activity_type="mint_result",
            agent_id=submitter,
            artifact_id=artifact_id,
            amount=scrip_minted,
            description=f"Mint scored {artifact_id} at {score:.1f}, minted {scrip_minted} scrip to {submitter}",
            details={"score": score},
        ))

    def _handle_invoke_success(self, event: dict[str, Any], timestamp: str) -> None:
        """Handle successful invocation event (Gap #27)."""
        invocation = InvocationEvent(
            tick=event.get("tick", self.state.current_tick),
            timestamp=timestamp,
            invoker_id=event.get("invoker_id", ""),
            artifact_id=event.get("artifact_id", ""),
            method=event.get("method", "run"),
            success=True,
            duration_ms=event.get("duration_ms", 0.0),
            result_type=event.get("result_type"),
        )
        self.state.invocation_events.append(invocation)

        # Update artifact invocation count
        artifact_id = event.get("artifact_id", "")
        if artifact_id in self.state.artifacts:
            self.state.artifacts[artifact_id].invocation_count += 1

    def _handle_invoke_failure(self, event: dict[str, Any], timestamp: str) -> None:
        """Handle failed invocation event (Gap #27)."""
        invocation = InvocationEvent(
            tick=event.get("tick", self.state.current_tick),
            timestamp=timestamp,
            invoker_id=event.get("invoker_id", ""),
            artifact_id=event.get("artifact_id", ""),
            method=event.get("method", "run"),
            success=False,
            duration_ms=event.get("duration_ms", 0.0),
            error_type=event.get("error_type"),
            error_message=event.get("error_message"),
        )
        self.state.invocation_events.append(invocation)

        # Update artifact invocation count (even for failures)
        artifact_id = event.get("artifact_id", "")
        if artifact_id in self.state.artifacts:
            self.state.artifacts[artifact_id].invocation_count += 1

    def _handle_intent_rejected(self, event: dict[str, Any], timestamp: str) -> None:
        """Handle rejected intent event."""
        agent_id = event.get("principal_id", "")
        if agent_id not in self.state.agents:
            self.state.agents[agent_id] = AgentState(agent_id=agent_id)

        action = ActionEvent(
            tick=self.state.current_tick,
            timestamp=timestamp,
            agent_id=agent_id,
            action_type="rejected",
            success=False,
            error=event.get("error", ""),
        )
        self.state.agents[agent_id].actions.append(action)

    def _handle_budget_pause(self, event: dict[str, Any], timestamp: str) -> None:
        """Handle budget pause event."""
        self.state.status = "budget_exhausted"

    def _handle_max_ticks(self, event: dict[str, Any], timestamp: str) -> None:
        """Handle simulation completion event."""
        self.state.status = "completed"

    def get_agent_summary(self, agent_id: str) -> AgentSummary | None:
        """Get summary for a single agent."""
        agent = self.state.agents.get(agent_id)
        if not agent:
            return None

        status: Literal["active", "low_resources", "frozen"] = "active"
        if agent.llm_tokens_used >= agent.llm_tokens_quota * 0.9:
            status = "low_resources"
        if agent.llm_tokens_used >= agent.llm_tokens_quota:
            status = "frozen"

        return AgentSummary(
            agent_id=agent.agent_id,
            scrip=agent.scrip,
            llm_tokens_used=agent.llm_tokens_used,
            llm_tokens_quota=agent.llm_tokens_quota,
            disk_used=agent.disk_used,
            disk_quota=agent.disk_quota,
            status=status,
            action_count=agent.action_count,
            last_action_tick=agent.last_action_tick,
        )

    def get_all_agent_summaries(self) -> list[AgentSummary]:
        """Get summaries for all agents."""
        summaries: list[AgentSummary] = []
        for agent_id in self.state.agents:
            summary = self.get_agent_summary(agent_id)
            if summary is not None:
                summaries.append(summary)
        return summaries

    def get_agent_detail(self, agent_id: str) -> AgentDetail | None:
        """Get full detail for an agent."""
        agent = self.state.agents.get(agent_id)
        if not agent:
            return None

        status: Literal["active", "low_resources", "frozen"] = "active"
        if agent.llm_tokens_used >= agent.llm_tokens_quota * 0.9:
            status = "low_resources"
        if agent.llm_tokens_used >= agent.llm_tokens_quota:
            status = "frozen"

        return AgentDetail(
            agent_id=agent.agent_id,
            scrip=agent.scrip,
            llm_tokens=ResourceBalance(
                current=agent.llm_tokens_quota - agent.llm_tokens_used,
                quota=agent.llm_tokens_quota,
                used=agent.llm_tokens_used,
            ),
            disk=ResourceBalance(
                current=agent.disk_quota - agent.disk_used,
                quota=agent.disk_quota,
                used=agent.disk_used,
            ),
            status=status,
            actions=agent.actions[-100:],  # Last 100 actions
            artifacts_owned=agent.artifacts_owned,
            thinking_history=agent.thinking_history[-50:],  # Last 50
        )

    def get_all_artifacts(self) -> list[ArtifactInfo]:
        """Get all artifact info."""
        return [
            ArtifactInfo(
                artifact_id=art.artifact_id,
                artifact_type=art.artifact_type,
                owner_id=art.owner_id,
                executable=art.executable,
                price=art.price,
                size_bytes=art.size_bytes,
                created_at=art.created_at,
                updated_at=art.updated_at,
                mint_score=art.mint_score,
                mint_status=art.mint_status,
            )
            for art in self.state.artifacts.values()
        ]

    def get_genesis_activity(self) -> GenesisActivitySummary:
        """Get combined genesis artifact activity."""
        return GenesisActivitySummary(
            mint=GenesisMintStatus(
                pending_count=len(self.state.mint_pending),
                pending_artifacts=self.state.mint_pending[:20],
                recent_scores=self.state.mint_scores[-20:],
                total_scrip_minted=self.state.total_scrip_minted,
            ),
            escrow=GenesisEscrowStatus(
                active_listings=list(self.state.escrow_listings.values()),
                recent_trades=[],  # Would need EscrowTrade conversion
            ),
            ledger=GenesisLedgerStatus(
                recent_transfers=self.state.ledger_transfers[-20:],
                recent_spawns=self.state.ledger_spawns[-10:],
                recent_ownership_transfers=self.state.ownership_transfers[-20:],
            ),
        )

    def get_progress(self) -> SimulationProgress:
        """Get simulation progress info."""
        elapsed = 0.0
        tps = 0.0
        if self.state.start_time and self.state.current_tick > 0:
            from datetime import datetime
            try:
                start = datetime.fromisoformat(self.state.start_time)
                now = datetime.now()
                elapsed = (now - start).total_seconds()
                tps = self.state.current_tick / elapsed if elapsed > 0 else 0
            except (ValueError, TypeError):
                pass

        return SimulationProgress(
            current_tick=self.state.current_tick,
            max_ticks=self.state.max_ticks,
            api_cost_spent=self.state.api_cost_spent,
            api_cost_limit=self.state.api_cost_limit,
            start_time=self.state.start_time,
            elapsed_seconds=elapsed,
            ticks_per_second=tps,
            status=self.state.status,
        )

    def get_llm_tokens_chart_data(self) -> ResourceChartData:
        """Get LLM tokens usage chart data."""
        agents = [
            AgentChartData(agent_id=agent_id, data=points)
            for agent_id, points in self.state.llm_tokens_history.items()
        ]

        # Calculate totals per tick
        totals: dict[int, float] = {}
        for points in self.state.llm_tokens_history.values():
            for p in points:
                totals[p.tick] = totals.get(p.tick, 0) + p.value

        total_points = [
            ChartDataPoint(tick=tick, value=value, label="total")
            for tick, value in sorted(totals.items())
        ]

        return ResourceChartData(
            resource_name="llm_tokens",
            agents=agents,
            totals=total_points,
        )

    def get_scrip_chart_data(self) -> ResourceChartData:
        """Get scrip balance chart data."""
        agents = [
            AgentChartData(agent_id=agent_id, data=points)
            for agent_id, points in self.state.scrip_history.items()
        ]

        totals: dict[int, float] = {}
        for points in self.state.scrip_history.values():
            for p in points:
                totals[p.tick] = totals.get(p.tick, 0) + p.value

        total_points = [
            ChartDataPoint(tick=tick, value=value, label="total")
            for tick, value in sorted(totals.items())
        ]

        return ResourceChartData(
            resource_name="scrip",
            agents=agents,
            totals=total_points,
        )

    def get_economic_flow_data(self) -> EconomicFlowData:
        """Get data for economic flow visualization."""
        # Collect all unique node IDs
        node_ids: set[str] = set()
        for flow in self.state.scrip_flows:
            node_ids.add(flow.source)
            node_ids.add(flow.target)

        # Create nodes
        nodes = []
        for node_id in node_ids:
            node_type: Literal["agent", "artifact", "genesis"] = "agent"
            if node_id.startswith("genesis_"):
                node_type = "genesis"
            elif node_id in self.state.artifacts:
                node_type = "artifact"
            nodes.append(FlowNode(id=node_id, name=node_id, type=node_type))

        return EconomicFlowData(
            nodes=nodes,
            links=self.state.scrip_flows,
        )

    def filter_events(
        self,
        event_types: list[str] | None = None,
        agent_id: str | None = None,
        artifact_id: str | None = None,
        tick_min: int | None = None,
        tick_max: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[RawEvent]:
        """Filter and paginate events."""
        events = self.state.all_events

        if event_types:
            events = [e for e in events if e.event_type in event_types]

        if agent_id:
            events = [
                e for e in events
                if e.data.get("principal_id") == agent_id
                or e.data.get("intent", {}).get("principal_id") == agent_id
            ]

        if artifact_id:
            events = [
                e for e in events
                if e.data.get("artifact_id") == artifact_id
                or e.data.get("intent", {}).get("artifact_id") == artifact_id
            ]

        if tick_min is not None:
            events = [
                e for e in events
                if e.data.get("tick", 0) >= tick_min
            ]

        if tick_max is not None:
            events = [
                e for e in events
                if e.data.get("tick", float('inf')) <= tick_max
            ]

        # Apply pagination
        return events[offset:offset + limit]

    def get_network_graph_data(self, tick_max: int | None = None) -> NetworkGraphData:
        """Get network graph data for visualization."""
        # Filter interactions by tick if specified
        interactions = self.state.interactions
        if tick_max is not None:
            interactions = [i for i in interactions if i.tick <= tick_max]

        # Build nodes from agents
        nodes: list[NetworkNode] = []
        for agent_id, agent in self.state.agents.items():
            status: Literal["active", "low_resources", "frozen"] = "active"
            if agent.llm_tokens_used >= agent.llm_tokens_quota * 0.9:
                status = "low_resources"
            if agent.llm_tokens_used >= agent.llm_tokens_quota:
                status = "frozen"

            node_type: Literal["agent", "genesis", "artifact"] = "agent"
            if agent_id.startswith("genesis_"):
                node_type = "genesis"

            nodes.append(NetworkNode(
                id=agent_id,
                label=agent_id,
                node_type=node_type,
                scrip=agent.scrip,
                status=status,
            ))

        # Build edges from interactions
        edges: list[NetworkEdge] = []
        for interaction in interactions:
            edges.append(NetworkEdge(
                from_id=interaction.from_id,
                to_id=interaction.to_id,
                interaction_type=interaction.interaction_type,
                tick=interaction.tick,
                weight=interaction.amount if interaction.amount else 1,
                label=interaction.details,
            ))

        # Calculate tick range
        tick_range = (0, self.state.current_tick)
        if interactions:
            tick_range = (
                min(i.tick for i in interactions),
                max(i.tick for i in interactions),
            )

        return NetworkGraphData(
            nodes=nodes,
            edges=edges,
            interactions=interactions,
            tick_range=tick_range,
        )

    def get_activity_feed(
        self,
        limit: int = 100,
        offset: int = 0,
        activity_types: list[str] | None = None,
        agent_id: str | None = None,
    ) -> ActivityFeed:
        """Get activity feed with filtering."""
        items = self.state.activity_items

        # Filter by type
        if activity_types:
            items = [i for i in items if i.activity_type in activity_types]

        # Filter by agent
        if agent_id:
            items = [
                i for i in items
                if i.agent_id == agent_id or i.target_id == agent_id
            ]

        # Sort by tick descending (most recent first)
        items = sorted(items, key=lambda x: (x.tick, x.timestamp), reverse=True)

        total = len(items)
        items = items[offset:offset + limit]

        return ActivityFeed(items=items, total_count=total)

    def get_artifact_detail(self, artifact_id: str) -> ArtifactDetail | None:
        """Get detailed information for an artifact."""
        art = self.state.artifacts.get(artifact_id)
        if not art:
            return None

        return ArtifactDetail(
            artifact_id=art.artifact_id,
            artifact_type=art.artifact_type,
            owner_id=art.owner_id,
            executable=art.executable,
            price=art.price,
            size_bytes=art.size_bytes,
            created_at=art.created_at,
            updated_at=art.updated_at,
            content=art.content,
            methods=art.methods,
            mint_score=art.mint_score,
            mint_status=art.mint_status,
            invocation_count=art.invocation_count,
            ownership_history=art.ownership_history,
            invocation_history=art.invocation_history[-50:],  # Last 50
            interface=art.interface,
        )

    def get_invocations(
        self,
        artifact_id: str | None = None,
        invoker_id: str | None = None,
        success: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[InvocationEvent]:
        """Get filtered invocation events (Gap #27).

        Args:
            artifact_id: Filter by artifact ID
            invoker_id: Filter by invoker ID
            success: Filter by success status
            limit: Max results to return
            offset: Skip first N results

        Returns:
            List of InvocationEvent objects
        """
        results = self.state.invocation_events

        if artifact_id is not None:
            results = [r for r in results if r.artifact_id == artifact_id]

        if invoker_id is not None:
            results = [r for r in results if r.invoker_id == invoker_id]

        if success is not None:
            results = [r for r in results if r.success == success]

        # Sort by tick descending (most recent first)
        results = sorted(results, key=lambda x: (x.tick, x.timestamp), reverse=True)

        return results[offset:offset + limit]

    def get_invocation_stats(self, artifact_id: str) -> InvocationStatsResponse:
        """Get invocation statistics for an artifact (Gap #27).

        Args:
            artifact_id: The artifact to get stats for

        Returns:
            InvocationStatsResponse with success rate, duration, failure types
        """
        relevant = [
            e for e in self.state.invocation_events
            if e.artifact_id == artifact_id
        ]

        if not relevant:
            return InvocationStatsResponse(artifact_id=artifact_id)

        successful = sum(1 for r in relevant if r.success)
        failed = len(relevant) - successful
        total = len(relevant)

        # Calculate average duration
        total_duration = sum(r.duration_ms for r in relevant)
        avg_duration = total_duration / total if total > 0 else 0.0

        # Count failure types
        failure_types: dict[str, int] = {}
        for r in relevant:
            if not r.success and r.error_type:
                failure_types[r.error_type] = failure_types.get(r.error_type, 0) + 1

        return InvocationStatsResponse(
            artifact_id=artifact_id,
            total_invocations=total,
            successful=successful,
            failed=failed,
            success_rate=successful / total if total > 0 else 0.0,
            avg_duration_ms=avg_duration,
            failure_types=failure_types,
        )

    def get_temporal_network_data(
        self,
        tick_min: int | None = None,
        tick_max: int | None = None,
    ) -> TemporalNetworkData:
        """Get artifact-centric temporal network data.

        Unlike the agent-only network graph, this includes ALL artifacts as nodes:
        - Agents (LLM-powered principals)
        - Genesis artifacts (system services)
        - Contracts (executable artifacts)
        - Data artifacts (non-executable)

        Edges represent:
        - Invocations (who called what artifact)
        - Dependencies (artifact A depends on artifact B)
        - Ownership (which principal owns which artifact)
        - Creation (who created what)
        """
        nodes: list[ArtifactNode] = []
        edges: list[ArtifactEdge] = []
        activity_by_tick: dict[int, dict[str, int]] = {}

        # Determine tick range
        min_tick = tick_min if tick_min is not None else 0
        max_tick = tick_max if tick_max is not None else self.state.current_tick

        # Helper to determine artifact type
        def get_artifact_type(
            artifact_id: str, artifact_state: ArtifactState | None
        ) -> Literal["agent", "genesis", "contract", "data", "unknown"]:
            if artifact_id.startswith("genesis_"):
                return "genesis"
            if artifact_id in self.state.agents:
                return "agent"
            if artifact_state:
                if artifact_state.executable:
                    return "contract"
                return "data"
            return "unknown"

        # Build nodes from ALL artifacts
        seen_nodes: set[str] = set()

        # Collect all artifact IDs referenced in invocations (includes genesis)
        invoked_artifacts: set[str] = set()
        for inv in self.state.invocation_events:
            if inv.artifact_id:
                invoked_artifacts.add(inv.artifact_id)

        # First, add all agents as nodes (skip empty IDs)
        for agent_id, agent in self.state.agents.items():
            if not agent_id:  # Skip empty agent IDs
                continue

            status: Literal["active", "low_resources", "frozen"] = "active"
            if agent.llm_tokens_used >= agent.llm_tokens_quota * 0.9:
                status = "low_resources"
            if agent.llm_tokens_used >= agent.llm_tokens_quota:
                status = "frozen"

            nodes.append(ArtifactNode(
                id=agent_id,
                label=agent_id,
                artifact_type="genesis" if agent_id.startswith("genesis_") else "agent",
                owner_id=None,  # Agents don't have owners
                executable=True,
                invocation_count=0,  # Agents aren't invoked directly
                scrip=agent.scrip,
                status=status,
            ))
            seen_nodes.add(agent_id)

        # Add genesis artifacts that were invoked but not in agents list
        for artifact_id in invoked_artifacts:
            if artifact_id in seen_nodes:
                continue
            if artifact_id.startswith("genesis_"):
                # Count invocations of this genesis artifact
                inv_count = sum(
                    1 for inv in self.state.invocation_events
                    if inv.artifact_id == artifact_id
                )
                nodes.append(ArtifactNode(
                    id=artifact_id,
                    label=artifact_id,
                    artifact_type="genesis",
                    owner_id=None,
                    executable=True,
                    invocation_count=inv_count,
                ))
                seen_nodes.add(artifact_id)

        # Then add all artifacts from state
        for artifact_id, artifact in self.state.artifacts.items():
            if artifact_id in seen_nodes:
                continue

            artifact_type = get_artifact_type(artifact_id, artifact)

            nodes.append(ArtifactNode(
                id=artifact_id,
                label=artifact_id,
                artifact_type=artifact_type,
                owner_id=artifact.owner_id,
                executable=artifact.executable,
                invocation_count=artifact.invocation_count,
            ))
            seen_nodes.add(artifact_id)

        # Build edges from invocation events
        for inv in self.state.invocation_events:
            if inv.tick < min_tick or inv.tick > max_tick:
                continue

            # Only add edge if both nodes exist
            if inv.invoker_id in seen_nodes and inv.artifact_id in seen_nodes:
                edges.append(ArtifactEdge(
                    from_id=inv.invoker_id,
                    to_id=inv.artifact_id,
                    edge_type="invocation",
                    tick=inv.tick,
                    weight=1,
                    details=f"{inv.invoker_id} invoked {inv.artifact_id}.{inv.method}",
                ))

            # Track activity by tick
            if inv.tick not in activity_by_tick:
                activity_by_tick[inv.tick] = {}
            activity_by_tick[inv.tick][inv.invoker_id] = (
                activity_by_tick[inv.tick].get(inv.invoker_id, 0) + 1
            )

        # Build edges from artifact dependencies
        for artifact_id, artifact in self.state.artifacts.items():
            for dep_id in artifact.depends_on:
                if artifact_id in seen_nodes and dep_id in seen_nodes:
                    edges.append(ArtifactEdge(
                        from_id=artifact_id,
                        to_id=dep_id,
                        edge_type="dependency",
                        tick=0,  # Dependencies are static
                        weight=1,
                        details=f"{artifact_id} depends on {dep_id}",
                    ))

        # Build edges from ownership (artifact → owner)
        for artifact_id, artifact in self.state.artifacts.items():
            if artifact.owner_id and artifact.owner_id in seen_nodes:
                edges.append(ArtifactEdge(
                    from_id=artifact_id,
                    to_id=artifact.owner_id,
                    edge_type="ownership",
                    tick=0,  # Current ownership
                    weight=1,
                    details=f"{artifact_id} owned by {artifact.owner_id}",
                ))

        # Track activity from actions
        for agent_id, agent in self.state.agents.items():
            for action in agent.actions:
                if action.tick < min_tick or action.tick > max_tick:
                    continue
                if action.tick not in activity_by_tick:
                    activity_by_tick[action.tick] = {}
                activity_by_tick[action.tick][agent_id] = (
                    activity_by_tick[action.tick].get(agent_id, 0) + 1
                )

        # Calculate tick range
        tick_range = (min_tick, max_tick)

        return TemporalNetworkData(
            nodes=nodes,
            edges=edges,
            tick_range=tick_range,
            activity_by_tick=activity_by_tick,
            total_artifacts=len(nodes),
            total_interactions=len(edges),
        )
