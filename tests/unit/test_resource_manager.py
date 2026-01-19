"""Unit tests for the ResourceManager class.

Tests the unified resource management system that consolidates:
- Balance tracking (from Ledger.resources)
- Rate limiting (from RateTracker)
- Quota management (from World._quota_limits)

Plan #95: Unified Resource System
"""

from __future__ import annotations

import pytest

from src.world.resource_manager import ResourceManager, ResourceType


class TestResourceManagerInit:
    """Tests for ResourceManager initialization."""

    def test_creates_empty_manager(self) -> None:
        """Manager starts with no resources or principals."""
        rm = ResourceManager()
        assert rm.get_all_balances() == {}
        assert rm.get_all_quotas() == {}

    def test_custom_rate_window(self) -> None:
        """Can configure rate limiting window."""
        rm = ResourceManager(rate_window_seconds=120.0)
        assert rm.rate_window_seconds == 120.0


class TestResourceTypes:
    """Tests for resource type classification."""

    def test_register_depletable_resource(self) -> None:
        """Can register a depletable resource (once spent, gone)."""
        rm = ResourceManager()
        rm.register_resource("llm_budget", ResourceType.DEPLETABLE, unit="dollars")

        assert rm.get_resource_type("llm_budget") == ResourceType.DEPLETABLE

    def test_register_allocatable_resource(self) -> None:
        """Can register an allocatable resource (quota-based, reclaimable)."""
        rm = ResourceManager()
        rm.register_resource("disk", ResourceType.ALLOCATABLE, unit="bytes")

        assert rm.get_resource_type("disk") == ResourceType.ALLOCATABLE

    def test_register_renewable_resource(self) -> None:
        """Can register a renewable resource (rate-limited)."""
        rm = ResourceManager()
        rm.register_resource("llm_tokens", ResourceType.RENEWABLE, unit="tokens")

        assert rm.get_resource_type("llm_tokens") == ResourceType.RENEWABLE

    def test_unknown_resource_type_is_none(self) -> None:
        """Unknown resource returns None for type."""
        rm = ResourceManager()
        assert rm.get_resource_type("unknown") is None


class TestPrincipalManagement:
    """Tests for principal (agent/artifact) management."""

    def test_create_principal(self) -> None:
        """Can create a principal with initial resources."""
        rm = ResourceManager()
        rm.register_resource("llm_budget", ResourceType.DEPLETABLE)
        rm.register_resource("disk", ResourceType.ALLOCATABLE)

        rm.create_principal("agent_a", initial_resources={"llm_budget": 1.0, "disk": 1000.0})

        assert rm.get_balance("agent_a", "llm_budget") == 1.0
        assert rm.get_balance("agent_a", "disk") == 1000.0

    def test_create_principal_empty(self) -> None:
        """Can create a principal with no initial resources."""
        rm = ResourceManager()
        rm.create_principal("agent_a")

        assert rm.principal_exists("agent_a")
        assert rm.get_balance("agent_a", "llm_budget") == 0.0

    def test_principal_exists(self) -> None:
        """Check if principal exists."""
        rm = ResourceManager()
        rm.create_principal("agent_a")

        assert rm.principal_exists("agent_a")
        assert not rm.principal_exists("unknown")


class TestBalanceOperations:
    """Tests for balance get/set/spend/credit operations."""

    @pytest.fixture
    def rm_with_agent(self) -> ResourceManager:
        """ResourceManager with one agent and resources."""
        rm = ResourceManager()
        rm.register_resource("llm_budget", ResourceType.DEPLETABLE)
        rm.register_resource("disk", ResourceType.ALLOCATABLE)
        rm.create_principal("agent_a", initial_resources={"llm_budget": 1.0, "disk": 1000.0})
        return rm

    def test_get_balance(self, rm_with_agent: ResourceManager) -> None:
        """Get balance for a resource."""
        assert rm_with_agent.get_balance("agent_a", "llm_budget") == 1.0
        assert rm_with_agent.get_balance("agent_a", "disk") == 1000.0

    def test_get_balance_unknown_principal(self, rm_with_agent: ResourceManager) -> None:
        """Get balance for unknown principal returns 0."""
        assert rm_with_agent.get_balance("unknown", "llm_budget") == 0.0

    def test_get_balance_unknown_resource(self, rm_with_agent: ResourceManager) -> None:
        """Get balance for unknown resource returns 0."""
        assert rm_with_agent.get_balance("agent_a", "unknown") == 0.0

    def test_set_balance(self, rm_with_agent: ResourceManager) -> None:
        """Set balance directly."""
        rm_with_agent.set_balance("agent_a", "llm_budget", 0.5)
        assert rm_with_agent.get_balance("agent_a", "llm_budget") == 0.5

    def test_credit(self, rm_with_agent: ResourceManager) -> None:
        """Credit adds to balance."""
        rm_with_agent.credit("agent_a", "llm_budget", 0.5)
        assert rm_with_agent.get_balance("agent_a", "llm_budget") == 1.5

    def test_spend_success(self, rm_with_agent: ResourceManager) -> None:
        """Spend deducts from balance when sufficient."""
        result = rm_with_agent.spend("agent_a", "llm_budget", 0.3)
        assert result is True
        assert rm_with_agent.get_balance("agent_a", "llm_budget") == pytest.approx(0.7)

    def test_spend_insufficient(self, rm_with_agent: ResourceManager) -> None:
        """Spend fails when insufficient balance."""
        result = rm_with_agent.spend("agent_a", "llm_budget", 2.0)
        assert result is False
        assert rm_with_agent.get_balance("agent_a", "llm_budget") == 1.0  # Unchanged

    def test_can_spend(self, rm_with_agent: ResourceManager) -> None:
        """Check if can spend without actually spending."""
        assert rm_with_agent.can_spend("agent_a", "llm_budget", 0.5) is True
        assert rm_with_agent.can_spend("agent_a", "llm_budget", 2.0) is False


