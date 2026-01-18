"""Unit tests for inter-CC messaging system.

Plan #85: Inter-CC Messaging System
"""

import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

# Import modules under test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from send_message import (
    MESSAGE_TYPES,
    create_message,
    generate_message_id,
    get_sender_identity,
    send_message,
)
from check_messages import (
    acknowledge_all,
    archive_message,
    count_unread,
    get_identity,
    list_messages,
    parse_message_frontmatter,
    read_message,
)


class TestSendMessage:
    """Tests for send_message.py functionality."""

    def test_send_message_creates_file(self, tmp_path: Path) -> None:
        """Test that sending a message creates a file in recipient's inbox."""
        # Setup mock repo root
        inbox_dir = tmp_path / ".claude" / "messages" / "inbox" / "test-recipient"

        with patch("send_message.get_repo_root", return_value=tmp_path):
            with patch("send_message.get_sender_identity", return_value="test-sender"):
                success, result = send_message(
                    recipient="test-recipient",
                    msg_type="info",
                    subject="Test Subject",
                    content="Test content",
                )

        assert success is True
        assert inbox_dir.exists()
        files = list(inbox_dir.glob("*.md"))
        assert len(files) == 1

    def test_message_format_valid(self, tmp_path: Path) -> None:
        """Test that message has required frontmatter fields."""
        with patch("send_message.get_repo_root", return_value=tmp_path):
            with patch("send_message.get_sender_identity", return_value="test-sender"):
                success, result = send_message(
                    recipient="test-recipient",
                    msg_type="suggestion",
                    subject="Code Improvement",
                    content="Please review this change",
                )

        assert success is True
        # Read the created file
        inbox_dir = tmp_path / ".claude" / "messages" / "inbox" / "test-recipient"
        files = list(inbox_dir.glob("*.md"))
        content = files[0].read_text()

        # Parse frontmatter
        metadata = parse_message_frontmatter(content)

        # Verify required fields
        assert "id" in metadata
        assert metadata["from"] == "test-sender"
        assert metadata["to"] == "test-recipient"
        assert "timestamp" in metadata
        assert metadata["type"] == "suggestion"
        assert metadata["subject"] == "Code Improvement"
        assert metadata["status"] == "unread"

    def test_invalid_message_type_rejected(self) -> None:
        """Test that invalid message types are rejected."""
        success, result = send_message(
            recipient="anyone",
            msg_type="invalid-type",
            subject="Test",
            content="Test",
        )

        assert success is False
        assert "Invalid message type" in result

    def test_sender_identity_from_worktree(self) -> None:
        """Test that sender identity is detected from worktree path."""
        # Mock being in a worktree directory
        worktree_path = "/home/user/project/worktrees/plan-83-feature/src"
        with patch("send_message.Path.cwd", return_value=Path(worktree_path)):
            identity = get_sender_identity()

        assert identity == "plan-83-feature"

    def test_sender_identity_from_port(self, tmp_path: Path) -> None:
        """Test that sender identity is detected from port mapping."""
        # Create sessions.yaml
        sessions_file = tmp_path / ".claude" / "sessions.yaml"
        sessions_file.parent.mkdir(parents=True)
        sessions_file.write_text("12345: meta-instance\n54321: plan-42\n")

        with patch("send_message.Path.cwd", return_value=Path("/home/user/main")):
            with patch("send_message.get_repo_root", return_value=tmp_path):
                with patch.dict(os.environ, {"CLAUDE_CODE_SSE_PORT": "12345"}):
                    identity = get_sender_identity()

        assert identity == "meta-instance"

    def test_sender_identity_fallback(self, tmp_path: Path) -> None:
        """Test that sender identity falls back to 'main'."""
        with patch("send_message.Path.cwd", return_value=Path("/home/user/main")):
            with patch("send_message.get_repo_root", return_value=tmp_path):
                with patch.dict(os.environ, {}, clear=True):
                    if "CLAUDE_CODE_SSE_PORT" in os.environ:
                        del os.environ["CLAUDE_CODE_SSE_PORT"]
                    identity = get_sender_identity()

        assert identity == "main"


