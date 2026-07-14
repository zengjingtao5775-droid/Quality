# NEA 质量看板交接状态

更新日期：2026-07-14
当前仓库：`/Users/eric/Desktop/Decathlon/Quality`
主应用：`app.py`
最近部署状态：以 GitHub `main` 最新提交为准

## 当前结论

这个 POC 已从单一 ZX 质量看板扩展为 NEA 总览 + 三个 community 页面：

- `总览`：给 NEA / Quality Manager 看整体风险，对比 TU / BME / SE 的质量状态。
- `TU / ZX 中兴`：只保留 ZX 数据，重点做手套质量分析、CC 风险、疵点、工人/工序、原辅料和简道云 ZX FQC。
- `TU 看板2`：覆盖 ZX 中兴、GP 浙江高普、DS 贵州鼎盛三家 TU 供应商，按供应商与产品做统一风险分析。
- `BME / CMW 自行车`：基于当前 BME 数据做 FQC / PQC / IQC / Rework / Torque 分析，不接简道云。
- `SE / 帐篷`：基于 SE QMS 检验数据做现有字段能支持的分析，不接简道云。

Streamlit Cloud 通过 GitHub `main` 分支自动部署。最近一次代码已经推送成功；线上访问会跳 Streamlit Auth，说明当前 app 可能需要登录权限。

## 最近几轮已完成

- 统一了蓝色侧边栏风格，整体页面改成更轻的蓝白风格，避免黑白割裂。
- 左侧 sidebar 改为按页面入口选择：总览、TU / ZX、BME / CMW、SE / 帐篷。
- 语言切换支持 URL/query 记忆，切换页面后不应自动回中文。
- 总览页面定位为 manager 视角，保留 general overview，不做过多深钻。
- ZX community 页面改为大图优先：每个核心 chart 尽量占满页面宽度。
- ZX 主要图表顺序：高风险 CC 聚类、产品风险 Top CC、Top Defect Pareto、不良率趋势。
- ZX 其它分析项放入可展开区域，避免用户一进页面看到太多信息。
- ZX 高风险 CC 聚类：每个点代表一个 CC，综合风险 = 生产端 70% + 客户端 30%。
- 聚类图默认 X 轴聚焦 0-60，并增加高 / 中 / 低风险筛选。
- 聚类图 hover 中显示风险分计算逻辑。
- 产品风险 Top CC 也按生产端 70% + 客户端 30% 计算。
- 不良率趋势改回周维度，按 Online QC / End QC-FQC 区分。
- 简道云 ZX FQC 总结报告压缩为 300 字以内一段话，并可下载。
- 如果配置了 Dify 或通义千问 API key，简道云总结可以调用大模型；没有 key 时使用结构化规则总结。
- BME 新增读取 torque 标准、读数和偏离值，后续可继续优化机器扭力分析。

## 设计风格约束

- 视觉方向：Decathlon 蓝 + 白色/浅蓝背景，专业、清爽、dashboard 感，不要暗黑风和花哨渐变。
- Sidebar：深蓝背景、白色文字、卡片式入口，当前选中项用浅蓝/白色边框突出。
- 主内容：浅蓝灰背景，白色图表区域，少量蓝色强调线。
- 避免大面积橙色；风险颜色建议使用：
  - 高风险：红色，但不要过饱和。
  - 中风险：琥珀/金色，只做提示。
  - 低风险：绿色。
  - 普通主色：蓝色。
- 图表优先于文字，文字只做数据来源、计算逻辑和简短结论。
- 用户一眼要能看到“哪里有风险、为什么有风险、下一步看哪里”。
- 表格默认尽量收起，只有用户要看原始明细时再展开。
- 每个 chart 下方必须写清楚数据来源和计算逻辑，避免看起来像主观判断。

## 数据和算法逻辑

### ZX / TU

主要数据源：

- ZX QC data（当前成品检验源：`TU database/ZX Database/05.7-06.6检验数据.xlsx`，25,708 条记录）
- ZX RPM
- ZX Intern Voice
- ZX Material data
- 简道云 ZX FQC

### TU 看板2

