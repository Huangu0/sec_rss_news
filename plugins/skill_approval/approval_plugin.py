"""
SkillApprovalPlugin - Main plugin class for skill creation approval

This plugin provides a hook mechanism to intercept skill creation operations
in hermes-agent and require explicit user approval before proceeding.
"""

import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from .approval_handler import ApprovalHandler
from .config import ApprovalConfig


logger = logging.getLogger(__name__)


class SkillApprovalPlugin:
    """
    Plugin to enforce approval workflow for skill creation in hermes-agent.

    This plugin intercepts skill creation requests and prompts the user
    for approval before allowing the operation to proceed.
    """

    def __init__(self, config: Optional[ApprovalConfig] = None):
        """
        Initialize the approval plugin.

        Args:
            config: Optional configuration for the approval plugin
        """
        self.config = config or ApprovalConfig()
        self.approval_handler = ApprovalHandler(self.config)
        self.approval_history = []
        logger.info("SkillApprovalPlugin initialized")

    def before_skill_create(self, skill_info: Dict[str, Any]) -> bool:
        """
        Hook called before creating a new skill.

        Args:
            skill_info: Dictionary containing skill metadata
                - name: Skill name
                - description: Skill description
                - source: Where the skill comes from (url, local, etc)
                - permissions: List of requested permissions

        Returns:
            bool: True if approved, False if rejected
        """
        logger.info(f"Approval requested for skill: {skill_info.get('name', 'Unknown')}")

        # Check if auto-approval is enabled for this skill
        if self._should_auto_approve(skill_info):
            logger.info(f"Auto-approving skill: {skill_info.get('name')}")
            self._record_approval(skill_info, approved=True, auto=True)
            return True

        # Request human approval
        approved = self.approval_handler.request_approval(skill_info)
        self._record_approval(skill_info, approved=approved, auto=False)

        return approved

    def after_skill_create(self, skill_info: Dict[str, Any], success: bool):
        """
        Hook called after skill creation attempt.

        Args:
            skill_info: Dictionary containing skill metadata
            success: Whether the skill was successfully created
        """
        status = "SUCCESS" if success else "FAILED"
        logger.info(f"Skill creation {status}: {skill_info.get('name')}")

        # Update approval record with result
        self._update_approval_record(skill_info, success)

    def get_approval_history(self) -> list:
        """
        Get the history of all approval requests.

        Returns:
            List of approval records
        """
        return self.approval_history.copy()

    def _should_auto_approve(self, skill_info: Dict[str, Any]) -> bool:
        """
        Determine if a skill should be auto-approved based on configuration.

        Args:
            skill_info: Skill metadata

        Returns:
            bool: True if should auto-approve
        """
        # Check whitelist
        if skill_info.get('name') in self.config.whitelist:
            return True

        # Check if source is trusted
        source = skill_info.get('source', '')
        for trusted_source in self.config.trusted_sources:
            if trusted_source in source:
                return True

        return False

    def _record_approval(self, skill_info: Dict[str, Any], approved: bool, auto: bool):
        """
        Record an approval decision.

        Args:
            skill_info: Skill metadata
            approved: Whether it was approved
            auto: Whether it was auto-approved
        """
        record = {
            'timestamp': datetime.now().isoformat(),
            'skill_name': skill_info.get('name', 'Unknown'),
            'skill_source': skill_info.get('source', 'Unknown'),
            'approved': approved,
            'auto_approved': auto,
            'permissions': skill_info.get('permissions', []),
            'completed': False
        }
        self.approval_history.append(record)

    def _update_approval_record(self, skill_info: Dict[str, Any], success: bool):
        """
        Update the approval record with the result.

        Args:
            skill_info: Skill metadata
            success: Whether creation was successful
        """
        skill_name = skill_info.get('name', 'Unknown')
        for record in reversed(self.approval_history):
            if record['skill_name'] == skill_name and not record['completed']:
                record['completed'] = True
                record['success'] = success
                break

    def hook_into_agent(self, agent):
        """
        Hook this plugin into a hermes-agent instance.

        Args:
            agent: The hermes-agent instance

        Usage:
            plugin = SkillApprovalPlugin()
            plugin.hook_into_agent(agent)
        """
        # This would be implemented based on hermes-agent's actual plugin API
        # For now, this is a conceptual implementation
        if hasattr(agent, 'register_hook'):
            agent.register_hook('before_skill_create', self.before_skill_create)
            agent.register_hook('after_skill_create', self.after_skill_create)
            logger.info("Plugin hooks registered with agent")
        else:
            logger.warning("Agent does not support hook registration")
