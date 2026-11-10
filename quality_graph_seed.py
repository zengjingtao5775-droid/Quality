"""Draft vocabulary and candidate links for the supplied ZX glove guide."""

QUALITY_GRAPH_RELEASE = 6
TAXONOMY_VERSION = "defects-v0.1"
GUIDE_DIGEST = "9ed23bae434a1e1d70069cc12fe48814d352029d628b0ed630d6e847e791a5d0"
GUIDE_SHEET = "2.Process Guidelines for CP "
GUIDE_FILENAME = "[Q] R3_TEMP_160_WW_EN_Process Guidelines for Control Plan_V1_HTC_Gloves - Cut  and sew_v2_ .xlsx"
GLOVES = "Gloves - Cut and sew"
STAGES = ("IQC", "PQC", "FQC")
LABELING_STAGES = ("PQC", "FQC")

# Hand-labeled pilot records from the bundled ZX inspection workbook.
ZX_PQC_PILOT_LABELS = {
    "CH202606300059": "TU-001", "CH202507010018": "TU-001",
    "CH202606260027": "TU-002", "CH202507100079": "TU-002",
    "CH202606150071": "TU-003", "CH202508250030": "TU-003",
    "CH202605130032": "TU-004", "CH202508210026": "TU-004",
    "CH202605290083": "TU-005", "CH202508230087": "TU-005",
    "CH202605110083": "TU-007", "CH202507050059": "TU-007",
    "CH202606170021": "TU-008", "CH202508130008": "TU-008",
    "CH202606010117": "TU-009", "CH202510150014": "TU-009", "CH202603270043": "TU-009",
    "CH202606220050": "TU-010", "CH202507140071": "TU-010",
}

# IDs are independent of display names. The definition describes observable
# evidence and sets a boundary for annotators, not a manufacturing cause.
TAXONOMY = {
    "TU": {
        "TU-001": ("缝份不均或超差", "Seam allowance variation", "缝份或止口宽度不均或超出要求。明线距边不匀单独标注。"),
        "TU-002": ("内里开缝", "Open lining seam", "内里接缝已开口或爆口。只有漏车记录时标注漏车。"),
        "TU-003": ("扭指", "Twisted finger", "手套手指形态扭转，未指明在内里。"),
        "TU-004": ("内里扭指", "Twisted lining finger", "明确发生在内里手指的扭转。"),
        "TU-005": ("网布抽丝", "Mesh snagging", "网布纱线被勾出或拉丝。破洞单独标注。"),
        "TU-006": ("线头未剪", "Untrimmed thread", "成品或半成品残留未修剪线头。"),
        "TU-007": ("网棉漏车", "Skipped mesh/padding operation", "网棉应有的车缝缺失。"),
        "TU-008": ("明线不匀", "Uneven topstitch", "明线走线或形态不均。已明确距边或针密度时用专门类型。"),
        "TU-009": ("线迹不良（未细分）", "Stitch defect, unspecified", "描述明确涉及线迹，细分表现缺失。"),
        "TU-010": ("死皱", "Set wrinkle", "部件或成品出现固定皱褶。"),
        "TU-011": ("针密度异常", "Stitch density deviation", "明确记录针密度不符合要求。"),
        "TU-012": ("明线距边不匀", "Topstitch edge distance variation", "明线到边缘的距离不均或超差。"),
        "TU-013": ("印刷异常", "Print defect", "印刷缺字、模糊或其他印刷外观异常。标签位置偏斜单独标注。"),
        "TU-014": ("面料色差", "Fabric shade deviation", "主料颜色或色阶与样板、同批或规定有偏差。"),
        "TU-015": ("材料破洞", "Material hole", "原料有明确破洞或撕破。"),
        "TU-016": ("材料拉力不足", "Insufficient material tensile strength", "来料拉力测试不达标。"),
        "TU-017": ("标签位置偏斜", "Misaligned label", "成品或半成品标签位置或角度偏离。"),
        "TU-018": ("脏污", "Contamination / stain", "材料或产品有脏污或污点。"),
        "TU-019": ("倒针不良", "Backstitch defect", "回针或倒针缺失、不完整或不合要求。"),
        "TU-020": ("附件毛刺", "Accessory burr", "辅料边缘或注塑口存在毛刺。"),
        "TU-021": ("针洞", "Needle hole", "在制品或成品检验明确记录针洞。来料破洞单独标注。"),
    },
    "BME": {
        "BME-001": ("外观不良（未细分）", "Appearance defect, unspecified", "源记录明确为外观异常，尚无可区分的缺陷细节。"),
        "BME-002": ("尺寸超差", "Dimensional deviation", "尺寸实测偏离标准或明确判定为尺寸不良。"),
        "BME-003": ("牙纹不良", "Thread defect", "螺纹牙型、完整性或配合不合格。"),
        "BME-004": ("混装或漏装（未细分）", "Mixed or missing assembly, unspecified", "原文合并记录混装和漏装，且无法判断具体一种。"),
        "BME-005": ("功能不良（未细分）", "Functional defect, unspecified", "明确功能检查不合格，具体失效表现缺失。"),
    },
}

