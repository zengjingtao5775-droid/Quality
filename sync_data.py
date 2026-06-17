import os

import requests

# ==================== 核心配置 ====================
# 密钥不再硬编码：优先读环境变量 JIANDAO_API_KEY，
# 否则尝试读取 .streamlit/secrets.toml 中的 JIANDAO_API_KEY（两者都不进 git）。
JIANDAO_API_KEY = os.environ.get("JIANDAO_API_KEY")
if not JIANDAO_API_KEY:
    try:
        import streamlit as st

        JIANDAO_API_KEY = st.secrets["JIANDAO_API_KEY"]
    except Exception:
        JIANDAO_API_KEY = None
if not JIANDAO_API_KEY:
    raise SystemExit(
        "缺少 JIANDAO_API_KEY。请二选一：\n"
        "  1) 设置环境变量： export JIANDAO_API_KEY=你的密钥\n"
        '  2) 在 .streamlit/secrets.toml 中加入： JIANDAO_API_KEY = "你的密钥"'
    )

# 填入你4个供应商对应的 APP_ID（名字可以自己定）
SUPPLIER_APPS = {
    "供应商A": "66042983e6883a1ded43a13b",
    "供应商B": "6603892131d79f31884c772a",
    "供应商C": "660389615b25f1d03168b4c9",
    "供应商D": "66038d0a5bb0b37b3ac5b492",
}
# ==================================================

print("MASTER_CONFIG = {")
for supplier_name, app_id in SUPPLIER_APPS.items():
    url = f"https://api.jiandaoyun.com/api/v2/app/{app_id}/entry"
    headers = {
        "Authorization": f"Bearer {JIANDAO_API_KEY}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(url, json={"limit": 100, "skip": 0}, headers=headers)
        if response.status_code == 200:
            entries = response.json().get('data', [])
            print(f'    "{supplier_name}": {{')
            print(f'        "app_id": "{app_id}",')
            print(f'        "forms": {{')
            for entry in entries:
                print(f'            "{entry.get("title")}": "{entry.get("name")}",')
            print(f'        }}')
            print(f'    }},')
        else:
            print(f'    # ❌ {supplier_name} 获取失败: {response.text}')
    except Exception as e:
        print(f'    # 💥 {supplier_name} 网络异常: {e}')
print("}")
