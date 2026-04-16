"""
Example: Batch approval for multiple skills

This example demonstrates how to approve multiple skills at once.
"""

import sys
from pathlib import Path

# Add plugin to path
plugin_path = Path(__file__).parent.parent
sys.path.insert(0, str(plugin_path))

from skill_approval import SkillApprovalPlugin
from skill_approval.config import ApprovalConfig


def main():
    print("=== Skill Approval Plugin - Batch Approval Example ===\n")

    # Create plugin
    config = ApprovalConfig(interactive_mode=True)
    plugin = SkillApprovalPlugin(config=config)

    # Define multiple skills to approve
    skills = [
        {
            "name": "email-notifier",
            "description": "Send email notifications",
            "source": "https://github.com/skills/email",
            "permissions": ["network_access", "email_send"]
        },
        {
            "name": "calendar-sync",
            "description": "Sync with calendar services",
            "source": "https://github.com/skills/calendar",
            "permissions": ["network_access", "calendar_read", "calendar_write"]
        },
        {
            "name": "file-organizer",
            "description": "Organize files by type and date",
            "source": "https://github.com/skills/file-org",
            "permissions": ["file_read", "file_write", "file_move"]
        }
    ]

    print(f"Requesting batch approval for {len(skills)} skills...\n")

    # Request batch approval
    approvals = plugin.approval_handler.request_batch_approval(skills)

    # Display results
    print("\n=== Batch Approval Results ===")
    for skill_name, approved in approvals.items():
        status = "✅ APPROVED" if approved else "❌ REJECTED"
        print(f"{skill_name}: {status}")

    # Simulate creation for approved skills
    print("\n=== Creating Approved Skills ===")
    for skill in skills:
        skill_name = skill["name"]
        if approvals.get(skill_name, False):
            print(f"Creating {skill_name}...")
            # Simulate creation
            plugin.after_skill_create(skill, True)
        else:
            print(f"Skipping {skill_name} (rejected)")
            plugin.after_skill_create(skill, False)

    # Display final history
    print("\n=== Final Approval History ===")
    history = plugin.get_approval_history()
    print(f"Total approvals processed: {len(history)}")
    approved_count = sum(1 for r in history if r['approved'])
    print(f"Approved: {approved_count}")
    print(f"Rejected: {len(history) - approved_count}")


if __name__ == "__main__":
    main()
