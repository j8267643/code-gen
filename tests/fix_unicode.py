import re

# 读取文件
with open('tests/test_complete_system.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 替换 emoji 字符
emoji_pattern = r'print\("[📁⚡🛡️💾📜🔒🎯💰🔌🌐]\s*'
content = re.sub(emoji_pattern, 'print("', content)

# 写入文件
with open('tests/test_complete_system.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done - removed emojis")
