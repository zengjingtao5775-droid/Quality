# Streamlit Cloud 部署说明

## 部署入口

- Repository: `zengjingtao5775-droid/Quality`
- Branch: `main`
- Main file path: `app.py`
- Python version: `3.12`（仓库已用 `runtime.txt` 固定）

## 部署步骤

1. 确认本地修改已经提交并推送到 GitHub。
2. 打开 [Streamlit Community Cloud](https://share.streamlit.io/)。
3. 点击 `Create app`，选择 `Yup, I have an app`。
4. 填写 GitHub 仓库、分支和入口文件：
   - Repository: `zengjingtao5775-droid/Quality`
   - Branch: `main`
   - Main file path: `app.py`
5. 在 Advanced settings 中确认 Python 为 `3.12`。
6. 如果需要线上实时读取简道云，在 Advanced settings 的 Secrets 里加入：

```toml
JIANDAOYUN_API_KEY = "你的简道云API Key"
```

也兼容历史键名：

```toml
JIANDAO_API_KEY = "你的简道云API Key"
```

7. 如果需要在 `08 简道云报表` 中生成专业大模型报告，选择以下一种方式配置。

直接调用通义千问：

```toml
DASHSCOPE_API_KEY = "你的阿里云百炼API Key"
QWEN_MODEL = "qwen-max"
```

通过 Dify 调用已配置好的通义千问应用：

```toml
DIFY_API_KEY = "你的Dify应用API Key"
DIFY_BASE_URL = "https://api.dify.ai/v1"
```

8. 点击 Deploy，等待依赖安装和应用启动。

## 数据文件

本 POC 使用仓库内的本地数据文件：

- `TU database/ZX Database/`
- `TU database/GP database/`
- `TU database/DS database/`
- `BME Database/`
- `SE Database/`

ZX Intern Voice 当前使用 `TU database/ZX Database/2026 ZX Intern Voice.xlsx`，不再上传原始截图文件夹。

这些文件必须跟随代码一起推送到 GitHub。

## 简道云 08 报表

TU 页面简道云数据支持三种模式：

- `部署快照`：默认读取 `TU database/ZX Database/ZX_FQC_normalized_snapshot.csv`，页面加载不访问 API。
- `实时 API`：仅在用户点击“刷新简道云 API”后读取，需要在 Secrets 配置 `JIANDAOYUN_API_KEY`。
- `本地原始 CSV`：开发环境可读取 `POC_Raw_Data/04_Gloves/ZX_FQC/` 下的导出文件。

`POC_Raw_Data/` 仍被 `.gitignore` 忽略；线上使用精简快照作为默认值，避免每次页面刷新都调用实时 API。

## 08 专业 AI 报告

报告分为两层：

- `专业AI质量分析`：把当前筛选后的简道云数据先转换成结构化事实包，再交给通义千问或 Dify 生成管理层报告。
- `规则诊断清单`：完全由代码计算，作为大模型报告的数字核对和降级方案。

大模型报告要求每个定量结论引用事实编号，并区分事实、分析推断和待工厂验证的根因假设。报告包括管理结论、风险诊断、根因假设、24小时/7天/30天行动、验证KPI和数据局限。

## 权重保存说明

当前权重方案会优先写入 `quality_dashboard_risk_settings.json`。在 Streamlit Cloud 上，本地文件存储不保证长期持久化；如果应用重启，线上保存过的权重可能恢复为仓库中的默认值。若需要多人长期共用权重方案，建议后续接入外部存储，例如 Google Sheets、Supabase 或公司内部数据库。
