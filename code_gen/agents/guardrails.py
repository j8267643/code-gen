"""
Guardrails System - 护栏/验证系统
Inspired by PraisonAI's Guardrails

为 AI Agent 输出提供验证和质量保证：
1. 格式验证 - JSON、XML、代码格式
2. 安全验证 - 敏感信息、危险代码检测
3. 内容验证 - 长度、关键词、正则匹配
4. 质量验证 - 重复、完整性检查
5. 自定义验证 - 支持自定义验证函数
"""
from typing import Dict, Any, List, Optional, Callable, Union, Tuple, Pattern
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import json
import re
import ast
from pathlib import Path


class ValidationResult(Enum):
    """验证结果"""
    PASSED = "passed"           # 通过
    FAILED = "failed"           # 失败
    WARNING = "warning"         # 警告
    ERROR = "error"             # 错误


@dataclass
class GuardrailResult:
    """护栏验证结果"""
    success: bool
    result: Union[str, Dict, Any]  # 验证后的结果
    error: Optional[str] = None     # 错误信息
    details: Dict[str, Any] = field(default_factory=dict)
    validator_name: str = ""        # 验证器名称
    
    def __bool__(self):
        return self.success


class BaseValidator(ABC):
    """验证器基类"""
    
    def __init__(self, name: str, fail_action: str = "error"):
        """
        Args:
            name: 验证器名称
            fail_action: 失败处理方式 - "error"(报错), "warning"(警告), "fix"(尝试修复)
        """
        self.name = name
        self.fail_action = fail_action
    
    @abstractmethod
    def validate(self, output: str, context: Optional[Dict] = None) -> GuardrailResult:
        """执行验证"""
        pass
    
    def __call__(self, output: str, context: Optional[Dict] = None) -> GuardrailResult:
        """便捷调用方式"""
        return self.validate(output, context)


# ========== 格式验证器 ==========

class JSONValidator(BaseValidator):
    """JSON 格式验证器"""
    
    def __init__(self, required_fields: Optional[List[str]] = None, 
                 field_types: Optional[Dict[str, type]] = None):
        super().__init__("JSONValidator")
        self.required_fields = required_fields or []
        self.field_types = field_types or {}
    
    def _extract_json(self, text: str) -> str:
        """从文本中提取 JSON 字符串"""
        # 尝试找 ```json 代码块
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            return match.group(1)
        
        # 尝试找 ``` 代码块
        match = re.search(r'```\s*(\{.*?\})\s*```', text, re.DOTALL)
        if match:
            return match.group(1)
        
        # 尝试找 {} 包裹的内容
        match = re.search(r'(\{.*\})', text, re.DOTALL)
        if match:
            return match.group(1)
        
        # 如果没有找到特定格式，返回原文本
        return text
    
    def validate(self, output: str, context: Optional[Dict] = None) -> GuardrailResult:
        """验证 JSON 格式"""
        try:
            # 尝试提取 JSON
            json_str = self._extract_json(output)
            data = json.loads(json_str)
            
            # 检查必需字段
            for field in self.required_fields:
                if field not in data:
                    return GuardrailResult(
                        success=False,
                        result=output,
                        error=f"缺少必需字段: {field}",
                        validator_name=self.name
                    )
            
            # 检查字段类型
            for field, expected_type in self.field_types.items():
                if field in data and not isinstance(data[field], expected_type):
                    return GuardrailResult(
                        success=False,
                        result=output,
                        error=f"字段 {field} 类型错误，期望 {expected_type.__name__}",
                        validator_name=self.name
                    )
            
            return GuardrailResult(
                success=True,
                result=data,
                details={"parsed": True, "fields": list(data.keys())},
                validator_name=self.name
            )
            
        except json.JSONDecodeError as e:
            return GuardrailResult(
                success=False,
                result=output,
                error=f"JSON 解析错误: {str(e)}",
                validator_name=self.name
            )


