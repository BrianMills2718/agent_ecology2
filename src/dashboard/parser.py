"""JSONL parser for reconstructing simulation state from event log."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .models import (
    AgentSummary,
    ArtifactInfo,
    ActionEvent,
    ThinkingEvent,
    RawEvent,
    SimulationProgress,
    GenesisOracleStatus,
    GenesisEscrowStatus,
    GenesisLedgerStatus,
    GenesisActivitySummary,
    OracleScore,
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
)


@dataclass
class AgentState:
    """Internal state tracking for an agent."""
    agent_id: str
    scrip: int = 0
    compute_used: float = 0
    compute_quota: float = 0
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
    oracle_score: float | None = None
    oracle_status: str = "none"


@dataclass
class SimulationState:
    """Complete reconstructed simulation state."""
    # Progress
    current_tick: int = 0
    max_ticks: int = 100
    api_cost_spent: float = 0
    api_cost_limit: float = 1.0
    start_time: str | None = None
    status: str = "running"

    # Agents
    agents: dict[str, AgentState] = field(default_factory=dict)

    # Artifacts
    artifacts: dict[str, ArtifactState] = field(default_factory=dict)

    # Genesis activity
    oracle_pending: list[str] = field(default_factory=list)
    oracle_scores: list[OracleScore] = field(default_factory=list)
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
    compute_history: dict[str, list[ChartDataPoint]] = field(default_factory=dict)
    scrip_history: dict[str, list[ChartDataPoint]] = field(default_factory=dict)

    # Flow data
    scrip_flows: list[FlowLink] = field(default_factory=list)


class JSONLParser:
    """Parser for JSONL event log with incremental updates."""

    def __init__(self, jsonl_path: str | Path) -> None:
        self.jsonl_path = Path(jsonl_path)
        self.file_position: int = 0
        self.state = SimulationState()
        self._current_tick_actions: int = 0
        self._current_tick_compute: float = 0
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
                    compute_quota=p.get("compute_quota", 0),
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
                total_compute_used=self._current_tick_compute,
                total_scrip_transferred=self._current_tick_scrip_transfers,
                artifacts_created=self._current_tick_artifacts,
                oracle_mints=self._current_tick_mints,
            )
            self.state.tick_summaries.append(summary)

        # Reset per-tick counters
        self._current_tick_actions = 0
        self._current_tick_compute = 0
        self._current_tick_scrip_transfers = 0
        self._current_tick_artifacts = 0
        self._current_tick_mints = 0

        # Update balances from tick event
        compute = event.get("compute", {})
        scrip = event.get("scrip", {})

        for agent_id, agent in self.state.agents.items():
            if agent_id in compute:
                agent.compute_used = agent.compute_quota - compute[agent_id]
            if agent_id in scrip:
                agent.scrip = scrip[agent_id]

            # Record history for charts
            if agent_id not in self.state.compute_history:
                self.state.compute_history[agent_id] = []
            self.state.compute_history[agent_id].append(
                ChartDataPoint(tick=tick, value=agent.compute_used, label=agent_id)
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

        thinking = ThinkingEvent(
            tick=self.state.current_tick,
            timestamp=timestamp,
            agent_id=agent_id,
            input_tokens=event.get("input_tokens", 0),
            output_tokens=event.get("output_tokens", 0),
            thinking_cost=event.get("thinking_cost", 0),
            success=True,
        )
        self.state.agents[agent_id].thinking_history.append(thinking)
        self._current_tick_compute += event.get("thinking_cost", 0)

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
            if artifact_id:
                self.state.artifacts[artifact_id] = ArtifactState(
                    artifact_id=artifact_id,
                    artifact_type=intent.get("artifact_type", "unknown"),
                    owner_id=agent_id,
                    executable=intent.get("executable", False),
                    price=intent.get("price", 0),
                    size_bytes=len(intent.get("content", "")),
                    created_at=timestamp,
                    updated_at=timestamp,
                )
                self.state.agents[agent_id].artifacts_owned.append(artifact_id)
        elif action_type == "invoke_artifact":
            target = intent.get("artifact_id")

        action = ActionEvent(
            tick=self.state.current_tick,
            timestamp=timestamp,
            agent_id=agent_id,
            action_type=action_type,
            target=target,
            compute_cost=event.get("compute_cost", 0),
            success=True,
            result=event.get("result"),
        )

        self.state.agents[agent_id].actions.append(action)
        self.state.agents[agent_id].action_count += 1
        self.state.agents[agent_id].last_action_tick = self.state.current_tick

        self._current_tick_actions += 1
        self._current_tick_compute += event.get("compute_cost", 0)

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
                transfer = LedgerTransfer(
                    from_id=str(args[0]),
                    to_id=str(args[1]),
                    amount=int(args[2]),
                    timestamp=timestamp,
                    tick=self.state.current_tick,
                )
                self.state.ledger_transfers.append(transfer)
                self._current_tick_scrip_transfers += int(args[2])

                # Add flow link
                self.state.scrip_flows.append(FlowLink(
                    source=str(args[0]),
                    target=str(args[1]),
                    value=int(args[2]),
                    tick=self.state.current_tick,
                ))

        # Principal spawns
        elif artifact_id == "genesis_ledger" and method == "spawn_principal":
            new_id = result.get("principal_id")
            if new_id:
                self.state.ledger_spawns.append(new_id)
                if new_id not in self.state.agents:
                    self.state.agents[new_id] = AgentState(agent_id=new_id)

        # Ownership transfers
        elif artifact_id == "genesis_ledger" and method == "transfer_ownership":
            args = intent.get("args", [])
            if len(args) >= 2:
                transfer = OwnershipTransfer(
                    artifact_id=str(args[0]),
                    from_id=agent_id,
                    to_id=str(args[1]),
                    timestamp=timestamp,
                )
                self.state.ownership_transfers.append(transfer)
                # Update artifact owner
                if args[0] in self.state.artifacts:
                    self.state.artifacts[args[0]].owner_id = str(args[1])

        # Oracle submissions
        elif artifact_id == "genesis_oracle" and method == "submit":
            args = intent.get("args", [])
            if args:
                submitted_id = str(args[0])
                if submitted_id not in self.state.oracle_pending:
                    self.state.oracle_pending.append(submitted_id)
                if submitted_id in self.state.artifacts:
                    self.state.artifacts[submitted_id].oracle_status = "pending"

        # Escrow deposits
        elif artifact_id == "genesis_escrow" and method == "deposit":
            args = intent.get("args", [])
            if len(args) >= 2:
                listing = EscrowListing(
                    artifact_id=str(args[0]),
                    seller_id=agent_id,
                    price=int(args[1]),
                    buyer_id=str(args[2]) if len(args) > 2 else None,
                    status="active",
                )
                self.state.escrow_listings[str(args[0])] = listing

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
                    del self.state.escrow_listings[art_id]

        # Escrow cancellations
        elif artifact_id == "genesis_escrow" and method == "cancel":
            args = intent.get("args", [])
            if args and str(args[0]) in self.state.escrow_listings:
                del self.state.escrow_listings[str(args[0])]

    def _handle_mint(self, event: dict[str, Any], timestamp: str) -> None:
        """Handle oracle minting event."""
        artifact_id = event.get("artifact_id", "")
        score = event.get("score", 0)
        scrip_minted = event.get("scrip_minted", 0)
        submitter = event.get("submitter", "")

        oracle_score = OracleScore(
            artifact_id=artifact_id,
            submitter=submitter,
            score=score,
            scrip_minted=scrip_minted,
            timestamp=timestamp,
        )
        self.state.oracle_scores.append(oracle_score)
        self.state.total_scrip_minted += scrip_minted
        self._current_tick_mints += 1

        # Update artifact oracle status
        if artifact_id in self.state.artifacts:
            self.state.artifacts[artifact_id].oracle_score = score
            self.state.artifacts[artifact_id].oracle_status = "scored"

        # Remove from pending
        if artifact_id in self.state.oracle_pending:
            self.state.oracle_pending.remove(artifact_id)

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

        status = "active"
        if agent.compute_used >= agent.compute_quota * 0.9:
            status = "low_resources"
        if agent.compute_used >= agent.compute_quota:
            status = "frozen"

        return AgentSummary(
            agent_id=agent.agent_id,
            scrip=agent.scrip,
            compute_used=agent.compute_used,
            compute_quota=agent.compute_quota,
            disk_used=agent.disk_used,
            disk_quota=agent.disk_quota,
            status=status,
            action_count=agent.action_count,
            last_action_tick=agent.last_action_tick,
        )

    def get_all_agent_summaries(self) -> list[AgentSummary]:
        """Get summaries for all agents."""
        return [
            self.get_agent_summary(agent_id)
            for agent_id in self.state.agents
            if self.get_agent_summary(agent_id) is not None
        ]

    def get_agent_detail(self, agent_id: str) -> AgentDetail | None:
        """Get full detail for an agent."""
        agent = self.state.agents.get(agent_id)
        if not agent:
            return None

        status = "active"
        if agent.compute_used >= agent.compute_quota * 0.9:
            status = "low_resources"
        if agent.compute_used >= agent.compute_quota:
            status = "frozen"

        return AgentDetail(
            agent_id=agent.agent_id,
            scrip=agent.scrip,
            compute=ResourceBalance(
                current=agent.compute_quota - agent.compute_used,
                quota=agent.compute_quota,
                used=agent.compute_used,
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
                oracle_score=art.oracle_score,
                oracle_status=art.oracle_status,
            )
            for art in self.state.artifacts.values()
        ]

    def get_genesis_activity(self) -> GenesisActivitySummary:
        """Get combined genesis artifact activity."""
        return GenesisActivitySummary(
            oracle=GenesisOracleStatus(
                pending_count=len(self.state.oracle_pending),
                pending_artifacts=self.state.oracle_pending[:20],
                recent_scores=self.state.oracle_scores[-20:],
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

    def get_compute_chart_data(self) -> ResourceChartData:
        """Get compute usage chart data."""
        agents = [
            AgentChartData(agent_id=agent_id, data=points)
            for agent_id, points in self.state.compute_history.items()
        ]

        # Calculate totals per tick
        totals: dict[int, float] = {}
        for points in self.state.compute_history.values():
            for p in points:
                totals[p.tick] = totals.get(p.tick, 0) + p.value

        total_points = [
            ChartDataPoint(tick=tick, value=value, label="total")
            for tick, value in sorted(totals.items())
        ]

        return ResourceChartData(
            resource_name="compute",
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
            node_type = "agent"
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
