"""
PRD Parser - PRD 解析器

将 Markdown PRD 转换为结构化数据
"""
import re
from typing import Dict, Any, List
from pathlib import Path
from dataclasses import dataclass, field

from .models import PRDData, UserStory


class PRDParser:
    """PRD 解析器"""
    
    def __init__(self):
        self.story_counter = 0
    
    def parse(self, prd_path: Path) -> PRDData:
        """
        解析 PRD Markdown 文件
        
        Args:
            prd_path: PRD 文件路径
            
        Returns:
            PRDData 对象
        """
        with open(prd_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取项目信息
        project = self._extract_project_name(content)
        description = self._extract_description(content)
        
        # 提取用户故事
        stories = self._extract_user_stories(content)
        
        # 生成分支名
        branch_name = self._generate_branch_name(project)
        
        return PRDData(
            project=project,
            branch_name=branch_name,
            description=description,
            user_stories=[s.to_dict() for s in stories],
            metadata={
                "source_file": str(prd_path),
                "parsed_at": "auto"
            }
        )
    
    def _extract_project_name(self, content: str) -> str:
        """提取项目名称"""
        # 匹配 # PRD: 或 # 开头的标题
        match = re.search(r'#\s*PRD[:\s]*(.+)', content, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # 尝试匹配第一个 # 标题
        match = re.search(r'#\s*(.+)', content)
        if match:
            return match.group(1).strip()
        
        return "Unknown Project"
    
    def _extract_description(self, content: str) -> str:
        """提取描述"""
        # 匹配概述部分
        match = re.search(r'##\s*概述\s*\n(.+?)(?=##|$)', content, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # 匹配 Introduction/Overview
        match = re.search(r'##\s*(?:Introduction|Overview)\s*\n(.+?)(?=##|$)', content, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        return ""
    
    def _extract_user_stories(self, content: str) -> List[UserStory]:
        """提取用户故事"""
        stories = []
        
        # 匹配用户故事部分
        story_sections = re.findall(
            r'###\s*(US-\d+|\[.+?\]):?\s*(.+?)\n(.+?)(?=###|##\s|$)',
            content,
            re.DOTALL
        )
        
        for i, (story_id, title, section) in enumerate(story_sections, 1):
            # 如果没有 ID，生成一个
            if not story_id.startswith("US-"):
                story_id = f"US-{i:03d}"
            
            # 提取描述
            description = self._extract_story_description(section)
            
            # 提取验收标准
            acceptance_criteria = self._extract_acceptance_criteria(section)
            
            # 提取优先级
            priority = self._extract_priority(section)
            
            story = UserStory(
                id=story_id,
                title=title.strip(),
                description=description,
                acceptance_criteria=acceptance_criteria,
                priority=priority
            )
            stories.append(story)
        
        # 如果没有找到标准格式的故事，尝试其他模式
        if not stories:
            stories = self._extract_stories_alternative(content)
        
        return stories
    
    def _extract_story_description(self, section: str) -> str:
        """提取故事描述"""
        # 匹配描述部分
        match = re.search(r'\*\*描述\*\*[:\s]*(.+?)(?=\*\*|$)', section, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # 匹配 Description
        match = re.search(r'\*\*Description\*\*[:\s]*(.+?)(?=\*\*|$)', section, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # 匹配 "As a..." 格式
        match = re.search(r'(As\s+a\[?n?\]?\s*.+?so\s+that\s*.+?)(?=\n|$)', section, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        return ""
    
    def _extract_acceptance_criteria(self, section: str) -> List[str]:
        """提取验收标准"""
        criteria = []
        
        # 匹配验收标准部分
        match = re.search(
            r'\*\*验收标准\*\*[:\s]*\n(.+?)(?=\*\*|###|##\s|$)',
            section,
            re.DOTALL
        )
        if match:
            criteria_text = match.group(1)
            # 提取列表项
            items = re.findall(r'[-\*]\s*\[?\s*\]?\s*(.+)', criteria_text)
            criteria = [item.strip() for item in items if item.strip()]
        
        # 匹配 Acceptance Criteria
        match = re.search(
            r'\*\*Acceptance\s*Criteria\*\*[:\s]*\n(.+?)(?=\*\*|###|##\s|$)',
            section,
            re.DOTALL | re.IGNORECASE
        )
        if match and not criteria:
            criteria_text = match.group(1)
            items = re.findall(r'[-\*]\s*\[?\s*\]?\s*(.+)', criteria_text)
            criteria = [item.strip() for item in items if item.strip()]
        
        return criteria
    
    def _extract_priority(self, section: str) -> int:
        """提取优先级"""
        match = re.search(r'\*\*优先级\*\*[:\s]*(\d+)', section)
        if match:
            return int(match.group(1))
        
        match = re.search(r'\*\*Priority\*\*[:\s]*(\d+)', section, re.IGNORECASE)
        if match:
            return int(match.group(1))
        
        return 1
    
    def _extract_stories_alternative(self, content: str) -> List[UserStory]:
        """备选故事提取方法"""
        stories = []
        
        # 尝试匹配任何看起来像故事的段落
        story_patterns = [
            r'\*\*用户故事\s*(\d+)\*\*[:\s]*(.+?)(?=\*\*用户故事|$)',
            r'故事\s*(\d+)[:\s]*(.+?)(?=故事\s*\d+|$)',
        ]
        
        for pattern in story_patterns:
            matches = re.findall(pattern, content, re.DOTALL)
            for i, (num, text) in enumerate(matches, 1):
                story = UserStory(
                    id=f"US-{i:03d}",
                    title=f"Story {num}",
                    description=text.strip()[:200],
                    acceptance_criteria=["实现功能", "测试通过"],
                    priority=i
                )
                stories.append(story)
            
            if stories:
                break
        
        return stories
    
    def _generate_branch_name(self, project: str) -> str:
        """生成分支名"""
        # 清理项目名称
        clean_name = re.sub(r'[^\w\s-]', '', project.lower())
        clean_name = re.sub(r'[-\s]+', '-', clean_name)
        clean_name = clean_name[:50]  # 限制长度
        
        return f"ralph/{clean_name}"
