"""
Task Router - 任务路由器

将用户故事路由到合适的 Agent 执行
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class TaskCategory(str, Enum):
    """任务类别"""
    FRONTEND = "frontend"      # 前端开发
    BACKEND = "backend"        # 后端开发
    DATABASE = "database"      # 数据库
    API = "api"                # API 开发
    TEST = "test"              # 测试
    DOCS = "docs"              # 文档
    CONFIG = "config"          # 配置
    REFACTOR = "refactor"      # 重构
    UNKNOWN = "unknown"        # 未知


@dataclass
class TaskAnalysis:
    """任务分析结果"""
    category: TaskCategory
    complexity: int  # 1-5
    estimated_time: int  # 分钟
    required_skills: List[str]
    dependencies: List[str]
    suggested_agent: str


class TaskRouter:
    """
    任务路由器
    
    分析用户故事并将其路由到合适的 Agent 配置
    """
    
    # 关键词映射
    CATEGORY_KEYWORDS = {
        TaskCategory.FRONTEND: [
            "ui", "界面", "组件", "页面", "前端", "react", "vue", "html", "css",
            "button", "form", "modal", "dropdown", "table", "chart", "可视化"
        ],
        TaskCategory.BACKEND: [
            "后端", "server", "service", "logic", "business", "处理", "计算",
            "algorithm", "worker", "queue", "job", "task"
        ],
        TaskCategory.DATABASE: [
            "数据库", "表", "schema", "migration", "model", "entity",
            "sql", "query", "index", "column", "field", "关系"
        ],
        TaskCategory.API: [
            "api", "接口", "endpoint", "route", "controller", "handler",
            "rest", "graphql", "grpc", "http", "请求", "响应"
        ],
        TaskCategory.TEST: [
            "测试", "test", "spec", "unit", "integration", "e2e",
            "jest", "pytest", "cypress", "playwright"
        ],
        TaskCategory.DOCS: [
            "文档", "doc", "readme", "注释", "说明", "guide",
            "tutorial", "example", "demo"
        ],
        TaskCategory.CONFIG: [
            "配置", "config", "setting", "env", "environment",
            "docker", "ci", "cd", "deploy", "build"
        ],
        TaskCategory.REFACTOR: [
            "重构", "refactor", "优化", "improve", "cleanup",
            "简化", "性能", "performance"
        ]
    }
    
    def __init__(self):
        pass
    
    def analyze(self, story: Dict[str, Any]) -> TaskAnalysis:
        """
        分析用户故事
        
        Args:
            story: 用户故事数据
            
        Returns:
            任务分析结果
        """
        # 合并标题和描述
        text = f"{story.get('title', '')} {story.get('description', '')}"
        text = text.lower()
        
        # 确定类别
        category = self._determine_category(text)
        
        # 评估复杂度
        complexity = self._assess_complexity(story)
        
        # 估算时间
        estimated_time = self._estimate_time(category, complexity)
        
        # 确定所需技能
        required_skills = self._determine_skills(category, text)
        
        # 提取依赖
        dependencies = self._extract_dependencies(story)
        
        # 推荐 Agent
        suggested_agent = self._suggest_agent(category, complexity)
        
        return TaskAnalysis(
            category=category,
            complexity=complexity,
            estimated_time=estimated_time,
            required_skills=required_skills,
            dependencies=dependencies,
            suggested_agent=suggested_agent
        )
    
    def _determine_category(self, text: str) -> TaskCategory:
        """确定任务类别"""
        scores = {cat: 0 for cat in TaskCategory}
        
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in text:
                    scores[category] += 1
        
        # 返回得分最高的类别
        max_score = max(scores.values())
        if max_score == 0:
            return TaskCategory.UNKNOWN
        
        for cat, score in scores.items():
            if score == max_score:
                return cat
        
        return TaskCategory.UNKNOWN
    
    def _assess_complexity(self, story: Dict[str, Any]) -> int:
        """评估任务复杂度 (1-5)"""
        complexity = 1
        
        # 基于验收标准数量
        criteria = story.get("acceptanceCriteria", [])
        if len(criteria) > 5:
            complexity += 2
        elif len(criteria) > 3:
            complexity += 1
        
        # 基于描述长度
        description = story.get("description", "")
        if len(description) > 500:
            complexity += 1
        
        # 基于关键词
        text = f"{story.get('title', '')} {description}".lower()
        complex_keywords = ["复杂", "集成", "架构", "重构", "优化", "算法"]
        for keyword in complex_keywords:
            if keyword in text:
                complexity += 1
                break
        
        return min(complexity, 5)
    
    def _estimate_time(self, category: TaskCategory, complexity: int) -> int:
        """估算所需时间（分钟）"""
        base_times = {
            TaskCategory.FRONTEND: 60,
            TaskCategory.BACKEND: 90,
            TaskCategory.DATABASE: 45,
            TaskCategory.API: 60,
            TaskCategory.TEST: 45,
            TaskCategory.DOCS: 30,
            TaskCategory.CONFIG: 30,
            TaskCategory.REFACTOR: 75,
            TaskCategory.UNKNOWN: 60
        }
        
        base = base_times.get(category, 60)
        multiplier = 1 + (complexity - 1) * 0.3
        
        return int(base * multiplier)
    
    def _determine_skills(self, category: TaskCategory, text: str) -> List[str]:
        """确定所需技能"""
        skills = []
        
        # 基于类别的基础技能
        category_skills = {
            TaskCategory.FRONTEND: ["React", "TypeScript", "CSS", "UI/UX"],
            TaskCategory.BACKEND: ["Python", "Node.js", "API Design", "Architecture"],
            TaskCategory.DATABASE: ["SQL", "Database Design", "Migrations"],
            TaskCategory.API: ["REST", "API Design", "Authentication"],
            TaskCategory.TEST: ["Testing", "TDD", "Test Design"],
            TaskCategory.DOCS: ["Technical Writing", "Documentation"],
            TaskCategory.CONFIG: ["DevOps", "CI/CD", "Docker"],
            TaskCategory.REFACTOR: ["Code Quality", "Design Patterns"]
        }
        
        skills.extend(category_skills.get(category, []))
        
        # 从文本中提取特定技术
        tech_patterns = {
            "react": "React",
            "vue": "Vue.js",
            "angular": "Angular",
            "typescript": "TypeScript",
            "python": "Python",
            "django": "Django",
            "fastapi": "FastAPI",
            "flask": "Flask",
            "postgresql": "PostgreSQL",
            "mysql": "MySQL",
            "mongodb": "MongoDB",
            "redis": "Redis",
            "docker": "Docker",
            "kubernetes": "Kubernetes",
            "aws": "AWS",
            "azure": "Azure"
        }
        
        for pattern, skill in tech_patterns.items():
            if pattern in text and skill not in skills:
                skills.append(skill)
        
        return skills
    
    def _extract_dependencies(self, story: Dict[str, Any]) -> List[str]:
        """提取依赖项"""
        dependencies = []
        
        # 从描述中提取依赖
        description = story.get("description", "")
        
        # 匹配 "depends on" 或 "依赖" 模式
        import re
        dep_patterns = [
            r'(?:depends?\s+on|依赖|需要)\s*:?\s*([A-Z]+-\d+)',
            r'(?:requires?|需要| prerequisite)\s*:?\s*([A-Z]+-\d+)'
        ]
        
        for pattern in dep_patterns:
            matches = re.findall(pattern, description, re.IGNORECASE)
            dependencies.extend(matches)
        
        return list(set(dependencies))
    
    def _suggest_agent(self, category: TaskCategory, complexity: int) -> str:
        """推荐 Agent 类型"""
        agent_map = {
            TaskCategory.FRONTEND: "FrontendDeveloper",
            TaskCategory.BACKEND: "BackendDeveloper",
            TaskCategory.DATABASE: "DatabaseEngineer",
            TaskCategory.API: "APIEngineer",
            TaskCategory.TEST: "TestEngineer",
            TaskCategory.DOCS: "TechnicalWriter",
            TaskCategory.CONFIG: "DevOpsEngineer",
            TaskCategory.REFACTOR: "CodeRefactorer",
            TaskCategory.UNKNOWN: "FullStackDeveloper"
        }
        
        base_agent = agent_map.get(category, "Developer")
        
        # 高复杂度任务使用高级 Agent
        if complexity >= 4:
            return f"Senior{base_agent}"
        
        return base_agent
    
    def route(self, story: Dict[str, Any]) -> Dict[str, Any]:
        """
        路由任务并返回执行配置
        
        Returns:
            包含分析结果和执行建议的字典
        """
        analysis = self.analyze(story)
        
        return {
            "story": story,
            "analysis": {
                "category": analysis.category.value,
                "complexity": analysis.complexity,
                "estimated_time": analysis.estimated_time,
                "required_skills": analysis.required_skills,
                "dependencies": analysis.dependencies,
                "suggested_agent": analysis.suggested_agent
            },
            "execution_config": self._generate_config(analysis)
        }
    
    def _generate_config(self, analysis: TaskAnalysis) -> Dict[str, Any]:
        """生成执行配置"""
        return {
            "agent_type": analysis.suggested_agent,
            "enable_reflection": analysis.complexity >= 3,
            "enable_guardrails": True,
            "enable_git": True,
            "timeout_minutes": analysis.estimated_time * 2,
            "max_retries": 2 if analysis.complexity >= 4 else 1,
            "required_tools": self._get_tools_for_category(analysis.category)
        }
    
    def _get_tools_for_category(self, category: TaskCategory) -> List[str]:
        """获取类别相关的工具"""
        tools_map = {
            TaskCategory.FRONTEND: ["file_read", "file_write", "shell"],
            TaskCategory.BACKEND: ["file_read", "file_write", "shell", "code_execute"],
            TaskCategory.DATABASE: ["file_read", "file_write", "shell", "database_query"],
            TaskCategory.API: ["file_read", "file_write", "shell", "api_test"],
            TaskCategory.TEST: ["file_read", "shell", "test_runner"],
            TaskCategory.DOCS: ["file_read", "file_write"],
            TaskCategory.CONFIG: ["file_read", "file_write", "shell"],
            TaskCategory.REFACTOR: ["file_read", "file_write", "shell", "code_analyze"]
        }
        
        return tools_map.get(category, ["file_read", "file_write"])
