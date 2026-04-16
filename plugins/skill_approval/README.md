# Skill Approval Plugin for Hermes Agent

## 概述 (Overview)

这是一个用于 Hermes Agent 的技能创建审批插件，当 Hermes Agent 尝试自动创建技能时，该插件会强制要求人工审批，确保用户可以控制哪些技能被创建和安装。

This is a skill creation approval plugin for Hermes Agent. When Hermes Agent attempts to automatically create skills, this plugin enforces mandatory human approval, ensuring users can control which skills are created and installed.

## 功能特性 (Features)

- ✅ **强制审批**: 所有技能创建操作都需要人工确认
- ✅ **交互式提示**: 清晰显示技能信息和权限请求
- ✅ **白名单支持**: 支持配置可信任的技能自动批准
- ✅ **审批历史**: 记录所有审批决策用于审计
- ✅ **批量审批**: 支持一次性审批多个技能
- ✅ **可配置**: 灵活的配置选项满足不同需求

## 安装 (Installation)

将插件目录复制到 Hermes Agent 的 `plugins` 目录:

```bash
cp -r plugins/skill_approval /path/to/hermes-agent/plugins/
```

## 使用方法 (Usage)

### 基础用法

```python
from plugins.skill_approval import SkillApprovalPlugin

# 创建插件实例
plugin = SkillApprovalPlugin()

# 集成到 Hermes Agent
# (具体集成方式取决于 Hermes Agent 的插件 API)
plugin.hook_into_agent(agent)
```

### 使用自定义配置

```python
from plugins.skill_approval import SkillApprovalPlugin
from plugins.skill_approval.config import ApprovalConfig

# 创建自定义配置
config = ApprovalConfig(
    interactive_mode=True,
    whitelist=["sec-rss-news", "trusted-skill"],
    trusted_sources=["https://agentskills.io/"],
    default_approval=False
)

# 使用配置创建插件
plugin = SkillApprovalPlugin(config=config)
plugin.hook_into_agent(agent)
```

### 从配置文件加载

```python
import yaml
from plugins.skill_approval import SkillApprovalPlugin
from plugins.skill_approval.config import ApprovalConfig

# 从 YAML 文件加载配置
with open('approval_config.yaml', 'r') as f:
    config_dict = yaml.safe_load(f)

config = ApprovalConfig.from_dict(config_dict)
plugin = SkillApprovalPlugin(config=config)
```

## 配置选项 (Configuration Options)

在 `approval_config.yaml` 中配置插件:

```yaml
# 是否启用交互式审批模式
interactive_mode: true

# 非交互模式下的默认决策（true=批准, false=拒绝）
default_approval: false

# 自动批准的技能白名单
whitelist:
  - sec-rss-news
  - weather-skill
  - calculator-skill

# 可信任的技能源
trusted_sources:
  - https://agentskills.io/
  - https://github.com/verified-skills/

# 是否记录所有审批请求
log_approvals: true

# 审批日志文件路径
approval_log_path: data/approval_log.json

# 审批提示超时时间（秒）
approval_timeout: 300

# 是否对技能更新也要求审批
require_update_approval: false
```

## 审批流程 (Approval Flow)

当 Hermes Agent 尝试创建技能时，插件会执行以下流程:

1. **拦截请求**: 插件拦截技能创建请求
2. **检查白名单**: 检查技能是否在白名单或来自可信源
   - 如果是，自动批准
   - 如果否，继续下一步
3. **显示信息**: 向用户显示技能详细信息
   - 技能名称
   - 描述
   - 来源
   - 请求的权限
4. **请求确认**: 提示用户确认是否创建
5. **记录决策**: 记录审批结果到历史记录
6. **返回结果**: 将决策返回给 Hermes Agent

## 示例场景 (Example Scenarios)

### 场景 1: 交互式审批

```
============================================================
🔔 SKILL CREATION APPROVAL REQUIRED
============================================================

📦 Skill Name: weather-forecast
📝 Description: Get weather forecasts for any location
🔗 Source: https://github.com/weather-skills/forecast

🔐 Requested Permissions:
   - network_access
   - location_access

============================================================

❓ Do you want to create this skill? (yes/no): yes
✅ Skill creation approved
```

### 场景 2: 自动批准（白名单）

```python
# 配置白名单
config = ApprovalConfig(
    whitelist=["sec-rss-news"]
)

plugin = SkillApprovalPlugin(config=config)

# 当创建 sec-rss-news 技能时，自动批准无需人工确认
# INFO: Auto-approving skill: sec-rss-news
```

