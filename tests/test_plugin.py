"""Test plugin system"""
import asyncio
import shutil
import json
from pathlib import Path
from code_gen.plugins import PluginLoader, PluginType

async def test_plugin_system():
    """Test plugin system functionality"""
    print("\n" + "="*60)
    print("测试插件系统")
    print("="*60)
    
    # Create test directory
    test_dir = Path(__file__).parent.parent / "test_workspace"
    test_dir.mkdir(exist_ok=True)
    
    try:
        # Create plugins directory
        plugins_dir = test_dir / ".claude" / "plugins"
        plugins_dir.mkdir(parents=True, exist_ok=True)
        
        # Create test plugin
        plugin1 = {
            "name": "test-plugin",
            "version": "1.0.0",
            "description": "A test plugin",
            "author": "Test Author",
            "config": {"setting1": "value1"}
        }
        
        plugin_file1 = plugins_dir / "test-plugin.json"
        with open(plugin_file1, 'w', encoding='utf-8') as f:
            json.dump(plugin1, f, indent=2, ensure_ascii=False)
        
        print(f"✓ 创建测试插件: {plugin_file1}")
        
        # Initialize plugin loader
        loader = PluginLoader(test_dir)
        print(f"\n✓ PluginLoader 初始化成功")
        
        # Load project plugins
        loader.load_project_plugins()
        print(f"✓ 加载项目插件: {len(loader.plugins)} 个插件")
        
        # Test plugin operations
        print("\n--- 测试插件操作 ---")
        
        # Get plugin
        plugin = loader.get_plugin("test-plugin")
        if plugin:
            print(f"✓ 找到插件: {plugin.manifest.name}")
            print(f"  版本: {plugin.manifest.version}")
            print(f"  描述: {plugin.manifest.description}")
            print(f"  启用状态: {plugin.enabled}")
        
        # Disable plugin
        loader.disable_plugin("test-plugin")
        plugin = loader.get_plugin("test-plugin")
        print(f"✓ 禁用插件后: {plugin is None}")
        
        # Enable plugin
        loader.enable_plugin("test-plugin")
        plugin = loader.get_plugin("test-plugin")
        print(f"✓ 启用插件后: {plugin is not None}")
        
        # Get all plugins
        all_plugins = loader.get_all_plugins()
        print(f"✓ 所有启用的插件: {len(all_plugins)} 个")
        
        # Test permission system
        print("\n--- 测试权限系统 ---")
        perm_system = loader.get_permission_system()
        perm_system.set_permission("test-plugin", "read_files", True)
        perm_system.set_permission("test-plugin", "write_files", False)
        
        has_read = perm_system.check_permission("test-plugin", "read_files")
        has_write = perm_system.check_permission("test-plugin", "write_files")
        
        print(f"✓ 插件 'read_files' 权限: {has_read}")
        print(f"✓ 插件 'write_files' 权限: {has_write}")
        
        print("\n" + "="*60)
        print("插件系统测试完成!")
        print("="*60)
        
    finally:
        # Cleanup
        if test_dir.exists():
            shutil.rmtree(test_dir)
        print(f"\n✓ 测试目录已清理: {test_dir}")

if __name__ == "__main__":
    asyncio.run(test_plugin_system())