class CodeSyntaxValidator(BaseValidator):
    """代码语法验证器"""
    
    def __init__(self, language: str = "python"):
        super().__init__("CodeSyntaxValidator")
        self.language = language.lower()
    
    def validate(self, output: str, context: Optional[Dict] = None) -> GuardrailResult:
        """验证代码语法"""
        # 提取代码
        code = self._extract_code(output)
        
        if self.language == "python":
            return self._validate_python(code)
        elif self.language in ["javascript", "js"]:
            return self._validate_javascript(code)
        else:
            return GuardrailResult(
                success=True,
                result=output,
                details={"warning": f"不支持 {self.language} 语法检查"},
                validator_name=self.name
            )
    
    def _extract_code(self, text: str) -> str:
        """提取代码块"""
        # 匹配 ```language ... ```
        pattern = r'```(?:\w+)?\s*(.*?)\s*```'
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1)
        return text
    
    def _validate_python(self, code: str) -> GuardrailResult:
        """验证 Python 语法"""
        try:
            ast.parse(code)
            return GuardrailResult(
                success=True,
                result=code,
                details={"language": "python", "valid": True},
                validator_name=self.name
            )
        except SyntaxError as e:
            return GuardrailResult(
                success=False,
                result=code,
                error=f"Python 语法错误 (行 {e.lineno}): {e.msg}",
                validator_name=self.name
            )
    
    def _validate_javascript(self, code: str) -> GuardrailResult:
        """验证 JavaScript 语法（简化版）"""
        # 检查基本语法错误
        errors = []
        
        # 检查括号匹配
        if code.count('(') != code.count(')'):
            errors.append("括号不匹配")
        if code.count('{') != code.count('}'):
            errors.append("花括号不匹配")
        if code.count('[') != code.count(']'):
            errors.append("方括号不匹配")
        
        # 检查常见错误
        if re.search(r'\bfunction\s*\(', code):
            errors.append("函数声明语法错误")
        
        if errors:
            return GuardrailResult(
                success=False,
                result=code,
                error="; ".join(errors),
                validator_name=self.name
            )
        
        return GuardrailResult(
            success=True,
            result=code,
            details={"language": "javascript", "valid": True},
            validator_name=self.name
        )


# ========== 安全验证器 ==========

class SecurityValidator(BaseValidator):
    """安全验证器 - 检测危险代码和敏感信息"""
    
    # 危险函数模式
    DANGEROUS_PATTERNS = {
        "python": [
            r'\beval\s*\(',
            r'\bexec\s*\(',
            r'\b__import__\s*\(',
            r'\bos\.system\s*\(',
            r'\bsubprocess\.call\s*\(',
            r'\bsubprocess\.run\s*\(',
        ],
        "javascript": [
            r'\beval\s*\(',
            r'\bFunction\s*\(',
            r'\bsetTimeout\s*\(\s*["\']',
            r'\bsetInterval\s*\(\s*["\']',
        ]
    }
    
    # 敏感信息模式
    SENSITIVE_PATTERNS = [
        r'sk-[a-zA-Z0-9]{48}',  # OpenAI API Key
        r'[a-zA-Z0-9]{32}-[a-zA-Z0-9]{16}',  # AWS Key
        r'password\s*[=:]\s*["\'][^"\']+',  # 硬编码密码
        r'api[_-]?key\s*[=:]\s*["\'][^"\']+',  # API Key
        r'\b\d{16}\b',  # 信用卡号 (16位数字)
        r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',  # 信用卡号 (带分隔符)
    ]
    
    def __init__(self, language: str = "python", check_sensitive: bool = True):
        super().__init__("SecurityValidator")
        self.language = language.lower()
        self.check_sensitive = check_sensitive
    
    def validate(self, output: str, context: Optional[Dict] = None) -> GuardrailResult:
        """执行安全验证"""
        issues = []
        
        # 检查危险函数
        patterns = self.DANGEROUS_PATTERNS.get(self.language, [])
        for pattern in patterns:
            if re.search(pattern, output, re.IGNORECASE):
                issues.append(f"发现危险函数: {pattern}")
        
        # 检查敏感信息
        if self.check_sensitive:
            for pattern in self.SENSITIVE_PATTERNS:
                if re.search(pattern, output, re.IGNORECASE):
                    issues.append("发现敏感信息")
                    break
        
        if issues:
            return GuardrailResult(
                success=False,
                result=output,
                error="; ".join(issues),
                details={"issues": issues},
                validator_name=self.name
            )
        
        return GuardrailResult(
            success=True,
            result=output,
            details={"safe": True},
            validator_name=self.name
        )


# ========== 内容验证器 ==========

class LengthValidator(BaseValidator):
    """长度验证器"""
    
    def __init__(self, min_length: Optional[int] = None, 
                 max_length: Optional[int] = None):
        super().__init__("LengthValidator")
        self.min_length = min_length
        self.max_length = max_length
    
    def validate(self, output: str, context: Optional[Dict] = None) -> GuardrailResult:
        """验证长度"""
        length = len(output)
        
        if self.min_length is not None and length < self.min_length:
            return GuardrailResult(
                success=False,
                result=output,
                error=f"输出长度 {length} 小于最小长度 {self.min_length}",
                validator_name=self.name
            )
        
        if self.max_length is not None and length > self.max_length:
            return GuardrailResult(
                success=False,
                result=output,
                error=f"输出长度 {length} 大于最大长度 {self.max_length}",
                validator_name=self.name
            )
        
        return GuardrailResult(
            success=True,
            result=output,
            details={"length": length},
            validator_name=self.name
        )


