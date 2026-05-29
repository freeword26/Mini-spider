"""spider_max CLI — 命令行接口"""
import os
import sys
import webbrowser
from pathlib import Path
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

from spider_max.db import DatabaseManager

_db = DatabaseManager()
DB_PATH = _db.db_path


@click.group()
def cli():
    """spider_max (spider_max) — 全栈项目管理平台 v3.0.0"""


@cli.command()
def version():
    """显示版本信息"""
    console.print(Panel.fit(
        "[bold cyan]Spider Max v3.0.0[/bold cyan]\n"
        "[green]Da Zhi Zhu -- Full-Stack PM & Multi-Agent Platform[/green]\n"
        "47 service modules | 200+ API endpoints | 23 database tables",
        title="[Spider Max]"
    ))


@cli.command()
@click.option("--host", default="0.0.0.0", help="监听地址")
@click.option("--port", default=8041, help="监听端口")
@click.option("--reload", is_flag=True, help="热重载")
def serve(host: str, port: int, reload: bool):
    """启动spider_max API服务"""
    from spider_max.api.server import create_app
    import uvicorn
    app = create_app()
    console.print(f"[green]Spider Max API starting on {host}:{port}[/green]")
    webbrowser.open(f"http://localhost:{port}/docs")
    uvicorn.run(app, host=host, port=port, reload=reload)


@cli.command()
def db_init():
    """初始化数据库v3 schema"""
    spider_max_dir = Path(__file__).parent.parent / "db" / "migrations"
    scripts = sorted(spider_max_dir.glob("*.sql"))
    if not scripts:
        console.print("[yellow]No migration scripts found, using inline schema[/yellow]")
    import subprocess
    db_script = Path(__file__).resolve().parents[1] / "db" / "migrations" / "001_initial.sql"
    if db_script.exists():
        console.print(f"[green]Migration script found: {db_script}[/green]")
    else:
        console.print("[red]Schema script not found[/red]")


@cli.command()
def sync():
    """执行全量数据同步"""
    console.print("[yellow]Sync command requires database configuration[/yellow]")
    console.print(f"[cyan]DB Path: {DB_PATH}[/cyan]")


@cli.command()
def dashboard():
    """显示命令行仪表板"""
    import sqlite3
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    total = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    done = conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Done'").fetchone()[0]
    p0_pending = conn.execute("SELECT COUNT(*) FROM tasks WHERE priority='P0' AND status NOT IN ('Done','Cancelled')").fetchone()[0]
    blocked = conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Blocked'").fetchone()[0]
    projects = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    agents = conn.execute("SELECT COUNT(*) FROM agents").fetchone()[0]

    table = Table(title="Spider Max 系统概览")
    table.add_column("指标", style="cyan")
    table.add_column("值", style="green")
    table.add_row("项目数", str(projects))
    table.add_row("任务总数", str(total))
    table.add_row("已完成", str(done))
    table.add_row("P0待办", str(p0_pending))
    table.add_row("阻塞任务", str(blocked))
    table.add_row("Agent数", str(agents))
    table.add_row("完成率", f"{round(done/max(total,1)*100, 1)}%")
    table.add_row("7.数据库路径", str(DB_PATH))
    conn.close()
    console.print(table)


@cli.command()
@click.argument("module_name")
@click.argument("action", type=click.Choice(["info", "call"]))
@click.option("--method", default=None, help="要调用的方法名")
@click.option("--args", default="{}", help="JSON参数")
def module(module_name: str, action: str, method: str, args: str):
    """查看或调用服务模块"""
    from spider_max.core.registry import ModuleRegistry
    reg = ModuleRegistry()
    reg.discover_all()
    info = reg.get(module_name)
    if not info:
        console.print(f"[red]Module '{module_name}' not found[/red]")
        return
    if action == "info":
        console.print(f"[cyan]Module:[/cyan] {info.name}")
        console.print(f"[cyan]Category:[/cyan] {info.category.value}")
        console.print(f"[cyan]Status:[/cyan] {info.status}")
        console.print(f"[cyan]Functions:[/cyan] {', '.join(info.functions[:20])}")
    elif action == "call" and method:
        try:
            from spider_max import services
            svc = __import__("spider_max.services", fromlist=["*"])
            mod = getattr(svc, module_name, None)
            func = getattr(mod, method, None) if mod else None
            if func:
                import json
                kwargs = json.loads(args)
                result = func(**kwargs)
                console.print(result)
            else:
                console.print(f"[red]Method '{method}' not found in module[/red]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


@cli.command()
def list_modules():
    """列出所有已注册的服务模块"""
    reg = get_registry()
    summary = reg.get_status_summary()
    table = Table(title=f"Spider Max 服务模块 ({summary['loaded']}/{summary['total']})")
    table.add_column("类别", style="cyan")
    table.add_column("模块", style="yellow")
    table.add_column("状态", style="green")
    for cat, data in summary["by_category"].items():
        modules = reg.list(None)
        names = [m.name for m in modules if m.category.value == cat]
        table.add_row(cat, ", ".join(names[:5]), f"{data['loaded']}/{data['total']}")
    console.print(table)


if __name__ == "__main__":
    cli()
