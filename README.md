# Microsoft Foundry Hosted Agent Lab

使用前提：**已有可运行并完成本地验证的 Microsoft Agent Framework（MAF）Agent**。
xAgent 是 Hosting 接入参考模板，重点展示如何使用 MAF 的 `ResponsesHostServer` 适配器实现 Responses 协议、
托管到 Microsoft Foundry Agent Service，
并使用 Foundry Evaluation、Trace、Monitor、Guardrails 和 Azure Monitor 完成部署后验证。

本仓库不要求把现有 Agent 重写成 xAgent。接入时保留已有 Agent、Tool、Workflow 和业务指令，
只复用本仓库中的 Hosting 入口、`azure.yaml`、部署脚本、评估样例和可观测性配置。

## 文档导航

| 文档 | 定位 | 入口 |
| --- | --- | --- |
| Microsoft Foundry Agent 托管部署与测试参考手册 | 面向开发、架构和平台工程人员；说明 Hosting 接入、Provision、Deploy、测试策略与验收标准 | [Markdown](docs/xAgent_Foundry构建部署与测试参考手册_v1.0.md) · [PDF](docs/xAgent_Foundry构建部署与测试参考手册_v1.0.pdf) |
| 性能、安全、遥测与 Guardrails 实验手册 | 面向测试、运维和安全人员；提供 Session、Trace、Monitor、Evaluation、Guardrail、性能与告警的独立实验和实测截图 | [Markdown](docs/xAgent_Foundry性能安全与Guardrails实验手册_v1.0.md) · [PDF](docs/xAgent_Foundry性能安全与Guardrails实验手册_v1.0.pdf) |
| 端到端部署与测试演示文稿 | 面向约 1 小时技术分享；26 页，包含架构图、实测截图、页码和逐页口播备注 | [下载 PPTX](docs/Foundry_Hosted_Agent_部署与测试_演示文稿.pptx) |
| macOS 操作指南 | 面向 Intel 与 Apple Silicon Mac；提供 zsh、Homebrew、az/azd、部署、测试和清理步骤 | [README_macOS.md](README_macOS.md) |

先用参考手册完成端到端接入并确定验收要求，再按需要从实验手册选择验证项目。macOS 用户先阅读操作指南，命令和路径均已按 macOS 环境调整。

### 按任务快速跳转

