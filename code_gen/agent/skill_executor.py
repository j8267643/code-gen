"""
Skill Executor - 执行匹配的技能

技能系统的工作流程：
1. 用户输入 -> 匹配技能
2. 匹配技能 -> 执行技能
3. 执行结果 -> 返回给用户
"""
import asyncio
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum

from .skills import Skill, SkillSystem


class SkillResultStatus(Enum):
    """技能执行结果状态"""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    SKIPPED = "skipped"


@dataclass
class SkillResult:
    """技能执行结果"""
    skill_name: str
    status: SkillResultStatus
    output: str
    data: Dict[str, Any] = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0


class SkillExecutor:
    """
    技能执行器

    负责执行匹配的技能，支持：
    - 内置技能函数
    - 外部命令执行
    - Python 脚本执行
    - 异步执行
    """

    def __init__(self, skill_system: SkillSystem):
        self.skill_system = skill_system
        self.builtin_skills: Dict[str, Callable] = {}
        self._register_builtin_skills()

    def _register_builtin_skills(self):
        """注册内置技能"""
        self.builtin_skills['code_review'] = self._skill_code_review
        self.builtin_skills['git_commit'] = self._skill_git_commit
        self.builtin_skills['code_search'] = self._skill_code_search
        self.builtin_skills['file_read'] = self._skill_file_read
        self.builtin_skills['file_write'] = self._skill_file_write

    async def execute_skill(self, skill: Skill, context: Dict[str, Any] = None) -> SkillResult:
        """
        执行单个技能

        Args:
            skill: 要执行的技能
            context: 执行上下文（用户输入、当前文件等）

        Returns:
            SkillResult: 执行结果
        """
        import time
        start_time = time.time()
        context = context or {}

        try:
            # 1. 检查是否是内置技能
            if skill.name in self.builtin_skills:
                result = await self.builtin_skills[skill.name](skill, context)
                result.execution_time_ms = (time.time() - start_time) * 1000
                return result

            # 2. 检查技能文件是否存在
            skill_path = Path(skill.path)
            if skill_path.exists():
                # 从文件加载并执行
                result = await self._execute_from_file(skill, context)
                result.execution_time_ms = (time.time() - start_time) * 1000
                return result

            # 3. 使用默认执行方式
            result = await self._default_execute(skill, context)
            result.execution_time_ms = (time.time() - start_time) * 1000
            return result

        except Exception as e:
            return SkillResult(
                skill_name=skill.name,
                status=SkillResultStatus.FAILED,
                output="",
                error=str(e),
                execution_time_ms=(time.time() - start_time) * 1000
            )

    async def execute_matching_skills(
        self,
        user_input: str,
        context: Dict[str, Any] = None
    ) -> List[SkillResult]:
        """
        执行所有匹配的技能

        Args:
            user_input: 用户输入
            context: 执行上下文

        Returns:
            List[SkillResult]: 所有执行结果
        """
        # 匹配技能
        matching_skills = self.skill_system.get_matching_skills(user_input)

        if not matching_skills:
            return []

        # 执行所有匹配的技能
        results = []
        for skill in matching_skills:
            if skill.enabled:
                ctx = {**(context or {}), 'user_input': user_input}
                result = await self.execute_skill(skill, ctx)
                results.append(result)

        return results

    # ===== 内置技能实现 =====

    async def _skill_code_review(self, skill: Skill, context: Dict) -> SkillResult:
        """代码审查技能"""
        user_input = context.get('user_input', '')

        # 提取文件路径
        import re
        file_match = re.search(r'(\S+\.(py|js|ts|java|cpp|c|h|go|rs))', user_input)

        if file_match:
            file_path = file_match.group(1)
            path_obj = Path(file_path)

            # 尝试多个路径
            if not path_obj.exists():
                # 尝试在当前工作目录下查找
                cwd_path = Path.cwd() / file_path
                if cwd_path.exists():
                    path_obj = cwd_path
                else:
                    # 尝试在 code_gen 目录下查找
                    code_gen_path = Path.cwd() / 'code_gen' / file_path
                    if code_gen_path.exists():
                        path_obj = code_gen_path

            if not path_obj.exists():
                return SkillResult(
                    skill_name=skill.name,
                    status=SkillResultStatus.SKIPPED,
                    output=f"文件不存在: {file_path}",
                    data={'reason': 'file_not_found', 'file': file_path}
                )

            try:
                content = path_obj.read_text(encoding='utf-8')

                # 简单的代码审查逻辑
                issues = []
                lines = content.split('\n')

                for i, line in enumerate(lines, 1):
                    # 检查长行
                    if len(line) > 100:
                        issues.append(f"Line {i}: 行太长 ({len(line)} 字符)")
                    # 检查 TODO
                    if 'TODO' in line:
                        issues.append(f"Line {i}: 发现 TODO")
                    # 检查 print/debug
                    if 'print(' in line or 'console.log(' in line:
                        issues.append(f"Line {i}: 发现调试代码")

                output = f"代码审查结果 ({file_path}):\n"
                if issues:
                    output += "\n".join(f"- {issue}" for issue in issues[:10])
                    if len(issues) > 10:
                        output += f"\n... 还有 {len(issues) - 10} 个问题"
                else:
                    output += "未发现明显问题"

                return SkillResult(
                    skill_name=skill.name,
                    status=SkillResultStatus.SUCCESS,
                    output=output,
                    data={'file': file_path, 'issues_count': len(issues)}
                )

            except Exception as e:
                return SkillResult(
                    skill_name=skill.name,
                    status=SkillResultStatus.FAILED,
                    output="",
                    error=f"无法读取文件: {e}"
                )

        return SkillResult(
            skill_name=skill.name,
            status=SkillResultStatus.SKIPPED,
            output="未找到代码文件路径",
            data={'reason': 'no_file_path'}
        )

    async def _skill_git_commit(self, skill: Skill, context: Dict) -> SkillResult:
        """Git 提交技能"""
        try:
            # 获取 git 状态
            result = subprocess.run(
                ['git', 'status', '--short'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return SkillResult(
                    skill_name=skill.name,
                    status=SkillResultStatus.FAILED,
                    output="",
                    error="无法获取 git 状态"
                )

            changes = result.stdout.strip()
            if not changes:
                return SkillResult(
                    skill_name=skill.name,
                    status=SkillResultStatus.SUCCESS,
                    output="没有待提交的更改",
                    data={'changes': []}
                )

            # 生成提交信息建议
            files = [line.strip() for line in changes.split('\n') if line.strip()]
            suggestions = self._generate_commit_suggestions(files)

            output = f"待提交更改 ({len(files)} 个文件):\n{changes}\n\n"
            output += "提交信息建议:\n" + "\n".join(f"- {s}" for s in suggestions)

            return SkillResult(
                skill_name=skill.name,
                status=SkillResultStatus.SUCCESS,
                output=output,
                data={'files': files, 'suggestions': suggestions}
            )

        except Exception as e:
            return SkillResult(
                skill_name=skill.name,
                status=SkillResultStatus.FAILED,
                output="",
                error=str(e)
            )

    async def _skill_code_search(self, skill: Skill, context: Dict) -> SkillResult:
        """代码搜索技能"""
        user_input = context.get('user_input', '')

        # 提取搜索关键词
        import re
        # 匹配 "search for X" 或 "find X" 或 "look for X"
        patterns = [
            r'search\s+(?:for\s+)?["\']?([^"\']+)["\']?',
            r'find\s+["\']?([^"\']+)["\']?',
            r'look\s+(?:for\s+)?["\']?([^"\']+)["\']?',
        ]

        query = None
        for pattern in patterns:
            match = re.search(pattern, user_input, re.IGNORECASE)
            if match:
                query = match.group(1)
                break

        if not query:
            return SkillResult(
                skill_name=skill.name,
                status=SkillResultStatus.SKIPPED,
                output="未找到搜索关键词",
                data={'reason': 'no_query'}
            )

        # 在当前目录搜索
        try:
            # 使用简单的文件搜索，不依赖 SearchTools
            results = []
            search_path = Path('.')

            for py_file in search_path.rglob('*.py'):
                try:
                    content = py_file.read_text(encoding='utf-8', errors='ignore')
                    if query in content:
                        # 找到匹配，记录前5行
                        lines = content.split('\n')
                        for i, line in enumerate(lines, 1):
                            if query in line:
                                results.append({
                                    'file': str(py_file),
                                    'line': i,
                                    'content': line.strip()
                                })
                                if len(results) >= 10:
                                    break
                        if len(results) >= 10:
                            break
                except:
                    continue

            output = f"搜索 '{query}' 的结果:\n"
            if results:
                for r in results[:5]:
                    output += f"\n{r['file']}:{r['line']}\n  {r['content'][:100]}...\n"
                if len(results) > 5:
                    output += f"\n... 还有 {len(results) - 5} 个结果"
            else:
                output += "未找到匹配结果"

            return SkillResult(
                skill_name=skill.name,
                status=SkillResultStatus.SUCCESS,
                output=output,
                data={'query': query, 'results_count': len(results)}
            )

        except Exception as e:
            return SkillResult(
                skill_name=skill.name,
                status=SkillResultStatus.FAILED,
                output="",
                error=str(e)
            )

    async def _skill_file_read(self, skill: Skill, context: Dict) -> SkillResult:
        """文件读取技能"""
        user_input = context.get('user_input', '')

        # 提取文件路径
        import re
        file_match = re.search(r'read\s+(?:file\s+)?["\']?(\S+)["\']?', user_input, re.IGNORECASE)

        if file_match:
            file_path = file_match.group(1)
            try:
                content = Path(file_path).read_text(encoding='utf-8')
                return SkillResult(
                    skill_name=skill.name,
                    status=SkillResultStatus.SUCCESS,
                    output=f"文件内容 ({file_path}):\n```\n{content[:2000]}\n```",
                    data={'file': file_path, 'size': len(content)}
                )
            except Exception as e:
                return SkillResult(
                    skill_name=skill.name,
                    status=SkillResultStatus.FAILED,
                    output="",
                    error=f"无法读取文件: {e}"
                )

        return SkillResult(
            skill_name=skill.name,
            status=SkillResultStatus.SKIPPED,
            output="未找到文件路径",
            data={'reason': 'no_file_path'}
        )

    async def _skill_file_write(self, skill: Skill, context: Dict) -> SkillResult:
        """文件写入技能"""
        # 这是一个示例实现，实际使用时需要更多参数
        return SkillResult(
            skill_name=skill.name,
            status=SkillResultStatus.SKIPPED,
            output="文件写入技能需要更多参数",
            data={'reason': 'needs_more_params'}
        )

    # ===== 辅助方法 =====

    def _generate_commit_suggestions(self, files: List[str]) -> List[str]:
        """生成提交信息建议"""
        suggestions = []

        # 根据文件类型生成建议
        has_py = any(f.endswith('.py') for f in files)
        has_js = any(f.endswith('.js') or f.endswith('.ts') for f in files)
        has_test = any('test' in f.lower() for f in files)
        has_doc = any(f.endswith('.md') or f.endswith('.rst') for f in files)

        if has_test:
            suggestions.append("Add/update tests")
        if has_doc:
            suggestions.append("Update documentation")
        if has_py:
            suggestions.append("Update Python code")
        if has_js:
            suggestions.append("Update JavaScript/TypeScript code")

        if not suggestions:
            suggestions.append("Update files")

        suggestions.append(f"Update {len(files)} files")

        return suggestions

    async def _execute_from_file(self, skill: Skill, context: Dict) -> SkillResult:
        """从技能文件执行"""
        try:
            content = Path(skill.path).read_text(encoding='utf-8')

            # 解析技能文件中的执行逻辑
            # 这里可以实现更复杂的解析

            return SkillResult(
                skill_name=skill.name,
                status=SkillResultStatus.SUCCESS,
                output=f"执行技能: {skill.name}\n{content[:500]}...",
                data={'skill_path': skill.path}
            )

        except Exception as e:
            return SkillResult(
                skill_name=skill.name,
                status=SkillResultStatus.FAILED,
                output="",
                error=str(e)
            )

    async def _default_execute(self, skill: Skill, context: Dict) -> SkillResult:
        """默认执行方式"""
        return SkillResult(
            skill_name=skill.name,
            status=SkillResultStatus.SUCCESS,
            output=f"技能 '{skill.name}' 已匹配\n描述: {skill.description}\n模式: {skill.patterns}\n命令: {skill.commands}",
            data={'skill': skill.to_dict()}
        )


# ===== 集成到 App =====

class SkillEnhancedApp:
    """
    增强版 App，集成技能执行

    使用示例:
        app = SkillEnhancedApp()
        await app.process_message("review my code in main.py")
        # 会自动匹配并执行 code_review 技能
    """

    def __init__(self, skill_system: SkillSystem):
        self.skill_system = skill_system
        self.skill_executor = SkillExecutor(skill_system)

    async def process_with_skills(self, user_input: str) -> str:
        """
        处理用户输入，执行匹配的技能

        Returns:
            str: 技能执行结果，如果没有匹配技能则返回空字符串
        """
        results = await self.skill_executor.execute_matching_skills(user_input)

        if not results:
            return ""

        # 组合所有技能的结果
        output_parts = []
        for result in results:
            if result.status == SkillResultStatus.SUCCESS:
                output_parts.append(f"## {result.skill_name}\n{result.output}")
            elif result.status == SkillResultStatus.FAILED:
                output_parts.append(f"## {result.skill_name} (失败)\n错误: {result.error}")

        return "\n\n".join(output_parts)
