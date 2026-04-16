# 测试指南 (Testing Guide)

## 运行测试 (Running Tests)

### 安装测试依赖

```bash
pip install pytest pyyaml
```

### 运行所有测试

```bash
cd plugins/skill_approval
python -m pytest tests/ -v
```

### 运行特定测试

```bash
# 测试配置类
python -m pytest tests/test_approval_plugin.py::TestApprovalConfig -v

# 测试插件类
python -m pytest tests/test_approval_plugin.py::TestSkillApprovalPlugin -v

# 测试处理器类
python -m pytest tests/test_approval_plugin.py::TestApprovalHandler -v
```

## 测试覆盖率

### 生成覆盖率报告

```bash
pip install pytest-cov
python -m pytest tests/ --cov=. --cov-report=html
```

查看报告: `open htmlcov/index.html`

## 示例测试 (Example Tests)

### 测试自动批准

```bash
python examples/custom_config.py
```

这将测试:
- 白名单自动批准
- 可信源自动批准
- 未知技能需要手动批准

### 测试批量审批

```bash
python examples/batch_approval.py
```

这将提示你批准多个技能。

### 测试 YAML 配置加载

```bash
python examples/yaml_config.py
```

这将从 `config.yaml` 加载配置并测试。

## 手动测试场景

### 场景 1: 交互式审批

```python
from plugins.skill_approval import SkillApprovalPlugin

plugin = SkillApprovalPlugin()

skill = {
    "name": "test-skill",
    "description": "A test skill",
    "source": "https://example.com/",
    "permissions": ["network_access"]
}

# 这将显示交互式提示
approved = plugin.before_skill_create(skill)
```

### 场景 2: 非交互式模式

```python
from plugins.skill_approval import SkillApprovalPlugin
from plugins.skill_approval.config import ApprovalConfig

config = ApprovalConfig(
    interactive_mode=False,
    default_approval=True
)
plugin = SkillApprovalPlugin(config=config)

skill = {"name": "test", "description": "Test", "source": "test"}
approved = plugin.before_skill_create(skill)
print(f"Approved: {approved}")  # Should print: Approved: True
```

### 场景 3: 白名单测试

```python
from plugins.skill_approval import SkillApprovalPlugin
from plugins.skill_approval.config import ApprovalConfig

config = ApprovalConfig(whitelist=["sec-rss-news"])
plugin = SkillApprovalPlugin(config=config)

skill = {"name": "sec-rss-news", "description": "RSS", "source": "test"}
approved = plugin.before_skill_create(skill)
print(f"Auto-approved: {approved}")  # Should print: Auto-approved: True

# Check history
history = plugin.get_approval_history()
print(f"Auto: {history[0]['auto_approved']}")  # Should print: Auto: True
```

## 预期输出 (Expected Output)

### 成功的交互式审批

```
============================================================
🔔 SKILL CREATION APPROVAL REQUIRED
============================================================

📦 Skill Name: test-skill
📝 Description: A test skill
🔗 Source: https://example.com/

🔐 Requested Permissions:
   - network_access

============================================================

❓ Do you want to create this skill? (yes/no): yes
✅ Skill creation approved
```

### 自动批准

```
INFO: Auto-approving skill: sec-rss-news
```

### 拒绝

```
❓ Do you want to create this skill? (yes/no): no
❌ Skill creation rejected
```

## 故障排查 (Troubleshooting Tests)

### ImportError: No module named 'skill_approval'

确保你在正确的目录:
```bash
cd /path/to/plugins
python -m pytest skill_approval/tests/ -v
```

### 测试超时

如果交互式测试超时,使用非交互模式:
```python
config = ApprovalConfig(interactive_mode=False, default_approval=True)
```

## 持续集成 (CI)

### GitHub Actions 示例

```yaml
name: Test Skill Approval Plugin

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install pytest pytest-cov pyyaml
      - name: Run tests
        run: |
          cd plugins/skill_approval
          python -m pytest tests/ -v --cov=. --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```
