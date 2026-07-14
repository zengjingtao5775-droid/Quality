# NEA 质量看板新会话交接

更新日期：2026-07-14  
仓库：`/Users/eric/Desktop/Decathlon/Quality`  
GitHub：`zengjingtao5775-droid/Quality`  
分支：`main`  
主程序：`app.py`  
当前功能提交：`181c14c Add GP and DS to TU dashboard`

## 1. 当前产品定位

平台服务三类用户：

- NEA Quality Manager：看跨 community 总览和优先风险。
- Community QM：管理一个 community 下的多家供应商。
- Factory QPS：跟进一至两家工厂的产品、工序、人员和整改证据。

页面判断标准：目标用户必须能快速看出哪里有风险、风险证据是什么、数据是否完整、下一步看哪里。缺少分母、日期、来源或覆盖范围的指标不能当作可靠结论。

## 2. 当前页面

- `总览`：NEA manager 视角，对比 TU、BME、SE；保留 01 总览、02 供应商面板、03 产品面板、04 Panel 管理。
- `TU / ZX 中兴`：旧版 ZX 单供应商深度看板，功能必须保留。
- `TU 看板2`：新版 TU community 看板，覆盖 ZX、GP、DS。
- `BME / CMW 自行车`：保留机器参数 / PQC 扭力数据。
- `SE / Soft Equipment`：使用 SE QMS 数据。

`TU 看板2` 包含：

1. 01 总览：核心 KPI、High Risk CC、数据置信度、优先问题卡。
2. 02 供应商风险：三家供应商风险卡、风险聚类、分项风险、供应商不良率趋势。
3. 03 产品风险：产品风险 Top CC、疵点 Pareto、By CC 不良率趋势。
4. 04 权重 / 数据设置：数据地图、字段缺口、权重设置。
5. 05 Community AI 总结：通义千问 TU community 管理报告。

## 3. TU 数据接入结论

### ZX 中兴

- 数据目录：`TU database/ZX Database/`
- 本地 QC：`05.7-06.6检验数据.xlsx`
- RPM：`ZX YTD Compare hierarchy.csv`
- Intern Voice：`2026 ZX Intern Voice.xlsx`
- 原辅料：`ZX 2026年原辅料不合格记录.xlsx`
- 简道云默认快照：`ZX_FQC_normalized_snapshot.csv`

### GP 浙江高普

- 文件：`TU database/GP database/GP Product Check Data_record.xlsx`
- CNUF 供应商代码：`46638`
- 原始数据 280 条。
- 235 条原始 CC 为空，产品分析回退使用 `Model Code`；数据地图必须继续显示此限制。

### DS 贵州鼎盛

- 文件：`TU database/DS database/DS Product Check Data_record.xlsx`
- CNUF 供应商代码：`61939`
- 原始数据 521 条，其中 98 条为完全重复记录；去重后使用 423 条。

### Excel 读取注意

GP、DS 工作簿的 worksheet dimension 错误写成 `A1:A1`。程序使用 `openpyxl` 重置工作表范围后读取，不能改回普通 `pandas.read_excel`，否则会误判为只有一个单元格。

### 分母口径

GP、DS 可能将同一次检验按多个疵点拆成多行。程序按“工厂内部流转卡号 + 检验日期 + 检验员”识别同一次检验：

- 检验数量只计一次。
- 疵点数量按所有疵点行完整累加。
- DS 完全重复行先删除。

不能直接对每一行的 `已检数量` 求和，否则检验分母会被放大、不良率会被低估。

## 4. FQC RFT 与 API

- 简道云 ZX FQC 默认读取仓库内的精简快照，不自动访问实时 API。
- 当前快照 FQC RFT：`95.65%`，即 `2,924 PASS / 3,057 有效记录`。
- `TU / ZX` 和 `TU 看板2` 都有“刷新简道云 API”按钮。
- 只有用户点击按钮时才访问 API；筛选、切页和普通重载不能反复请求 API。
- 刷新后的数据保存在当前 Streamlit 会话；失败时继续使用上一次可用数据。
- `PASS after re-check / 重验合格` 不算首次 PASS。
- API Key 只能放 Streamlit Secrets 或环境变量，禁止写进仓库和文档。

## 5. 数据置信度

TU 看板2当前公式：

`数据置信度 = Product Check关键字段完整度 x 70% + RPM/IV完整度与供应商覆盖率 x 15% + 简道云FQC/DKL完整度 x 15%`

当前完整数据环境约为 `89.5%`：

- Product Check：贡献 70%。
- RPM / IV：目前只覆盖 ZX，贡献约 4.5%。
- 简道云 FQC / DKL：贡献 15%。

关键原则：GP、DS 没有 RPM / IV 时必须标记为“数据缺失”，不能当成客户端风险为 0。风险综合时只使用已有证据并重新归一化权重。

