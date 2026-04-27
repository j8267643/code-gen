"""
Guardrails Example - 护栏/验证系统示例

展示 PraisonAI 风格的输出验证功能
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from code_gen.agents import (
    Guardrails,
    GuardrailPresets,
    JSONValidator,
    CodeSyntaxValidator,
    SecurityValidator,
    LengthValidator,
    KeywordValidator,
    RegexValidator,
    QualityValidator,
    CustomValidator,
    validate_json,
    validate_code,
    validate_safe
)


def example_1_json_validation():
    """示例1: JSON 格式验证"""
    print("\n" + "="*60)
    print("示例1: JSON 格式验证")
    print("="*60 + "\n")
    
    # 创建 JSON 验证器
    validator = JSONValidator(
        required_fields=["name", "age"],
        field_types={"name": str, "age": int}
    )
    
    # 测试有效 JSON
    valid_json = '''{"name": "张三", "age": 30, "email": "zhangsan@example.com"}'''
    print("测试1: 有效 JSON")
    print(f"  输入: {valid_json}")
    result = validator(valid_json)
    print(f"  结果: {'✅ 通过' if result else '❌ 失败'}")
    if result.success:
        print(f"  解析结果: {result.result}")
    else:
        print(f"  错误: {result.error}")
    
    # 测试缺少字段
    invalid_json = '''{"name": "李四"}'''
    print("\n测试2: 缺少必需字段")
    print(f"  输入: {invalid_json}")
    result = validator(invalid_json)
    print(f"  结果: {'✅ 通过' if result else '❌ 失败'}")
    if not result.success:
        print(f"  错误: {result.error}")
    
    # 测试类型错误
    type_error_json = '''{"name": "王五", "age": "30"}'''
    print("\n测试3: 字段类型错误")
    print(f"  输入: {type_error_json}")
    result = validator(type_error_json)
    print(f"  结果: {'✅ 通过' if result else '❌ 失败'}")
    if not result.success:
        print(f"  错误: {result.error}")


def example_2_code_validation():
    """示例2: 代码语法验证"""
    print("\n" + "="*60)
    print("示例2: 代码语法验证")
    print("="*60 + "\n")
    
    # Python 代码验证
    python_validator = CodeSyntaxValidator(language="python")
    
    # 有效代码
    valid_code = """
def hello():
    print("Hello, World!")
    return True
"""
    print("测试1: 有效 Python 代码")
    print(f"  代码:\n{valid_code}")
    result = python_validator(valid_code)
    print(f"  结果: {'✅ 通过' if result else '❌ 失败'}")
    
    # 语法错误代码
    invalid_code = """
def hello()
    print("Missing colon")
"""
    print("\n测试2: 语法错误的 Python 代码")
    print(f"  代码:\n{invalid_code}")
    result = python_validator(invalid_code)
    print(f"  结果: {'✅ 通过' if result else '❌ 失败'}")
    if not result.success:
        print(f"  错误: {result.error}")


def example_3_security_validation():
    """示例3: 安全验证"""
    print("\n" + "="*60)
    print("示例3: 安全验证")
    print("="*60 + "\n")
    
    security_validator = SecurityValidator(language="python")
    
    # 危险代码
    dangerous_code = """
# 用户输入处理
user_input = input("Enter command: ")
eval(user_input)  # 危险！
"""
    print("测试1: 包含危险函数的代码")
    print(f"  代码:\n{dangerous_code}")
    result = security_validator(dangerous_code)
    print(f"  结果: {'✅ 通过' if result else '❌ 失败'}")
    if not result.success:
        print(f"  错误: {result.error}")
    
    # 包含敏感信息（示例中的假key）
    sensitive_code = """
api_key = "sk-example-fake-key-do-not-use"
"""
    print("\n测试2: 包含敏感信息的代码")
    print(f"  代码:\n{sensitive_code}")
    result = security_validator(sensitive_code)
    print(f"  结果: {'✅ 通过' if result else '❌ 失败'}")
    if not result.success:
        print(f"  错误: {result.error}")
    
    # 安全代码
    safe_code = """
def process_data(data):
    return data.strip().lower()
