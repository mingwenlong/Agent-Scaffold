import typer
from typing import Optional
from agent.core.agent import ChatAgent
from agent.config import load_config, Config
from agent.tools.mcp_client import MCPClient
from rich.console import Console

app = typer.Typer(help="Agent CLI")
console = Console()
tools_app = typer.Typer(help="MCP 工具相关命令")
app.add_typer(tools_app, name="tools")


@app.command()
def chat(
    provider: Optional[str] = typer.Option(None, help="模型提供方：ollama 或 huggingface"),
    model: Optional[str] = typer.Option(None, help="模型名称"),
    stream: bool = typer.Option(False, help="是否流式输出"),
):
    """交互式对话模式。

    函数级注释：
    - 加载配置并支持通过参数覆盖 provider 与 model_name。
    - 显示已配置的 MCP 服务器列表，便于确认工具环境。
    - 提供一个简单的 REPL，对用户输入逐条生成并输出结果。
    """
    cfg: Config = load_config()
    if provider:
        cfg.provider = provider
    if model:
        cfg.model_name = model

    agent = ChatAgent(cfg)
    console.print(f"[bold green]Provider:[/bold green] {cfg.provider}, Model: {cfg.model_name}")
    if getattr(cfg, "mcp_servers", None):
        console.print("[bold blue]MCP Servers:[/bold blue]")
        for srv in cfg.mcp_servers:
            try:
                name = srv.name
                cmd = srv.command
            except Exception:
                # 兼容原始字典结构
                name = srv.get("name")
                cmd = srv.get("command")
            console.print(f" - {name}: {cmd}")

    while True:
        try:
            user_input = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if user_input.lower() in {"exit", "quit"}:
            break

        for chunk in agent.generate(user_input, stream=stream):
            print(chunk, end="", flush=True)
        print()

@app.command()
def run(
    prompt: str = typer.Argument(..., help="单次运行：给定 prompt，返回生成结果"),
    provider: Optional[str] = typer.Option(None, help="覆盖 provider：ollama 或 huggingface"),
    model: Optional[str] = typer.Option(None, help="覆盖模型名称，如 gpt-oss:20b"),
    stream: bool = typer.Option(True, help="尽可能启用流式输出"),
    list_tools: bool = typer.Option(False, help="启动时打印已配置的 MCP 服务器"),
):
    """无交互模式：执行一次生成任务。

    函数级注释：
    - 读取配置并支持参数覆盖，实例化 ChatAgent。
    - 可选打印 MCP 服务器列表。
    - 对单条 prompt 进行生成并输出，便于脚本化/流水线。
    """
    cfg: Config = load_config()
    if provider:
        cfg.provider = provider
    if model:
        cfg.model_name = model
    agent = ChatAgent(cfg)
    console.print(f"[bold green]Provider:[/bold green] {cfg.provider}, Model: {cfg.model_name}")
    if list_tools and getattr(cfg, "mcp_servers", None):
        console.print("[bold blue]MCP Servers:[/bold blue]")
        for srv in cfg.mcp_servers:
            try:
                name = srv.name
                cmd = srv.command
            except Exception:
                name = srv.get("name")
                cmd = srv.get("command")
            console.print(f" - {name}: {cmd}")

    for chunk in agent.generate(prompt, stream=stream):
        print(chunk, end="", flush=True)
    print()

@app.command()
def batch(
    input_file: str = typer.Argument(..., help="包含多行 prompt 的文本文件，每行一个"),
    provider: Optional[str] = typer.Option(None, help="覆盖 provider：ollama 或 huggingface"),
    model: Optional[str] = typer.Option(None, help="覆盖模型名称，如 gpt-oss:20b"),
    stream: bool = typer.Option(False, help="批量模式通常不启用流式输出"),
    output_file: Optional[str] = typer.Option(None, help="可选：将结果写入指定输出文件"),
):
    """批量运行：对文件中的多条 prompt 逐条生成。

    函数级注释：
    - 读取 input_file，每行作为一个独立 prompt。
    - 依次生成并打印结果，必要时写入 JSON 输出文件。
    - 适合离线数据预处理与实验跑批。
    """
    import os, json
    if not os.path.exists(input_file):
        console.print(f"[red]输入文件不存在：{input_file}[/red]")
        raise typer.Exit(code=1)

    cfg: Config = load_config()
    if provider:
        cfg.provider = provider
    if model:
        cfg.model_name = model
    agent = ChatAgent(cfg)
    console.print(f"[bold green]Provider:[/bold green] {cfg.provider}, Model: {cfg.model_name}")

    results = []
    with open(input_file, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            prompt = line.strip()
            if not prompt:
                continue
            console.print(f"\n[bold cyan]# {idx+1} Prompt[/bold cyan]: {prompt}")
            output_chunks = []
            for chunk in agent.generate(prompt, stream=stream):
                print(chunk, end="", flush=True)
                output_chunks.append(chunk)
            print()
            results.append({"prompt": prompt, "result": "".join(output_chunks)})

    if output_file:
        with open(output_file, "w", encoding="utf-8") as wf:
            json.dump(results, wf, ensure_ascii=False, indent=2)
        console.print(f"\n[bold green]已写入输出文件[/bold green]: {output_file}")

@tools_app.command("list")
def tools_list(server: Optional[str] = typer.Option(None, help="指定服务器名称；为空则列出全部")):
    """列出 MCP 服务器的可用工具。"""
    cfg: Config = load_config()
    client = MCPClient(cfg.mcp_servers)
    console.print("[bold blue]列出 MCP 工具[/bold blue]")
    result = client.list_tools(server_name=server)
    if not result:
        console.print("[yellow]未获取到任何工具，确认服务器安装与配置[/yellow]")
        return
    for srv, tools in result.items():
        console.print(f"\n[bold cyan]{srv}[/bold cyan]:")
        if tools:
            for t in tools:
                console.print(f" - {t}")
        else:
            console.print(" (无工具或连接失败)")

@tools_app.command("call")
def tools_call(
    name: str = typer.Argument(..., help="工具名称"),
    server: Optional[str] = typer.Option(None, help="指定服务器名称"),
    arguments: Optional[str] = typer.Option(None, help="JSON 格式的工具参数，如 '{\"path\": \"./README.md\"}'"),
):
    """调用指定 MCP 工具。"""
    import json
    cfg: Config = load_config()
    client = MCPClient(cfg.mcp_servers)
    args_dict = {}
    if arguments:
        try:
            args_dict = json.loads(arguments)
        except Exception:
            console.print("[red]参数解析失败：请提供合法 JSON[/red]")
            raise typer.Exit(code=1)
    console.print(f"[bold blue]调用工具[/bold blue]: {name} (server={server})")
    try:
        result = client.call_tool(name=name, arguments=args_dict, server_name=server)
    except Exception as e:
        console.print(f"[red]调用失败[/red]: {e}")
        raise typer.Exit(code=1)

    try:
        console.print_json(data=result)
    except Exception:
        console.print(result)

if __name__ == "__main__":
    app()