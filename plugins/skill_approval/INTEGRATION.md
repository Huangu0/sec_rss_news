# Hermes Agent 集成指南 (Integration Guide)

## 概述

本指南说明如何将技能创建审批插件集成到 Hermes Agent 中。

## 目录结构

```
sec_rss_news/
└── plugins/
    └── skill_approval/
        ├── __init__.py              # 插件入口
        ├── approval_plugin.py       # 主插件类
        ├── approval_handler.py      # 用户交互处理
        ├── config.py                # 配置数据类
        ├── config.yaml              # 默认配置文件
        ├── README.md                # 完整文档
        ├── examples/                # 使用示例
        │   ├── basic_usage.py
        │   ├── custom_config.py
        │   ├── batch_approval.py
        │   └── yaml_config.py
        └── tests/                   # 单元测试
            ├── test_approval_plugin.py
            └── TESTING.md
```

## 集成方法

### 方法 1: 复制到 Hermes Agent

将插件目录复制到 Hermes Agent 的 plugins 目录:

```bash
# 假设 Hermes Agent 在 ~/hermes-agent
cp -r plugins/skill_approval ~/hermes-agent/plugins/

# 或者使用符号链接
ln -s $(pwd)/plugins/skill_approval ~/hermes-agent/plugins/skill_approval
```

### 方法 2: 修改 Hermes Agent 源码

如果需要深度集成,可以修改 Hermes Agent 的技能创建流程:

#### 步骤 1: 在 Hermes Agent 中导入插件

编辑 Hermes Agent 的主文件 (例如 `run_agent.py`):

```python
# 在文件开头添加导入
import sys
sys.path.append('/path/to/sec_rss_news')

from plugins.skill_approval import SkillApprovalPlugin
from plugins.skill_approval.config import ApprovalConfig
```

#### 步骤 2: 初始化插件

```python
# 在 Agent 初始化代码中添加
approval_config = ApprovalConfig(
    interactive_mode=True,
    whitelist=['trusted-skill-1', 'trusted-skill-2'],
    trusted_sources=['https://agentskills.io/']
)

approval_plugin = SkillApprovalPlugin(config=approval_config)
```

#### 步骤 3: Hook 技能创建函数

找到 Hermes Agent 中创建技能的函数(可能类似 `install_skill` 或 `create_skill`),并添加审批检查:

```python
def install_skill(skill_info):
    """安装技能到 Hermes Agent"""

    # === 添加审批检查 ===
    if not approval_plugin.before_skill_create(skill_info):
        print(f"❌ Skill creation rejected: {skill_info.get('name')}")
        return False
    # ===================

    try:
        # 原有的技能安装逻辑
        success = _do_install_skill(skill_info)

        # === 添加完成回调 ===
        approval_plugin.after_skill_create(skill_info, success)
        # ===================

        return success
    except Exception as e:
        approval_plugin.after_skill_create(skill_info, False)
        raise e
```

### 方法 3: 使用装饰器模式

创建一个装饰器来包装技能创建函数:

```python
from functools import wraps
from plugins.skill_approval import SkillApprovalPlugin

approval_plugin = SkillApprovalPlugin()

def require_approval(func):
    """装饰器: 要求技能创建审批"""
    @wraps(func)
    def wrapper(skill_info, *args, **kwargs):
        # 请求审批
        if not approval_plugin.before_skill_create(skill_info):
            raise PermissionError(f"Skill creation rejected: {skill_info.get('name')}")

        try:
            # 执行原函数
            result = func(skill_info, *args, **kwargs)
            approval_plugin.after_skill_create(skill_info, True)
            return result
        except Exception as e:
            approval_plugin.after_skill_create(skill_info, False)
            raise e

    return wrapper

# 使用装饰器
@require_approval
def create_skill(skill_info):
    # 技能创建逻辑
    pass
```

## 配置集成

### 通过环境变量

```bash
export SKILL_APPROVAL_MODE=interactive
export SKILL_APPROVAL_DEFAULT=false
export SKILL_APPROVAL_WHITELIST=sec-rss-news,calculator
```

在代码中读取:

```python
import os
from plugins.skill_approval.config import ApprovalConfig

config = ApprovalConfig(
    interactive_mode=os.getenv('SKILL_APPROVAL_MODE', 'true').lower() == 'true',
    default_approval=os.getenv('SKILL_APPROVAL_DEFAULT', 'false').lower() == 'true',
    whitelist=os.getenv('SKILL_APPROVAL_WHITELIST', '').split(',')
)
```

### 通过 Hermes Agent 配置文件

如果 Hermes Agent 使用 YAML 配置文件,添加插件配置:

```yaml
# hermes-config.yaml
plugins:
  skill_approval:
    enabled: true
    interactive_mode: true
    default_approval: false
    whitelist:
      - sec-rss-news
      - calculator
    trusted_sources:
      - https://agentskills.io/
```

## 完整集成示例

### 示例 1: 最小集成

```python
# minimal_integration.py
import sys
sys.path.append('/path/to/sec_rss_news')

from plugins.skill_approval import SkillApprovalPlugin

# 全局插件实例
approval_plugin = SkillApprovalPlugin()

def create_skill_with_approval(skill_info):
    """创建技能 (带审批)"""
    if not approval_plugin.before_skill_create(skill_info):
        return False

    # 这里放置实际的技能创建逻辑
    print(f"Creating skill: {skill_info['name']}")
    success = True  # 假设成功

    approval_plugin.after_skill_create(skill_info, success)
    return success

# 使用
skill = {
    "name": "weather-skill",
    "description": "Get weather info",
    "source": "https://example.com/weather",
    "permissions": ["network_access"]
}

create_skill_with_approval(skill)
```

