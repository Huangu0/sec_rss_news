"""
Unit tests for Skill Approval Plugin

Run with: python -m pytest test_approval_plugin.py -v
"""

import sys
from pathlib import Path

# Add plugin to path
plugin_path = Path(__file__).parent.parent
sys.path.insert(0, str(plugin_path))

import pytest
from skill_approval import SkillApprovalPlugin, ApprovalHandler
from skill_approval.config import ApprovalConfig


class TestApprovalConfig:
    """Test ApprovalConfig class"""

    def test_default_config(self):
        """Test default configuration values"""
        config = ApprovalConfig()
        assert config.interactive_mode is True
        assert config.default_approval is False
        assert config.whitelist == []
        assert config.trusted_sources == []

    def test_config_from_dict(self):
        """Test creating config from dictionary"""
        config_dict = {
            'interactive_mode': False,
            'default_approval': True,
            'whitelist': ['skill1', 'skill2'],
            'trusted_sources': ['https://example.com/']
        }
        config = ApprovalConfig.from_dict(config_dict)
        assert config.interactive_mode is False
        assert config.default_approval is True
        assert config.whitelist == ['skill1', 'skill2']
        assert config.trusted_sources == ['https://example.com/']

    def test_config_to_dict(self):
        """Test converting config to dictionary"""
        config = ApprovalConfig(
            interactive_mode=False,
            whitelist=['test'],
            trusted_sources=['https://test.com/']
        )
        config_dict = config.to_dict()
        assert config_dict['interactive_mode'] is False
        assert config_dict['whitelist'] == ['test']
        assert config_dict['trusted_sources'] == ['https://test.com/']


class TestSkillApprovalPlugin:
    """Test SkillApprovalPlugin class"""

    def test_plugin_initialization(self):
        """Test plugin initializes correctly"""
        plugin = SkillApprovalPlugin()
        assert plugin.config is not None
        assert plugin.approval_handler is not None
        assert plugin.approval_history == []

    def test_whitelist_auto_approval(self):
        """Test auto-approval for whitelisted skills"""
        config = ApprovalConfig(whitelist=['trusted-skill'])
        plugin = SkillApprovalPlugin(config=config)

        skill_info = {
            'name': 'trusted-skill',
            'description': 'A trusted skill',
            'source': 'https://example.com/'
        }

        # Should be auto-approved without user interaction
        approved = plugin.before_skill_create(skill_info)
        assert approved is True

        # Check history
        history = plugin.get_approval_history()
        assert len(history) == 1
        assert history[0]['approved'] is True
        assert history[0]['auto_approved'] is True

    def test_trusted_source_auto_approval(self):
        """Test auto-approval for trusted sources"""
        config = ApprovalConfig(trusted_sources=['https://agentskills.io/'])
        plugin = SkillApprovalPlugin(config=config)

        skill_info = {
            'name': 'some-skill',
            'description': 'A skill from trusted source',
            'source': 'https://agentskills.io/skills/test'
        }

        # Should be auto-approved
        approved = plugin.before_skill_create(skill_info)
        assert approved is True

        history = plugin.get_approval_history()
        assert history[0]['auto_approved'] is True

    def test_non_interactive_mode_default_approval(self):
        """Test non-interactive mode with default approval"""
        config = ApprovalConfig(
            interactive_mode=False,
            default_approval=True
        )
        plugin = SkillApprovalPlugin(config=config)

        skill_info = {
            'name': 'test-skill',
            'description': 'Test skill',
            'source': 'https://example.com/'
        }

        # Should use default approval
        approved = plugin.before_skill_create(skill_info)
        assert approved is True

    def test_non_interactive_mode_default_rejection(self):
        """Test non-interactive mode with default rejection"""
        config = ApprovalConfig(
            interactive_mode=False,
            default_approval=False
        )
        plugin = SkillApprovalPlugin(config=config)

        skill_info = {
            'name': 'test-skill',
            'description': 'Test skill',
            'source': 'https://example.com/'
        }

        # Should use default rejection
        approved = plugin.before_skill_create(skill_info)
        assert approved is False

    def test_after_skill_create_updates_history(self):
        """Test that after_skill_create updates the history"""
        config = ApprovalConfig(whitelist=['test'])
        plugin = SkillApprovalPlugin(config=config)

        skill_info = {'name': 'test', 'description': 'Test', 'source': 'test'}

        plugin.before_skill_create(skill_info)
        plugin.after_skill_create(skill_info, success=True)

        history = plugin.get_approval_history()
        assert len(history) == 1
        assert history[0]['completed'] is True
        assert history[0]['success'] is True

    def test_approval_history_multiple_skills(self):
        """Test approval history with multiple skills"""
        config = ApprovalConfig(
            whitelist=['skill1', 'skill2'],
            default_approval=False,
            interactive_mode=False
        )
        plugin = SkillApprovalPlugin(config=config)

        skills = [
            {'name': 'skill1', 'description': 'First', 'source': 'test1'},
            {'name': 'skill2', 'description': 'Second', 'source': 'test2'},
            {'name': 'skill3', 'description': 'Third', 'source': 'test3'}
        ]

        for skill in skills:
            plugin.before_skill_create(skill)

        history = plugin.get_approval_history()
        assert len(history) == 3
        assert history[0]['approved'] is True  # skill1 - whitelisted
        assert history[1]['approved'] is True  # skill2 - whitelisted
        assert history[2]['approved'] is False  # skill3 - not whitelisted


class TestApprovalHandler:
    """Test ApprovalHandler class"""

    def test_handler_initialization(self):
        """Test handler initializes correctly"""
        config = ApprovalConfig()
        handler = ApprovalHandler(config)
        assert handler.config == config

    def test_non_interactive_approval(self):
        """Test non-interactive approval"""
        config = ApprovalConfig(
            interactive_mode=False,
            default_approval=True
        )
        handler = ApprovalHandler(config)

        skill_info = {
            'name': 'test',
            'description': 'Test skill',
            'source': 'https://example.com/'
        }

        # Should return default approval without interaction
        approved = handler.request_approval(skill_info)
        assert approved is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
