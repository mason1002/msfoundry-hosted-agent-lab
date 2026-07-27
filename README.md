# Microsoft Foundry Hosted Agent Lab

本仓库提供一个可运行的 xAgent 参考实现，展示如何使用 Microsoft Agent Framework、Microsoft Foundry 和 Azure Developer CLI 完成 Agent 的构建、本地测试、托管部署、远程调用与评估。

## 文档导航

| 文档 | Markdown | PDF |
| --- | --- | --- |
| Foundry 构建、托管部署与测试参考手册 | [在线阅读](docs/xAgent_Foundry构建部署与测试参考手册_v1.0.md) | [下载 PDF](docs/xAgent_Foundry构建部署与测试参考手册_v1.0.pdf) |
| 性能、安全、遥测与 Guardrails 实验手册 | [在线阅读](docs/xAgent_Foundry性能安全与Guardrails实验手册_v1.0.md) | [下载 PDF](docs/xAgent_Foundry性能安全与Guardrails实验手册_v1.0.pdf) |

### 按任务快速跳转

| 我想做什么 | 直接进入主手册 |
| --- | --- |
| 了解架构与组件职责 | [总体架构](docs/xAgent_Foundry构建部署与测试参考手册_v1.0.md#architecture) |
| 本地运行与 Prompt 调试 | [本地运行与调试](docs/xAgent_Foundry构建部署与测试参考手册_v1.0.md#local-debug) |
| 部署并调用 Hosted Agent | [托管部署](docs/xAgent_Foundry构建部署与测试参考手册_v1.0.md#hosted-deployment) |
| 执行 Agent Prompt Smoke Test | [Prompt 测试](docs/xAgent_Foundry构建部署与测试参考手册_v1.0.md#prompt-testing) |
| 执行批量质量与安全评估 | [Evaluation](docs/xAgent_Foundry构建部署与测试参考手册_v1.0.md#evaluation) |
| 查看 Agent Session 日志 | [Hosted Session 日志](docs/xAgent_Foundry构建部署与测试参考手册_v1.0.md#agent-session-logs) |
| 查看 Foundry Trace 与 Span | [Foundry Portal Trace](docs/xAgent_Foundry构建部署与测试参考手册_v1.0.md#agent-traces) |
| 查看 Monitor 指标与告警 | [Agent Monitoring Dashboard](docs/xAgent_Foundry构建部署与测试参考手册_v1.0.md#agent-monitoring) |
| 配置并验证 Guardrails | [Guardrails](docs/xAgent_Foundry构建部署与测试参考手册_v1.0.md#guardrails) |
| 执行性能与负载测试 | [性能测试](docs/xAgent_Foundry构建部署与测试参考手册_v1.0.md#performance-testing) |

## 技术路径

```text
Agent Framework Python 代码
  -> ResponsesHostServer
  -> azd ai agent run
  -> 本地 Responses endpoint
  -> azd deploy
  -> Microsoft Foundry 托管 Agent
  -> azd ai agent invoke / 评估
```

## 关键文件

| 文件 | 作用 |
| --- | --- |
| `azure.yaml` | Foundry Project、模型和 Hosted Agent 声明 |
| `src/agent-framework-agent-basic-responses/main.py` | xAgent 入口与系统指令 |
| `src/agent-framework-agent-basic-responses/requirements.txt` | Python 运行依赖 |
| `.vscode/tasks.json` | 本地 Agent Server 与 Inspector 任务 |
| `.vscode/launch.json` | debugpy 调试入口 |
| `docs/xAgent_Foundry构建部署与测试参考手册_v1.0.md` | 构建、部署、测试与运维参考步骤 |
| `docs/xAgent_Foundry性能安全与Guardrails实验手册_v1.0.md` | 性能、安全、遥测和 Guardrails 实验 |
| `infra/observability.bicep` | Application Insights 与 Log Analytics |
| `scripts/get-lab-context.ps1` | 自动发现当前 azd/Azure 环境资源名称 |
| `scripts/connect-observability.ps1` | 动态连接当前环境的 Application Insights |
| `scripts/apply-hosted-agent-guardrail.ps1` | Hosted Agent Guardrail REST 回退脚本 |
| `scripts/requirements-docs.txt` | 生成参考资料 PDF 所需的独立 Python 依赖 |
| `src/agent-framework-agent-basic-responses/eval-security.yaml` | 可复用的质量与安全评估配置 |
| `tests/test_project_contract.py` | 不调用 Azure 的项目契约测试 |

## 获取自己的训练环境

每次 `azd` 初始化和 Provision 都可能生成不同的资源组、Foundry Account 后缀、Project、Agent 与监控资源名称。不要复制文档中的示例资源名。

完成 Provision 后，在项目根目录执行：

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

## 常用命令

所有 `azd` 命令都应在项目根目录执行。

```powershell
$env:AZURE_DEV_USER_AGENT = 'microsoft_foundry_skill'

azd ai project show --output json
azd ai agent run --no-client
azd ai agent invoke --local "请用三步说明 Hosted Agent 的部署流程。"
$ctx = .\scripts\get-lab-context.ps1
azd env set AZURE_AI_RAI_POLICY_ID $ctx.RaiPolicyId
azd deploy --no-prompt
azd ai agent show --output json
azd ai agent invoke "请解释本地运行和托管部署的区别。"
azd ai agent eval run
```

性能、安全、Portal/CLI 评估、追踪、监控、AI 红队测试与防护栏的完整步骤见两份参考手册。

重新生成 PDF 时，使用独立环境安装文档工具依赖：

```powershell
python -m venv .venv-docs
.\.venv-docs\Scripts\python.exe -m pip install -r .\scripts\requirements-docs.txt
.\.venv-docs\Scripts\python.exe .\scripts\render_reference_docs.py .\docs\xAgent_Foundry构建部署与测试参考手册_v1.0.md .\docs\xAgent_Foundry性能安全与Guardrails实验手册_v1.0.md
```

Observability 资源也采用动态名称：

```powershell
$ctx = .\scripts\get-lab-context.ps1
az deployment group create `
  --name xagent-observability `
  --resource-group $ctx.ResourceGroup `
  --template-file .\infra\observability.bicep
.\scripts\connect-observability.ps1
```

## 本地配置

服务目录中的 `.env` 只包含非秘密的 Foundry Project endpoint 和模型部署名，并已被 `.gitignore` 排除。不要向 `.env` 写入 Token、API Key 或客户端密码。

Windows 深层工作区可能触发 Python 长路径问题。建议将代码放在较短路径，例如 `C:\labs\xagent`。如果不能移动，可临时使用 `subst` 映射短盘符。

## 清理

不再需要实验环境时执行：

```powershell
azd down --purge --force
```

该命令会删除本 azd 环境创建的 Resource Group、Foundry Project、模型部署和相关数据。执行前应再次确认目标环境。
