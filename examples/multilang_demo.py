"""Multi-language Demo - 多语言支持演示

演示知识图谱的多语言解析功能：
1. Python 代码解析
2. TypeScript 代码解析
3. 跨语言统计
4. 统一查询
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from code_gen.knowledge_graph import (
    KnowledgeGraph,
    CodeIndexer,
    Language,
    NodeType,
    TypeScriptParser,
)


# 示例 TypeScript 代码
SAMPLE_TS_CODE = '''
/**
 * User service for managing users
 */
export class UserService {
    private users: Map<string, User> = new Map();

    constructor(private apiClient: ApiClient) {}

    async getUser(id: string): Promise<User> {
        const user = this.users.get(id);
        if (user) return user;
        
        const response = await this.apiClient.get(`/users/${id}`);
        this.users.set(id, response.data);
        return response.data;
    }

    async createUser(data: CreateUserInput): Promise<User> {
        const response = await this.apiClient.post('/users', data);
        return response.data;
    }
}

export interface User {
    id: string;
    name: string;
    email: string;
}

export interface CreateUserInput {
    name: string;
    email: string;
}

export type UserRole = 'admin' | 'user' | 'guest';

export enum UserStatus {
    ACTIVE = 'active',
    INACTIVE = 'inactive',
    PENDING = 'pending',
}
'''


async def demo_typescript_parser():
    """演示 TypeScript 解析器"""
    print("=" * 60)
    print("1. TypeScript 解析器")
    print("=" * 60)

    parser = TypeScriptParser()

    print("\n支持的文件扩展名:")
    for ext in parser.extensions:
        print(f"  - {ext}")

    print("\n解析示例代码...")
    result = parser.parse(SAMPLE_TS_CODE, "sample.ts")

    print(f"\n解析结果:")
    print(f"  节点数: {len(result.nodes)}")
    print(f"  边数: {len(result.edges)}")
    print(f"  错误数: {len(result.errors)}")

    # 按类型分组
    by_type = {}
    for node in result.nodes:
        t = node.node_type.value
        by_type[t] = by_type.get(t, 0) + 1

    print("\n节点类型分布:")
    for node_type, count in sorted(by_type.items()):
        print(f"  - {node_type}: {count}")

    # 显示具体节点
    print("\n具体节点:")
    for node in result.nodes[:10]:
        print(f"  - {node.name} ({node.node_type.value})")
        if node.signature:
            print(f"    签名: {node.signature}")


async def demo_multilang_indexing():
    """演示多语言索引"""
    print("\n" + "=" * 60)
    print("2. 多语言索引")
    print("=" * 60)

    graph = KnowledgeGraph()
    indexer = CodeIndexer(graph)

    # 索引当前项目（包含 Python 和 TypeScript）
    project_path = Path(__file__).parent.parent / "code_gen" / "knowledge_graph"
    print(f"\n索引项目: {project_path}")

    stats = indexer.index_directory(project_path)

    print(f"\n索引完成!")
    print(f"  总节点数: {stats['total_nodes']}")
    print(f"  总边数: {stats['total_edges']}")

    # 按语言统计
    by_language = {}
    for node in graph:
        lang = node.language.value
        by_language[lang] = by_language.get(lang, 0) + 1

    print("\n按语言统计:")
    for lang, count in sorted(by_language.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {lang}: {count} 个节点")

    # 按类型统计
    print("\n按类型统计:")
    for node_type, count in sorted(stats['node_types'].items(), key=lambda x: x[1], reverse=True):
        print(f"  - {node_type}: {count}")


async def demo_language_aware_search():
    """演示语言感知的搜索"""
    print("\n" + "=" * 60)
    print("3. 语言感知搜索")
    print("=" * 60)

    # 创建包含多语言的图谱
    graph = KnowledgeGraph()

    # 添加 Python 节点
    py_node = Node(
        name="UserService",
        node_type=NodeType.CLASS,
        language=Language.PYTHON,
        file_path="backend/user_service.py",
        signature="class UserService",
    )
    graph.add_node(py_node)

    # 添加 TypeScript 节点
    ts_node = Node(
        name="UserService",
        node_type=NodeType.CLASS,
        language=Language.TYPESCRIPT,
        file_path="frontend/userService.ts",
        signature="export class UserService",
    )
    graph.add_node(ts_node)

    # 添加 JavaScript 节点
    js_node = Node(
        name="UserService",
        node_type=NodeType.CLASS,
        language=Language.JAVASCRIPT,
        file_path="legacy/userService.js",
        signature="class UserService",
    )
    graph.add_node(js_node)

    print("\n搜索 'UserService':")
    results = graph.find_nodes_by_pattern("UserService")
    print(f"  找到 {len(results)} 个结果:")

    for node in results:
        lang_icon = {
            "python": "🐍",
            "typescript": "📘",
            "javascript": "📒",
        }.get(node.language.value, "📄")

        print(f"  {lang_icon} {node.name}")
        print(f"     语言: {node.language.value}")
        print(f"     文件: {node.file_path}")


async def demo_cross_language_analysis():
    """演示跨语言分析"""
    print("\n" + "=" * 60)
    print("4. 跨语言分析场景")
    print("=" * 60)

    print("\n场景: 全栈项目结构")
    print("-" * 50)

    # 模拟一个全栈项目
    project_structure = {
        "backend/": {
            "language": Language.PYTHON,
            "files": [
                ("api.py", NodeType.FILE),
                ("models.py", NodeType.FILE),
                ("services.py", NodeType.FILE),
            ],
        },
        "frontend/": {
            "language": Language.TYPESCRIPT,
            "files": [
                ("App.tsx", NodeType.FILE),
                ("api.ts", NodeType.FILE),
                ("types.ts", NodeType.FILE),
            ],
        },
        "shared/": {
            "language": Language.TYPESCRIPT,
            "files": [
                ("types.ts", NodeType.FILE),
            ],
        },
    }

    graph = KnowledgeGraph()

    for folder, info in project_structure.items():
        lang = info["language"]
        for filename, node_type in info["files"]:
            node = Node(
                name=filename,
                node_type=node_type,
                language=lang,
                file_path=f"{folder}{filename}",
            )
            graph.add_node(node)

    # 统计
    print("\n项目结构统计:")
    by_folder = {}
    by_lang = {}

    for node in graph:
        folder = node.file_path.split('/')[0] if node.file_path else 'unknown'
        by_folder[folder] = by_folder.get(folder, 0) + 1
        by_lang[node.language.value] = by_lang.get(node.language.value, 0) + 1

    print("\n按目录:")
    for folder, count in sorted(by_folder.items()):
        print(f"  - {folder}/: {count} 个文件")

    print("\n按语言:")
    for lang, count in sorted(by_lang.items()):
        icon = {"python": "🐍", "typescript": "📘"}.get(lang, "📄")
        print(f"  {icon} {lang}: {count} 个文件")

    print("\n跨语言场景:")
    print("  • 后端 API (Python) ←→ 前端调用 (TypeScript)")
    print("  • 共享类型定义 (TypeScript)")
    print("  • 统一代码搜索和导航")


async def demo_parser_comparison():
    """演示不同解析器的对比"""
    print("\n" + "=" * 60)
    print("5. 解析器对比")
    print("=" * 60)

    # Python 代码示例
    py_code = '''
def calculate_sum(a: int, b: int) -> int:
    """Calculate sum of two numbers."""
    return a + b

class Calculator:
    def __init__(self):
        self.result = 0
    
    def add(self, value: int):
        self.result += value
        return self
'''

    # TypeScript 代码示例
    ts_code = '''
function calculateSum(a: number, b: number): number {
    return a + b;
}

class Calculator {
    private result: number = 0;
    
    add(value: number): this {
        this.result += value;
        return this;
    }
}
'''

    print("\nPython 解析 (AST):")
    import ast
    try:
        tree = ast.parse(py_code)
        funcs = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        print(f"  函数: {funcs}")
        print(f"  类: {classes}")
        print(f"  ✅ 精确、完整")
    except Exception as e:
        print(f"  错误: {e}")

    print("\nTypeScript 解析 (正则):")
    parser = TypeScriptParser()
    result = parser.parse(ts_code, "sample.ts")
    funcs = [n.name for n in result.nodes if n.node_type == NodeType.FUNCTION]
    classes = [n.name for n in result.nodes if n.node_type == NodeType.CLASS]
    print(f"  函数: {funcs}")
    print(f"  类: {classes}")
    print(f"  ⚠️  轻量、快速（生产环境建议使用 tree-sitter）")

    print("\n对比:")
    print("  Python AST:")
    print("    ✅ 官方支持，100% 准确")
    print("    ✅ 完整的语法树")
    print("    ❌ 仅支持 Python")
    print("\n  TypeScript 正则:")
    print("    ✅ 无需外部依赖")
    print("    ✅ 跨平台")
    print("    ⚠️  准确性略低")
    print("    ⚠️  复杂语法可能解析失败")


async def main():
    """主函数"""
    print("\n" + "🌐 " * 20)
    print("多语言支持系统演示")
    print("🌐 " * 20 + "\n")

    await demo_typescript_parser()
    await demo_multilang_indexing()
    await demo_language_aware_search()
    await demo_cross_language_analysis()
    await demo_parser_comparison()

    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)
    print("\n多语言支持特点:")
    print("  ✅ Python - AST 解析，精确完整")
    print("  ✅ TypeScript - 正则解析，轻量快速")
    print("  ✅ JavaScript - 与 TS 共用解析器")
    print("  ✅ 统一图模型，跨语言查询")
    print("\n支持的语言:")
    print("  🐍 Python (.py)")
    print("  📘 TypeScript (.ts, .tsx)")
    print("  📒 JavaScript (.js, .jsx, .mjs)")
    print("\n扩展计划:")
    print("  • Go (使用 tree-sitter)")
    print("  • Java/Kotlin")
    print("  • Rust")
    print("  • SQL")


if __name__ == "__main__":
    # 导入 Node 类
    from code_gen.knowledge_graph import Node
    asyncio.run(main())
