"""
AutoDev Core - 自主开发系统核心
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
import json
import asyncio

from code_gen.agents.unified_agent import UnifiedAgent, UnifiedAgentConfig
from code_gen.agents.agent import Agent
from code_gen.agents.memory import MemorySystem
from code_gen.agents.git_integration import GitIntegration, GitConfig
from code_gen.client import AIClient

from .models import PRDData


@dataclass
class AutoDevConfig:
    """自主开发配置"""
    work_dir: Path
    
    # PRD 配置
    prd_dir: Path = field(default=None)
    prd_json_path: Path = field(default=None)
    
    # 进度跟踪
    progress_file: Path = field(default=None)
    state_file: Path = field(default=None)
    
    # 执行配置
    auto_commit: bool = True
    max_iterations: int = 100
    stop_on_error: bool = False
    
    # Agent 配置
    agent_config: Optional[UnifiedAgentConfig] = None
    
    def __post_init__(self):
        if self.prd_dir is None:
            self.prd_dir = self.work_dir / "tasks"
        if self.prd_json_path is None:
            self.prd_json_path = self.work_dir / ".code-gen" / "prd.json"
        if self.progress_file is None:
            self.progress_file = self.work_dir / ".code-gen" / "progress.txt"
        if self.state_file is None:
            self.state_file = self.work_dir / ".code-gen" / "autodev_state.json"
        
        # 确保目录存在
        self.prd_dir.mkdir(parents=True, exist_ok=True)
        self.prd_json_path.parent.mkdir(parents=True, exist_ok=True)


class AutoDevIntegration:
    """
    自主开发集成主类
    
    将自主开发能力集成到 Code-Gen 框架中
    """
    
    def __init__(self, config: AutoDevConfig):
        self.config = config
        self.prd_data: Optional[PRDData] = None
        self.current_story_index: int = 0
        self.client: Optional[AIClient] = None
        self.agent: Optional[UnifiedAgent] = None
        self.git: Optional[GitIntegration] = None
        try:
            self._load_state()
        except Exception as e:
            print(f"⚠️  加载状态失败: {e}")
            self.current_story_index = 0
    
    def _load_state(self):
        """加载持久化状态"""
        if self.config.state_file.exists():
            with open(self.config.state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
                self.current_story_index = state.get("current_story_index", 0)
    
    def _save_state(self):
        """保存状态"""
        state = {
            "current_story_index": self.current_story_index,
            "timestamp": datetime.now().isoformat(),
            "prd_loaded": self.prd_data is not None
        }
        with open(self.config.state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    
    async def initialize(self):
        """初始化组件"""
        # 初始化 AI 客户端
        try:
            self.client = AIClient()
        except ValueError as e:
            raise RuntimeError(
                f"AI 客户端初始化失败: {e}\n"
                f"请确保已配置 API 密钥环境变量或 .env 文件"
            ) from e
        except Exception as e:
            raise RuntimeError(
                f"AI 客户端初始化时发生未知错误: {e}"
            ) from e
        
        # 初始化 UnifiedAgent
        agent_cfg = self.config.agent_config or UnifiedAgentConfig(
            name="AutoDevExecutor",
            agent_id=f"autodev_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            enable_reflection=True,
            enable_guardrails=True,
            enable_git=self.config.auto_commit,
            verbose=True
        )
        self.agent = UnifiedAgent(Agent(), agent_cfg)
        
        # 初始化 Git 集成
        if self.config.auto_commit:
            git_config = GitConfig(
                auto_commit="on_success",
                repo_path=str(self.config.work_dir)
            )
            self.git = GitIntegration(git_config)
        
        # 加载 PRD
        if self.config.prd_json_path.exists():
            with open(self.config.prd_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.prd_data = PRDData.from_json(data)
    
    def create_prd(self, feature_description: str) -> Path:
        """
        创建 PRD 模板文件
        
        Args:
            feature_description: 功能描述
            
        Returns:
            PRD 文件路径
        """
        # 生成文件名
        feature_slug = feature_description.lower().replace(" ", "-")[:50]
        prd_path = self.config.prd_dir / f"prd-{feature_slug}.md"
        
        # 创建 PRD 模板
        prd_template = f"""# PRD: {feature_description}

## 概述
{feature_description}

## 目标
- [ ] 目标 1
- [ ] 目标 2
- [ ] 目标 3

## 用户故事

### US-001: [故事标题]
**描述**: 作为 [用户角色]，我想要 [功能]，以便 [价值]

**验收标准**:
- [ ] 标准 1
- [ ] 标准 2
- [ ] 标准 3
- [ ] 类型检查通过
- [ ] 测试通过

**优先级**: 1
**状态**: 待办

---

## 技术方案

### 架构
[描述技术架构]

### 数据模型
[描述数据模型]

### API 设计
[描述 API]

## 非功能需求
- 性能要求
- 安全要求
- 兼容性要求

## 风险与缓解
| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 风险1 | 高 | 措施1 |

