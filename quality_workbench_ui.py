"""Server-owned annotation queue and progress."""
from pathlib import Path
import sqlite3
from uuid import uuid4

import streamlit as st
import streamlit.components.v1 as components

from quality_graph import TextBaseline, accepted_samples, candidate_aliases, clean, defect_types, key_for, label_decision, normalized
from quality_graph_seed import LABELING_STAGES
from quality_label_storage import render_browser_backup, restore_browser_backup


QUALITY_GRAPH_RELEASE = 9
DIST = Path(__file__).resolve().parent / "quality_workbench/dist"
WIDGET_KEY = "quality_labeling_react"
NATIVE_EVENT_KEY = "_qg_native_labeling_event"
ANSWERED = {"confirmed", "approved"}
ACTOR = "workbench"


def progress_by_gate(observations, decisions):
    stages = {stage: dict(stage=stage, total=0, remaining=0, labeled=0, uncertain=0, trainable=0) for stage in LABELING_STAGES}
    for obs in observations:
        if obs.stage not in stages:
            continue
        row = stages[obs.stage]
        decision = decisions.get(obs.id, {})
        row["total"] += 1
        if decision.get("status") not in ANSWERED:
            row["remaining"] += 1
        elif labels := decision.get("labels"):
            row["labeled"] += 1
            row["trainable"] += len(labels) == 1
        else:
            row["uncertain"] += 1
    return list(stages.values())


def work_queue(observations, decisions, query):
    phrase = normalized(query)
    return [obs for obs in observations if obs.stage in LABELING_STAGES
            and decisions.get(obs.id, {}).get("status") not in ANSWERED
            and (not phrase or phrase in normalized(f"{obs.description} {obs.record} {obs.process} {obs.raw_type} {obs.cc} {obs.model}"))]


def _sample(obs, decision, decisions, types, t):
    if obs is None:
        return None
    _, _, suggestion, _ = candidate_aliases([obs])[0]
    if not suggestion:
        train = [(item, result["labels"][0]) for item, result in accepted_samples(decisions)
                 if item.stage in LABELING_STAGES and item.domain == obs.domain and len(result["labels"]) == 1]
        if len(train) >= 10 and len({label for _, label in train}) >= 2:
            suggestion, _ = TextBaseline(train).predict(obs.description)
    factory = t("中兴（ZX）", "Zhongxing (ZX)") if obs.factory == "ZX" else obs.factory
    return {"id": obs.id, "description": obs.description, "rawType": obs.raw_type, "factory": factory,
            "family": obs.family, "stage": obs.stage, "process": obs.process, "date": obs.date,
            "cc": obs.cc.removesuffix(".0"), "model": obs.model,
            "source": obs.source, "record": obs.record, "revision": decision.get("revision", 0),
            "suggestion": suggestion,
            "options": [{"id": code, "name": t(zh, en)} for code, (zh, en, _) in types.items()]}


def _apply(event, scoped, decisions, queue, sample, decision, settings, store, t, types=None):
    action = event.get("action")
    if action == "search":
        settings.update(query=clean(event.get("query"))[:150], cursor=0)
        settings.pop("undo", None)
        return ""
    stale = t("记录已更新，请核对当前样本。", "The record changed. Check the current sample.")
    if action == "undo":
        item, revision = settings.get("undo", (None, None))
        previous = decisions.get(item, {})
        if previous.get("status") != "confirmed" or previous.get("revision") != revision:
            settings.pop("undo", None)
            raise ValueError(stale)
        store.write("label", item, revision, ACTOR, {"status": "withdrawn"})
        settings.pop("undo", None)
        restored = work_queue(scoped, {key: row for key, row in decisions.items() if key != item}, settings["query"])
        settings["cursor"] = next((i for i, obs in enumerate(restored) if obs.id == item), 0)
        return t("已撤销，可以重新选择。", "Answer undone. Choose again.")
    revision = decision.get("revision", 0)
    if sample is None or event.get("id") != sample.id or event.get("revision") != revision:
        raise ValueError(stale)
    if action == "next":
        settings["cursor"] = (settings["cursor"] + 1) % len(queue)
        return ""
    if action != "answer":
        raise ValueError("Invalid annotation action")
    choice = event.get("choice")
    if types is None:
        types = defect_types(sample.community, store.latest("taxonomy").get(sample.community))
    if not isinstance(choice, str) or (choice != "unsure" and choice not in types):
        raise ValueError(t("请选择有效的标准疵点。", "Choose a valid canonical defect."))
    unsure = choice == "unsure"
    payload = label_decision(sample, [] if unsure else [choice], "insufficient" if unsure else "labeled",
                             "Annotator selected unable to determine" if unsure else "", "confirmed", types=types)
    store.write("label", sample.id, revision, ACTOR, payload)
    settings["undo"] = (sample.id, revision + 1)
    return t("已记录：暂无法判断。", "Recorded as unable to determine.") if unsure else t("标签已保存。", "Label saved.")


def _queue_state(scoped, decisions, settings):
    queue = work_queue(scoped, decisions, settings["query"])
    if queue:
        settings["cursor"] %= len(queue)
    sample = queue[settings["cursor"]] if queue else None
    return queue, sample, decisions.get(sample.id, {}) if sample else {}


def _queue_native_event(action, sample=None, choice=None, input_key=None):
    event = {"action": action, "nonce": uuid4().hex}
    if sample:
        event.update(id=sample["id"], revision=sample["revision"])
    if action == "answer":
        event["choice"] = choice or st.session_state.get(input_key)
        if not event["choice"]:
            return
    if action == "search":
        event["query"] = st.session_state.get(input_key, "")
    st.session_state[NATIVE_EVENT_KEY] = event


