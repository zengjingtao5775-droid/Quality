"""Defect mapping, annotation, evaluation and evidence inside the Quality Dashboard."""
from __future__ import annotations

from dataclasses import asdict
import csv
from collections import Counter
from pathlib import Path
import re
import sqlite3
from tempfile import TemporaryDirectory

import pandas as pd
import streamlit as st

from quality_graph import (EVALUATION_MINIMUMS, Observation, ReviewStore, accepted_samples, candidate_aliases, clean,
                           csv_bytes, defect_types, evaluate_with_readiness, extract_decathlon_model, graph_db, graph_mode, guide_path, link_candidates,
                           link_key, normalized, read_controls, read_csv_observations, read_zx_observations,
                           report_control_candidates, save_defect_type)
from quality_graph_seed import GLOVES, GUIDE_DIGEST, LABELING_STAGES, STAGES, TAXONOMY, TAXONOMY_VERSION, ZX_PQC_PILOT_LABELS
from quality_label_storage import render_browser_backup, restore_browser_backup
from quality_workbench_ui import render_labeling_workbench

QUALITY_GRAPH_RELEASE = 9


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
def _cached_zx(directory, source_versions, parser_release):
    return read_zx_observations(directory)


def local_zx(root):
    directory = root / "TU database/ZX Database/Factory data"
    versions = tuple(sorted((path.name, path.stat().st_mtime_ns, path.stat().st_size) for path in directory.glob("*.xlsx")))
    return _cached_zx(directory, versions, QUALITY_GRAPH_RELEASE)


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
                clean(record.get("date"))[:10], clean(record.get("cc")).removesuffix(".0"), raw_type=field,
                model=extract_decathlon_model(record.get("model")) or clean(record.get("model"))))
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
                clean(record.get("date"))[:10], model=clean(record.get("model_code"))))
    return rows


def _name(code, types, t):
    if not code:
        return "—"
    zh, en, _ = types[code]
    return f"{code} · {t(zh, en)}"


def _save(store, kind, key, previous, actor, payload, t):
    try:
        store.write(kind, key, previous.get("revision", 0), actor, payload)
    except (ValueError, sqlite3.Error) as error:
        st.error(str(error))
    else:
        st.session_state["qg_saved"] = t("已保存审核记录。", "Review saved.")
        st.rerun()


def mapping_rows(observations, aliases, links, controls, catalog):
    """Export the two edge types independently, preserving many-to-many links."""
    rows = []
    for key, obs, draft, count in candidate_aliases(observations):
        saved = aliases.get(key, {})
        defect = saved.get("defect", draft)
        zh, en, _ = catalog[obs.community].get(defect, ("", "", ""))
        rows.append(dict(edge="ALIAS_OF", community=obs.community, factory=obs.factory, family=obs.family, stage=obs.stage,
            raw_type=obs.raw_type, raw_description=obs.description, records=count, canonical_id=defect,
            canonical_name=zh, canonical_name_en=en,
            status=saved.get("status", "draft" if draft else "unmapped"), relation="EXACT_WITHIN_SCOPE",
            what="", how="", target="", tolerance="", frequency="", sampling="", how_to_react="", cp_version="", cp_sha256="", reference="",
            approved_ccs="", note=saved.get("reason", ""), source=obs.source, reviewer=saved.get("actor", ""),
            reviewed_at=saved.get("at", ""), taxonomy=TAXONOMY_VERSION))
    for key, stage, defect, row, relation, note in link_candidates(links):
        control, saved = controls.get(row, {}), links.get(key, {})
        zh, en, _ = catalog["TU"].get(defect, ("", "", ""))
        rows.append(dict(edge="CONTROL_LINK", community="TU", factory="ZX", family=GLOVES, stage=stage,
            raw_type="", raw_description="", records="", canonical_id=defect, canonical_name=zh, canonical_name_en=en,
            status=saved.get("status", "draft") if control else "source_unavailable", relation=relation,
            what=control.get("what", ""), how=control.get("how", ""), target=control.get("target", ""),
            tolerance=control.get("tolerance", ""), frequency=control.get("frequency", ""), sampling=control.get("sampling", ""),
            how_to_react=control.get("reaction", ""), cp_version=control.get("version", ""),
            cp_sha256=GUIDE_DIGEST if control else "", reference=control.get("reference", ""),
            approved_ccs=" / ".join(saved.get("ccs", [])), note=" | ".join(filter(None, [note, saved.get("reason")])),
            source=control.get("source", ""), reviewer=saved.get("actor", ""), reviewed_at=saved.get("at", ""), taxonomy=TAXONOMY_VERSION))
    return rows


