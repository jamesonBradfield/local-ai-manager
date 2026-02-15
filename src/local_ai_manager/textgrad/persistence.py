"""Persistence layer for textgrad workflows."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import TextgradWorkflow, SystemConfig


WORKFLOWS_FILENAME = "textgrad-workflows.json"


def get_workflows_path(config: SystemConfig | None = None) -> Path:
    """Get path to workflows file.

    Args:
        config: System configuration (uses textgrad.workflows_dir if set)

    Returns:
        Path to workflows JSON file
    """
    if config and config.textgrad.workflows_dir:
        return Path(config.textgrad.workflows_dir) / WORKFLOWS_FILENAME

    # Default to config directory
    from ..system_platform import platform_instance

    return platform_instance().get_default_config_dir() / WORKFLOWS_FILENAME


def load_workflows(config: SystemConfig | None = None) -> dict[str, TextgradWorkflow]:
    """Load all workflows from storage.

    Args:
        config: System configuration

    Returns:
        Dictionary mapping workflow IDs to Workflow objects
    """
    from ..models import TextgradWorkflow

    workflows_path = get_workflows_path(config)

    if not workflows_path.exists():
        return {}

    try:
        with open(workflows_path, encoding="utf-8") as f:
            data = json.load(f)

        workflows = {}
        for workflow_id, workflow_data in data.items():
            try:
                workflows[workflow_id] = TextgradWorkflow(**workflow_data)
            except Exception:
                # Skip corrupted workflows
                continue

        return workflows

    except (json.JSONDecodeError, IOError):
        return {}


def save_workflow(
    workflow: TextgradWorkflow,
    config: SystemConfig | None = None,
) -> bool:
    """Save a workflow to storage.

    Args:
        workflow: Workflow to save
        config: System configuration

    Returns:
        True if saved successfully
    """
    workflows = load_workflows(config)
    workflows[workflow.id] = workflow
    return save_workflows(workflows, config)


def save_workflows(
    workflows: dict[str, TextgradWorkflow],
    config: SystemConfig | None = None,
) -> bool:
    """Save all workflows to storage.

    Args:
        workflows: Dictionary of workflows
        config: System configuration

    Returns:
        True if saved successfully
    """
    workflows_path = get_workflows_path(config)
    workflows_path.parent.mkdir(parents=True, exist_ok=True)

    # Atomic write
    import tempfile
    import os

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=workflows_path.parent,
            delete=False,
            suffix=".tmp",
        ) as f:
            # Convert workflows to dict
            data = {wid: w.model_dump(mode="json") for wid, w in workflows.items()}
            json.dump(data, f, indent=2)
            temp_path = f.name

        # Atomic rename
        os.replace(temp_path, workflows_path)
        return True

    except Exception:
        return False


def list_workflows(config: SystemConfig | None = None) -> list[TextgradWorkflow]:
    """List all saved workflows.

    Args:
        config: System configuration

    Returns:
        List of workflows sorted by updated_at (most recent first)
    """
    workflows = load_workflows(config)
    return sorted(
        workflows.values(),
        key=lambda w: w.updated_at,
        reverse=True,
    )


def delete_workflow(workflow_id: str, config: SystemConfig | None = None) -> bool:
    """Delete a workflow from storage.

    Args:
        workflow_id: ID of workflow to delete
        config: System configuration

    Returns:
        True if deleted successfully
    """
    workflows = load_workflows(config)
    if workflow_id not in workflows:
        return False

    del workflows[workflow_id]
    return save_workflows(workflows, config)


def get_workflow(
    workflow_id: str,
    config: SystemConfig | None = None,
) -> TextgradWorkflow | None:
    """Get a specific workflow by ID.

    Args:
        workflow_id: Workflow ID
        config: System configuration

    Returns:
        Workflow or None if not found
    """
    workflows = load_workflows(config)
    return workflows.get(workflow_id)