def _native_workbench(view, t):
    record, progress = st.columns([1.75, 1], gap="medium")
    with progress, st.container(border=True):
        st.subheader(t("标注进度", "Labeling progress"))
        total = sum(gate["total"] for gate in view["gates"])
        done = sum(gate["labeled"] + gate["uncertain"] for gate in view["gates"])
        st.metric(t("已处理", "Answered"), f"{done:,} / {total:,}")
        st.progress(done / total if total else 0.0)
        for gate in view["gates"]:
            completed = gate["labeled"] + gate["uncertain"]
            st.text(f'{gate["stage"]}  {completed:,} / {gate["total"]:,}')

    with record, st.container(border=True):
        st.subheader(t("检验记录", "Inspection record"))
        sample = view["sample"]
        if sample:
            st.text(f'{sample["stage"]} · {sample["factory"]} · {sample["family"]}')
            fields = st.columns(3)
            for column, name, key in zip(fields, (t("检验日期", "Inspection date"), "CC", "Model"), ("date", "cc", "model")):
                column.text(f'{name}\n{sample[key] or "—"}')
            st.markdown(t("**原始 Defect Description**", "**Original Defect Description**"))
            st.text(sample["description"])
            st.markdown(t("**选择标准 Defect Type**", "**Choose a Standard Defect Type**"))
            types = {option["id"]: option["name"] for option in sample["options"]}
            suggestion = sample["suggestion"]
            sample_key = f'{sample["id"]}_{sample["revision"]}'
            if suggestion in types:
                st.button(f"A · {types[suggestion]} · {suggestion}", key=f"qg_native_a_{sample_key}", type="primary",
                          on_click=_queue_native_event, args=("answer", sample, suggestion))
            selector_key = f"qg_native_choice_{sample_key}"
            st.selectbox(t("B · 选其他标准类型", "B · Choose another standard type"),
                         [code for code in types if code != suggestion], index=None, key=selector_key,
                         format_func=lambda code: f"{types[code]} · {code}",
                         on_change=_queue_native_event, args=("answer", sample, None, selector_key))
            unsure, skip = st.columns(2)
            unsure.button(t("暂无法判断", "Unable to determine"), key=f"qg_native_unsure_{sample_key}",
                          on_click=_queue_native_event, args=("answer", sample, "unsure"))
            skip.button(t("跳过", "Skip"), key=f"qg_native_skip_{sample_key}",
                        on_click=_queue_native_event, args=("next", sample))
            with st.expander(t("查看原始来源", "View source record")):
                st.text(" · ".join(filter(None, (sample["source"], sample["record"], sample["process"], sample["rawType"]))))
        else:
            st.info(t("当前筛选范围没有待作答的记录。", "No unanswered records match the current filters."))
        if view["error"]:
            st.error(view["error"])
        elif view["message"]:
            st.success(view["message"])
        if view["canUndo"]:
            st.button(t("撤销上一条", "Undo last answer"), key="qg_native_undo",
                      on_click=_queue_native_event, args=("undo",))
        with st.expander(t("搜索记录", "Find a record")):
            search_key = f'qg_native_search_{view["scopeKey"]}'
            with st.form(f"{search_key}_form"):
                st.text_input(t("疵点、CC、Model 或记录号", "Defect, CC, Model or record ID"),
                              value=view["query"], max_chars=150, key=search_key)
                st.form_submit_button(t("查找", "Find"), on_click=_queue_native_event, args=("search", None, None, search_key))


@st.fragment
def render_labeling_workbench(scoped, store, scope, t, browser_ids=None):
    if browser_ids is not None:
        restore_browser_backup(store, browser_ids, t)
    built = (DIST / "index.html").is_file()
    native = st.toggle(t("兼容模式", "Compatibility mode"), value=not built, disabled=not built,
                       help=t("自定义组件加载异常时，可以用兼容模式继续标注。",
                              "Use compatibility mode to keep labeling if the custom workbench fails to load."),
                       key="qg_native_labeling") or not built
    settings = st.session_state.setdefault("_qg_answer_queue", dict(query="", cursor=0))
    scope_key = key_for(*scope)
    if settings.get("scope") != scope_key:
        settings.update(scope=scope_key, query="", cursor=0, message="", error="")
        settings.pop("undo", None)
    decisions = store.latest("label")
    community = scope[0]
    types = defect_types(community, store.latest("taxonomy").get(community))
    queue, sample, decision = _queue_state(scoped, decisions, settings)
    event = st.session_state.pop(NATIVE_EVENT_KEY, None) if native else st.session_state.get(WIDGET_KEY)
    if isinstance(event, dict) and event.get("nonce") and event["nonce"] != settings.get("event"):
        settings.update(event=event["nonce"], message="", error="")
        try:
            settings["message"] = _apply(event, scoped, decisions, queue, sample, decision, settings, store, t, types=types)
        except (ValueError, TypeError, sqlite3.Error) as error:
            settings["error"] = str(error)
        decisions = store.latest("label")
        queue, sample, decision = _queue_state(scoped, decisions, settings)
    if browser_ids is not None:
        render_browser_backup(store)
    view = dict(language=t("zh", "en"), gates=progress_by_gate(scoped, decisions), query=settings["query"],
                scope=[value for value in scope if value], scopeKey=scope_key, queueCount=len(queue),
                queuePosition=settings["cursor"] + 1 if sample else 0, canUndo="undo" in settings,
                sample=_sample(sample, decision, decisions, types, t), message=settings.get("message", ""),
                error=settings.get("error", ""), acknowledgedEvent=settings.get("event"))
    if native:
        _native_workbench(view, t)
    else:
        workbench = components.declare_component("quality_defect_labeler_v8", path=DIST)
        workbench(**view, key=WIDGET_KEY, default=None)