| 任务 | 直接进入主手册 |
| --- | --- |
| 了解架构与组件职责 | [总体架构](docs/xAgent_Foundry构建部署与测试参考手册_v1.0.md#architecture) |
| 为已有 MAF Agent 选择并实现托管协议 | [Hosting 接入检查](docs/xAgent_Foundry构建部署与测试参考手册_v1.0.md#hosting-adaptation) |
| 创建 Foundry Project、模型和资源组 | [创建 Foundry 资源](docs/xAgent_Foundry构建部署与测试参考手册_v1.0.md#foundry-provision) |
| 部署前验证 Hosting 兼容性 | [本地 Hosting 验证](docs/xAgent_Foundry构建部署与测试参考手册_v1.0.md#local-debug) |
| 部署并调用 Hosted Agent | [托管部署](docs/xAgent_Foundry构建部署与测试参考手册_v1.0.md#hosted-deployment) |
| 执行 Agent Prompt Smoke Test | [Prompt 测试](docs/xAgent_Foundry构建部署与测试参考手册_v1.0.md#prompt-testing) |
| 执行批量质量与安全评估 | [Evaluation](docs/xAgent_Foundry构建部署与测试参考手册_v1.0.md#evaluation) |
| 查看 Agent Session 日志 | [Hosted Session 日志](docs/xAgent_Foundry构建部署与测试参考手册_v1.0.md#agent-session-logs) |
| 查看 Foundry Trace 与 Span | [Foundry Portal Trace](docs/xAgent_Foundry构建部署与测试参考手册_v1.0.md#agent-traces) |
| 查看 Monitor 指标与告警 | [Agent Monitoring Dashboard](docs/xAgent_Foundry构建部署与测试参考手册_v1.0.md#agent-monitoring) |
| 配置并验证 Guardrails | [Guardrails](docs/xAgent_Foundry构建部署与测试参考手册_v1.0.md#guardrails) |
| 执行性能与负载测试 | [性能测试](docs/xAgent_Foundry构建部署与测试参考手册_v1.0.md#performance-testing) |

具体命令、适用场景和执行顺序请参阅参考手册。

## 技术路径

```text
已有并通过本地验证的 MAF Agent
  -> 选择 Responses 或 Invocations 协议
  -> 本 Lab：ResponsesHostServer Hosting Adapter
  -> 本地 Hosting 兼容性验证
  -> azd deploy
  -> Microsoft Foundry 托管 Agent
  -> 远程调用 / Evaluation / Trace / Monitor / Guardrails / 性能测试
```

## 关键文件

| 文件 | 作用 |
| --- | --- |
| `azure.yaml` | Foundry Project、模型和 Hosted Agent 声明 |
| `src/agent-framework-agent-basic-responses/main.py` | xAgent 入口与系统指令 |
| `src/agent-framework-agent-basic-responses/requirements.txt` | Python 运行依赖 |
| `src/agent-framework-agent-basic-responses/devui.py` | 复用同一 xAgent 的本地 MAF DevUI 入口 |
| `src/agent-framework-agent-basic-responses/requirements-dev.txt` | DevUI 本地开发依赖，不参与托管部署 |
| `.vscode/tasks.json` | 本地 Agent Server 与 Inspector 任务 |
| `.vscode/launch.json` | debugpy 调试入口 |
| `docs/xAgent_Foundry构建部署与测试参考手册_v1.0.md` | Hosting 接入、部署、测试与运维参考步骤 |
| `docs/xAgent_Foundry性能安全与Guardrails实验手册_v1.0.md` | 性能、安全、遥测和 Guardrails 实验 |
| `infra/observability.bicep` | Application Insights 与 Log Analytics |
| `scripts/get-lab-context.ps1` | 自动发现当前 azd/Azure 环境资源名称 |
| `scripts/connect-observability.ps1` | 动态连接当前环境的 Application Insights |
| `scripts/show_context.py` | 显示当前 azd/Foundry/Agent 上下文 |
| `scripts/connect_observability.py` | 连接 App Insights 并配置 Project MI 权限 |
| `scripts/apply-hosted-agent-guardrail.ps1` | Hosted Agent Guardrail REST 回退脚本 |
| `scripts/invoke_hosted.py` | 使用 Azure AI Projects SDK 调用远程 Hosted Agent |
| `scripts/compare_agent.py` | 使用同一 JSONL 对比本地和 Hosted Agent |
| `scripts/send_traffic.py` | 生成受控流量以填充 Trace 与 Monitor |
| `scripts/locustfile.py` | Hosted Agent 并发负载测试 |
| `scripts/continuous_eval.py` | 基于近期 Trace 配置持续评估 |
| `scripts/configure_eval_alert.py` | 配置 Azure Monitor 评估通过率告警 |
| `scripts/verify_monitoring.py` | 验证容器遥测配置与 App Insights 摄取 |
| `scripts/run_ops.sh` | macOS/Linux 测试与监控入口 |
| `scripts/run_ops.cmd` | Windows 测试与监控入口 |
| `src/agent-framework-agent-basic-responses/eval-security.yaml` | 可复用的质量与安全评估配置 |
| `tests/test_project_contract.py` | 不调用 Azure 的项目契约测试 |

## 获取自己的实验环境

每次 `azd` 初始化和 Provision 都可能生成不同的资源组、Foundry Account 后缀、Project、Agent 与监控资源名称。不要复制文档中的示例资源名。

完成 Provision 后，在项目根目录执行：

```bash
python scripts/show_context.py
```

需要 PowerShell 结构化对象时执行：

```powershell
$ctx = .\scripts\get-lab-context.ps1
$ctx | Format-List
```

| 项目 | 动态来源 |
| --- | --- |
| 资源组 | `$ctx.ResourceGroup` |
| 区域 | `$ctx.Location` |
| Foundry Account | `$ctx.FoundryAccountName` |
| Foundry 项目 | `$ctx.FoundryProjectName` |
| 模型部署 | `$ctx.ModelDeploymentName` |
| Agent | `$ctx.AgentName` |
| 协议 | Responses 2.0 |
| 部署模式 | 直接代码部署 |
| Agent 框架 | Microsoft Agent Framework |
| Application Insights | `$ctx.ApplicationInsightsName` |
| Log Analytics | `$ctx.LogAnalyticsName` |
| 防护栏 | `Microsoft.DefaultV2` |

`get-lab-context.ps1` 只读取当前 azd 环境和目标资源组。订阅 ID、资源 ID 和 endpoint 仅用于本地操作，不应粘贴到公开材料。

## 测试与监控

共同前提：Python 3.13、`uv`、Azure Developer CLI、有效的 `azd auth login`，以及已选择并部署过的 azd environment。
依赖按用途拆分，避免全部安装：Hosted runtime 使用服务目录的 `requirements.txt`，DevUI 使用 `requirements-dev.txt`，
SDK/比较/顺序流量/持续评估/告警使用根目录的 `requirements-ops.txt`，Locust 仅在压测时使用
`requirements-load.txt`。首次运行 Ops：

```bash
uv venv .venv-local --python 3.13
uv pip install --python .venv-local/bin/python --prerelease allow -r requirements-ops.txt
```

Windows 将 Python 路径改为 `.venv-local\Scripts\python.exe`。也可按操作系统使用入口脚本：

```text
scripts\run_ops.cmd scripts\invoke_hosted.py "<prompt>"
./scripts/run_ops.sh scripts/invoke_hosted.py "<prompt>"
```

仅在运行 Locust 前安装可选负载依赖：

```bash
uv pip install --python .venv-local/bin/python --prerelease allow -r requirements-load.txt
```

完整命令、成本控制和验证顺序见两份参考手册。

## 本地配置

服务目录中的 `.env` 只包含非秘密的 Foundry Project endpoint 和模型部署名，并已被 `.gitignore` 排除。不要向 `.env` 写入 Token、API Key 或客户端密码。

Windows 深层工作区可能触发 Python 长路径问题。建议将代码放在较短路径，例如 `C:\labs\xagent`。如果不能移动，可临时使用 `subst` 映射短盘符。

## 清理

不再需要实验环境时执行：

```powershell
azd down --purge --force
```

该命令会删除本 azd 环境创建的 Resource Group、Foundry Project、模型部署和相关数据。执行前应再次确认目标环境。
