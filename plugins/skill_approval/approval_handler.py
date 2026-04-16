"""
ApprovalHandler - Handles user interaction for approval requests
"""

import sys
import logging
from typing import Dict, Any
from .config import ApprovalConfig


logger = logging.getLogger(__name__)


class ApprovalHandler:
    """
    Handles the user interaction for skill creation approval.
    """

    def __init__(self, config: ApprovalConfig):
        """
        Initialize the approval handler.

        Args:
            config: Configuration for approval behavior
        """
        self.config = config

    def request_approval(self, skill_info: Dict[str, Any]) -> bool:
        """
        Request approval from the user for skill creation.

        Args:
            skill_info: Dictionary containing skill metadata

        Returns:
            bool: True if approved, False if rejected
        """
        # Display skill information to user
        self._display_skill_info(skill_info)

        # Get user decision
        if self.config.interactive_mode:
            return self._get_interactive_approval()
        else:
            # In non-interactive mode, use configured default
            return self.config.default_approval

    def _display_skill_info(self, skill_info: Dict[str, Any]):
        """
        Display skill information to the user.

        Args:
            skill_info: Skill metadata
        """
        print("\n" + "="*60)
        print("🔔 SKILL CREATION APPROVAL REQUIRED")
        print("="*60)
        print(f"\n📦 Skill Name: {skill_info.get('name', 'Unknown')}")
        print(f"📝 Description: {skill_info.get('description', 'No description provided')}")
        print(f"🔗 Source: {skill_info.get('source', 'Unknown')}")

        # Display permissions if available
        permissions = skill_info.get('permissions', [])
        if permissions:
            print(f"\n🔐 Requested Permissions:")
            for perm in permissions:
                print(f"   - {perm}")
        else:
            print(f"\n🔐 Requested Permissions: None specified")

        # Display metadata if available
        metadata = skill_info.get('metadata', {})
        if metadata:
            print(f"\n📊 Metadata:")
            for key, value in metadata.items():
                print(f"   - {key}: {value}")

        print("\n" + "="*60)

    def _get_interactive_approval(self) -> bool:
        """
        Get approval decision from user via interactive prompt.

        Returns:
            bool: True if approved, False if rejected
        """
        max_attempts = 3
        attempt = 0

        while attempt < max_attempts:
            try:
                response = input("\n❓ Do you want to create this skill? (yes/no): ").strip().lower()

                if response in ['yes', 'y', '是', '同意']:
                    print("✅ Skill creation approved")
                    return True
                elif response in ['no', 'n', '否', '拒绝']:
                    print("❌ Skill creation rejected")
                    return False
                else:
                    print("⚠️  Invalid response. Please enter 'yes' or 'no'.")
                    attempt += 1
            except (KeyboardInterrupt, EOFError):
                print("\n❌ Approval interrupted. Rejecting skill creation.")
                return False

        # Max attempts reached
        print(f"\n❌ Maximum attempts ({max_attempts}) reached. Rejecting skill creation.")
        return False

    def request_batch_approval(self, skills: list) -> Dict[str, bool]:
        """
        Request approval for multiple skills at once.

        Args:
            skills: List of skill_info dictionaries

        Returns:
            Dictionary mapping skill names to approval decisions
        """
        approvals = {}

        print(f"\n🔔 Batch approval requested for {len(skills)} skills")

        for i, skill_info in enumerate(skills, 1):
            print(f"\n--- Skill {i}/{len(skills)} ---")
            skill_name = skill_info.get('name', f'Unknown_{i}')
            approvals[skill_name] = self.request_approval(skill_info)

        return approvals
