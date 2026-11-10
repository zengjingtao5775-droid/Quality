"""Server-owned queue and progress for the React labeling workbench."""
from pathlib import Path
import sqlite3

import streamlit as st
import streamlit.components.v1 as components

from quality_graph import TextBaseline, approved_samples, candidate_aliases, clean, key_for, label_decision, normalized
from quality_graph_seed import STAGES, TAXONOMY


DIST = Path(__file__).resolve().parent / "quality_workbench/dist"
_workbench = components.declare_component("quality_labeling_workbench", path=str(DIST))


def progress_by_gate(observations, decisions):
    stages = {stage: dict(stage=stage, total=0, unreviewed=0, submitted=0, returned=0, approved=0, trainable=0) for stage in STAGES}
    for obs in observations:
        row = stages[obs.stage]
        decision = decisions.get(obs.id, {})
        status = decision.get("status", "unreviewed")
        row["total"] += 1
        row[status] += 1
        if status == "approved" and len(decision["labels"]) == 1:
            row["trainable"] += 1
    return list(stages.values())


def work_queue(observations, decisions, mode, query, actor):
    phrase = normalized(query)
    queue = []
    for obs in observations:
        decision = decisions.get(obs.id, {})
        status = decision.get("status", "unreviewed")
        eligible = status == "submitted" if mode == "review" else status in {"unreviewed", "returned"}
        if not eligible or (mode == "review" and normalized(actor) and normalized(decision.get("actor")) == normalized(actor)):
            continue
        if phrase and phrase not in normalized(f"{obs.description} {obs.record} {obs.process} {obs.raw_type}"):
            continue
        queue.append(obs)
    if mode == "label":
        queue.sort(key=lambda obs: decisions.get(obs.id, {}).get("status") != "returned")
    return queue


def _sample(obs, decision, decisions, t):
    if obs is None:
        return None
    codes = TAXONOMY[obs.community]
    _, _, suggestion, _ = candidate_aliases([obs])[0]
    source = "dictionary"
    if not suggestion and decision.get("status", "unreviewed") == "unreviewed":
        train = [(item, result["labels"][0]) for item, result in approved_samples(decisions)
                 if item.domain == obs.domain and len(result["labels"]) == 1]
        if len(train) >= 10 and len({label for _, label in train}) >= 2:
            suggestion, _ = TextBaseline(train).predict(obs.description)
            source = "model"
    return {"id": obs.id, "description": obs.description, "rawType": obs.raw_type, "factory": obs.factory,
            "family": obs.family, "stage": obs.stage, "process": obs.process, "date": obs.date,
            "source": obs.source, "record": obs.record, "status": decision.get("status", "unreviewed"),
            "labels": decision.get("labels", []), "actor": decision.get("actor", ""), "revision": decision.get("revision", 0),
            "outcome": decision.get("outcome", "labeled"), "reason": decision.get("reason", ""),
            "suggestion": suggestion, "suggestionSource": source,
            "options": [{"id": code, "name": t(zh, en), "definition": definition if t("zh", "en") == "zh" else ""}
                        for code, (zh, en, definition) in codes.items()]}


def _apply(event, queue, sample, decision, settings, store, t):
    action = event.get("action")
    actor = clean(event.get("actor"))[:80]
    settings["actor"] = actor
    if action == "queue":
        mode = event.get("mode")
        if mode not in {"label", "review"}:
            raise ValueError("Invalid queue")
        settings.update(mode=mode, query=clean(event.get("query"))[:150], cursor=0)
        return ""
    if sample is None or event.get("id") != sample.id or event.get("revision") != decision.get("revision", 0):
        raise ValueError(t("记录已更新，请核对当前样本。", "The record changed. Check the current sample."))
    if action == "next":
        settings["cursor"] = (settings["cursor"] + 1) % len(queue)
        return ""
    expected = {"label": {"submit": "submitted"}, "review": {"approve": "approved", "return": "returned"}}
    status = expected[settings["mode"]].get(action)
    labels, outcome, reason = event.get("labels"), event.get("outcome"), event.get("reason", "")
    if not status or not isinstance(labels, list) or not all(isinstance(code, str) for code in labels) or not isinstance(reason, str):
        raise ValueError("Invalid decision")
    payload = label_decision(sample, labels, outcome, reason[:1000], status)
    store.write("label", sample.id, decision.get("revision", 0), actor, payload)
    return {"submitted": t("已提交，等待第二人复核。", "Submitted for second review."),
            "approved": t("复核已保存，进度已更新。", "Review saved and progress updated."),
            "returned": t("已退回标注队列。", "Returned to the labeling queue.")}[status]


def render_labeling_workbench(scoped, decisions, store, scope, t):
    if not (DIST / "index.html").is_file():
        st.error(t("标注工作台前端尚未构建。", "The labeling workbench frontend has not been built."))
        return
    settings = st.session_state.setdefault("_qg_queue", dict(mode="label", query="", cursor=0, actor=""))
    scope_key = key_for(*scope)
    if settings.get("scope") != scope_key:
        settings.update(scope=scope_key, query="", cursor=0)
    queue = work_queue(scoped, decisions, settings["mode"], settings["query"], settings["actor"])
    if queue:
        settings["cursor"] %= len(queue)
    sample = queue[settings["cursor"]] if queue else None
    decision = decisions.get(sample.id, {}) if sample else {}
    event = _workbench(language=t("zh", "en"), gates=progress_by_gate(scoped, decisions),
                       mode=settings["mode"], query=settings["query"], actor=settings["actor"],
                       scope=[value for value in scope if value], queueCount=len(queue),
                       queuePosition=settings["cursor"] + 1 if sample else 0,
                       sample=_sample(sample, decision, decisions, t), message=settings.get("message", ""),
                       error=settings.get("error", ""), key="quality_labeling_react", default=None)
    if isinstance(event, dict) and event.get("nonce") and event["nonce"] != settings.get("event"):
        settings.update(event=event["nonce"], message="", error="")
        try:
            settings["message"] = _apply(event, queue, sample, decision, settings, store, t)
        except (ValueError, TypeError, sqlite3.Error) as error:
            settings["error"] = str(error)
        st.rerun()