class KeywordValidator(BaseValidator):
    """关键词验证器"""
    
    def __init__(self, required: Optional[List[str]] = None,
                 forbidden: Optional[List[str]] = None,
                 case_sensitive: bool = False):
        super().__init__("KeywordValidator")
        self.required = required or []
        self.forbidden = forbidden or []
        self.case_sensitive = case_sensitive
    
    def validate(self, output: str, context: Optional[Dict] = None) -> GuardrailResult:
        """验证关键词"""
        text = output if self.case_sensitive else output.lower()
        
        # 检查必需关键词
        for keyword in self.required:
            check = keyword if self.case_sensitive else keyword.lower()
            if check not in text:
                return GuardrailResult(
                    success=False,
                    result=output,
                    error=f"缺少必需关键词: {keyword}",
                    validator_name=self.name
                )
        
        # 检查禁用关键词
        for keyword in self.forbidden:
            check = keyword if self.case_sensitive else keyword.lower()
            if check in text:
                return GuardrailResult(
                    success=False,
                    result=output,
                    error=f"包含禁用关键词: {keyword}",
                    validator_name=self.name
                )
        
        return GuardrailResult(
            success=True,
            result=output,
            details={"required_found": self.required, "forbidden_absent": self.forbidden},
            validator_name=self.name
        )


class RegexValidator(BaseValidator):
    """正则表达式验证器"""
    
    def __init__(self, pattern: str, must_match: bool = True):
        super().__init__("RegexValidator")
        self.pattern = re.compile(pattern)
        self.must_match = must_match
    
    def validate(self, output: str, context: Optional[Dict] = None) -> GuardrailResult:
        """正则验证"""
        matches = self.pattern.findall(output)
        has_match = len(matches) > 0
        
        if self.must_match and not has_match:
            return GuardrailResult(
                success=False,
                result=output,
                error=f"未匹配到模式: {self.pattern.pattern}",
                validator_name=self.name
            )
        
        if not self.must_match and has_match:
            return GuardrailResult(
                success=False,
                result=output,
                error=f"不应匹配到模式: {self.pattern.pattern}",
                validator_name=self.name
            )
        
        return GuardrailResult(
            success=True,
            result=output,
            details={"matches": matches},
            validator_name=self.name
        )


# ========== 质量验证器 ==========

class QualityValidator(BaseValidator):
    """质量验证器"""
    
    def __init__(self, min_word_count: Optional[int] = None,
                 check_repetition: bool = True,
                 max_repetition_ratio: float = 0.3):
        super().__init__("QualityValidator")
        self.min_word_count = min_word_count
        self.check_repetition = check_repetition
        self.max_repetition_ratio = max_repetition_ratio
    
    def validate(self, output: str, context: Optional[Dict] = None) -> GuardrailResult:
        """验证质量"""
        issues = []
        
        # 检查字数
        if self.min_word_count:
            word_count = len(output.split())
            if word_count < self.min_word_count:
                issues.append(f"字数 {word_count} 少于最小要求 {self.min_word_count}")
        
        # 检查重复
        if self.check_repetition:
            repetition_ratio = self._calculate_repetition(output)
            if repetition_ratio > self.max_repetition_ratio:
                issues.append(f"重复率 {repetition_ratio:.2%} 过高")
        
        if issues:
            return GuardrailResult(
                success=False,
                result=output,
                error="; ".join(issues),
                validator_name=self.name
            )
        
        return GuardrailResult(
            success=True,
            result=output,
            details={"quality_check": "passed"},
            validator_name=self.name
        )
    
    def _calculate_repetition(self, text: str) -> float:
        """计算重复率"""
        sentences = re.split(r'[.!?。！？]+', text)
        if len(sentences) < 2:
            return 0.0
        
        unique_sentences = set(s.strip() for s in sentences if s.strip())
        return 1 - (len(unique_sentences) / len(sentences))


