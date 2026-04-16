"""
Skill Creation Approval Plugin for Hermes Agent

This plugin intercepts skill creation requests and requires human approval
before allowing the skill to be created or installed.

Usage:
    from plugins.skill_approval import SkillApprovalPlugin

    plugin = SkillApprovalPlugin()
    # Hook into hermes-agent's skill creation pipeline
"""

from .approval_plugin import SkillApprovalPlugin
from .approval_handler import ApprovalHandler

__all__ = ["SkillApprovalPlugin", "ApprovalHandler"]
__version__ = "1.0.0"