class TestQuotaManagement:
    """Tests for quota-based resource management (allocatable resources)."""

    @pytest.fixture
    def rm_with_quotas(self) -> ResourceManager:
        """ResourceManager with quota-based resources."""
        rm = ResourceManager()
        rm.register_resource("disk", ResourceType.ALLOCATABLE)
        rm.create_principal("agent_a")
        rm.set_quota("agent_a", "disk", 10000.0)  # 10KB quota
        return rm

    def test_set_quota(self, rm_with_quotas: ResourceManager) -> None:
        """Set quota for a principal."""
        assert rm_with_quotas.get_quota("agent_a", "disk") == 10000.0

    def test_get_quota_unset(self) -> None:
        """Unset quota returns 0."""
        rm = ResourceManager()
        rm.register_resource("disk", ResourceType.ALLOCATABLE)
        rm.create_principal("agent_a")
        assert rm.get_quota("agent_a", "disk") == 0.0

    def test_allocate_within_quota(self, rm_with_quotas: ResourceManager) -> None:
        """Can allocate within quota limit."""
        result = rm_with_quotas.allocate("agent_a", "disk", 5000.0)
        assert result is True
        assert rm_with_quotas.get_balance("agent_a", "disk") == 5000.0

    def test_allocate_exceeds_quota(self, rm_with_quotas: ResourceManager) -> None:
        """Allocate fails when exceeding quota."""
        result = rm_with_quotas.allocate("agent_a", "disk", 15000.0)
        assert result is False
        assert rm_with_quotas.get_balance("agent_a", "disk") == 0.0

    def test_deallocate(self, rm_with_quotas: ResourceManager) -> None:
        """Deallocate releases resources back."""
        rm_with_quotas.allocate("agent_a", "disk", 5000.0)
        rm_with_quotas.deallocate("agent_a", "disk", 2000.0)
        assert rm_with_quotas.get_balance("agent_a", "disk") == 3000.0

    def test_get_available_quota(self, rm_with_quotas: ResourceManager) -> None:
        """Get remaining quota capacity."""
        rm_with_quotas.allocate("agent_a", "disk", 3000.0)
        assert rm_with_quotas.get_available_quota("agent_a", "disk") == 7000.0


