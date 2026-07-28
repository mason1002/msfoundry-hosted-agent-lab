---
title: Microsoft Foundry Hosted Agent Lab
description: 使用 Microsoft Agent Framework、Microsoft Foundry 和 Azure Developer CLI 构建、部署、测试与评估 xAgent
ms.date: 2026-07-27
ms.topic: tutorial
---

本仓库提供一个可运行的 xAgent 参考实现，展示如何使用 Microsoft Agent Framework、Microsoft Foundry 和 Azure Developer CLI 完成 Agent 的构建、本地测试、托管部署、远程调用与评估。

## 文档导航

| 文档 | 定位 | 入口 |
| --- | --- | --- |
| Foundry 构建、托管部署与测试参考手册 | Hosting 接入、Provision、Deploy、测试策略与验收标准 | [Markdown](docs/xAgent_Foundry构建部署与测试参考手册_v1.0.md) · [PDF](docs/xAgent_Foundry构建部署与测试参考手册_v1.0.pdf) |
| 性能、安全、遥测与 Guardrails 实验手册 | Session、Trace、Monitor、Evaluation、Guardrail、性能与告警的独立实验和实测截图 | [Markdown](docs/xAgent_Foundry性能安全与Guardrails实验手册_v1.0.md) · [PDF](docs/xAgent_Foundry性能安全与Guardrails实验手册_v1.0.pdf) |
| 端到端部署与测试演示文稿 | 约 1 小时技术分享，含架构图、实测截图和逐页口播备注 | [下载 PPTX](docs/Foundry_Hosted_Agent_部署与测试_演示文稿.pptx) |
| 项目首页 | 项目定位、技术路径、关键文件和跨平台测试入口 | [README.md](README.md) |

本文件专门提供 macOS 命令与路径。先按本文件完成环境准备和部署，再使用参考手册理解整体方法，按需进入实验手册执行平台验证。

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
| `src/agent-framework-agent-basic-responses/eval-security.yaml` | 可复用的质量与安全评估配置 |
| `tests/test_project_contract.py` | 不调用 Azure 的项目契约测试 |

## macOS 快速开始

以下步骤适用于 Intel 和 Apple Silicon Mac，并只使用 zsh、Azure CLI 和 Azure Developer CLI。

> [!IMPORTANT]
> 本实验不是免费沙盒。`azd provision` 会创建 Foundry Account、Project 和模型部署，
> `azd deploy` 会创建 Hosted Agent，远程调用和评估会消耗模型 Token。可选的 Observability
> 步骤还会创建 Application Insights 和 Log Analytics。开始前，准备专用订阅、已验证支持
> `gpt-5.4-mini` 的区域和足够配额。不要使用生产订阅。

| 阶段 | 是否更改 Azure | 是否可能产生费用 |
| --- | --- | --- |
| 安装工具、登录、创建本地 azd environment | 否 | 否 |
| `azd provision --preview` | 否 | 否 |
| `azd provision`、`azd deploy` | 是 | 是 |
| 本地或远程模型调用、Evaluation | 是 | 是 |
| Observability | 是 | 是 |
| `azd down --purge` | 删除资源 | 停止后续资源费用 |

### 安装工具

