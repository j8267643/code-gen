"""
AutoDev Command - 自主开发集成命令

提供 CLI 接口使用 AutoDev 功能
"""
import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from code_gen.autodev import AutoDevIntegration, AutoDevConfig

console = Console()
app = typer.Typer(help="AutoDev 自主开发集成")


@app.command("init")
def init_autodev(
    work_dir: Optional[Path] = typer.Option(
        None,
        "--work-dir", "-w",
        help="工作目录"
    )
):
    """初始化 AutoDev 集成"""
    work_dir = work_dir or Path.cwd()
    
    # 创建必要的目录
    (work_dir / "tasks").mkdir(exist_ok=True)
    (work_dir / ".code-gen").mkdir(exist_ok=True)
    
    console.print(Panel(
        f"✅ AutoDev 集成已初始化\n"
        f"工作目录: {work_dir}\n"
        f"任务目录: {work_dir / 'tasks'}\n"
        f"配置目录: {work_dir / '.code-gen'}",
        title="AutoDev Init",
        border_style="green"
    ))


@app.command("prd")
def create_prd(
    description: str = typer.Argument(..., help="功能描述"),
    work_dir: Optional[Path] = typer.Option(None, "--work-dir", "-w")
):
    """创建 PRD 模板"""
    work_dir = work_dir or Path.cwd()
    
    config = AutoDevConfig(work_dir=work_dir)
    autodev = AutoDevIntegration(config)
    
    prd_path = autodev.create_prd(description)
    
    console.print(Panel(
        f"✅ PRD 模板已创建\n"
        f"路径: {prd_path}\n\n"
        f"请编辑该文件，添加详细的用户故事和验收标准。\n"
        f"完成后运行: code-gen autodev convert {prd_path}",
        title="PRD Created",
        border_style="blue"
    ))


@app.command("convert")
def convert_prd(
    prd_path: Path = typer.Argument(..., help="PRD 文件路径"),
    work_dir: Optional[Path] = typer.Option(None, "--work-dir", "-w")
):
    """将 PRD 转换为可执行格式"""
    work_dir = work_dir or Path.cwd()
    
    if not prd_path.exists():
        console.print(f"❌ 文件不存在: {prd_path}", style="red")
        raise typer.Exit(1)
    
    config = AutoDevConfig(work_dir=work_dir)
    autodev = AutoDevIntegration(config)
    
    try:
        prd_data = autodev.convert_prd(prd_path)
        
        # 显示转换结果
        table = Table(title="PRD 转换结果")
        table.add_column("项目", style="cyan")
        table.add_column("值", style="green")
        
        table.add_row("项目名称", prd_data.project)
        table.add_row("分支名", prd_data.branch_name)
        table.add_row("描述", prd_data.description[:50] + "...")
        table.add_row("用户故事数", str(len(prd_data.user_stories)))
        
        console.print(table)
        
        # 显示用户故事
        stories_table = Table(title="用户故事")
        stories_table.add_column("ID", style="cyan")
        stories_table.add_column("标题", style="green")
        stories_table.add_column("优先级", style="yellow")
        
        for story in sorted(prd_data.user_stories, key=lambda x: x.get("priority", 999)):
            stories_table.add_row(
                story.get("id", "N/A"),
                story.get("title", "Untitled")[:40],
                str(story.get("priority", "-"))
            )
        
        console.print(stories_table)
        
        console.print(f"\n✅ 已保存到: {config.prd_json_path}")
        console.print("运行 'code-gen autodev run' 开始执行")
        
    except Exception as e:
        console.print(f"❌ 转换失败: {e}", style="red")
        raise typer.Exit(1)