"""
    print("\n测试3: 安全代码")
    print(f"  代码:\n{safe_code}")
    result = security_validator(safe_code)
    print(f"  结果: {'✅ 通过' if result else '❌ 失败'}")


def example_4_content_validation():
    """示例4: 内容验证"""
    print("\n" + "="*60)
    print("示例4: 内容验证")
    print("="*60 + "\n")
    
    # 长度验证
    length_validator = LengthValidator(min_length=10, max_length=100)
    
    print("长度验证测试:")
    test_cases = [
        ("太短", "短文本"),
        ("合适", "这是一个长度合适的文本内容"),
        ("太长", "x" * 150)
    ]
    
    for test_name, text in test_cases:
        result = length_validator(text)
        print(f"  {test_name}: {'✅' if result else '❌'} {result.error if not result.success else '通过'}")
    
    # 关键词验证
    keyword_validator = KeywordValidator(
        required=["Python", "AI"],
        forbidden=["bad", "error"]
    )
    
    print("\n关键词验证测试:")
    keyword_tests = [
        ("缺少关键词", "我喜欢编程"),
        ("包含禁用词", "Python AI 很棒 but bad"),
        ("符合要求", "Python 和 AI 是未来的趋势")
    ]
    
    for test_name, text in keyword_tests:
        result = keyword_validator(text)
        print(f"  {test_name}: {'✅' if result else '❌'} {result.error if not result.success else '通过'}")


def example_5_custom_validator():
    """示例5: 自定义验证器"""
    print("\n" + "="*60)
    print("示例5: 自定义验证器")
    print("="*60 + "\n")
    
    # 定义自定义验证函数
    def validate_email_format(text: str):
        """验证是否包含有效的邮箱格式"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        if re.search(email_pattern, text):
            return True, "找到有效邮箱"
        return False, "未找到有效邮箱格式"
    
    email_validator = CustomValidator(validate_email_format, name="EmailValidator")
    
    # 测试
    test_texts = [
        "请联系 support@example.com 获取帮助",
        "我的邮箱是 user.name+tag@company.co.uk",
        "这段文本没有邮箱地址"
    ]
    
    print("邮箱格式验证:")
    for text in test_texts:
        result = email_validator(text)
        print(f"  {'✅' if result else '❌'} {text[:40]}...")
        if not result.success:
            print(f"     错误: {result.error}")


def example_6_guardrails_chain():
    """示例6: 护栏链式验证"""
    print("\n" + "="*60)
    print("示例6: 护栏链式验证")
    print("="*60 + "\n")
    
    # 创建护栏链
    guardrails = Guardrails(stop_on_first_fail=True)
    guardrails \
        .add(LengthValidator(min_length=20)) \
        .add(KeywordValidator(required=["function"])) \
        .add(CodeSyntaxValidator(language="python")) \
        .add(SecurityValidator(language="python"))
    
    # 测试代码
    test_code = """
def calculate_sum(a, b):
    return a + b
"""
    print("测试代码:")
    print(test_code)
    print("\n执行护栏验证...")
    result = guardrails(test_code)
    
    print(f"\n验证结果: {'✅ 全部通过' if result else '❌ 验证失败'}")
    if not result.success:
        print(f"错误: {result.error}")
    else:
        print(f"通过 {result.details['validated_count']} 个验证器")


def example_7_preset_guardrails():
    """示例7: 预设护栏组合"""
    print("\n" + "="*60)
    print("示例7: 预设护栏组合")
    print("="*60 + "\n")
    
    # 代码生成验证
    print("1. 代码生成验证预设:")
    code_guardrails = GuardrailPresets.code_generation("python")
    
    test_code = """
def hello():
    print("Hello")
    eval("dangerous()")
"""
    result = code_guardrails(test_code)
    print(f"   结果: {'✅ 通过' if result else '❌ 失败'}")
    if not result.success:
        print(f"   错误: {result.error}")
    
    # JSON 输出验证
    print("\n2. JSON 输出验证预设:")
    json_guardrails = GuardrailPresets.json_output(required_fields=["status", "data"])
    
    test_json = '{"status": "ok", "data": [1, 2, 3]}'
    result = json_guardrails(test_json)
    print(f"   输入: {test_json}")
    print(f"   结果: {'✅ 通过' if result else '❌ 失败'}")
    
    # 安全内容验证
    print("\n3. 安全内容验证预设:")
    safe_guardrails = GuardrailPresets.safe_content(forbidden_words=["spam", "scam"])
    
    test_text = "这是一个正常的内容"
    result = safe_guardrails(test_text)
    print(f"   输入: {test_text}")
    print(f"   结果: {'✅ 通过' if result else '❌ 失败'}")


def example_8_convenience_functions():
    """示例8: 便捷函数"""
    print("\n" + "="*60)
    print("示例8: 便捷函数")
    print("="*60 + "\n")
    
    # 便捷 JSON 验证
    print("1. validate_json 便捷函数:")
    json_str = '{"name": "test", "value": 123}'
    result = validate_json(json_str, required_fields=["name"])
    print(f"   输入: {json_str}")
    print(f"   结果: {'✅ 通过' if result else '❌ 失败'}")
    
    # 便捷代码验证
    print("\n2. validate_code 便捷函数:")
    code = "def test(): pass"
    result = validate_code(code, language="python")
    print(f"   输入: {code}")
    print(f"   结果: {'✅ 通过' if result else '❌ 失败'}")
    
    # 便捷安全验证
    print("\n3. validate_safe 便捷函数:")
    code = "x = 1 + 2"
    result = validate_safe(code, language="python")
    print(f"   输入: {code}")
    print(f"   结果: {'✅ 通过' if result else '❌ 失败'}")


def main():
    """运行所有示例"""
    print("\n" + "🛡️"*30)
    print("Guardrails (护栏/验证系统) 示例")
    print("🛡️"*30)
    
    example_1_json_validation()
    example_2_code_validation()
    example_3_security_validation()
    example_4_content_validation()
    example_5_custom_validator()
    example_6_guardrails_chain()
    example_7_preset_guardrails()
    example_8_convenience_functions()
    
    print("\n" + "="*60)
    print("所有示例完成!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