class TestRateLimiting:
    """Tests for rate-limited (renewable) resources."""

    @pytest.fixture
    def rm_with_rate_limit(self) -> ResourceManager:
        """ResourceManager with rate-limited resources."""
        rm = ResourceManager(rate_window_seconds=60.0)
        rm.register_resource("llm_tokens", ResourceType.RENEWABLE)
        rm.set_rate_limit("llm_tokens", max_per_window=1000.0)
        rm.create_principal("agent_a")
        return rm

    def test_set_rate_limit(self, rm_with_rate_limit: ResourceManager) -> None:
        """Set rate limit for a resource."""
        assert rm_with_rate_limit.get_rate_limit("llm_tokens") == 1000.0

    def test_consume_rate_limited(self, rm_with_rate_limit: ResourceManager) -> None:
        """Consume rate-limited resource within limit."""
        result = rm_with_rate_limit.consume_rate("agent_a", "llm_tokens", 100.0)
        assert result is True

    def test_consume_rate_limited_exceeds(self, rm_with_rate_limit: ResourceManager) -> None:
        """Consume fails when exceeding rate limit."""
        rm_with_rate_limit.consume_rate("agent_a", "llm_tokens", 1000.0)
        result = rm_with_rate_limit.consume_rate("agent_a", "llm_tokens", 100.0)
        assert result is False

    def test_get_rate_remaining(self, rm_with_rate_limit: ResourceManager) -> None:
        """Get remaining rate capacity."""
        rm_with_rate_limit.consume_rate("agent_a", "llm_tokens", 300.0)
        assert rm_with_rate_limit.get_rate_remaining("agent_a", "llm_tokens") == 700.0

    def test_has_rate_capacity(self, rm_with_rate_limit: ResourceManager) -> None:
        """Check rate capacity without consuming."""
        rm_with_rate_limit.consume_rate("agent_a", "llm_tokens", 800.0)
        assert rm_with_rate_limit.has_rate_capacity("agent_a", "llm_tokens", 100.0) is True
        assert rm_with_rate_limit.has_rate_capacity("agent_a", "llm_tokens", 300.0) is False


class TestTransfers:
    """Tests for resource transfers between principals."""

    @pytest.fixture
    def rm_with_agents(self) -> ResourceManager:
        """ResourceManager with two agents."""
        rm = ResourceManager()
        rm.register_resource("llm_budget", ResourceType.DEPLETABLE)
        rm.create_principal("agent_a", initial_resources={"llm_budget": 1.0})
        rm.create_principal("agent_b", initial_resources={"llm_budget": 0.5})
        return rm

    def test_transfer_success(self, rm_with_agents: ResourceManager) -> None:
        """Transfer resource between agents."""
        result = rm_with_agents.transfer("agent_a", "agent_b", "llm_budget", 0.3)

        assert result is True
        assert rm_with_agents.get_balance("agent_a", "llm_budget") == pytest.approx(0.7)
        assert rm_with_agents.get_balance("agent_b", "llm_budget") == pytest.approx(0.8)

    def test_transfer_insufficient(self, rm_with_agents: ResourceManager) -> None:
        """Transfer fails with insufficient balance."""
        result = rm_with_agents.transfer("agent_a", "agent_b", "llm_budget", 2.0)

        assert result is False
        assert rm_with_agents.get_balance("agent_a", "llm_budget") == 1.0
        assert rm_with_agents.get_balance("agent_b", "llm_budget") == 0.5

    def test_transfer_creates_recipient(self, rm_with_agents: ResourceManager) -> None:
        """Transfer to non-existent recipient creates them."""
        result = rm_with_agents.transfer("agent_a", "new_agent", "llm_budget", 0.2)

        assert result is True
        assert rm_with_agents.get_balance("new_agent", "llm_budget") == 0.2


class TestReporting:
    """Tests for balance/quota reporting."""

    def test_get_all_balances(self) -> None:
        """Get all balances snapshot."""
        rm = ResourceManager()
        rm.register_resource("llm_budget", ResourceType.DEPLETABLE)
        rm.create_principal("agent_a", initial_resources={"llm_budget": 1.0})
        rm.create_principal("agent_b", initial_resources={"llm_budget": 0.5})

        balances = rm.get_all_balances()

        assert balances == {
            "agent_a": {"llm_budget": 1.0},
            "agent_b": {"llm_budget": 0.5},
        }

    def test_get_all_quotas(self) -> None:
        """Get all quotas snapshot."""
        rm = ResourceManager()
        rm.register_resource("disk", ResourceType.ALLOCATABLE)
        rm.create_principal("agent_a")
        rm.create_principal("agent_b")
        rm.set_quota("agent_a", "disk", 10000.0)
        rm.set_quota("agent_b", "disk", 5000.0)

        quotas = rm.get_all_quotas()

        assert quotas == {
            "agent_a": {"disk": 10000.0},
            "agent_b": {"disk": 5000.0},
        }

    def test_get_principal_summary(self) -> None:
        """Get summary for a single principal."""
        rm = ResourceManager()
        rm.register_resource("llm_budget", ResourceType.DEPLETABLE)
        rm.register_resource("disk", ResourceType.ALLOCATABLE)
        rm.create_principal("agent_a", initial_resources={"llm_budget": 1.0})
        rm.set_quota("agent_a", "disk", 10000.0)
        rm.allocate("agent_a", "disk", 3000.0)

        summary = rm.get_principal_summary("agent_a")

        assert summary["balances"] == {"llm_budget": 1.0, "disk": 3000.0}
        assert summary["quotas"] == {"disk": 10000.0}
        assert summary["available"] == {"disk": 7000.0}