def _alias_editor(scoped, aliases, links, controls, store, actor, types, t):
    candidates = sorted(candidate_aliases(scoped), key=lambda item: (-item[3], item[1].description))
    if candidates:
        selected = st.selectbox(t("选择待映射描述", "Select a description"), candidates, index=None,
            format_func=lambda item: (f"{item[1].description} · {item[1].raw_type or '—'} · "
                                      f"{item[1].factory} / {item[1].family} / {item[1].stage} · {item[3]}"), key="qg_alias")
        if selected:
            key, obs, draft, _ = selected
            previous = aliases.get(key, {})
            seed = previous.get("defect", draft)
            codes = list(types)
            if seed:
                path = [{"Control Plan": controls[row]["what"], "How to control": controls[row]["how"],
                         t("来源", "Source"): controls[row]["reference"],
                         t("状态", "Status"): links.get(link, {}).get("status", "draft")}
                        for link, stage, defect, row, _, _ in link_candidates(links)
                        if (obs.community, obs.factory, obs.family) == ("TU", "ZX", GLOVES)
                        and stage == obs.stage and defect == seed and row in controls]
                if path:
                    with st.expander(t("关联的控制项", "Related controls")):
                        st.dataframe(path, hide_index=True, width="stretch")
            with st.form(f"qg_alias_{key}_{previous.get('revision', 0)}"):
                defect = st.selectbox(t("标准疵点", "Canonical defect"), codes, index=codes.index(seed) if seed in codes else None,
                                      format_func=lambda code: _name(code, types, t))
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



def _cp_editor(links, controls, store, actor, stage_filter, types, t):
    if not controls:
        st.info(t("请加载本试点对应版本的 ZX 手套 CP。", "Load the ZX glove guide version for this pilot."))
        return
    options = [item for item in link_candidates(links) if item[3] in controls and (not stage_filter or item[1] == stage_filter)]
    selected = st.selectbox(t("核对 ZX 手套控制项", "Review a ZX glove control link"), options, index=None,
        format_func=lambda item: f"{item[1]} · {_name(item[2], types, t)} · {t('原表行', 'Source row')} {item[3]} · {controls[item[3]]['what']}", key="qg_edge")
    if selected:
        key, stage, defect, row, relation, note = selected
        control = controls[row]
        previous = links.get(key, {})
        with st.expander(t("查看 CP 原表信息", "View CP source details")):
            for field, label in (("reference", t("来源", "Source")), ("what", t("控制项", "Control")),
                                 ("how", t("方法", "Method")), ("target", t("目标", "Target")),
                                 ("tolerance", t("公差", "Tolerance")), ("reaction", t("应对", "Reaction"))):
                if control[field] not in {"", "NA", "N/A"}:
                    st.write(label, control[field])
            st.write(note)
        with st.form(f"qg_edge_{key}_{previous.get('revision', 0)}"):
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
            defect = st.selectbox(t("标准疵点", "Canonical defect"), types, format_func=lambda code: _name(code, types, t))
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


def _dictionary_editor(store, community, saved, types, t):
    rows = [dict(code=code, zh=zh, en=en, definition=definition) for code, (zh, en, definition) in types.items()]
    listing, editor = st.columns([1.7, 1], gap="medium")
    with listing:
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", height=420, column_config={
            "code": t("编号", "ID"), "zh": t("中文名称", "Chinese name"), "en": t("英文名称", "English name"),
            "definition": t("判定定义", "Definition"),
        })
        st.download_button(t("下载字典 CSV", "Download dictionary CSV"), csv_bytes(rows), "quality-defect-types.csv", "text/csv")
    with editor, st.container(border=True, key="qg_mapping_editor"):
        st.subheader(t("编辑标准疵点", "Edit canonical defects"))
        code = st.selectbox(t("选择疵点", "Choose a defect"), ["", *types], key=f"qg_type_{community}",
                            format_func=lambda item: _name(item, types, t) if item else t("＋ 新增疵点", "+ Add a defect"))
        zh, en, definition = types.get(code, ("", "", ""))
        with st.form(f"qg_type_form_{community}_{code}_{saved.get('revision', 0)}"):
            zh = st.text_input(t("中文名称", "Chinese name"), value=zh, max_chars=80)
            en = st.text_input(t("英文名称", "English name"), value=en, max_chars=120)
            definition = st.text_area(t("判定定义", "Definition"), value=definition, max_chars=500)
            submit = st.form_submit_button(t("保存疵点", "Save defect"), type="primary")
        if submit:
            try:
                updated = save_defect_type(store, community, saved, code, zh, en, definition)
            except (ValueError, sqlite3.Error) as error:
                st.error(str(error))
            else:
                st.session_state["qg_saved"] = t(f"已保存标准疵点 {updated}。", f"Saved defect type {updated}.")
                st.rerun()


