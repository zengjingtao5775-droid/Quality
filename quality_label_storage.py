"""Keep online trial labels in the browser and restore them into the session."""
from datetime import datetime, timezone
from pathlib import Path
import re
import sqlite3

import streamlit as st
import streamlit.components.v1 as components

from quality_graph import Observation, accepted_samples, defect_types, label_decision
from quality_graph_seed import LABELING_STAGES, TAXONOMY, TAXONOMY_VERSION


KEY = "quality_browser_label_backup"
DIST = Path(__file__).resolve().parent / "quality_workbench/label_storage"


def render_browser_backup(store):
    entries = []
    for kind, actor in (("label", "workbench"), ("taxonomy", "defect-dictionary")):
        for item, decision in store.latest(kind).items():
            if decision["actor"] == actor:
                payload = {key: value for key, value in decision.items() if key not in {"actor", "at", "revision"}}
                entries.append(dict(key=f"{kind}:{item}", at=decision["at"], payload=payload))
    backup = components.declare_component("trial_label_backup", path=DIST)
    backup(entries=entries, key=KEY, default=None)


def _parse_entry(entry):
    kind, item = entry["key"].split(":", 1)
    at = datetime.fromisoformat(entry["at"])
    if at.utcoffset() is None or at > datetime.now(timezone.utc):
        raise ValueError("Invalid backup timestamp")
    return kind, item, at.astimezone(timezone.utc).isoformat(), entry["payload"]


def _restore(store, entries, known_ids):
    taxonomies = store.latest("taxonomy")
    validated = []
    labels = []
    for entry in entries:
        try:
            kind, item, at, payload = _parse_entry(entry)
            if kind == "label" and re.fullmatch(r"[a-f0-9]{64}", item):
                labels.append((item, at, payload))
            elif kind == "taxonomy" and item in TAXONOMY:
                types = {code: names for code, names in payload["types"].items()
                         if (code in TAXONOMY[item] or re.fullmatch(rf"{item}-C-[A-F0-9]{{12}}", code))
                         and isinstance(names, list) and len(names) == 3
                         and all(isinstance(name, str) and len(name) <= limit for name, limit in zip(names, (80, 120, 500)))
                         and names[0].strip() and names[1].strip()}
                if at > taxonomies.get(item, {}).get("at", ""):
                    validated.append((kind, item, "defect-dictionary", at, {"types": types}))
                    taxonomies[item] = {"types": types, "at": at}
        except (AttributeError, KeyError, TypeError, ValueError):
            continue

    catalog = {community: defect_types(community, taxonomies.get(community)) for community in TAXONOMY}
    for item, at, payload in labels:
        try:
            if payload["status"] == "withdrawn":
                validated.append(("label", item, "workbench", at, {"status": "withdrawn"}))
            elif payload["status"] == "confirmed" and payload["taxonomy"] == TAXONOMY_VERSION:
                observation = payload["observation"]
                if not all(isinstance(value, str) for value in observation.values()):
                    continue
                obs = Observation(**observation)
                if obs.id == item and obs.stage in LABELING_STAGES:
                    result = label_decision(obs, payload["labels"], payload["outcome"], payload["reason"],
                                            "confirmed", types=catalog[obs.community])
                    validated.append(("label", item, "workbench", at, result))
        except (AttributeError, KeyError, TypeError, ValueError):
            continue
    store.restore_browser_decisions(validated)
    return store.import_observations(obs for obs, _ in accepted_samples(store.latest("label")) if obs.id not in known_ids)


def restore_browser_backup(store, known_ids, t):
    event = st.session_state.get(KEY)
    if (isinstance(event, dict) and isinstance(event.get("nonce"), str)
            and event["nonce"] != st.session_state.get("_qg_backup_event")):
        st.session_state["_qg_backup_event"] = event["nonce"]
        st.session_state["_qg_backup_available"] = not event.get("error")
        if isinstance(event.get("entries"), list) and event["entries"]:
            try:
                added = _restore(store, event["entries"][:25_000], known_ids)
            except sqlite3.Error:
                st.session_state["_qg_backup_available"] = False
            else:
                if added:
                    st.rerun()
    if st.session_state.get("_qg_backup_available") is False:
        st.warning(t("浏览器存储不可用。关闭页面前可在数据与评估中下载标签 CSV。",
                     "Browser storage is unavailable. Download your label CSV before closing the page."))