## 参考资料
- [链接1]
- [链接2]
"""
        
        with open(prd_path, 'w', encoding='utf-8') as f:
            f.write(prd_template)
        
        return prd_path
    
    def convert_prd(self, prd_path: Path) -> PRDData:
        """
        将 Markdown PRD 转换为 prd.json
        
        实际项目中，这里应该使用 LLM 解析 PRD
        简化版本：解析基本结构
        """
        from .prd_parser import PRDParser
        
        parser = PRDParser()
        self.prd_data = parser.parse(prd_path)
        
        # 保存为 JSON
        with open(self.config.prd_json_path, 'w', encoding='utf-8') as f:
            json.dump(self.prd_data.to_json(), f, indent=2, ensure_ascii=False)
        
        return self.prd_data
    
    def get_next_story(self) -> Optional[Dict[str, Any]]:
        """获取下一个待执行的用户故事"""
        if not self.prd_data:
            return None
        
        stories = self.prd_data.user_stories
        
        # 按优先级排序
        stories = sorted(stories, key=lambda x: x.get("priority", 999))
        
        # 找到第一个未完成的
        for i, story in enumerate(stories):
            if not story.get("passes", False):
                self.current_story_index = i
                return story
        
        return None
    
    async def execute_story(self, story: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行单个用户故事
        
        Args:
            story: 用户故事数据
            
        Returns:
            执行结果
        """
        story_id = story.get("id", "unknown")
        story_title = story.get("title", "Untitled")
        
        print(f"\n🎯 执行用户故事: {story_id} - {story_title}")
        
        # 构建任务描述
        task = self._build_task_from_story(story)
        
        # 使用 UnifiedAgent 执行
        if self.agent:
            result = await self.agent.execute(task)
        else:
            result = {"success": False, "error": "Agent 未初始化"}
        
        # 更新故事状态
        story["passes"] = result.get("success", False)
        if result.get("success"):
            story["notes"] = f"完成于 {datetime.now().isoformat()}"
        else:
            story["notes"] = f"失败: {result.get('error', 'Unknown error')}"
        
        # 保存进度
        self._save_progress(story, result)
        self._save_prd()
        
        return result
    
    def _build_task_from_story(self, story: Dict[str, Any]) -> str:
        """从用户故事构建任务描述"""
        story_id = story.get("id", "unknown")
        title = story.get("title", "")
        description = story.get("description", "")
        acceptance_criteria = story.get("acceptanceCriteria", [])
        
        task = f"""# 用户故事: {story_id} - {title}

## 描述
{description}

## 验收标准
"""
        for criterion in acceptance_criteria:
            task += f"- {criterion}\n"
        
        task += """
## 要求
1. 实现上述功能
2. 确保所有验收标准通过
3. 遵循项目的代码规范
4. 完成后提交更改
"""
        
        return task
    
    def _save_progress(self, story: Dict[str, Any], result: Dict[str, Any]):
        """保存执行进度"""
        progress_entry = f"""
## {datetime.now().isoformat()} - {story.get('id', 'unknown')}
- 故事: {story.get('title', 'Untitled')}
- 状态: {'✅ 完成' if result.get('success') else '❌ 失败'}
- 输出: {result.get('output', 'N/A')[:200]}
- 学习点:
  - [记录代码库模式]
  - [记录遇到的问题]
---
"""
        
        with open(self.config.progress_file, 'a', encoding='utf-8') as f:
            f.write(progress_entry)
    
    def _save_prd(self):
        """保存更新后的 PRD"""
        if self.prd_data:
            with open(self.config.prd_json_path, 'w', encoding='utf-8') as f:
                json.dump(self.prd_data.to_json(), f, indent=2, ensure_ascii=False)
    
    async def run(self) -> Dict[str, Any]:
        """
        运行自主开发执行循环
        
        Returns:
            执行统计
        """
        if not self.prd_data:
            return {"success": False, "error": "没有加载 PRD"}
        
        stats = {
            "total": len(self.prd_data.user_stories),
            "completed": 0,
            "failed": 0,
            "skipped": 0
        }
        
        iteration = 0
        while iteration < self.config.max_iterations:
            story = self.get_next_story()
            
            if not story:
                print("\n✨ 所有用户故事已完成！")
                break
            
            result = await self.execute_story(story)
            
            if result.get("success"):
                stats["completed"] += 1
            else:
                stats["failed"] += 1
                if self.config.stop_on_error:
                    print(f"\n❌ 执行失败，停止循环")
                    break
            
            self._save_state()
            iteration += 1
            
            # 短暂暂停，避免过快执行
            await asyncio.sleep(1)
        
        return {
            "success": stats["failed"] == 0,
            "stats": stats,
            "message": f"完成 {stats['completed']}/{stats['total']} 个故事"
        }
    
    def status(self) -> Dict[str, Any]:
        """获取当前状态"""
        if not self.prd_data:
            return {"status": "未初始化", "prd_loaded": False}
        
        total = len(self.prd_data.user_stories)
        completed = sum(1 for s in self.prd_data.user_stories if s.get("passes", False))
        
        return {
            "status": "运行中" if completed < total else "已完成",
            "prd_loaded": True,
            "project": self.prd_data.project,
            "branch": self.prd_data.branch_name,
            "progress": f"{completed}/{total}",
            "percentage": (completed / total * 100) if total > 0 else 0,
            "current_story": self.current_story_index
        }