class TestCheckMessages:
    """Tests for check_messages.py functionality."""

    def test_check_messages_lists_inbox(self, tmp_path: Path) -> None:
        """Test that list_messages returns messages in inbox."""
        # Create test messages
        inbox_dir = tmp_path / ".claude" / "messages" / "inbox" / "test-identity"
        inbox_dir.mkdir(parents=True)

        msg1 = inbox_dir / "20260118_120000_from-sender1_info.md"
        msg1.write_text("""---
id: msg-20260118-120000-sender1-abc123
from: sender1
to: test-identity
timestamp: 2026-01-18T12:00:00Z
type: info
subject: First message
status: unread
---

## Content

Hello!
""")

        msg2 = inbox_dir / "20260118_130000_from-sender2_question.md"
        msg2.write_text("""---
id: msg-20260118-130000-sender2-def456
from: sender2
to: test-identity
timestamp: 2026-01-18T13:00:00Z
type: question
subject: Second message
status: read
---

## Content

Question?
""")

        messages = list_messages(inbox_dir, show_all=True)

        assert len(messages) == 2
        assert messages[0]["from"] == "sender1"
        assert messages[1]["from"] == "sender2"

    def test_count_unread(self, tmp_path: Path) -> None:
        """Test counting unread messages."""
        inbox_dir = tmp_path / ".claude" / "messages" / "inbox" / "test"
        inbox_dir.mkdir(parents=True)

        # Create unread message
        (inbox_dir / "unread.md").write_text("---\nstatus: unread\n---\n")
        # Create read message
        (inbox_dir / "read.md").write_text("---\nstatus: read\n---\n")

        count = count_unread(inbox_dir)
        assert count == 1

    def test_archive_moves_message(self, tmp_path: Path) -> None:
        """Test that archive moves message from inbox to archive dir."""
        inbox_dir = tmp_path / ".claude" / "messages" / "inbox" / "test"
        archive_dir = tmp_path / ".claude" / "messages" / "archive" / "test"
        inbox_dir.mkdir(parents=True)

        msg_content = """---
id: msg-to-archive
from: sender
to: test
timestamp: 2026-01-18T12:00:00Z
type: info
subject: Archive me
status: read
---

## Content

Archive this.
"""
        msg_file = inbox_dir / "message.md"
        msg_file.write_text(msg_content)

        success = archive_message(inbox_dir, archive_dir, "msg-to-archive")

        assert success is True
        assert not msg_file.exists()
        assert (archive_dir / "message.md").exists()

    def test_acknowledge_all_marks_read(self, tmp_path: Path) -> None:
        """Test that acknowledge_all marks all messages as read."""
        inbox_dir = tmp_path / ".claude" / "messages" / "inbox" / "test"
        inbox_dir.mkdir(parents=True)

        # Create unread messages
        (inbox_dir / "msg1.md").write_text("---\nstatus: unread\n---\n")
        (inbox_dir / "msg2.md").write_text("---\nstatus: unread\n---\n")
        (inbox_dir / "msg3.md").write_text("---\nstatus: read\n---\n")

        count = acknowledge_all(inbox_dir)

        assert count == 2
        assert "status: read" in (inbox_dir / "msg1.md").read_text()
        assert "status: read" in (inbox_dir / "msg2.md").read_text()


class TestMessageFormat:
    """Tests for message format utilities."""

    def test_generate_message_id_unique(self) -> None:
        """Test that message IDs are unique."""
        timestamp = datetime.now(timezone.utc)
        id1 = generate_message_id("sender", timestamp)
        id2 = generate_message_id("sender", timestamp)

        # Even with same sender and timestamp, IDs should differ (random suffix)
        assert id1 != id2

    def test_generate_message_id_format(self) -> None:
        """Test message ID format."""
        timestamp = datetime(2026, 1, 18, 14, 30, 0, tzinfo=timezone.utc)
        msg_id = generate_message_id("test-sender", timestamp)

        assert msg_id.startswith("msg-20260118-143000-test-sender-")
        # Should have 6 char hash suffix
        parts = msg_id.split("-")
        assert len(parts[-1]) == 6

    def test_create_message_suggestion_actions(self) -> None:
        """Test that suggestion messages have correct action items."""
        timestamp = datetime(2026, 1, 18, 14, 30, 0, tzinfo=timezone.utc)
        content = create_message(
            msg_id="test-id",
            sender="sender",
            recipient="recipient",
            timestamp=timestamp,
            msg_type="suggestion",
            subject="Test",
            content="Test content",
        )

        assert "Review and integrate suggested changes" in content
        assert "Reply with questions if unclear" in content

    def test_create_message_question_actions(self) -> None:
        """Test that question messages have correct action items."""
        timestamp = datetime(2026, 1, 18, 14, 30, 0, tzinfo=timezone.utc)
        content = create_message(
            msg_id="test-id",
            sender="sender",
            recipient="recipient",
            timestamp=timestamp,
            msg_type="question",
            subject="Test",
            content="Test content",
        )

        assert "Reply with answer" in content

    def test_parse_message_frontmatter(self) -> None:
        """Test frontmatter parsing."""
        content = """---
id: msg-123
from: sender
to: recipient
timestamp: 2026-01-18T12:00:00Z
type: info
subject: Test Subject
status: unread
---

## Content

Body here.
"""
        metadata = parse_message_frontmatter(content)

        assert metadata["id"] == "msg-123"
        assert metadata["from"] == "sender"
        assert metadata["to"] == "recipient"
        assert metadata["type"] == "info"
        assert metadata["subject"] == "Test Subject"
        assert metadata["status"] == "unread"
