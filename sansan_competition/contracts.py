from __future__ import annotations

from .models import AgentTaskType


SCHEMA_VERSION = "1.0.0"
ALLOWED_AGENT_TASK_TYPES = {member.value for member in AgentTaskType}
ALLOWED_STATUSES = {"success", "partial_success", "error"}
