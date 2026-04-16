"""Output Parser for ActionNode"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Type

from .node import FieldDefinition


class OutputParser(ABC):
    """输出解析器基类"""
    
    @abstractmethod
    def parse(self, content: str, fields: List[FieldDefinition]) -> Dict[str, Any]:
        """解析输出内容"""
        pass


class JSONParser(OutputParser):
    """JSON 解析器"""
    
    def parse(self, content: str, fields: List[FieldDefinition]) -> Dict[str, Any]:
        """解析 JSON 输出"""
        # 尝试直接解析
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        
        # 尝试从 Markdown 代码块中提取
        code_block_pattern = r'```(?:json)?\s*(.*?)```'
        matches = re.findall(code_block_pattern, content, re.DOTALL)
        
        for match in matches:
            try:
                return json.loads(match.strip())
            except json.JSONDecodeError:
                continue
        
        # 尝试从文本中提取键值对
        result = {}
        for field in fields:
            # 尝试匹配 "field_name": value 或 field_name: value
            patterns = [
                rf'["\']?{field.name}["\']?\s*[:=]\s*["\']?([^"\'\n,]+)["\']?',
                rf'{field.name}\s*[:=]\s*(.+?)(?:\n|$)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    # 尝试类型转换
                    try:
                        if field.field_type == int:
                            value = int(value)
                        elif field.field_type == float:
                            value = float(value)
                        elif field.field_type == bool:
                            value = value.lower() in ('true', 'yes', '1')
                        elif field.field_type == list:
                            # 尝试解析列表
                            try:
                                value = json.loads(value)
                            except:
                                value = [v.strip() for v in value.split(',')]
                        elif field.field_type == dict:
                            try:
                                value = json.loads(value)
                            except:
                                pass
                    except:
                        pass
                    
                    result[field.name] = value
                    break
        
        return result


class MarkdownParser(OutputParser):
    """Markdown 解析器"""
    
    def parse(self, content: str, fields: List[FieldDefinition]) -> Dict[str, Any]:
        """解析 Markdown 输出"""
        result = {}
        
        # 按标题分割
        sections = re.split(r'\n##?\s+', content)
        
        for field in fields:
            # 查找对应章节
            field_name_lower = field.name.lower().replace('_', ' ')
            
            for section in sections:
                section_lower = section.lower()
                if section_lower.startswith(field_name_lower):
                    # 提取内容（去掉标题）
                    lines = section.split('\n', 1)
                    if len(lines) > 1:
                        result[field.name] = lines[1].strip()
                    else:
                        result[field.name] = ""
                    break
            
            # 如果没找到，尝试其他模式
            if field.name not in result:
                # 查找 **field_name**: value 模式
                pattern = rf'\*\*{field.name}\*\*\s*[:=]\s*(.+?)(?:\n\n|\n\*\*|$)'
                match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
                if match:
                    result[field.name] = match.group(1).strip()
        
        return result


class XMLParser(OutputParser):
    """XML 解析器"""
    
    def parse(self, content: str, fields: List[FieldDefinition]) -> Dict[str, Any]:
        """解析 XML 输出"""
        result = {}
        
        for field in fields:
            # 查找 <field_name>...</field_name>
            pattern = rf'<{field.name}>(.*?)</{field.name}>'
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            
            if match:
                value = match.group(1).strip()
                # 尝试类型转换
                try:
                    if field.field_type == int:
                        value = int(value)
                    elif field.field_type == float:
                        value = float(value)
                    elif field.field_type == bool:
                        value = value.lower() in ('true', 'yes', '1')
                    elif field.field_type in (list, dict):
                        value = json.loads(value)
                except:
                    pass
                
                result[field.name] = value
        
        return result


class AutoParser(OutputParser):
    """自动解析器
    
    自动检测格式并解析
    """
    
    def __init__(self):
        self.parsers = {
            'json': JSONParser(),
            'markdown': MarkdownParser(),
            'xml': XMLParser(),
        }
    
    def detect_format(self, content: str) -> str:
        """检测内容格式"""
        content_stripped = content.strip()
        
        # 检查 JSON
        if content_stripped.startswith(('{', '[')):
            return 'json'
        
        # 检查 XML
        if content_stripped.startswith('<'):
            return 'xml'
        
        # 检查 Markdown
        if '```' in content or content_stripped.startswith('#'):
            return 'markdown'
        
        # 默认 Markdown
        return 'markdown'
    
    def parse(self, content: str, fields: List[FieldDefinition]) -> Dict[str, Any]:
        """自动解析"""
        format_type = self.detect_format(content)
        parser = self.parsers.get(format_type, self.parsers['markdown'])
        return parser.parse(content, fields)
