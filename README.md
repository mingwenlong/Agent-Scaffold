# Agent 框架（Ollama / HuggingFace / MCP）

本项目提供一个最小可用的 Agent 脚手架，支持：
- 本地 **Ollama** 模型（如 `llama3` 等）
- 本地 **Hugging Face Transformers** 模型（如 `Qwen/Qwen2-0.5B-Instruct` 等）
- **MCP（Model Context Protocol）** 客户端占位，便于后续接工具服务器

## 环境准备

1. 使用 Conda 创建环境（已由脚本完成）：
   - `conda create -n agent python=3.10 -y`
   - `conda activate agent`
2. 安装依赖（已由脚本完成）：
   - `pip install -U pip setuptools wheel`
   - `pip install -r requirements.txt`
3. 安装并运行 Ollama（可选，如果使用 Ollama 提供模型）：
   - Windows 安装 Ollama 后，确保本地服务运行（默认 `http://localhost:11434`）。
   - 拉取模型示例：`ollama pull llama3`

## 配置

编辑项目根目录的 `config.yaml` 来选择模型提供方与模型名，并配置 MCP 服务器：

```yaml
provider: ollama  # 可选：ollama 或 huggingface
model_name: gpt-oss:20b
max_new_tokens: 512
temperature: 0.7
device: cpu      # huggingface 使用；可选 cpu 或 cuda
mcp_servers:
  - name: github
    command: mcp-github
  - name: filesystem
    command: mcp-filesystem
  - name: semgrep
    command: mcp-semgrep
```

> 注意：如果使用 Hugging Face，请将 `model_name` 设置为你希望下载的模型，例如：`Qwen/Qwen2-0.5B-Instruct`。

## 运行

交互式对话（默认读取 `config.yaml`）：

```bash
python cli.py chat
```

指定提供方与模型（覆盖配置）：

```bash
python cli.py chat --provider ollama --model gpt-oss:20b --stream
python cli.py chat --provider huggingface --model Qwen/Qwen2-0.5B-Instruct
```

打印 MCP 配置与单次生成：

```bash
python cli.py run --list_tools "展示已配置的 MCP 服务器"
```

无交互单次运行：

```bash
python cli.py run "你好，测试一次生成"
python cli.py run --provider ollama --model gpt-oss:20b "用中文解释 MCP 的作用"
```

批量运行（每行一个 prompt）：

```bash
# 假设 prompts.txt 每行一个输入
python cli.py batch prompts.txt --provider huggingface --model Qwen/Qwen2-0.5B-Instruct --output_file results.json
```

远程连接 Ollama（例如在 Vast.ai 上）：

```bash
set OLLAMA_HOST=http://<server-ip>:11434  # Windows PowerShell
# 或 Linux/macOS：export OLLAMA_HOST=http://<server-ip>:11434
python cli.py chat --provider ollama --model gpt-oss:20b
```

### 在 AutoDL 服务器运行

1. 在服务器上准备 Conda/Python 环境与依赖：
   - `conda create -n agent python=3.10 -y && conda activate agent`
   - `pip install -r requirements.txt`
2. 如使用 Ollama，确保服务已运行并拉取模型：
   - `curl -fsSL https://ollama.com/install.sh | sh`（Linux）
   - `ollama pull gpt-oss:20b`
3. 使用环境变量覆盖关键参数（无需改配置文件）：
   - `export AGENT_PROVIDER=ollama`
   - `export AGENT_MODEL_NAME=gpt-oss:20b`
   - `export OLLAMA_HOST=http://localhost:11434`（如远程）
   - 可选：`export AGENT_MAX_NEW_TOKENS=512`、`export AGENT_TEMPERATURE=0.7`、`export AGENT_DEVICE=cpu`
4. 运行命令：
   - `python cli.py run "你好，AutoDL 上的单次运行"`
   - 批量：`python cli.py batch prompts.txt --output_file results.json`

> 提示：若需对外访问，确保平台侧已放通端口或采用隧道方式；内部使用则可直接本机访问。

MCP 服务器（公开示例）建议先行安装：`mcp-github`、`mcp-filesystem`、`mcp-semgrep`。
客户端已接入 stdio 协议，支持列出与调用工具；请确保上述命令在 PATH 可执行，并按需提供环境变量（如 GitHub Token）。

### MCP 工具使用示例

列出 MCP 工具（全部或指定服务器）：

```bash
python cli.py tools list
python cli.py tools list --server github
```

调用 MCP 工具（传入 JSON 参数）：

```bash
# 示例：调用 filesystem 的读取工具（工具名以实际服务器提供为准）
python cli.py tools call read_file --server filesystem --arguments '{"path": "./README.md"}'

# 示例：调用 github 的工具（需先配置 token 等环境变量，具体依服务器文档）
python cli.py tools call list_issues --server github --arguments '{"repo": "owner/name"}'

# 示例：调用 semgrep 分析（需本机安装 semgrep）
python cli.py tools call scan_repo --server semgrep --arguments '{"path": "./"}'
```

> 说明：本项目的 MCP 客户端已接入 stdio 协议，命令会按需启动并连接服务器，拉取工具列表后执行调用；请确保相关 MCP 服务器可用并在 PATH 或通过配置的 `command/args/env` 正确指定。

输入你的提问，按回车获得回复；输入 `exit` 退出。

## 目录结构

```
agent/
  core/agent.py           # 对话循环与上下文
  models/
    base.py               # 模型统一接口
    ollama.py             # Ollama 适配器
    huggingface.py        # HF 适配器
  tools/mcp_client.py     # MCP 客户端占位
config.yaml               # 默认配置
cli.py                    # 命令行入口
requirements.txt          # 依赖列表
```

## MCP 说明

当前已接入 MCP Python SDK（stdio），支持：
- 通过 `cli.py tools list` 列出各服务器的可用工具
- 通过 `cli.py tools call` 调用指定工具，并传入 JSON 参数

请确保所需的 MCP 服务器（如 `mcp-github`、`mcp-filesystem`、`mcp-semgrep`）已安装并可执行；如需令牌或环境配置，请在 `config.yaml` 的 `mcp_servers.env` 中添加或直接在环境变量中提供。

## 常见问题

- 如果使用 Hugging Face，本地首次加载会自动下载模型，建议选用小尺寸模型以加快启动和推理。
- Windows 下 GPU 使用需安装匹配的 CUDA 版本与对应的 `torch`，当前默认安装的是 CPU 版 `torch`。