### 示例 2: 带配置的集成

```python
# configured_integration.py
import sys
import yaml
sys.path.append('/path/to/sec_rss_news')

from plugins.skill_approval import SkillApprovalPlugin
from plugins.skill_approval.config import ApprovalConfig

# 从配置文件加载
with open('approval_config.yaml', 'r') as f:
    config_dict = yaml.safe_load(f)

config = ApprovalConfig.from_dict(config_dict)
approval_plugin = SkillApprovalPlugin(config=config)

class SkillManager:
    """技能管理器 (带审批)"""

    def __init__(self):
        self.installed_skills = []

    def install(self, skill_info):
        """安装技能"""
        # 请求审批
        if not approval_plugin.before_skill_create(skill_info):
            print(f"❌ Installation cancelled: {skill_info['name']}")
            return False

        try:
            # 实际安装逻辑
            self._do_install(skill_info)
            self.installed_skills.append(skill_info['name'])

            approval_plugin.after_skill_create(skill_info, True)
            print(f"✅ Installed: {skill_info['name']}")
            return True

        except Exception as e:
            approval_plugin.after_skill_create(skill_info, False)
            print(f"❌ Installation failed: {e}")
            return False

    def _do_install(self, skill_info):
        # 实际的安装逻辑
        pass

# 使用
manager = SkillManager()
manager.install({
    "name": "sec-rss-news",
    "description": "Security RSS aggregator",
    "source": "https://github.com/example/sec-rss-news"
})
```

### 示例 3: 与 Hermes Agent CLI 集成

```python
# hermes_cli_integration.py
"""
将此代码添加到 Hermes Agent 的 cli.py 文件中
"""
import sys
sys.path.append('/path/to/sec_rss_news')

from plugins.skill_approval import SkillApprovalPlugin
from plugins.skill_approval.config import ApprovalConfig

# 在 CLI 类中添加
class HermesCLI:
    def __init__(self):
        # 初始化审批插件
        self.approval_plugin = SkillApprovalPlugin(
            config=ApprovalConfig(
                interactive_mode=True,
                log_approvals=True
            )
        )

    def cmd_install_skill(self, args):
        """命令: 安装技能"""
        skill_info = self._parse_skill_info(args)

        # 请求审批
        if not self.approval_plugin.before_skill_create(skill_info):
            print("Skill installation cancelled.")
            return

        # 安装技能
        try:
            success = self._install_skill(skill_info)
            self.approval_plugin.after_skill_create(skill_info, success)

            if success:
                print(f"Skill {skill_info['name']} installed successfully!")
        except Exception as e:
            self.approval_plugin.after_skill_create(skill_info, False)
            print(f"Installation failed: {e}")

    def cmd_approval_history(self, args):
        """命令: 查看审批历史"""
        history = self.approval_plugin.get_approval_history()

        print("\n=== Approval History ===")
        for i, record in enumerate(history, 1):
            print(f"\n{i}. {record['skill_name']}")
            print(f"   Approved: {record['approved']}")
            print(f"   Auto: {record['auto_approved']}")
            print(f"   Time: {record['timestamp']}")
```

## 测试集成

### 测试步骤

1. **安装依赖**:
```bash
pip install pyyaml pytest
```

2. **运行基础测试**:
```bash
cd /path/to/sec_rss_news/plugins/skill_approval
python examples/basic_usage.py
```

3. **测试配置加载**:
```bash
python examples/yaml_config.py
```

4. **运行单元测试**:
```bash
python -m pytest tests/ -v
```

### 验证集成

创建测试脚本:

```python
# test_integration.py
from plugins.skill_approval import SkillApprovalPlugin

plugin = SkillApprovalPlugin()

# 测试技能
test_skill = {
    "name": "test-integration",
    "description": "Integration test skill",
    "source": "test",
    "permissions": ["test"]
}

print("Testing approval plugin integration...")
approved = plugin.before_skill_create(test_skill)
print(f"Approval result: {approved}")

history = plugin.get_approval_history()
print(f"History entries: {len(history)}")

if len(history) > 0:
    print("✅ Integration successful!")
else:
    print("❌ Integration failed!")
```

## 常见问题

### Q: 如何在 Hermes Agent 中找到技能创建函数?

A: 在 Hermes Agent 源码中搜索以下关键字:
```bash
grep -r "install.*skill" *.py
grep -r "create.*skill" *.py
grep -r "add.*skill" *.py
```

### Q: 插件会影响 Hermes Agent 性能吗?

A: 影响极小。审批检查只在技能创建时执行,不影响正常运行。

### Q: 可以在运行时修改配置吗?

A: 可以,通过修改 `plugin.config` 属性:
```python
plugin.config.whitelist.append('new-trusted-skill')
plugin.config.interactive_mode = False
```

### Q: 如何禁用插件?

A: 简单地不调用 `before_skill_create` 即可,或者设置:
```python
config = ApprovalConfig(
    interactive_mode=False,
    default_approval=True  # 自动批准所有
)
```

## 下一步

- 查看 [README.md](README.md) 了解完整功能
- 查看 [examples/](examples/) 目录获取更多示例
- 查看 [tests/TESTING.md](tests/TESTING.md) 了解测试方法
- 根据你的 Hermes Agent 版本调整集成方式

## 贡献

如果你成功集成到 Hermes Agent,欢迎分享你的集成方法!