## 6. 风险分析口径

- K-means 只用于分组和排序，不是缺陷概率、审计结论或根因证明。
- 聚类气泡面积由综合风险分决定，圆越大代表风险越高。
- 产品与供应商风险都要显示真实分母、疵点数、不良率和数据覆盖情况。
- 风险权重可调整；默认生产端权重大于客户端。
- Top CC 和 Top 疵点支持 Top 20% / 全部切换。
- 缺少客户信号时不允许用 0 填充后降低综合风险。
- `End-of-line 计算RFT参考值 = 1 - 疵点数 / 检验量`，它不是被证明的首次通过件数 RFT，AI 报告必须保留这个限制。

## 7. AI 报告规则

- TU 看板2 AI 报告覆盖 ZX、GP、DS，不再只写 ZX。
- CNUF 是供应商代码，必须与供应商名称、CC、Model、Item Code 分开。
- 简道云 FQC、RPM、IV 目前只属于 ZX，不能归因给 GP 或 DS。
- AI 只能使用结构化事实包，不得编造数字、目标、根因、机器参数或客户影响。
- 每个定量结论必须引用事实编号。
- 区分：已观察事实、管理解读、待验证假设。
- 没有正式目标时不得说“好、坏、超标、低于目标”。
- 行动计划必须包含责任角色、时间、证据、KPI 和关闭标准。

## 8. 设计风格

- 主色：Decathlon 蓝 + 白色 + 浅蓝灰背景。
- 风险色：高风险红、中风险琥珀、低风险绿；不要让页面被单一蓝色或大面积橙色占满。
- 风格：专业、清爽、管理型 dashboard，不做营销首页，不使用装饰性渐变球或花哨背景。
- 页面先展示可操作的图表和 KPI，不堆解释文字。
- README 按钮保持短，只显示 `README`；内容放在弹出层。
- README 固定结构：1. 数据分析方法；2. 计算逻辑；3. 数据来源。
- 图表 Y 轴标题水平显示，不能要求用户歪头阅读。
- 筛选器使用整洁的多选框、分段控件或下拉框；不要使用突兀的大红按钮。
- 图表 hover 要大、清楚，优先显示供应商、CNUF、CC、Model、检验量、疵点、不良率和风险分。
- 中英文切换必须完整，原始中文分类在英文页面也要本地化。
- 表格和原始明细默认收起，主页面保持低信息噪声。
- 不删除旧功能；修改新版 TU 看板2时必须回归旧 TU/ZX、总览、BME、SE。

## 9. 当前已验证

- Python 语法检查通过。
- Streamlit AppTest 已覆盖：总览、旧 TU/ZX、TU 看板2五个页面、英文 TU 看板2、BME、SE。
- 云端等价测试在没有 `POC_Raw_Data` 且禁止网络请求的条件下通过。
- 默认页面不访问简道云 API，FQC 快照仍可显示 95.65%。
- 最新代码已推送 GitHub `main`，Streamlit Cloud 会自动部署。

## 10. 待办

1. 在线检查 Streamlit Cloud 是否已部署提交 `181c14c`，重点查看 TU 看板2供应商卡、聚类、趋势和数据地图。
2. 点击一次“刷新简道云 API”，确认线上 Secrets 有效且刷新后仍为合理 FQC RFT。
3. 后续拿到 GP、DS 的 RPM / IV 或客户退货数据后，补齐客户端风险覆盖。
4. 后续拿到 GP 更完整的 CC 字段后，减少 `Model Code fallback`。
5. 确认 GP、DS 的“流转卡 + 日期 + 检验员”是否就是业务认可的唯一检验批次键。
6. 权重目前写入本地 JSON；Streamlit Cloud 重启后不保证长期持久，后续可接外部存储。
7. 继续检查英文页面的供应商名称、疵点类型和 hover 是否完全英文化。

## 11. 新会话建议开场

新会话第一句话可以直接使用：

> 请先阅读 `SESSION_HANDOFF_2026-07-14.md`、`QUALITY_DASHBOARD_HANDOFF.md` 和 `DEPLOYMENT.md`，理解当前 NEA 质量看板。先不要删除任何已有功能。然后检查 GitHub main 和 Streamlit Cloud 当前版本，再继续处理我的下一条修改建议。

## 12. 本地验证命令

```bash
cd /Users/eric/Desktop/Decathlon/Quality
PYTHONPYCACHEPREFIX=/tmp/quality-pycache python3 -m py_compile app.py
PYTHONPYCACHEPREFIX=/tmp/quality-pycache PYTHONPATH=.vendor python3 -m streamlit run app.py --server.headless true --server.port 8501
```

不要提交现有未跟踪的 `outputs/`、`简道云openclaw.zip` 或 `简道云openclaw/`，除非用户明确要求。
