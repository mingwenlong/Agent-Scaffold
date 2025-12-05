from typing import Iterable, Optional, List, Any
from agent.config import Config
from agent.models.ollama import OllamaAdapter
from agent.models.huggingface import HFAdapter
from agent.tools.mcp_client import MCPClient


class ChatAgent:
    def __init__(self, cfg: Config):
        """初始化 Agent，并根据配置选择模型适配器。

        函数级注释：
        - 保存配置 `cfg`；根据 provider 初始化 Ollama 或 HuggingFace 适配器。
        - 预留 MCP 客户端挂钩 `self.mcp_client`，便于后续工具调用。
        """
        self.cfg = cfg
        self.mcp_client: Optional[MCPClient] = None
        if cfg.provider == "ollama":
            self.model = OllamaAdapter(cfg.model_name, temperature=cfg.temperature, max_new_tokens=cfg.max_new_tokens)
        elif cfg.provider == "huggingface":
            self.model = HFAdapter(cfg.model_name, device=cfg.device, temperature=cfg.temperature, max_new_tokens=cfg.max_new_tokens)
        else:
            raise ValueError(f"Unknown provider: {cfg.provider}")

    def generate(self, prompt: str, stream: bool = False) -> Iterable[str]:
        """调用底层模型生成结果，支持流式输出。"""
        yield from self.model.generate(prompt, stream=stream)

    def list_mcp_servers(self) -> List[str]:
        """返回配置中的 MCP 服务器名称列表。"""
        return [s.name for s in (self.cfg.mcp_servers or [])]

    def attach_mcp_client(self, client: MCPClient) -> None:
        """注入 MCP 客户端实例，用于后续工具调用。"""
        self.mcp_client = client

    def use_tool(self, tool_name: str, **kwargs) -> Any:
        """通过 MCP 客户端调用指定工具（占位）。

        说明：
        - 若未注入 MCP 客户端，则抛出错误提示。
       - 接口与 Agent 统一，后续可在对话流程中编排调用工具。
        """
        if not self.mcp_client:
            raise RuntimeError("MCP 客户端尚未注入，无法调用工具")
        return self.mcp_client.call_tool(tool_name, **kwargs)