"""
Example: Using custom configuration with whitelist and trusted sources

This example shows how to configure the plugin to auto-approve certain skills
and sources while requiring manual approval for others.
"""

import sys
from pathlib import Path

# Add plugin to path
plugin_path = Path(__file__).parent.parent
sys.path.insert(0, str(plugin_path))

from skill_approval import SkillApprovalPlugin
from skill_approval.config import ApprovalConfig


def main():
    print("=== Skill Approval Plugin - Custom Configuration Example ===\n")

    # Create custom configuration
    config = ApprovalConfig(
        interactive_mode=True,
        whitelist=["sec-rss-news", "calculator", "time-utils"],
        trusted_sources=["https://agentskills.io/", "https://github.com/NousResearch/"],
        default_approval=False,
        log_approvals=True
    )

    # Create plugin with custom config
    plugin = SkillApprovalPlugin(config=config)

    # Test case 1: Whitelisted skill (should auto-approve)
    print("Test 1: Whitelisted skill\n")
    skill1 = {
        "name": "sec-rss-news",
        "description": "Security RSS news aggregator",
        "source": "https://github.com/example/sec-rss-news",
        "permissions": ["network_access"]
    }
    approved1 = plugin.before_skill_create(skill1)
    print(f"Result: {'Approved' if approved1 else 'Rejected'}")
    print(f"Auto-approved: Yes (in whitelist)\n")

    # Test case 2: Trusted source (should auto-approve)
    print("\nTest 2: Skill from trusted source\n")
    skill2 = {
        "name": "morpheus-skill",
        "description": "Decentralized AI inference",
        "source": "https://agentskills.io/skills/morpheus",
        "permissions": ["network_access", "compute"]
    }
    approved2 = plugin.before_skill_create(skill2)
    print(f"Result: {'Approved' if approved2 else 'Rejected'}")
    print(f"Auto-approved: Yes (trusted source)\n")

    # Test case 3: Unknown skill (requires manual approval)
    print("\nTest 3: Unknown skill (manual approval required)\n")
    skill3 = {
        "name": "unknown-skill",
        "description": "A new untrusted skill",
        "source": "https://unknown-source.com/skill",
        "permissions": ["file_access", "network_access", "execute"]
    }
    approved3 = plugin.before_skill_create(skill3)
    print(f"Result: {'Approved' if approved3 else 'Rejected'}")
    print(f"Auto-approved: No (manual review required)\n")

    # Display approval history
    print("\n=== Approval History ===")
    history = plugin.get_approval_history()
    for i, record in enumerate(history, 1):
        print(f"\n{i}. {record['skill_name']}")
        print(f"   Approved: {record['approved']}")
        print(f"   Auto: {record['auto_approved']}")
        print(f"   Source: {record['skill_source']}")


if __name__ == "__main__":
    main()
