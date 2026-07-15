# NEA 质量管理平台｜新会话交接

更新：2026-07-16

仓库：`/Users/eric/Desktop/Decathlon/Quality`

远端：`https://github.com/zengjingtao5775-droid/Quality.git`

分支：`main`

主程序：`app.py`

本地页面：`http://127.0.0.1:8502/?scope=ZX&lang=zh`

## 1. 当前最重要状态

- 目前只汇报并展示 **Textile Unit 看板**，平台中文名为 **NEA 质量管理平台**，英文名为 **NEA QUALITY PLATFORM**。
- Overview、TU 看板2、BME、SE 已通过配置开关隐藏，**不得删除**，以后要能快速恢复。
- 最新修改已在本地完成并通过测试。
- 文件已经 `git add` 暂存，但**尚未 commit、尚未 push、Streamlit Cloud 尚未收到本次版本**。
- 用户原本要求“推送 Streamlit”，但推送流程被本交接文档请求打断。新会话应先检查暂存内容，然后提交并推送。

## 2. 当前任务边界

### 本阶段要做

- 做好 ZX / 中兴的 Textile Unit 单供应商深度看板。
- 整合工厂 MES / Excel、Decathlon PS / 简道云、客户 RPM / IV 数据。
- 明确高风险 CC、Model、工序、客户信号和可执行优先级。
- 所有公式、分母、数据来源必须可解释、可追溯。
- 中文为默认语言，支持完整英文切换。

### 本阶段不做

- 不删除隐藏页面，不重做 Overview、TU 看板2、BME、SE。
- 不把 K-means 或风险分描述成缺陷概率、根因证明或审计结论。
- 不承诺已经实现节省金额、消费者价值金额或完整 action 闭环；这些仍缺数据。
- 不把 API Key、Secrets 或个人凭证写入代码或文档。
- 不提交 `outputs/`、`reports/`、`~$` Excel 临时文件、`.DS_Store`、`简道云openclaw/` 或其 zip。

## 3. 当前数据结构

目录：`TU database/ZX Database/`

### Factory data

- `Factory data/05.7-06.6检验数据.xlsx`
- `Factory data/2026年原辅料不合格记录.xlsx`

### Decathlon PS data

- `Decathlon PS data/ZX_FQC_normalized_snapshot.csv`
- 简道云实时数据通过 API 手动刷新；本地快照只是部署回退，不是独立接入方式。

### Decathlon Customer data

- `Decathlon Customer data/Compare hierarchy (CC).xlsx`
- `Decathlon Customer data/Compare hierarchy (model).csv`
- `Decathlon Customer data/ZX intervoice.xlsx`
- `Decathlon Customer data/Info - RPM (1).csv`
- `Decathlon Customer data/NQC.csv`
- 两份 Defloc CSV：退货缺陷、退货部位。

### FQC 人员归属

以下人员属于 Decathlon：

- Wuhao
- EricZeng
- Daisy yu
- 李秀玲
- 韩永红

`ZX FQC检验表` 中其他人员属于中兴工厂。两类人员的合格率必须分开计算。

## 4. 当前页面结构

### 筛选

顺序固定：

1. 供应商下拉框
2. CC 下拉框
3. Model 下拉框
4. 检验日期
5. 检验阶段

日期范围可从 2025 年 7 月开始。当前不再把“CC 双击聚焦 / 再次双击取消”作为页面说明或核心交互要求。

### 核心 KPI

- 迪卡侬验货合格率
- 中兴工厂自检合格率
- End of line RFT：环比上升为绿色，下降为红色；文案只讲 RFT，不讲 defect rate。
- RPM（R12M）
- 工厂售前 IV：只统计属于工厂责任的售前 IV。
- 工厂检验占比
- Decathlon FQC 抽检率

### 检验占比

`工厂检验占比 = 有效检验量 / 订单参考量`

有效检验量按生产通知单汇总 Online / End 检验，再对每张通知单使用：

`min(累计检验数, 订单数量)`

所以重复检验不会重复计算覆盖量，比例不会超过 100%。

`Decathlon FQC 抽检率 = 指定 Decathlon 检验员的抽样数 / 同范围订单参考量`

订单参考量仍是当前可用的出货代理分母，不是独立核验的实际出货量。

## 5. 高风险产品聚类

### 公式

生产端小样本收缩：

`收缩后不良率 = (疵点数 + 基准不良率 × 200) / (检验数 + 200)`

- ZX QC 基准通常为 4%。
- 基准不良率对应生产风险 50 分；再增加 8 个百分点达到 100 分。
- 小样本更靠近基准，大样本更接近实际不良率，避免 1/1 与 1000/10000 被当成同等可靠证据。

客户端标准化：

`RPM风险 = min(RPM / RPM上限 × 100, 100)`

`IV风险 = min(IV / IV上限 × 100, 100)`

当前上限通常为 RPM 1500、IV 30。`min` 只给标准化风险封顶，原始值仍保留，避免极端值压扁其他 CC。

客户端权重：

- RPM 与 IV 都存在：50% / 50%。
- 只有一个信号：已有信号自动承担 100%，缺失数据不能当 0 分。
- 目前没有结果验证证据支持 70% / 30%，所以使用中性 50% / 50%；未来应按 action 有效性和后续退货结果校准。

综合风险：

`综合风险 = 生产端风险 × 70% + 客户端风险 × 30%`

