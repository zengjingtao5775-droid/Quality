"""Defect mapping, annotation, evaluation and evidence inside the Quality Dashboard."""
from __future__ import annotations

from dataclasses import asdict
import csv
from pathlib import Path
import re
import sqlite3
from tempfile import TemporaryDirectory

import pandas as pd
import streamlit as st

from quality_graph import (Observation, ReviewStore, accepted_samples, candidate_aliases, clean,
                           csv_bytes, evaluate, graph_db, graph_mode, guide_path, link_candidates, link_key, normalized,
                           read_controls, read_csv_observations, read_zx_observations, report_control_candidates)
from quality_graph_seed import GLOVES, GUIDE_DIGEST, STAGES, TAXONOMY, TAXONOMY_VERSION
from quality_workbench_ui import render_labeling_workbench

QUALITY_GRAPH_RELEASE = 2


def review_store(root):
    if graph_mode() != "trial":
        return ReviewStore(graph_db(root))
    key = "_quality_graph_trial_store"
    if key not in st.session_state:
        folder = TemporaryDirectory(prefix="quality-graph-trial-")
        st.session_state[key] = (folder, ReviewStore(Path(folder.name) / "reviews.sqlite3"))
    return st.session_state[key][1]


@st.cache_data(show_spinner=False)
def _cached_guide(path, mtime, size):
    return read_controls(path)


def load_guide():
    path = guide_path()
    try:
        stat = path.stat()
        return _cached_guide(path, stat.st_mtime_ns, stat.st_size), ""
    except (OSError, ValueError) as error:
        return {}, str(error)


@st.cache_data(show_spinner=False)
def _cached_zx(directory, source_versions):
    return read_zx_observations(directory)


def local_zx(root):
    directory = root / "TU database/ZX Database/Factory data"
    versions = tuple(sorted((path.name, path.stat().st_mtime_ns, path.stat().st_size) for path in directory.glob("*.xlsx")))
    return _cached_zx(directory, versions)


def dashboard_observations(jdy, bme):
    """Read descriptions and source IDs only. Never import inspector or worker names."""
    rows = []
    for record in jdy.to_dict("records"):
        record_id = clean(record.get("record_id"))
        if not record_id:
            continue
        unique = set()
        for field in ("gtd_issue", "visual_issue", "functional_issue", "liner_issue", "size_issue", "important_issue"):
            desc = clean(record.get(field))
            if not desc or desc in {"0", "0.0", "/", "无", "无疵点", "无不良"} or normalized(desc) in unique:
                continue
            unique.add(normalized(desc))
            rows.append(Observation("TU", "ZX", GLOVES, "FQC", desc, field,
                clean(record.get("source")) or "Jiandaoyun FQC", f"{record_id}/{field}", clean(record.get("po")),
                clean(record.get("date"))[:10], clean(record.get("cc")).removesuffix(".0"), raw_type=field))
    if not bme.empty:
        for record in bme.loc[bme["is_alert"].fillna(False)].to_dict("records"):
            stage = clean(record.get("stage")).upper()
            if stage in {"DKL", "AQL"}:
                stage = "FQC"
            desc, supplier, source, row = (clean(record.get(field)) for field in ("issue_driver", "supplier", "source_file", "source_row"))
            if stage not in STAGES or not all((desc, supplier, source, row)):
                continue
            family = clean(record.get("family")) or "Unspecified BME family"
            rows.append(Observation("BME", supplier, family, stage, desc, clean(record.get("process")),
                f"{source} / {clean(record.get('source_sheet'))}", row, clean(record.get("order_po")),
                clean(record.get("date"))[:10]))
    return rows


def _name(code, t):
    if not code:
        return "—"
    zh, en, _ = TAXONOMY[code.split("-")[0]][code]
    return f"{code} · {t(zh, en)}"


def _save(store, kind, key, previous, actor, payload, t):
    try:
        store.write(kind, key, previous.get("revision", 0), actor, payload)
    except (ValueError, sqlite3.Error) as error:
        st.error(str(error))
    else:
        st.session_state["qg_saved"] = t("已保存审核记录。", "Review saved.")
        st.rerun()


