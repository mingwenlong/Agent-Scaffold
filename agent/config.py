from pydantic import BaseModel
import yaml
from pathlib import Path
from typing import List, Dict
import os


class MCPServer(BaseModel):
    name: str
    command: str
    args: List[str] = []
    env: Dict[str, str] = {}


class Config(BaseModel):
    provider: str = "ollama"  # or "huggingface"
    model_name: str = "llama3"
    max_new_tokens: int = 256
    temperature: float = 0.7
    device: str = "cpu"  # for huggingface: cpu or cuda
    mcp_servers: List[MCPServer] = []


def load_config(path: Path | None = None) -> Config:
    """加载配置文件并应用环境变量覆盖，返回最终的 Config。

    函数级注释：
    - 默认读取项目根目录下的 `config.yaml`，并解析为 Config。
    - 支持通过环境变量覆盖关键参数，便于在 AutoDL/Vast.ai 等服务器上无改文件运行：
      - AGENT_PROVIDER（ollama 或 huggingface）
      - AGENT_MODEL_NAME（如 gpt-oss:20b 或 HF 仓库名）
      - AGENT_MAX_NEW_TOKENS（整数）
      - AGENT_TEMPERATURE（浮点数）
      - AGENT_DEVICE（cpu 或 cuda）
    - 若配置文件不存在，返回带默认值的 Config。
    """
    path = path or Path("config.yaml")
    data = {}
    if path.exists():
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    cfg = Config(**data)

    provider = os.getenv("AGENT_PROVIDER")
    if provider:
        cfg.provider = provider

    model = os.getenv("AGENT_MODEL_NAME")
    if model:
        cfg.model_name = model

    max_new = os.getenv("AGENT_MAX_NEW_TOKENS")
    if max_new:
        try:
            cfg.max_new_tokens = int(max_new)
        except ValueError:
            pass

    temp = os.getenv("AGENT_TEMPERATURE")
    if temp:
        try:
            cfg.temperature = float(temp)
        except ValueError:
            pass

    device = os.getenv("AGENT_DEVICE")
    if device:
        cfg.device = device

    return cfg