# Candidate exact aliases by observation stage. Drafts never resolve report data.
ZX_ALIASES = {
    "IQC": {
        "印刷不良": "TU-013", "印字不全": "TU-013", "有印刷不良现象": "TU-013", "印刷不清晰": "TU-013",
        "色差3级": "TU-014", "色差大、不是一个色系": "TU-014",
        "拉力不达标": "TU-016", "拉力不符合要求": "TU-016", "注塑点毛刺": "TU-020",
    },
    "PQC": {
        "缝份不匀": "TU-001", "内里爆口": "TU-002", "扭指": "TU-003", "内里扭指": "TU-004",
        "网布抽丝": "TU-005", "网棉漏车": "TU-007", "明线不匀": "TU-008", "线迹不良": "TU-009",
        "死皱": "TU-010", "针密度": "TU-011", "明线距边不匀": "TU-012", "织标倾斜": "TU-017",
        "脏污": "TU-018", "倒针不良": "TU-019", "外连倒回针未打满": "TU-019", "针洞": "TU-021",
    },
    "FQC": {
        "缝份不匀": "TU-001", "内里爆口": "TU-002", "扭指": "TU-003", "线头": "TU-006",
        "网棉漏车": "TU-007", "明线不匀": "TU-008", "线迹不良": "TU-009", "死皱": "TU-010",
        "针密度": "TU-011", "明线距边不匀": "TU-012", "针洞": "TU-021",
    },
}

# stage = where the defect was observed, which can differ from the step where
# the check would be performed. Rows are pinned to the supplied workbook digest.
ZX_LINKS = (
    ("IQC", "TU-013", 15, "VERIFY", "仅在印刷异常发生在来料标签时核对 Techpack。"),
    ("IQC", "TU-014", 10, "DETECT", "对照批准的色样核对布料色差。"),
    ("IQC", "TU-015", 10, "DETECT", "确认面料适用四分制后复检破洞。"),
    ("IQC", "TU-016", 9, "VERIFY", "核对批次测试报告和实际拉力标准。"),
    ("PQC", "TU-001", 51, "DETECT", "核对实际工序和该款 Techpack 的缝份要求。"),
    ("PQC", "TU-002", 53, "DETECT", "检查接缝有无开口，确认该点覆盖内里工序。"),
    ("PQC", "TU-002", 61, "VERIFY", "在适用时复核内里结构和连接方式。"),
    ("PQC", "TU-003", 59, "DETECT", "复检手指形态和扭转。"),
    ("PQC", "TU-004", 61, "VERIFY", "在适用时复核内里结构，另行确认扭转判定。"),
    ("PQC", "TU-005", 59, "DETECT", "目检抽丝并定位部位。"),
    ("PQC", "TU-007", 53, "VERIFY", "沿接缝复查缺失车缝，确认网棉工序适用。"),
    ("PQC", "TU-008", 52, "DETECT", "核对线迹规律性，按实际针型确认方法。"),
    ("PQC", "TU-009", 52, "VERIFY", "先拆分具体线迹现象，再选择检查方法。"),
    ("PQC", "TU-010", 59, "DETECT", "目检固定皱褶并记录部位。"),
    ("PQC", "TU-011", 52, "DETECT", "先确认针型，再按适用标准量针密度。"),
    ("PQC", "TU-017", 64, "DETECT", "核对水洗标或尺码标的位置。"),
    ("PQC", "TU-018", 59, "DETECT", "目检污点并记录部位。"),
    ("PQC", "TU-021", 59, "DETECT", "按外观要求复查孔洞，记录部位并回查相关工序。"),
    ("FQC", "TU-001", 51, "VERIFY", "回查对应车缝工序和该款缝份要求。"),
    ("FQC", "TU-002", 53, "VERIFY", "复查接缝开口及其工序。"),
    ("FQC", "TU-002", 99, "VERIFY", "仅适用于无 insert 的对应结构，按批准方法检查内里。"),
    ("FQC", "TU-003", 59, "DETECT", "复检扭指，核实成品验货的批准方法。"),
    ("FQC", "TU-006", 82, "DETECT", "目检未剪线头。"),
    ("FQC", "TU-007", 53, "VERIFY", "回查接缝和网棉车缝工序。"),
    ("FQC", "TU-008", 52, "VERIFY", "回查线迹规律性。"),
    ("FQC", "TU-009", 52, "VERIFY", "确认线迹异常细节后回查车缝工序。"),
    ("FQC", "TU-010", 59, "DETECT", "复查皱褶部位和外观。"),
    ("FQC", "TU-011", 52, "VERIFY", "回查针密度及适用针型。"),
    ("FQC", "TU-021", 82, "DETECT", "按成品外观要求复查孔洞，记录位置和批次。"),
)