先安装 [Homebrew](https://brew.sh/)，再执行：

```bash
brew update
brew install azure-cli
brew tap azure/azd
brew trust azure/azd
brew install azure/azd/azd
brew install uv
```

Homebrew 6 或启用了 tap 信任检查的版本会拒绝加载尚未信任的 `azure/azd`。
执行 `brew trust azure/azd` 前，可以先查看
[Azure Developer CLI Homebrew tap](https://github.com/Azure/homebrew-azd) 的来源。
安装和升级时使用完整限定名 `azure/azd/azd`，避免与 `homebrew/core` 中的同名公式冲突：

```bash
brew upgrade azure/azd/azd
```

也可以跳过该 tap，改用官方安装脚本：

```bash
curl -fsSL https://aka.ms/install-azd.sh | bash
```

验证工具是否可用：

```bash
az version
azd version
uv --version
```

### 登录并选择实验订阅

在项目根目录登录 Azure。浏览器无法自动打开时，`az login --use-device-code` 可改用设备代码登录。

```bash
az login
az account list --output table
az account set --subscription "<实验订阅名称或 ID>"
az account show --query '{name:name,id:id,tenantId:tenantId}' --output table
export AZURE_TENANT_ID="$(az account show --query tenantId --output tsv)"
azd auth login --tenant-id "$AZURE_TENANT_ID"
azd auth status
azd auth token --tenant-id "$AZURE_TENANT_ID" >/dev/null
azd extension install azure.ai.agents --no-prompt
azd extension show azure.ai.agents
```

`azure.ai.agents` 扩展提供 `azure.ai.agent` host。`azure.yaml` 中的
`requiredVersions` 要求该扩展不低于 `1.0.0-beta.4`。`azd auth token` 的输出被丢弃，该命令只验证
azd 能否在目标 tenant 获取令牌。不要继续操作，直到 `az account show` 显示指定的实验订阅，
token 检查成功，且扩展状态显示已安装。

如果 Preview 报告 `failed to resolve user access to subscription`，通常是 azd 仍缓存其他环境的
账号或 tenant。先退出两套 CLI，再使用目标 tenant ID 和订阅重新登录：

```bash
az logout
azd auth logout
az login --tenant "<目标 tenant ID>"
az account set --subscription "<实验订阅名称或 ID>"
export AZURE_TENANT_ID="$(az account show --query tenantId --output tsv)"
azd auth login --tenant-id "$AZURE_TENANT_ID"
azd auth token --tenant-id "$AZURE_TENANT_ID" >/dev/null
```

浏览器自动选择错误账号时，改用 `az login --tenant "<tenant ID>" --use-device-code`，并在设备登录页
明确选择目标实验账号。

### 创建隔离的 azd environment

每个实验使用独立的 environment 名称。以下命令在 macOS 默认的 zsh 和 Bash 中均可运行。
输入已验证模型可用性的区域，例如 `eastus`；不要根据示例自行选择区域。

```bash
export LAB_ENV_NAME="xagent-${USER:-student}"
export AZURE_SUBSCRIPTION_ID="$(az account show --query id --output tsv)"
printf '请输入已验证的 Azure 区域: '
read -r AZURE_LOCATION
export AZURE_LOCATION

azd env new "$LAB_ENV_NAME" \
  --subscription "$AZURE_SUBSCRIPTION_ID" \
  --location "$AZURE_LOCATION" \
  --no-prompt
azd env list
azd env get-value AZURE_SUBSCRIPTION_ID
azd env get-value AZURE_LOCATION
```

如果 `azd env new` 提示同名 environment 已存在，先运行 `azd env list`，然后为
`LAB_ENV_NAME` 选择新的名称。不要复用其他实验或生产环境。

### 预览并确认资源

Preview 只计算资源变化，不创建或修改 Azure 资源。运行后停下来检查输出，确认目标订阅、区域、
Resource Group、Foundry Project 和模型部署均属于本次实验。

```bash
export AZURE_DEV_USER_AGENT=microsoft_foundry_skill
azd provision --preview --no-prompt
```

> [!WARNING]
> 下一条命令会创建收费资源。只有在确认 Preview 和配额后才执行。实验默认流程不使用
> `--no-state`，因为该参数会忽略已保存的部署状态并强制重新部署。

```bash
azd provision --no-prompt
azd ai project show --output json
```

Provision 完成后，直接从当前 azd environment 读取动态上下文：

```bash
for key in \
  AZURE_RESOURCE_GROUP \
  AZURE_LOCATION \
  AZURE_AI_ACCOUNT_NAME \
  AZURE_AI_PROJECT_NAME \
  FOUNDRY_PROJECT_ENDPOINT; do
  printf '%s=%s\n' "$key" "$(azd env get-value "$key")"
done
```

`azd env get-values` 可能包含订阅 ID、资源 ID 和 endpoint。排障时不要把完整输出粘贴到公开聊天、
Issue 或共享截图中。

### 安装依赖并本地运行

Agent 使用 Python 3.13。`uv` 会在创建虚拟环境时安装或选择相应的 Python 版本。

```bash
cd src/agent-framework-agent-basic-responses
uv venv .venv --python 3.13
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python --version
cd ../..

export FOUNDRY_PROJECT_ENDPOINT="$(azd env get-value FOUNDRY_PROJECT_ENDPOINT)"
export AZURE_AI_MODEL_DEPLOYMENT_NAME="$(
  azd env get-value AI_PROJECT_DEPLOYMENTS |
    src/agent-framework-agent-basic-responses/.venv/bin/python -c \
      'import json, sys; raw = sys.stdin.read().strip(); data = json.loads(raw); data = json.loads(data) if isinstance(data, str) else data; print(data[0]["name"])'
)"
: "${FOUNDRY_PROJECT_ENDPOINT:?请先完成 azd provision}"
: "${AZURE_AI_MODEL_DEPLOYMENT_NAME:?当前 azd 环境没有模型部署}"

export AZURE_DEV_USER_AGENT=microsoft_foundry_skill
azd ai agent run --no-client
```

`azd provision` 将项目 endpoint 和模型部署清单保存在 azd environment 中，
但 `azd ai agent run` 不会自动把这些值导出给 Python 子进程。以上命令从当前训练环境读取配置，
不需要手工填写 endpoint 或模型名称。

服务就绪后，在另一个终端执行本地调用：

```bash
azd ai agent invoke --local "请用三步说明 Hosted Agent 的部署流程。"
```

VS Code 调试时选择 `src/agent-framework-agent-basic-responses/.venv/bin/python` 作为 Python 解释器。

### 部署和调用 Hosted Agent

先读取模型部署名称，并从已创建的 Foundry Account 推导内置 `Microsoft.DefaultV2` policy ID。
将两者写入当前 azd environment。该步骤必须在 `azd provision` 之后、`azd deploy` 之前执行；
只在终端中使用 `export` 不会保证部署时能解析 `azure.yaml` 中的变量。

```bash
model_deployment_name="$(
  azd env get-value AI_PROJECT_DEPLOYMENTS |
    python3 -c \
      'import json, sys; raw = sys.stdin.read().strip(); data = json.loads(raw); data = json.loads(data) if isinstance(data, str) else data; print(data[0]["name"])'
)"
project_id="$(azd env get-value AZURE_AI_PROJECT_ID)"
rai_policy_id="${project_id%/projects/*}/raiPolicies/Microsoft.DefaultV2"
: "${model_deployment_name:?当前 azd environment 没有模型部署}"
: "${project_id:?请先完成 azd provision}"
azd env set AZURE_AI_MODEL_DEPLOYMENT_NAME "$model_deployment_name"
azd env set AZURE_AI_RAI_POLICY_ID "$rai_policy_id"
azd env get-value AZURE_AI_MODEL_DEPLOYMENT_NAME
```

> [!WARNING]
> 部署、远程调用和 Evaluation 都可能产生费用。只运行必要的 smoke test；批量评估应先确认
> 成本和配额。

```bash
export AZURE_DEV_USER_AGENT=microsoft_foundry_skill
azd deploy --no-prompt
azd ai agent show --output json |
  python3 -c 'import json, sys; agent = json.load(sys.stdin); model = agent["definition"]["environment_variables"].get("AZURE_AI_MODEL_DEPLOYMENT_NAME"); assert agent["status"] == "active", agent["status"]; assert model, "Hosted Agent 的模型部署名称为空"; print(f"agent_status={agent['"'"'status'"'"']} model={model}")'
azd ai agent invoke --new-session "请解释本地运行和托管部署的区别。"
```

首次远程调用会创建 session sandbox。若调用返回 `424 session_not_ready`，不要重新 Provision；
先查看该 session 的容器日志：

```bash
azd ai agent monitor --tail 100
```

若 `monitor` 报告 `failed to get auth token: AzureDeveloperCLICredential: signal: killed`，先执行
不显示 token 内容的凭据预检：

```bash
export AZURE_TENANT_ID="$(az account show --query tenantId --output tsv)"
azd auth token --tenant-id "$AZURE_TENANT_ID" >/dev/null
```

预检成功表示租户凭据仍然有效，直接重试一次 `azd ai agent monitor --tail 100`，不需要退出或重新
登录。只有预检也失败时，才使用前文的多租户认证恢复步骤。

日志中的 Python traceback 是首要依据。模型部署名称为空时，重新执行本节的 `azd env set` 后再
Deploy；只有日志没有启动异常、仅显示仍在预热时，才等待 15 到 30 秒并复用同一 session 重试：

```bash
azd ai agent invoke \
  --session-id "<错误输出中的 Session ID>" \
  "请解释本地运行和托管部署的区别。"
```

需要执行课程中的质量与安全评估时，显式指定仓库内的配置文件：

```bash
azd ai agent eval run \
  --config src/agent-framework-agent-basic-responses/eval-security.yaml \
  --no-wait
```

### 可选：创建 Observability 资源

此步骤不是 Agent 本地运行或托管部署的前置条件，并会产生 Log Analytics 数据摄取费用。
先执行 What-if，确认后再创建资源并连接 Application Insights：

```bash
resource_group="$(azd env get-value AZURE_RESOURCE_GROUP)"
project_id="$(azd env get-value AZURE_AI_PROJECT_ID)"

az deployment group what-if \
  --resource-group "$resource_group" \
  --template-file ./infra/observability.bicep

az deployment group create \
  --name xagent-observability \
  --resource-group "$resource_group" \
  --template-file ./infra/observability.bicep

app_insights_id="$(
  az resource list \
    --resource-group "$resource_group" \
    --resource-type Microsoft.Insights/components \
    --query '[0].id' \
    --output tsv
)"
app_insights_name="${app_insights_id##*/}"
connection_url="https://management.azure.com${project_id}/connections/${app_insights_name}?api-version=2025-06-01"
: "${project_id:?请先完成 azd provision}"
: "${app_insights_id:?未在当前资源组找到 Application Insights}"
connection_body="$(
  APP_INSIGHTS_ID="$app_insights_id" python3 -c \
    'import json, os; print(json.dumps({"properties": {"authType": "ProjectManagedIdentity", "category": "AppInsights", "target": os.environ["APP_INSIGHTS_ID"], "metadata": {"purpose": "agent-tracing-monitoring"}}}))'
)"

az rest \
  --method put \
  --url "$connection_url" \
  --body "$connection_body" \
  --headers Content-Type=application/json \
  --output none
```

### 清理 macOS 实验环境

`azd down --purge` 会永久删除当前 environment 的 Resource Group、Foundry Project、模型部署、
Hosted Agent，以及其中的 Evaluation、Trace 和遥测数据。先导出课程要求保留的结果，再核对目标：

```bash
azd env list
azd env get-value AZURE_RESOURCE_GROUP
```

确认活动 environment 和 Resource Group 都属于当前实验后，再执行交互式清理。本步骤不使用
`--force`，执行者必须阅读并确认删除提示。

```bash
azd down --purge
```

## 获取自己的训练环境

每次 `azd` 初始化和 Provision 都可能生成不同的资源组、Foundry Account 后缀、Project、Agent 与监控资源名称。不要复制文档中的示例资源名。

完成 Provision 后，在项目根目录执行：

```bash
for key in \
  AZURE_RESOURCE_GROUP \
  AZURE_LOCATION \
  AZURE_AI_ACCOUNT_NAME \
  AZURE_AI_PROJECT_NAME \
  AZURE_AI_MODEL_DEPLOYMENT_NAME \
  AZURE_AI_RAI_POLICY_ID \
  AGENT_XAGENT_FOUNDRY_LAB_NAME \
  AGENT_XAGENT_FOUNDRY_LAB_VERSION \
  AGENT_XAGENT_FOUNDRY_LAB_RESPONSES_ENDPOINT; do
  printf '%s=%s\n' "$key" "$(azd env get-value "$key" 2>/dev/null || printf '<尚未创建>')"
done
```

| 项目 | 动态来源 |
| --- | --- |
| 资源组 | `AZURE_RESOURCE_GROUP` |
| 区域 | `AZURE_LOCATION` |
| Foundry Account | `AZURE_AI_ACCOUNT_NAME` |
| Foundry 项目 | `AZURE_AI_PROJECT_NAME` |
| 模型部署 | `AZURE_AI_MODEL_DEPLOYMENT_NAME` 或 `AI_PROJECT_DEPLOYMENTS` |
| Agent | `AGENT_XAGENT_FOUNDRY_LAB_NAME` |
| 协议 | Responses 2.0 |
| 部署模式 | 直接代码部署 |
| Agent 框架 | Microsoft Agent Framework |
| Application Insights | 从资源组按 `Microsoft.Insights/components` 类型查询 |
| Log Analytics | 从资源组按 `Microsoft.OperationalInsights/workspaces` 类型查询 |
| 防护栏 | `AZURE_AI_RAI_POLICY_ID` |

部分 azd environment 值包含资源 ID 和 endpoint。只在本地查看，不要把完整输出粘贴到公开聊天、
Issue 或共享截图中。

## 常用命令

所有 `azd` 命令都应在项目根目录执行。

```bash
export AZURE_DEV_USER_AGENT=microsoft_foundry_skill
export FOUNDRY_PROJECT_ENDPOINT="$(azd env get-value FOUNDRY_PROJECT_ENDPOINT)"
export AZURE_AI_MODEL_DEPLOYMENT_NAME="$(azd env get-value AZURE_AI_MODEL_DEPLOYMENT_NAME)"

azd ai project show --output json
azd ai agent run --no-client
azd ai agent invoke --local "请用三步说明 Hosted Agent 的部署流程。"
azd deploy --no-prompt
azd ai agent show --output json
azd ai agent invoke --new-session "请解释本地运行和托管部署的区别。"
azd ai agent monitor --tail 100
azd ai agent eval run \
  --config ./src/agent-framework-agent-basic-responses/eval-security.yaml \
  --no-wait
```

性能、安全、Portal/CLI 评估、追踪、监控、AI 红队测试与防护栏的完整步骤见两份参考手册。

Observability 资源也采用动态名称：

```bash
resource_group="$(azd env get-value AZURE_RESOURCE_GROUP)"
az resource list \
  --resource-group "$resource_group" \
  --query '[].{name:name,type:type}' \
  --output table
```

## 本地配置

服务目录中的 `.env` 只包含非秘密的 Foundry Project endpoint 和模型部署名，并已被 `.gitignore` 排除。不要向 `.env` 写入 Token、API Key 或客户端密码。

Windows 深层工作区可能触发 Python 长路径问题。建议将代码放在较短路径，例如 `C:\labs\xagent`。如果不能移动，可临时使用 `subst` 映射短盘符。

## 清理

不再需要实验环境时，先核对活动 environment 和 Resource Group：

```bash
azd env list
azd env get-value AZURE_RESOURCE_GROUP
```

确认 environment 和 Resource Group 无误后，再单独执行删除：

```bash
azd down --purge
```

该命令会删除本 azd 环境创建的 Resource Group、Foundry Project、模型部署和相关数据。
本指南不使用 `--force`，执行者必须阅读并确认删除提示。
