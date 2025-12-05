from typing import Any, Optional, List, Dict
import subprocess
import os
import asyncio

from agent.config import MCPServer

# MCP Python SDK（modelcontextprotocol）
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPClient:
    """MCP 客户端：进程管理 + stdio 协议工具调用。

    函数级注释：
    - 进程管理：兼容早期骨架（启动/停止），但工具调用优先通过 stdio 协议与服务器交互。
    - stdio 客户端：按需连接每个 MCP 服务器，拉取工具列表与执行工具调用。
    - 轻量去耦：不与上层 Agent 强绑定；上层通过 `use_tool` 调用本客户端。
    """

    def __init__(self, servers: Optional[List[MCPServer]] = None) -> None:
        """初始化客户端。

        参数：
        - servers: 来自配置的 MCPServer 列表；可为空，稍后再注入。
        """
        self.servers: List[MCPServer] = servers or []
        self.processes: Dict[str, subprocess.Popen] = {}

    def list_configured(self) -> List[str]:
        """返回已配置的 MCP 服务器名称列表。"""
        return [s.name for s in self.servers]

    def start_all(self) -> List[str]:
        """按配置启动全部 MCP 服务器进程，返回成功启动的服务名列表。

        说明：
        - 使用 `command + args` 启动；合并 `env` 与当前环境变量。
        - 注意：工具调用不依赖此启动；stdio 客户端会按需启动并连接。
        """
        started: List[str] = []
        for srv in self.servers:
            if srv.name in self.processes and self.processes[srv.name].poll() is None:
                continue  # 已在运行
            cmd = [srv.command] + (srv.args or [])
            env = os.environ.copy()
            env.update(srv.env or {})
            try:
                proc = subprocess.Popen(cmd, env=env)
                self.processes[srv.name] = proc
                started.append(srv.name)
            except Exception:
                # 启动失败时暂不抛出，后续在具体接入时再做细粒度错误处理
                pass
        return started

    def get_status(self) -> Dict[str, bool]:
        """返回各 MCP 服务器的运行状态字典：name -> 是否运行。"""
        status: Dict[str, bool] = {}
        for name, proc in self.processes.items():
            status[name] = (proc.poll() is None)
        # 未启动但在配置中的也返回 False
        for srv in self.servers:
            status.setdefault(srv.name, False)
        return status

    def stop_all(self) -> List[str]:
        """停止全部已启动的 MCP 服务器进程，返回已停止的服务名。"""
        stopped: List[str] = []
        for name, proc in list(self.processes.items()):
            try:
                proc.terminate()
                stopped.append(name)
            except Exception:
                pass
            finally:
                self.processes.pop(name, None)
        return stopped

    # ===== stdio 客户端实现 =====
    async def _with_session(self, srv: MCPServer, coro):
        """为给定服务器创建一次性的 stdio 会话，运行指定协程，并确保清理资源。"""
        params = StdioServerParameters(
            command=srv.command,
            args=srv.args or [],
            env=(srv.env or None),
        )
        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                return await coro(session)

    def list_tools(self, server_name: Optional[str] = None) -> Dict[str, List[str]]:
        """列出各服务器可用的工具名称列表。

        返回：{ server_name: [tool_name, ...], ... }
        """
        async def _list_for_srv(srv: MCPServer):
            async def _run(session: ClientSession):
                ret = await session.list_tools()
                return [t.name for t in ret.tools]
            try:
                return await self._with_session(srv, _run)
            except Exception:
                return []

        async def _gather():
            result: Dict[str, List[str]] = {}
            for srv in self.servers:
                if server_name and srv.name != server_name:
                    continue
                names = await _list_for_srv(srv)
                result[srv.name] = names
            return result

        return asyncio.run(_gather())

    def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None, server_name: Optional[str] = None) -> Any:
        """调用指定名称的 MCP 工具。

        参数：
        - name: 工具名
        - arguments: 工具入参（字典）
        - server_name: 限定在某个服务器上调用；空则在配置服务器中轮询查找。

        返回：协议的 `CallToolResult` 或其 `content` 字段（若存在）。
        """
        arguments = arguments or {}

        async def _try_call(srv: MCPServer):
            async def _run(session: ClientSession):
                # 先列出工具以确认存在
                try:
                    ret = await session.list_tools()
                    names = [t.name for t in ret.tools]
                    if name not in names:
                        raise RuntimeError("tool_not_found")
                except Exception:
                    raise
                # 调用工具
                result = await session.call_tool(name=name, arguments=arguments)
                # result 可能包含 `content` 字段
                try:
                    return getattr(result, "content", result)
                except Exception:
                    return result
            return await self._with_session(srv, _run)

        async def _run_all():
            # 如限定服务器，则仅对该服务器尝试
            servers = [s for s in self.servers if (not server_name or s.name == server_name)]
            if not servers:
                raise RuntimeError("未找到匹配的 MCP 服务器配置")
            last_err: Optional[Exception] = None
            for srv in servers:
                try:
                    return await _try_call(srv)
                except Exception as e:
                    last_err = e
                    continue
            # 所有尝试失败
            raise RuntimeError(f"工具调用失败：{name}; 最后错误：{last_err}")

        return asyncio.run(_run_all())