def mapping_rows(observations, aliases, links, controls):
    """Export the two edge types independently, preserving many-to-many links."""
    rows = []
    for key, obs, draft, count in candidate_aliases(observations):
        saved = aliases.get(key, {})
        defect = saved.get("defect", draft)
        rows.append(dict(edge="ALIAS_OF", community=obs.community, factory=obs.factory, family=obs.family, stage=obs.stage,
            raw_type=obs.raw_type, raw_description=obs.description, records=count, canonical_id=defect,
            canonical_name=TAXONOMY[obs.community].get(defect, ("",))[0],
            canonical_name_en=TAXONOMY[obs.community][defect][1] if defect else "",
            status=saved.get("status", "draft" if draft else "unmapped"), relation="EXACT_WITHIN_SCOPE",
            what="", how="", target="", tolerance="", frequency="", sampling="", how_to_react="", cp_version="", cp_sha256="", reference="",
            approved_ccs="", note=saved.get("reason", ""), source=obs.source, reviewer=saved.get("actor", ""),
            reviewed_at=saved.get("at", ""), taxonomy=TAXONOMY_VERSION))
    for key, stage, defect, row, relation, note in link_candidates(links):
        control, saved = controls.get(row, {}), links.get(key, {})
        rows.append(dict(edge="CONTROL_LINK", community="TU", factory="ZX", family=GLOVES, stage=stage,
            raw_type="", raw_description="", records="", canonical_id=defect, canonical_name=TAXONOMY["TU"][defect][0],
            canonical_name_en=TAXONOMY["TU"][defect][1],
            status=saved.get("status", "draft") if control else "source_unavailable", relation=relation,
            what=control.get("what", ""), how=control.get("how", ""), target=control.get("target", ""),
            tolerance=control.get("tolerance", ""), frequency=control.get("frequency", ""), sampling=control.get("sampling", ""),
            how_to_react=control.get("reaction", ""), cp_version=control.get("version", ""),
            cp_sha256=GUIDE_DIGEST if control else "", reference=control.get("reference", ""),
            approved_ccs=" / ".join(saved.get("ccs", [])), note=" | ".join(filter(None, [note, saved.get("reason")])),
            source=control.get("source", ""), reviewer=saved.get("actor", ""), reviewed_at=saved.get("at", ""), taxonomy=TAXONOMY_VERSION))
    return rows


