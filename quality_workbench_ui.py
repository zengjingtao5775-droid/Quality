"""Server-owned single-click annotation queue and progress."""
from pathlib import Path
import sqlite3

import streamlit as st
import streamlit.components.v1 as components

from quality_graph import TextBaseline, accepted_samples, candidate_aliases, clean, key_for, label_decision, normalized
from quality_graph_seed import STAGES, TAXONOMY


QUALITY_GRAPH_RELEASE = 2
DIST = Path(__file__).resolve().parent / "quality_workbench/dist"
_workbench = components.declare_component("quality_single_choice_workbench", path=str(DIST))
ANSWERED = {"confirmed", "approved"}
ACTOR = "workbench"


def progress_by_gate(observations, decisions):
    stages = {stage: dict(stage=stage, total=0, remaining=0, labeled=0, uncertain=0, trainable=0) for stage in STAGES}
    for obs in observations:
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
    return [obs for obs in observations if decisions.get(obs.id, {}).get("status") not in ANSWERED
            and (not phrase or phrase in normalized(f"{obs.description} {obs.record} {obs.process} {obs.raw_type}"))]


def _sample(obs, decision, decisions, t):
    if obs is None:
        return None
    codes = TAXONOMY[obs.community]
    _, _, suggestion, _ = candidate_aliases([obs])[0]
    source = "dictionary"
    if not suggestion:
        train = [(item, result["labels"][0]) for item, result in accepted_samples(decisions)
                 if item.domain == obs.domain and len(result["labels"]) == 1]
        if len(train) >= 10 and len({label for _, label in train}) >= 2:
            suggestion, _ = TextBaseline(train).predict(obs.description)
            source = "model"
    return {"id": obs.id, "description": obs.description, "rawType": obs.raw_type, "factory": obs.factory,
            "family": obs.family, "stage": obs.stage, "process": obs.process, "date": obs.date,
            "source": obs.source, "record": obs.record, "revision": decision.get("revision", 0),
            "suggestion": suggestion, "suggestionSource": source,
            "options": [{"id": code, "name": t(zh, en)} for code, (zh, en, _) in codes.items()]}


def _apply(event, scoped, decisions, queue, sample, decision, settings, store, t):
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
    if not isinstance(choice, str) or (choice != "unsure" and choice not in TAXONOMY[sample.community]):
        raise ValueError(t("请选择有效的标准疵点。", "Choose a valid canonical defect."))
    unsure = choice == "unsure"
    payload = label_decision(sample, [] if unsure else [choice], "insufficient" if unsure else "labeled",
                             "Annotator selected unable to determine" if unsure else "", "confirmed")
    store.write("label", sample.id, revision, ACTOR, payload)
    settings["undo"] = (sample.id, revision + 1)
    return t("已记录：暂无法判断。", "Recorded as unable to determine.") if unsure else t("标签已保存。", "Label saved.")


def render_labeling_workbench(scoped, decisions, store, scope, t):
    if not (DIST / "index.html").is_file():
        st.error(t("标注工作台前端尚未构建。", "The labeling workbench frontend has not been built."))
        return
    settings = st.session_state.setdefault("_qg_answer_queue", dict(query="", cursor=0))
    scope_key = key_for(*scope)
    if settings.get("scope") != scope_key:
        settings.update(scope=scope_key, query="", cursor=0)
        settings.pop("undo", None)
    queue = work_queue(scoped, decisions, settings["query"])
    if queue:
        settings["cursor"] %= len(queue)
    sample = queue[settings["cursor"]] if queue else None
    decision = decisions.get(sample.id, {}) if sample else {}
    event = _workbench(language=t("zh", "en"), gates=progress_by_gate(scoped, decisions), query=settings["query"],
                       scope=[value for value in scope if value], scopeKey=scope_key, queueCount=len(queue),
                       queuePosition=settings["cursor"] + 1 if sample else 0, canUndo="undo" in settings,
                       sample=_sample(sample, decision, decisions, t), message=settings.get("message", ""),
                       error=settings.get("error", ""), key="quality_labeling_react", default=None)
    if isinstance(event, dict) and event.get("nonce") and event["nonce"] != settings.get("event"):
        settings.update(event=event["nonce"], message="", error="")
        try:
            settings["message"] = _apply(event, scoped, decisions, queue, sample, decision, settings, store, t)
        except (ValueError, TypeError, sqlite3.Error) as error:
            settings["error"] = str(error)
        st.rerun()