def _render_mapping(scoped, aliases, links, controls, store, community, factory, stage, family, t):
    saved_types = store.latest("taxonomy")
    catalog = {key: defect_types(key, saved_types.get(key)) for key in TAXONOMY}
    types = catalog[community]
    show_zx = community == "TU" and factory in (None, "ZX") and family in (None, GLOVES)
    modes = {"dictionary": t("标准疵点字典", "Defect dictionary"), "aliases": t("疵点描述映射", "Defect descriptions"), "controls": "Control Plan"}
    st.subheader("Defect Mapping")
    mode = st.radio(t("映射类型", "Mapping type"), modes if show_zx else ["dictionary", "aliases"], format_func=modes.get,
                    horizontal=True, label_visibility="collapsed", key="qg_mapping_kind")
    if mode == "dictionary":
        _dictionary_editor(store, community, saved_types.get(community, {}), types, t)
        return
    rows = [row for row in mapping_rows(scoped, aliases, links, controls, catalog) if row["community"] == community
            and (not stage or row["stage"] == stage) and (not factory or row["factory"] == factory)
            and (not family or row["family"] == family)]
    descriptions = [row for row in rows if row["edge"] == "ALIAS_OF"]
    control_links = [row for row in rows if row["edge"] == "CONTROL_LINK"]
    with st.container(key="qg_mapping_metrics"):
        cards = st.columns(3)
        cards[0].metric(t("疵点描述", "Defect descriptions"), len(descriptions))
        cards[1].metric(t("已确认映射", "Approved mappings"), sum(row["status"] == "approved" for row in descriptions))
        cards[2].metric(t("CP 关联", "CP links"), len(control_links))
    statuses = {"draft": t("待确认", "Pending"), "unmapped": t("未匹配", "Unmapped"),
                "approved": t("已确认", "Approved"), "unresolved": t("待澄清", "Unresolved"),
                "source_unavailable": t("来源缺失", "Source unavailable")}
    name_key = "canonical_name" if t("zh", "en") == "zh" else "canonical_name_en"
    fields = {"raw_description": t("原始描述", "Original wording"), "stage": t("环节", "Stage"),
              name_key: t("标准疵点", "Canonical defect"), "records": t("记录数", "Records"),
              "how": t("控制方法", "Method"), "what": t("控制项", "Control"), "status": t("状态", "Status")}
    keys = ["raw_description", name_key, "stage", "records", "status"] if mode == "aliases" else ["stage", name_key, "how", "what", "status"]
    table = pd.DataFrame(descriptions if mode == "aliases" else control_links, columns=keys)
    table["status"] = table["status"].map(statuses)
    listing, editor = st.columns([1.7, 1], gap="medium")
    with listing:
        st.dataframe(table.rename(columns=fields), hide_index=True, width="stretch", height=420)
        st.download_button(t("下载映射 CSV", "Download CSV"), csv_bytes(rows), "quality-defect-mapping.csv", "text/csv", disabled=not rows)
    with editor, st.container(border=True, key="qg_mapping_editor"):
        st.subheader(t("审核描述映射", "Review defect mapping") if mode == "aliases" else t("审核控制项", "Review control link"))
        actor = st.text_input(t("映射审核人", "Mapping reviewer"), key="qg_mapping_actor", max_chars=80)
        if mode == "aliases":
            _alias_editor(scoped, aliases, links, controls, store, actor, types, t)
        else:
            _cp_editor(links, controls, store, actor, stage, types, t)


def _import_evaluation_data(store, trial, t):
    with st.popover(t("导入样本", "Import records"), width="stretch"):
        upload = st.file_uploader(t("检验样本 CSV", "Inspection records CSV"), type="csv", key="qg_import")
        if st.button(t("导入", "Import"), disabled=upload is None, key="qg_import_button"):
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
                st.session_state["qg_saved"] = t(f"已导入 {count:,} 条新记录。", f"Imported {count:,} new records.")
                st.rerun()