def _mapping_editor(scoped, aliases, links, controls, store, actor, show_zx, stage_filter, t):
    st.subheader(t("原始描述 → 标准疵点", "Source wording → canonical defect"))
    st.caption(t("同一个社区、工厂、产品族和检验环节内确认同义词。表中的次数是描述记录数。",
                 "Approve aliases within the same community, factory, product family and gate. Counts are observation records."))
    candidates = sorted(candidate_aliases(scoped), key=lambda item: (-item[3], item[1].description))
    if candidates:
        selected = st.selectbox(t("选择待映射描述", "Select a description"), candidates, index=None,
            format_func=lambda item: (f"{item[1].description} · {item[1].raw_type or '—'} · "
                                      f"{item[1].factory} / {item[1].family} / {item[1].stage} · {item[3]}"), key="qg_alias")
        if selected:
            key, obs, draft, _ = selected
            previous = aliases.get(key, {})
            seed = previous.get("defect", draft)
            codes = list(TAXONOMY[obs.community])
            if seed:
                path = [{"Control Plan": controls[row]["what"], "How to control": controls[row]["how"],
                         t("来源", "Source"): controls[row]["reference"],
                         t("状态", "Status"): links.get(link, {}).get("status", "draft")}
                        for link, stage, defect, row, _, _ in link_candidates(links)
                        if (obs.community, obs.factory, obs.family) == ("TU", "ZX", GLOVES)
                        and stage == obs.stage and defect == seed and row in controls]
                st.caption(f"{obs.description} → {_name(seed, t)} → Control Plan")
                if path:
                    st.dataframe(path, hide_index=True, width="stretch")
            with st.form(f"qg_alias_{key}_{previous.get('revision', 0)}"):
                defect = st.selectbox(t("标准疵点", "Canonical defect"), codes, index=codes.index(seed) if seed in codes else None,
                                      format_func=lambda code: _name(code, t))
                st.caption(t("当前状态", "Current status") + " · " + previous.get("status", "draft" if draft else "unmapped"))
                reason = st.text_area(t("判定依据或适用边界", "Evidence or applicability limits"), value=previous.get("reason", ""))
                approve = st.form_submit_button(t("确认同义映射", "Approve alias"), disabled=not bool(clean(actor)))
                block = st.form_submit_button(t("标为待澄清", "Mark unresolved"), disabled=not bool(clean(actor)))
            if approve or block:
                if not clean(reason) or (approve and not defect):
                    st.error(t("请填写判定依据，并为确认的映射选择标准疵点。", "Add evidence and select a defect for approval."))
                else:
                    _save(store, "alias", key, previous, actor,
                          dict(defect=defect or "", reason=reason, status="approved" if approve else "unresolved"), t)
    else:
        st.info(t("这个范围暂无描述。可以在「数据与评估」导入 CSV。", "No observations in this scope. Import a CSV in Data and evaluation."))

    if not show_zx:
        return
    st.subheader(t("标准疵点 → Control Plan", "Canonical defect → Control Plan"))
    if not controls:
        st.info(t("请加载本试点对应版本的 ZX 手套 CP。", "Load the ZX glove guide version for this pilot."))
        return
    options = [item for item in link_candidates(links) if item[3] in controls and (not stage_filter or item[1] == stage_filter)]
    selected = st.selectbox(t("核对 ZX 手套控制项", "Review a ZX glove control link"), options, index=None,
        format_func=lambda item: f"{item[1]} · {_name(item[2], t)} · {t('原表行', 'Source row')} {item[3]} · {controls[item[3]]['what']}", key="qg_edge")
    if selected:
        key, stage, defect, row, relation, note = selected
        control = controls[row]
        previous = links.get(key, {})
        st.write(control["reference"], control["section"], control["step"])
        st.markdown(f"**What to control**  \n{control['what']}  \n**How to control**  \n{control['how']}")
        st.text(f"Target · {control['target']}\nTolerance · {control['tolerance']}\nHow to React · {control['reaction'] or '—'}")
        st.caption(f"{relation} · {note}")
        with st.form(f"qg_edge_{key}_{previous.get('revision', 0)}"):
            st.caption(t("当前状态", "Current status") + " · " + previous.get("status", "draft"))
            ccs = st.text_input(t("已确认适用的 CC（六位，空格分隔）", "Confirmed applicable CCs (six digits, space separated)"), value=" ".join(previous.get("ccs", [])))
            reason = st.text_area(t("适用依据（如 ZX 批准 CP 或 Techpack 版本及定位）", "Applicability evidence (e.g. approved ZX CP or Techpack revision and reference)"), value=previous.get("reason", ""))
            approve = st.form_submit_button(t("确认控制项与适用 CC", "Approve control and CC scope"), disabled=not bool(clean(actor)))
            block = st.form_submit_button(t("标为待复核", "Mark for review"), disabled=not bool(clean(actor)))
        if approve or block:
            ids = sorted(set(ccs.split())) if approve else []
            if not clean(reason) or (approve and (not ids or not all(re.fullmatch(r"[0-9]{6}", cc) for cc in ids))):
                st.error(t("请填依据，并为确认的关联填写有效 CC。", "Enter evidence and valid CCs for an approved link."))
            else:
                _save(store, "link", key, previous, actor, dict(ccs=ids, reason=reason, edge=[stage, defect, row, relation, note],
                      status="approved" if approve else "unresolved"), t)
    with st.expander(t("新增 ZX 控制关联候选", "Add a ZX control-link candidate")):
        with st.form("qg_new_edge"):
            stage = st.selectbox(t("发现疵点的环节", "Observation gate"), STAGES, index=STAGES.index(stage_filter) if stage_filter else 0)
            defect = st.selectbox(t("标准疵点", "Canonical defect"), TAXONOMY["TU"], format_func=lambda code: _name(code, t))
            row = st.selectbox(t("CP 原表行", "CP source row"), list(controls), index=None,
                format_func=lambda n: f"{n} · {controls[n]['step']} / {controls[n]['what'] or controls[n]['how']}")
            relation = st.selectbox(t("关系", "Relation"), {"DETECT": t("用于检出", "Detect"), "VERIFY": t("用于复核", "Verify")},
                                    format_func={"DETECT": t("用于检出", "Detect"), "VERIFY": t("用于复核", "Verify")}.get)
            note = st.text_area(t("建议如何检查及适用条件", "Proposed check and conditions"))
            add = st.form_submit_button(t("保存为候选", "Save candidate"), disabled=not bool(clean(actor)))
        if add:
            key = link_key(stage, defect, row)
            if not row or not clean(note):
                st.error(t("请选择 CP 条目并填写检查说明。", "Select a CP entry and describe the check."))
            elif key in {edge[0] for edge in link_candidates(links)}:
                st.error(t("这条关联已存在，可在上方核对。", "The link already exists. Review it above."))
            else:
                _save(store, "link", key, {}, actor, dict(ccs=[], reason="", edge=[stage, defect, row, relation, note], status="draft"), t)