class CustomValidator(BaseValidator):
    """自定义验证器"""
    
    def __init__(self, validator_func: Callable[[str], Tuple[bool, Union[str, Any]]],
                 name: str = "CustomValidator"):
        super().__init__(name)
        self.validator_func = validator_func
    
    def validate(self, output: str, context: Optional[Dict] = None) -> GuardrailResult:
        """执行自定义验证"""
        try:
            success, result = self.validator_func(output)
            
            if success:
                return GuardrailResult(
                    success=True,
                    result=result,
                    validator_name=self.name
                )
            else:
                return GuardrailResult(
                    success=False,
                    result=output,
                    error=str(result),
                    validator_name=self.name
                )
        except Exception as e:
            return GuardrailResult(
                success=False,
                result=output,
                error=f"自定义验证器错误: {str(e)}",
                validator_name=self.name
            )


# ========== Guardrails 管理器 ==========

class Guardrails:
    """
    护栏管理器
    
    管理多个验证器，支持链式验证和失败处理
    """
    
    def __init__(self, max_retries: int = 3, stop_on_first_fail: bool = True):
        self.validators: List[BaseValidator] = []
        self.max_retries = max_retries
        self.stop_on_first_fail = stop_on_first_fail
        self.validation_history: List[Dict] = []
    
    def add(self, validator: BaseValidator) -> 'Guardrails':
        """添加验证器（链式调用）"""
        self.validators.append(validator)
        return self
    
    def validate(self, output: str, context: Optional[Dict] = None) -> GuardrailResult:
        """
        执行所有验证
        
        Args:
            output: 待验证的输出
            context: 验证上下文
            
        Returns:
            GuardrailResult: 验证结果
        """
        all_results = []
        
        for validator in self.validators:
            result = validator.validate(output, context)
            
            record = {
                "validator": validator.name,
                "success": result.success,
                "error": result.error
            }
            self.validation_history.append(record)
            all_results.append(result)
            
            # 如果失败且需要立即停止
            if not result.success and self.stop_on_first_fail:
                return GuardrailResult(
                    success=False,
                    result=output,
                    error=f"[{validator.name}] {result.error}",
                    details={"all_results": all_results},
                    validator_name="Guardrails"
                )
        
        # 检查是否有任何失败
        failed_results = [r for r in all_results if not r.success]
        if failed_results:
            errors = [f"[{r.validator_name}] {r.error}" for r in failed_results]
            return GuardrailResult(
                success=False,
                result=output,
                error="; ".join(errors),
                details={"all_results": all_results},
                validator_name="Guardrails"
            )
        
        # 全部通过
        return GuardrailResult(
            success=True,
            result=output,
            details={"validated_count": len(self.validators)},
            validator_name="Guardrails"
        )
    
    def __call__(self, output: str, context: Optional[Dict] = None) -> GuardrailResult:
        """便捷调用"""
        return self.validate(output, context)


# ========== 预设验证器组合 ==========

class GuardrailPresets:
    """预设护栏组合"""
    
    @staticmethod
    def code_generation(language: str = "python") -> Guardrails:
        """代码生成验证"""
        return Guardrails() \
            .add(CodeSyntaxValidator(language)) \
            .add(SecurityValidator(language)) \
            .add(LengthValidator(min_length=10))
    
    @staticmethod
    def json_output(required_fields: Optional[List[str]] = None) -> Guardrails:
        """JSON 输出验证"""
        return Guardrails() \
            .add(JSONValidator(required_fields=required_fields)) \
            .add(LengthValidator(min_length=2))
    
    @staticmethod
    def safe_content(forbidden_words: Optional[List[str]] = None) -> Guardrails:
        """安全内容验证"""
        guardrails = Guardrails()
        guardrails.add(SecurityValidator(check_sensitive=True))
        if forbidden_words:
            guardrails.add(KeywordValidator(forbidden=forbidden_words))
        return guardrails
    
    @staticmethod
    def quality_assurance(min_length: Optional[int] = None) -> Guardrails:
        """质量保证验证"""
        return Guardrails() \
            .add(QualityValidator(min_word_count=min_length)) \
            .add(LengthValidator(min_length=min_length))


# ========== 便捷函数 ==========

def validate_json(output: str, required_fields: Optional[List[str]] = None) -> GuardrailResult:
    """便捷函数：验证 JSON"""
    validator = JSONValidator(required_fields=required_fields)
    return validator(output)


def validate_code(output: str, language: str = "python") -> GuardrailResult:
    """便捷函数：验证代码"""
    guardrails = GuardrailPresets.code_generation(language)
    return guardrails(output)


def validate_safe(output: str, language: str = "python") -> GuardrailResult:
    """便捷函数：安全验证"""
    validator = SecurityValidator(language=language)
    return validator(output)