def _data_and_evaluation(scoped, pilot_labels, decisions, store, trial, t):
    scoped_ids = {obs.id for obs in scoped}
    pilot_labels = [(obs, label) for obs, label in pilot_labels if obs.id in scoped_ids]
    accepted = [(obs, item) for obs, item in accepted_samples(decisions) if obs.id in scoped_ids]
    labels = [(obs, item["labels"][0]) for obs, item in accepted if len(item["labels"]) == 1]
    export = [{"sample_id": obs.id, **asdict(obs), "labels": "|".join(item["labels"]), "outcome": item["outcome"],
               "reason": item["reason"], "annotator": item.get("annotator", item["actor"]),
               "reviewer": item["actor"] if item["status"] == "approved" else "",
               "reviewed_at": item["at"] if item["status"] == "approved" else "",
               "confirmed_at": item["at"], "taxonomy": item["taxonomy"]}
              for obs, item in accepted]
    heading, importer, download = st.columns([3, 1, 1], vertical_alignment="center")
    heading.subheader(t("模型评估", "Model evaluation"))
    with importer:
        _import_evaluation_data(store, trial, t)
    download.download_button(t("下载标签 CSV", "Download labels CSV"), csv_bytes(export), "quality-labels.csv", "text/csv",
                             disabled=not export, width="stretch")
    saved_by_gate = Counter(obs.stage for obs, decision in accepted if decision["labels"])
    st.markdown(t(f"**我的标注 {sum(saved_by_gate.values()):,} 条**", f"**My labels: {sum(saved_by_gate.values()):,} saved**")
                + f' · PQC {saved_by_gate["PQC"]:,} · FQC {saved_by_gate["FQC"]:,}')

    def domain_of(obs):
        return (obs.community, obs.family, obs.stage)

    observations_by_domain = Counter(domain_of(obs) for obs in scoped)
    labels_by_domain = Counter(domain_of(obs) for obs, _ in labels)
    domains = sorted(observations_by_domain, key=lambda item: (-labels_by_domain[item], -observations_by_domain[item], item))
    minimum_total = EVALUATION_MINIMUMS["train_records"] + EVALUATION_MINIMUMS["test_records"]
    show_pilot = False
    if pilot_labels:
        sources = {"pilot": t("ZX PQC 共享试标", "ZX PQC shared pilot"), "mine": t("我的标注", "My labels")}
        show_pilot = st.radio(t("评估样本", "Evaluation samples"), sources, format_func=sources.get,
                             horizontal=True, key="qg_eval_source") == "pilot"
    with st.container(border=True, key="qg_model_panel"):
        model, selection, count = st.columns([1, 1.2, .65], vertical_alignment="center")
        model.markdown(t("**当前模型**\n\n### 字符 TF-IDF + 最近质心", "**Current model**\n\n### Character TF-IDF + nearest centroid"))
        holdout = None
        if show_pilot:
            domain = ("TU", GLOVES, "PQC")
            rows = pilot_labels
            selection.markdown(t("**评估范围**", "**Evaluation domain**") + "\n\nZX / " + " / ".join(domain))
            count.markdown(t(f"**共享试标样本**\n\n### {len(rows):,}", f"**Shared pilot records**\n\n### {len(rows):,}"))
        else:
            domain = selection.selectbox(t("评估范围", "Evaluation domain"), domains, index=0 if domains else None,
                                         format_func=lambda item: " / ".join(item), key="qg_eval_domain")
            rows = [(obs, label) for obs, label in labels if domain_of(obs) == domain]
            count.markdown(t(f"**有效单标签**\n\n### {len(rows):,} / 至少 {minimum_total}",
                             f"**Single-label records**\n\n### {len(rows):,} / minimum {minimum_total}"))
            factories = sorted({obs.factory for obs, _ in rows})
            if len(factories) > 1:
                holdout = selection.selectbox(t("留出工厂", "Hold out factory"), factories, index=None,
                                              placeholder=t("按描述分组", "Group by wording"), key="qg_eval_factory")
    readiness, metrics = evaluate_with_readiness(rows, holdout)
    with st.container(key="qg_eval_metrics"):
        for column, label, metric in zip(st.columns(3), ["Accuracy", "Recall (Macro)", "F1 Score (Macro)"],
                                         ["accuracy", "macro_recall", "macro_f1"]):
            column.metric(label, f"{metrics[metric]:.1%}" if metrics else "—")

    with st.container(border=True, key="qg_readiness"):
        left, right = st.columns([2, 1], vertical_alignment="center")
        left.subheader(t("评估样本门槛", "Evaluation requirements"))
        status = t("可评估", "Ready") if metrics else t("样本不足", "More labels needed")
        right.markdown(f'<span class="qg-eval-status {"ready" if metrics else "pending"}">{status}</span>', unsafe_allow_html=True)
        headings = [t("训练样本", "Train records"), t("测试样本", "Test records"),
                    t("训练类别", "Train classes"), t("测试描述", "Test descriptions")]
        for column, label, (key, minimum) in zip(st.columns(4), headings, EVALUATION_MINIMUMS.items()):
            column.metric(label, f"{readiness[key]:,} / {minimum}")
            column.progress(min(readiness[key] / minimum, 1))
    if metrics:
        st.subheader(t("按疵点类别", "Performance by defect"))
        types = defect_types(domain[0], store.latest("taxonomy").get(domain[0]))
        per_label = pd.DataFrame([{
            t("标准疵点", "Canonical defect"): _name(row["defect"], types, t), t("测试组", "Test groups"): row["test_groups"],
            "Recall": f'{row["recall"]:.1%}', "F1 Score": f'{row["f1"]:.1%}',
        } for row in metrics["per_label"]])
        st.dataframe(per_label, hide_index=True, width="stretch")
        with st.expander(t("混淆明细", "Confusion details")):
            st.dataframe(metrics["confusion"], hide_index=True, width="stretch")


