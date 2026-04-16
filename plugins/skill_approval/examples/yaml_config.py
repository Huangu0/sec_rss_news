"""
Example: Loading configuration from YAML file

This example shows how to load plugin configuration from a YAML file.
"""

import sys
from pathlib import Path
import yaml

# Add plugin to path
plugin_path = Path(__file__).parent.parent
sys.path.insert(0, str(plugin_path))

from skill_approval import SkillApprovalPlugin
from skill_approval.config import ApprovalConfig


def main():
    print("=== Skill Approval Plugin - YAML Configuration Example ===\n")

    # Load configuration from YAML file
    config_path = Path(__file__).parent.parent / "config.yaml"

    print(f"Loading configuration from: {config_path}\n")

    with open(config_path, 'r', encoding='utf-8') as f:
        config_dict = yaml.safe_load(f)

    # Create config object
    config = ApprovalConfig.from_dict(config_dict)

    # Display loaded configuration
    print("=== Loaded Configuration ===")
    print(f"Interactive Mode: {config.interactive_mode}")
    print(f"Default Approval: {config.default_approval}")
    print(f"Whitelist: {config.whitelist}")
    print(f"Trusted Sources: {config.trusted_sources}")
    print(f"Log Approvals: {config.log_approvals}")
    print(f"Approval Timeout: {config.approval_timeout}s")
    print()

    # Create plugin with loaded config
    plugin = SkillApprovalPlugin(config=config)

    # Test with a skill that's in the whitelist
    skill_info = {
        "name": "sec-rss-news",
        "description": "Security RSS news aggregator (should be auto-approved)",
        "source": "https://github.com/example/sec-rss-news",
        "permissions": ["network_access"]
    }

    print("Testing skill approval with loaded configuration...\n")
    approved = plugin.before_skill_create(skill_info)

    print(f"\nResult: {'✅ Approved' if approved else '❌ Rejected'}")

    # Display approval history
    print("\n=== Approval History ===")
    history = plugin.get_approval_history()
    for record in history:
        print(f"Skill: {record['skill_name']}")
        print(f"Auto-approved: {record['auto_approved']}")
        print(f"Reason: {'In whitelist' if record['auto_approved'] else 'Manual approval'}")


if __name__ == "__main__":
    main()