def _data_and_evaluation(scoped, decisions, store, trial, t):
    st.subheader(t("导入检验样本", "Import inspection observations"))
    st.caption(t("CSV 用 UTF-8。必填字段为 community、factory、family、stage、description、source、record。可带 raw_type、process、batch、date、cc。",
                 "Use UTF-8 CSV. Required fields are community, factory, family, stage, description, source and record. Optional fields are raw_type, process, batch, date and cc."))
    upload = st.file_uploader(t("上传 CSV", "Upload CSV"), type="csv", key="qg_import")
    if st.button(t("导入本机队列", "Import to the local queue"), disabled=upload is None, key="qg_import_button"):
        try:
            if trial and upload.size > 2_000_000:
                raise ValueError(t("试用单个 CSV 上限为 2 MB。", "Trial CSVs are limited to 2 MB."))
            records = read_csv_observations(upload.getvalue())
            if trial and len({obs.id for obs in [*records, *store.observations()]}) > 5000:
                raise ValueError(t("试用每个会话最多导入 5,000 条记录。", "A trial session can import up to 5,000 records."))
            count = store.import_observations(records)
        except (UnicodeError, ValueError, csv.Error, sqlite3.Error) as error:
            st.error(str(error))
        else:
            st.session_state["qg_saved"] = t(f"新增 {count:,} 条，重复记录已跳过。", f"Imported {count:,} new records. Duplicates skipped.")
            st.rerun()
    st.subheader(t("标签与模型评估", "Labels and model evaluation"))
    st.caption(t("分类基线在看板服务器的 Python 进程内，用当前标签即时拟合。评估会先留出测试样本，再计算准确率。",
                 "The dashboard's Python process fits the baseline on the current labels. Evaluation holds out test records before calculating accuracy."))
    scoped_ids = {obs.id for obs in scoped}
    accepted = [(obs, item) for obs, item in accepted_samples(decisions) if obs.id in scoped_ids]
    labels = [(obs, item["labels"][0]) for obs, item in accepted if len(item["labels"]) == 1]
    export = [{"sample_id": obs.id, **asdict(obs), "labels": "|".join(item["labels"]), "outcome": item["outcome"],
               "reason": item["reason"], "annotator": item.get("annotator", item["actor"]),
               "reviewer": item["actor"] if item["status"] == "approved" else "",
               "reviewed_at": item["at"] if item["status"] == "approved" else "",
               "confirmed_at": item["at"], "taxonomy": item["taxonomy"]}
              for obs, item in accepted]
    st.caption(t(f"已处理 {len(accepted):,} 条，其中单标签 {len(labels):,} 条可用于本轮基线。", f"{len(accepted):,} answered records, including {len(labels):,} single-label baseline records."))
    st.download_button(t("下载标签 CSV", "Download labels CSV"), csv_bytes(export), "quality-labels.csv", "text/csv", disabled=not export)
    domains = sorted({(obs.community, obs.family, obs.stage) for obs, _ in labels})
    domain = st.selectbox(t("评估范围", "Evaluation domain"), domains, index=None, format_func=lambda item: " / ".join(item), key="qg_eval_domain")
    if not domain:
        st.info(t("暂无可报告的准确率。先为同一产品族和检验环节标注足够样本。", "No accuracy to report yet. Label enough records within a product family and inspection gate first."))
        return
    rows = [(obs, label) for obs, label in labels if (obs.community, obs.family, obs.stage) == domain]
    factories = sorted({obs.factory for obs, _ in rows})
    holdout = st.selectbox(t("留出工厂（可选）", "Hold out a factory (optional)"), factories if len(factories) > 1 else [], index=None,
                           key="qg_eval_factory")
    metrics = evaluate(rows, holdout)
    if not metrics:
        st.info(t("去除重复描述和重叠批次后，至少需要 10 条训练、5 条测试、3 种测试描述和两个训练标签。",
                  "After excluding repeated wording and overlapping batches, evaluation needs at least 10 train records, 5 test records, 3 test phrases and 2 train classes."))
        return
    cols = st.columns(4)
    for column, label, metric in zip(cols, ["Accuracy", "Macro F1", t("预测覆盖率", "Coverage"), t("多数类基线", "Majority baseline")],
                                     ["accuracy", "macro_f1", "coverage", "majority_accuracy"]):
        column.metric(label, f"{metrics[metric]:.1%}")
    st.caption(t(f"训练 {metrics['train_records']} 条，测试 {metrics['test_records']} 条，按 {metrics['test_groups']} 组去重计分。弃权计为未命中。",
                 f"{metrics['train_records']} train records and {metrics['test_records']} test records scored as {metrics['test_groups']} deduplicated groups. Abstentions count as misses."))
    st.dataframe(metrics["per_label"], hide_index=True, width="stretch")
    with st.expander(t("混淆明细", "Confusion details")):
        st.dataframe(metrics["confusion"], hide_index=True, width="stretch")