def render_quality_graph(root, jdy, bme, t):
    st.header(t("质量知识图谱 · 疵点标注", "Quality Knowledge Graph · Defect Labeling"))
    trial = graph_mode() == "trial"
    store = review_store(root)
    controls, error = load_guide()
    if error:
        st.warning(t("ZX CP 来源不可用，报告中的 CP 关联暂停。", "ZX CP source unavailable. Report control links are suspended."))
    connected = [] if trial else dashboard_observations(jdy, bme)
    zx = local_zx(root)
    by_id = {obs.id: obs for obs in [*zx, *connected, *store.observations()]}
    browser_ids = set(by_id) if trial else None
    observations = list(by_id.values())
    if message := st.session_state.pop("qg_saved", ""):
        st.success(message)
    mapping = st.session_state.get("qg_panel") == "mapping"
    stages = STAGES if mapping else LABELING_STAGES
    observations = [obs for obs in observations if obs.stage in stages]
    with st.expander(t("按社区、工厂或检验环节筛选", "Filter by community, factory or inspection gate")):
        filters = st.columns(4)
        community = filters[0].selectbox("Community", list(TAXONOMY), key="qg_community")
        factories = sorted({obs.factory for obs in observations if obs.community == community})
        factory = filters[1].selectbox(t("工厂", "Factory"), factories, index=None, placeholder=t("全部工厂", "All factories"), key="qg_factory")
        stage = filters[2].selectbox(t("检验环节", "Inspection gate"), stages, index=None, placeholder=t("全部环节", "All gates"),
                                     key="qg_mapping_stage" if mapping else "qg_labeling_stage")
        families = sorted({obs.family for obs in observations if obs.community == community and (not factory or obs.factory == factory)})
        family = filters[3].selectbox(t("产品族", "Product family"), families, index=None, placeholder=t("全部产品族", "All families"), key="qg_family")
    scoped = [obs for obs in observations if obs.community == community and (not factory or factory == obs.factory)
              and (not stage or stage == obs.stage) and (not family or family == obs.family)]
    panels = {"label": t("标注工作台", "Labeling workbench"), "mapping": "Defect Mapping", "data": t("数据与评估", "Data and evaluation")}
    panel = st.radio(t("质量知识图谱功能", "Quality graph view"), panels, format_func=panels.get,
                     horizontal=True, label_visibility="collapsed", key="qg_panel")
    if trial and panel != "label":
        restore_browser_backup(store, browser_ids, t)
        render_browser_backup(store)
    if panel == "mapping":
        _render_mapping(scoped, store.latest("alias"), store.latest("link"), controls, store, community, factory, stage, family, t)
    elif panel == "data":
        pilot = [(obs, ZX_PQC_PILOT_LABELS[obs.record]) for obs in zx if obs.stage == "PQC" and obs.record in ZX_PQC_PILOT_LABELS]
        _data_and_evaluation(scoped, pilot, store.latest("label"), store, trial, t)
    else:
        render_labeling_workbench(scoped, store, (community, factory, stage, family), t, browser_ids=browser_ids)


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