TU 看板2覆盖三家供应商：ZX 中兴、GP 浙江高普、DS 贵州鼎盛。

- ZX：`TU database/ZX Database/`
- GP：`TU database/GP database/GP Product Check Data_record.xlsx`
- DS：`TU database/DS database/DS Product Check Data_record.xlsx`
- `CNUF` 是供应商代码，GP 为 46638，DS 为 61939；供应商名称与 CNUF 分开保存和展示。
- GP / DS 的异常记录按流转卡、检验日期和检验员识别同一次检验，检验量只计一次，疵点数完整累加。
- GP 原始 CC 为空时回退到 Model Code，数据地图会显示回退记录数。
- 简道云默认读取仓库内的精简 ZX FQC 快照；只有用户点击“刷新简道云 API”时才读取实时 API。
- 数据置信度 = Product Check 关键字段完整度 x 70% + RPM/IV 完整度与供应商覆盖率 x 15% + 简道云 FQC/DKL 完整度 x 15%。

核心风险逻辑：

- 生产端风险：主要来自 QC 不良率。
- 客户端风险：来自 RPM 百万退货率和 Intern Voice 退货发起次数。
- 综合风险：生产端 70% + 客户端 30%。
- K-means 聚类：用于把 CC 分成高 / 中 / 低风险群，不作为唯一结论，必须结合 hover 里的真实值看。

### BME / CMW

主要数据源：

- FQC Daily Report
- PQC 生产扭力记录
- IQC Daily Report
- 返工作业申请书

重点方向：

- FQC / PQC 不良率
- IQC 与返工压力
- Torque 记录数、合格/不合格、偏离标准多少

### SE / 帐篷

主要数据源：

- SE QMS 最近一个月检验数据

重点方向：

- FQC / IPQC 检验分布
- 工序 / 检查点风险
- 产品或款号维度风险

## 待办

- 检查 Streamlit Cloud 部署页面是否完成构建；因为线上目前跳 Streamlit Auth，命令行无法直接看到页面内容。
- 如果希望所有人都能访问，需要在 Streamlit Cloud 设置里确认 app visibility / sharing 权限。
- 继续优化 ZX 聚类图：当前已限制 X 轴到 60，但如果高生产端风险 CC 超出 60，需要提供“一键看全部”或缩放说明。
- 检查简道云大模型总结是否有真实 Dify / Qwen key；没有 key 时只能显示规则总结。
- BME torque 图还可以继续优化为两张图：记录量分布 + 不合格偏离明细。
- SE 数据字段需要再确认，若原始文件缺少疵点数量或检验数量，应在页面明确提示“当前字段不足”。
- 总览页应继续控制信息密度，只保留 manager 要看的跨 community 对比。
- 所有 tooltip / hover 里的中英文混杂需要继续全局检查。
- 未跟踪文件 `简道云openclaw.zip` 和 `简道云openclaw/` 当前没有提交，如需部署相关技能或文档，需要单独决定是否纳入版本库。

## 新会话建议打开顺序

1. 先读本文件。
2. 再看 `DEPLOYMENT.md`。
3. 再看 `app.py` 中这些函数：
   - `render_community_cockpit`
   - `render_zx_high_risk_cluster`
   - `render_product_priority`
   - `render_stage_trend`
   - `render_tu_jiandaoyun_snapshot`
   - `build_jdy_action_report_markdown`
4. 本地验证优先：
   - `python3 -m py_compile app.py`
   - `streamlit run app.py`
   - `curl http://127.0.0.1:8501/_stcore/health`

## 部署提醒

推送 GitHub：

```bash
cd /Users/eric/Desktop/Decathlon/Quality
git push origin main
```

如果 GitHub 推送要求认证，之前已经配置过：

```bash
git config credential.helper manager
```

若 Streamlit Cloud 长时间停留在 “Your app is in the oven”，优先检查：

- GitHub 最新 commit 是否已推到 `main`。
- Streamlit Cloud logs 是否有 Python 版本、依赖或文件路径错误。
- `requirements.txt` 是否包含需要的依赖。
- 大文件或无用图片是否进入仓库。
