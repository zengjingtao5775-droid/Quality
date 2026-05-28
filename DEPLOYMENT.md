# Streamlit Cloud 部署说明

## 部署入口

- Repository: `zengjingtao5775-droid/Quality`
- Branch: `main`
- Main file path: `app.py`
- Python version: 建议选择 `3.12`

## 部署步骤

1. 确认本地修改已经提交并推送到 GitHub。
2. 打开 [Streamlit Community Cloud](https://share.streamlit.io/)。
3. 点击 `Create app`，选择 `Yup, I have an app`。
4. 填写 GitHub 仓库、分支和入口文件：
   - Repository: `zengjingtao5775-droid/Quality`
   - Branch: `main`
   - Main file path: `app.py`
5. 在 Advanced settings 中选择 Python `3.12`。
6. 点击 Deploy，等待依赖安装和应用启动。

## 数据文件

本 POC 使用仓库内的本地数据文件：

- `ZX Database/`
- `DS Database/`
- `JS Database/`
- `TF Database/`

ZX Intern Voice 当前使用 `ZX Database/2026 ZX Intern Voice.xlsx`，不再上传原始截图文件夹。

这些文件必须跟随代码一起推送到 GitHub。当前版本不需要额外配置数据库或密钥。

## 权重保存说明

当前权重方案会优先写入 `quality_dashboard_risk_settings.json`。在 Streamlit Cloud 上，本地文件存储不保证长期持久化；如果应用重启，线上保存过的权重可能恢复为仓库中的默认值。若需要多人长期共用权重方案，建议后续接入外部存储，例如 Google Sheets、Supabase 或公司内部数据库。
