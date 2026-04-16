"""
Example: Basic usage of the Skill Approval Plugin

This example demonstrates how to use the approval plugin in its simplest form.
"""

import sys
from pathlib import Path

# Add plugin to path
plugin_path = Path(__file__).parent.parent
sys.path.insert(0, str(plugin_path))

from skill_approval import SkillApprovalPlugin


def main():
    print("=== Skill Approval Plugin - Basic Example ===\n")

    # Create plugin with default configuration
    plugin = SkillApprovalPlugin()

    # Simulate a skill creation request
    skill_info = {
        "name": "weather-forecast",
        "description": "Get weather forecasts for any location worldwide",
        "source": "https://github.com/weather-skills/forecast",
        "permissions": ["network_access", "location_access"],
        "metadata": {
            "author": "Weather Skills Team",
            "version": "1.0.0",
            "license": "MIT"
        }
    }

    # Request approval
    print("Requesting approval for skill creation...\n")
    approved = plugin.before_skill_create(skill_info)

    if approved:
        print("\n✅ Skill approved! Proceeding with creation...")
        # Simulate skill creation
        success = True  # In real scenario, this would be the actual creation result
        plugin.after_skill_create(skill_info, success)
    else:
        print("\n❌ Skill rejected! Canceling creation...")
        plugin.after_skill_create(skill_info, False)

    # Display approval history
    print("\n=== Approval History ===")
    history = plugin.get_approval_history()
    for record in history:
        print(f"\nSkill: {record['skill_name']}")
        print(f"Approved: {record['approved']}")
        print(f"Auto-approved: {record['auto_approved']}")
        print(f"Timestamp: {record['timestamp']}")


if __name__ == "__main__":
    main()