def render_quality_graph(root, jdy, bme, t):
    st.header(t("质量知识图谱 · 疵点标注", "Quality Knowledge Graph · Defect Labeling"))
    trial = graph_mode() == "trial"
    if trial:
        st.caption(t("线上试用 · 标注、导入和审批保存在当前浏览器会话。离开前可从「数据与评估」导出标签。",
                     "Online trial · Labels, imports and approvals stay in this session. Export labels from Data and evaluation before leaving."))
    store = review_store(root)
    controls, error = load_guide()
    if error:
        st.warning(t("ZX CP 来源不可用，报告中的 CP 关联暂停。", "ZX CP source unavailable. Report control links are suspended."))
    connected = [] if trial else dashboard_observations(jdy, bme)
    observations = list({obs.id: obs for obs in [*local_zx(root), *connected, *store.observations()]}.values())
    labels, aliases, links = (store.latest(kind) for kind in ("label", "alias", "link"))
    if message := st.session_state.pop("qg_saved", ""):
        st.success(message)
    with st.expander(t("按社区、工厂或检验环节筛选", "Filter by community, factory or inspection gate")):
        filters = st.columns(4)
        community = filters[0].selectbox("Community", list(TAXONOMY), key="qg_community")
        factories = sorted({obs.factory for obs in observations if obs.community == community})
        factory = filters[1].selectbox(t("工厂", "Factory"), factories, index=None, placeholder=t("全部工厂", "All factories"), key="qg_factory")
        stage = filters[2].selectbox(t("检验环节", "Inspection gate"), STAGES, index=None, placeholder=t("全部环节", "All gates"), key="qg_stage")
        families = sorted({obs.family for obs in observations if obs.community == community and (not factory or obs.factory == factory)})
        family = filters[3].selectbox(t("产品族", "Product family"), families, index=None, placeholder=t("全部产品族", "All families"), key="qg_family")
    scoped = [obs for obs in observations if obs.community == community and (not factory or factory == obs.factory)
              and (not stage or stage == obs.stage) and (not family or family == obs.family)]
    panels = {"label": t("标注工作台", "Labeling workbench"), "mapping": "Defect Mapping", "data": t("数据与评估", "Data and evaluation")}
    panel = st.radio(t("质量知识图谱功能", "Quality graph view"), panels, format_func=panels.get,
                     horizontal=True, label_visibility="collapsed", key="qg_panel")
    if panel == "mapping":
        actor = st.text_input(t("映射审核人", "Mapping reviewer"), key="qg_mapping_actor", max_chars=80)
        if controls:
            st.caption(t(f"ZX 手套 CP V2.0 · {len(controls)} 条控制条目", f"ZX glove guide V2.0 · {len(controls)} control entries"))
        rows = [row for row in mapping_rows(scoped, aliases, links, controls) if row["community"] == community
                and (not stage or row["stage"] == stage) and (not factory or row["factory"] == factory)
                and (not family or row["family"] == family)]
        visible = pd.DataFrame(rows, columns=["edge", "stage", "raw_type", "raw_description", "canonical_name", "status", "how", "reference"])
        if community == "BME":
            st.info(t("BME 需要自己的 Control Plan。可先导入和标注，ZX 控制条目只适用 TU 手套试点。", "BME can import and label data now. It needs its own control plan. ZX controls are scoped to the TU glove pilot."))
        st.dataframe(visible, hide_index=True, width="stretch", height=290)
        st.download_button(t("下载当前映射 CSV", "Download mapping CSV"), csv_bytes(rows), "quality-defect-mapping.csv", "text/csv", disabled=not rows)
        show_zx = community == "TU" and factory in (None, "ZX") and family in (None, GLOVES)
        _mapping_editor(scoped, aliases, links, controls, store, actor, show_zx, stage, t)
    elif panel == "data":
        _data_and_evaluation(scoped, labels, store, trial, t)
    else:
        render_labeling_workbench(scoped, labels, store, (community, factory, stage, family), t)