@app.command("run")
def run_autodev(
    work_dir: Optional[Path] = typer.Option(None, "--work-dir", "-w"),
    stop_on_error: bool = typer.Option(False, "--stop-on-error", "-s"),
    max_iterations: int = typer.Option(100, "--max-iterations", "-m")
):
    """运行 AutoDev 执行循环"""
    work_dir = work_dir or Path.cwd()
    
    config = AutoDevConfig(
        work_dir=work_dir,
        stop_on_error=stop_on_error,
        max_iterations=max_iterations
    )
    autodev = AutoDevIntegration(config)
    
    async def _run():
        await autodev.initialize()
        
        if not autodev.prd_data:
            console.print("❌ 没有找到 prd.json，请先运行 'code-gen autodev convert'", style="red")
            return
        
        # 显示状态
        status = autodev.status()
        console.print(Panel(
            f"项目: {status['project']}\n"
            f"分支: {status['branch']}\n"
            f"进度: {status['progress']} ({status['percentage']:.1f}%)",
            title="AutoDev Status",
            border_style="blue"
        ))
        
        # 运行
        result = await autodev.run()
        
        # 显示结果
        stats = result.get("stats", {})
        console.print(Panel(
            f"总计: {stats.get('total', 0)}\n"
            f"完成: {stats.get('completed', 0)} ✅\n"
            f"失败: {stats.get('failed', 0)} ❌\n"
            f"跳过: {stats.get('skipped', 0)} ⏭️",
            title="执行结果",
            border_style="green" if result.get("success") else "red"
        ))
    
    asyncio.run(_run())


@app.command("status")
def show_status(
    work_dir: Optional[Path] = typer.Option(None, "--work-dir", "-w")
):
    """显示 AutoDev 执行状态"""
    work_dir = work_dir or Path.cwd()
    
    config = AutoDevConfig(work_dir=work_dir)
    autodev = AutoDevIntegration(config)
    
    status = autodev.status()
    
    if not status.get("prd_loaded"):
        console.print("❌ 没有加载 PRD，请先运行 'code-gen autodev convert'", style="red")
        return
    
    # 显示状态表格
    table = Table(title="AutoDev 执行状态")
    table.add_column("属性", style="cyan")
    table.add_column("值", style="green")
    
    table.add_row("状态", status.get("status", "Unknown"))
    table.add_row("项目", status.get("project", "N/A"))
    table.add_row("分支", status.get("branch", "N/A"))
    table.add_row("进度", status.get("progress", "0/0"))
    table.add_row("完成度", f"{status.get('percentage', 0):.1f}%")
    table.add_row("当前故事", str(status.get("current_story", 0)))
    
    console.print(table)
    
    # 显示进度文件
    progress_file = config.progress_file
    if progress_file.exists():
        console.print(f"\n📄 进度日志: {progress_file}")


@app.command("resume")
def resume_autodev(
    work_dir: Optional[Path] = typer.Option(None, "--work-dir", "-w")
):
    """从中断处恢复执行"""
    work_dir = work_dir or Path.cwd()
    
    config = AutoDevConfig(work_dir=work_dir)
    
    if not config.state_file.exists():
        console.print("❌ 没有找到状态文件，无法恢复", style="red")
        raise typer.Exit(1)
    
    console.print("🔄 恢复执行...", style="blue")
    
    # 恢复执行
    asyncio.run(_run_resume(config))


async def _run_resume(config: AutoDevConfig):
    """恢复执行的异步函数"""
    autodev = AutoDevIntegration(config)
    await autodev.initialize()
    
    result = await autodev.run()
    
    console.print(Panel(
        f"恢复执行完成\n"
        f"完成: {result.get('stats', {}).get('completed', 0)}\n"
        f"失败: {result.get('stats', {}).get('failed', 0)}",
        title="Resume Complete",
        border_style="green" if result.get("success") else "yellow"
    ))


# 添加命令组到主 CLI
def register_autodev_commands(cli_app: typer.Typer):
    """注册 AutoDev 命令到主 CLI"""
    cli_app.add_typer(app, name="autodev", help="AutoDev 自主开发集成")
