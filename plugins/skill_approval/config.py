"""
Configuration for Skill Approval Plugin
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class ApprovalConfig:
    """
    Configuration for skill creation approval plugin.
    """

    # Whether to use interactive mode for approvals
    interactive_mode: bool = True

    # Default approval decision when not in interactive mode
    default_approval: bool = False

    # List of skill names that are automatically approved
    whitelist: List[str] = field(default_factory=list)

    # List of trusted sources that are auto-approved
    trusted_sources: List[str] = field(default_factory=list)

    # Whether to log all approval requests
    log_approvals: bool = True

    # Path to approval log file
    approval_log_path: str = "data/approval_log.json"

    # Timeout for approval prompts (seconds)
    approval_timeout: int = 300  # 5 minutes

    # Whether to require approval for skill updates
    require_update_approval: bool = False

    @classmethod
    def from_dict(cls, config_dict: dict) -> "ApprovalConfig":
        """
        Create config from dictionary.

        Args:
            config_dict: Configuration dictionary

        Returns:
            ApprovalConfig instance
        """
        return cls(**{
            k: v for k, v in config_dict.items()
            if k in cls.__dataclass_fields__
        })

    def to_dict(self) -> dict:
        """
        Convert config to dictionary.

        Returns:
            Configuration as dictionary
        """
        return {
            'interactive_mode': self.interactive_mode,
            'default_approval': self.default_approval,
            'whitelist': self.whitelist,
            'trusted_sources': self.trusted_sources,
            'log_approvals': self.log_approvals,
            'approval_log_path': self.approval_log_path,
            'approval_timeout': self.approval_timeout,
            'require_update_approval': self.require_update_approval,
        }