生产端 / 客户端权重可调整。K-means 根据两个坐标分三组，再按组内平均综合分命名高、中、低风险；这是当前数据范围内的相对等级。

页面公式示例可选择任意 CC，逐行展示实际数值。

## 6. 其他分析

### Top CC 帕累托

- 当前名称：`Top CC 帕累托`。
- 默认只展示综合风险 Top 20%，可切换全部。

### CC 不良率趋势

- 按自然日期 / 周展示，不使用 `2025 W44` 作为主要阅读格式。
- 支持多 CC 对比。

### 工序风险

页面提供两个可切换视角：

- **疵点帕累托**：回答疵点主要集中在哪里；适合安排改善资源，作为日常改善首选。
- **风险分**：回答相对不良率哪里异常；可发现绝对疵点不多但表现异常的工序，作为预警补充。

工序风险也使用 200 个先验样本的小样本收缩，固定等级为：低 `<35`、中 `35–54.9`、高 `55–74.9`、严重 `≥75`。

### 客户 360

中文名固定为 `客户 360`。

当前联合图：`工厂不良率 × 客户 RPM`

- 横轴：工厂不良率
- 纵轴：客户 RPM（对数轴）
- 圆圈大小：退货量
- 颜色：生产端 + 客户端双高、生产端重点、客户端重点、观察
- 只展示联合关注分最高的 6 个 CC
- 联合关注分：标准化工厂风险 50% + 标准化客户 RPM 风险 50%

消费者退货缺陷 / 部位文件暂时没有 CC 或 Model 键，因此仍是 ZX 总体视角，不能跟随 CC 筛选。

### 数据地图

- 手动 Excel 与 API 在同一张表中展示。
- 简道云接入方式只显示 `API`，不显示 `API + 本地快照`。
- `刷新简道云 API` 已放入数据地图内部。
- 当前本地页面仍显示 Intern Voice 缺失，虽然新目录存在 `ZX intervoice.xlsx`；这是下一会话需要优先核查的数据识别问题。

### 指标说明

- 所有“指标说明”按钮尺寸统一。
- 内容只保留计算逻辑和数据来源。
- 数据来源一个文件一行，存在仓库中的文件提供 GitHub 可点击链接。

## 7. AI 总结报告

- 默认中文，可切换英文。
- 可选择模型，包括 Flash 与其他已配置模型。
- 固定结构：
  1. 总结高风险 CC 和 Model。
  2. 查询这些 CC 已执行的简道云 PS action，包括 CP 与 FQC。
  3. 判断是否适合动态调整 AQL，并解释原因。
- AI 必须区分事实、管理判断、待验证假设；不得编造 action、根因、目标或金额。

## 8. 项目价值边界

### 已部分做到

- **效率**：统一识别高优先级 CC、Model、工序和客户风险。
- **整合**：已把工厂、PS、RPM、IV、退货缺陷数据放在同一分析入口。
- **消费者导向**：已连接工厂不良率与客户 RPM，能看到双高产品。

### 尚未证明

- **闭环**：缺少 action 创建、责任人、截止时间、完成证据、复验结果的统一键。
- **Money**：缺少退货成本、NQC 成本、重工成本、检验成本、停线损失、action 成本。
- **消费者价值**：缺少投诉严重度、评分变化、复购、退货原因与 CC / Model 的完整关联。
- **动态 AQL**：缺少当前 AQL、批次、抽样等级、放行 / 拒收结果、调整后的质量结果。

不要在 presentation 中说平台已经创造了确定金额。当前准确定位是：**跨系统风险决策层和验证中的 action prioritization prototype**。

## 9. Git 与部署状态

当前已暂存：

- `app.py`
- ZX 三类新数据目录
- 旧数据文件删除 / 移动记录

当前未暂存且必须继续排除：

- `TU database/ZX Database/~$2026 ZX Intern Voice.xlsx`
- `outputs/`
- `reports/`
- `简道云openclaw/`
- `简道云openclaw.zip`

提交前检查：

```bash
cd /Users/eric/Desktop/Decathlon/Quality
git status --short
git diff --cached --check
PYTHONPYCACHEPREFIX=/tmp/quality-pycache python3 -m py_compile app.py
```

建议提交：

```bash
git commit -m "Refine ZX risk analysis and data integration"
git push origin main
```

推送后 Streamlit Cloud 应自动部署。随后在线检查：

1. 数据地图与 API 刷新。
2. 聚类公式示例。
3. 工序帕累托 / 风险分切换。
4. 客户 360 联合图。
5. 中英文页面。
6. 新目录在无本地旧文件情况下能否完整加载。

## 10. 已完成验证

- `python3 -m py_compile app.py` 通过。
- Streamlit `AppTest` 中文 ZX 页面通过。
- Streamlit `AppTest` 英文 ZX 页面通过。
- 浏览器本地检查无 JavaScript 错误。
- 已实际检查数据地图、聚类解释、工序双视角和客户 360 联合图。

## 11. 新会话开场

直接复制：

> 请先完整阅读 `SESSION_HANDOFF_2026-07-16.md`，不要删除隐藏页面，不要改动未列入范围的功能。先检查当前暂存文件和本地测试状态，完成 commit、push 到 `main`，再验证 Streamlit Cloud。特别检查新目录下的 `ZX intervoice.xlsx` 为什么仍在数据地图显示缺失。