### 场景 3: 批量审批

```python
skills = [
    {"name": "skill1", "description": "First skill", "source": "..."},
    {"name": "skill2", "description": "Second skill", "source": "..."},
    {"name": "skill3", "description": "Third skill", "source": "..."}
]

approvals = plugin.approval_handler.request_batch_approval(skills)
# 用户将依次被提示审批每个技能
```

## 审批历史 (Approval History)

查看所有审批历史:

```python
history = plugin.get_approval_history()

for record in history:
    print(f"Skill: {record['skill_name']}")
    print(f"Approved: {record['approved']}")
    print(f"Auto-approved: {record['auto_approved']}")
    print(f"Timestamp: {record['timestamp']}")
    print("---")
```

历史记录格式:

```json
{
  "timestamp": "2026-04-16T10:30:00",
  "skill_name": "weather-forecast",
  "skill_source": "https://github.com/weather-skills/forecast",
  "approved": true,
  "auto_approved": false,
  "permissions": ["network_access", "location_access"],
  "completed": true,
  "success": true
}
```

## 集成到 Hermes Agent (Integration with Hermes Agent)

### 方法 1: 通过 Hermes Agent 配置文件

如果 Hermes Agent 支持通过配置文件加载插件:

```yaml
# hermes-config.yaml
plugins:
  - name: skill_approval
    enabled: true
    config:
      interactive_mode: true
      whitelist:
        - sec-rss-news
```

### 方法 2: 程序化集成

```python
from hermes_agent import HermesAgent
from plugins.skill_approval import SkillApprovalPlugin

# 创建 Hermes Agent 实例
agent = HermesAgent()

# 创建并注册审批插件
approval_plugin = SkillApprovalPlugin()
approval_plugin.hook_into_agent(agent)

# 运行 agent
agent.run()
```

### 方法 3: Hook 方式集成

```python
# 如果 Hermes Agent 支持 hook 机制
def before_skill_create_hook(skill_info):
    plugin = SkillApprovalPlugin()
    return plugin.before_skill_create(skill_info)

agent.register_hook('before_skill_create', before_skill_create_hook)
```

## 安全建议 (Security Recommendations)

1. **始终启用交互模式**: 对于生产环境，建议启用 `interactive_mode`
2. **谨慎配置白名单**: 仅将完全信任的技能添加到白名单
3. **审查权限请求**: 在批准前仔细查看技能请求的权限
4. **定期审计日志**: 定期检查审批历史记录
5. **限制可信源**: 仅添加经过验证的源到 `trusted_sources`

## API 参考 (API Reference)

### SkillApprovalPlugin

主插件类。

#### 方法

- `__init__(config: Optional[ApprovalConfig] = None)`: 初始化插件
- `before_skill_create(skill_info: Dict[str, Any]) -> bool`: 技能创建前的钩子
- `after_skill_create(skill_info: Dict[str, Any], success: bool)`: 技能创建后的钩子
- `get_approval_history() -> list`: 获取审批历史
- `hook_into_agent(agent)`: 将插件集成到 agent

### ApprovalHandler

处理用户交互的类。

#### 方法

- `request_approval(skill_info: Dict[str, Any]) -> bool`: 请求单个审批
- `request_batch_approval(skills: list) -> Dict[str, bool]`: 请求批量审批

### ApprovalConfig

配置数据类。

#### 属性

- `interactive_mode: bool`: 是否启用交互模式
- `default_approval: bool`: 非交互模式的默认决策
- `whitelist: List[str]`: 技能白名单
- `trusted_sources: List[str]`: 可信源列表
- `log_approvals: bool`: 是否记录审批
- `approval_log_path: str`: 日志文件路径
- `approval_timeout: int`: 审批超时时间
- `require_update_approval: bool`: 是否对更新也要求审批

## 故障排查 (Troubleshooting)

### 问题: 插件无法加载

**解决方案**: 确保插件目录在 Python 路径中:

```python
import sys
sys.path.append('/path/to/hermes-agent')
```

### 问题: 审批提示未显示

**解决方案**: 确保 `interactive_mode` 已启用:

```python
config = ApprovalConfig(interactive_mode=True)
```

### 问题: 所有技能都被自动批准

**解决方案**: 检查白名单和可信源配置，移除不需要的条目。

## 许可证 (License)

MIT License - 详见 LICENSE 文件

## 贡献 (Contributing)

欢迎提交 Issue 和 Pull Request！

## 联系方式 (Contact)

如有问题或建议，请通过 GitHub Issues 联系。