def report_control_evidence(root, finished, products):
    """Return CP evidence for the exact displayed defect in each CC's report row."""
    controls, error = load_guide()
    if error or finished.empty or not products:
        return {}, bool(error)
    store = review_store(root)
    aliases, links = store.latest("alias"), store.latest("link")
    defects = {str(item["cc"]): clean(item.get("top_defect")) for item in products[:5]}
    kinds = {"中间检验": "PQC", "成品检验": "FQC"}
    source = finished.loc[finished["product_code"].isin(defects) & finished["defect_qty"].gt(0),
                          ["product_code", "inspection_type", "defect_type"]].drop_duplicates()
    evidence = {}
    for row in source.itertuples(index=False):
        cc, stage = str(row.product_code), kinds.get(row.inspection_type)
        if not stage or not defects[cc] or normalized(row.defect_type) != normalized(defects[cc]):
            continue
        observation = Observation("TU", "ZX", GLOVES, stage, clean(row.defect_type),
                                  source="Dashboard factory inspections", record=cc, cc=cc)
        status, matches = report_control_candidates(observation, aliases, links, controls)
        evidence.setdefault(cc, []).extend({**item, "stage": stage, "status": status} for item in matches)
    for matches in evidence.values():
        matches.sort(key=lambda item: (item["status"] != "linked", item["stage"] != "PQC", item["row"]))
    return evidence, False
