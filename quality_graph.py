"""Local defect observations, review history, control edges and a text baseline."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import re
import sqlite3
import unicodedata
from collections import Counter, defaultdict
from contextlib import closing
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from openpyxl import load_workbook

from quality_graph_seed import (
    GLOVES, GUIDE_DIGEST, GUIDE_FILENAME, GUIDE_SHEET, STAGES, TAXONOMY,
    TAXONOMY_VERSION, ZX_ALIASES, ZX_LINKS,
)

QUALITY_GRAPH_RELEASE = 9


def clean(value):
    text = str(value).strip() if value is not None else ""
    return "" if text.casefold() in {"nan", "nat", "<na>", "none", "n/a", "-"} else text


def normalized(value):
    return " ".join(unicodedata.normalize("NFKC", clean(value)).casefold().split())


def extract_decathlon_model(value: object) -> str:
    match = re.match(r"^(\d{7})(?!\d)", clean(value))
    return match.group(1) if match else ""


def key_for(*parts):
    return hashlib.sha256(json.dumps(parts, ensure_ascii=False).encode()).hexdigest()


def bundled_guide():
    return Path(__file__).resolve().parent / "assets/quality-graph" / GUIDE_FILENAME


def graph_mode():
    if os.environ.get("QUALITY_GRAPH_ENABLED") == "1":
        return "local"
    return "trial" if bundled_guide().is_file() else ""


def guide_path():
    local_path = Path.home() / "Downloads" / GUIDE_FILENAME
    default = bundled_guide() if bundled_guide().is_file() else local_path
    return Path(os.environ.get("QUALITY_GRAPH_CP", str(default)))


def graph_db(root):
    return Path(os.environ.get("QUALITY_GRAPH_DB", str(root / ".runtime/quality-graph/reviews.sqlite3")))


@dataclass(frozen=True)
class Observation:
    community: str
    factory: str
    family: str
    stage: str
    description: str
    process: str = ""
    source: str = ""
    record: str = ""
    batch: str = ""
    date: str = ""
    cc: str = ""
    raw_type: str = ""
    model: str = ""

    def __post_init__(self):
        if self.community not in TAXONOMY or self.stage not in STAGES:
            raise ValueError("Invalid community or inspection stage")
        if not all((self.factory, self.family, self.description, self.source, self.record)):
            raise ValueError("Factory, product family, description, source and record are required")

    @property
    def id(self):
        # Model is display metadata. Existing decisions retain their record IDs.
        return key_for(*(value for name, value in asdict(self).items() if name != "model"))

    @property
    def alias_key(self):
        return key_for(TAXONOMY_VERSION, self.community, normalized(self.factory), normalized(self.family),
                       self.stage, normalized(self.raw_type), normalized(self.description))

    @property
    def domain(self):
        return (self.community, normalized(self.family), self.stage)


def read_controls(path):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != GUIDE_DIGEST:
        raise ValueError("The workbook differs from the version reviewed for this pilot")
    controls = {}
    workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    try:
        sheet = workbook[GUIDE_SHEET]
        section = step = ""
        for number, row in enumerate(sheet.iter_rows(min_row=6, max_col=12, values_only=True), 6):
            name, what, how, target, tolerance, nc, kind, severity, frequency, sampling, reaction = map(clean, row[1:])
            if name and not any((what, how, target, kind)):
                section, step = name, ""
                continue
            if name:
                step = name
            if what or how or target:
                controls[number] = dict(row=number, source=GUIDE_FILENAME, sheet=GUIDE_SHEET.strip(), version="2.0",
                    reference=f"'{GUIDE_SHEET}'!B{number}:L{number}", section=section, step=step,
                    what=what, how=how, target=target, tolerance=tolerance, nonconformity=nc,
                    control_type=kind, severity=severity, frequency=frequency, sampling=sampling, reaction=reaction)
    finally:
        workbook.close()
    return controls


def read_zx_observations(directory):
    result = []
    iqc = directory / "2026年原辅料不合格记录.xlsx"
    inspection = directory / "05.7-06.6检验数据.xlsx"
    for path in (iqc, inspection):
        if not path.is_file():
            continue
        workbook = load_workbook(path, read_only=True, data_only=True)
        try:
            if path == iqc:
                for sheet_name in ("辅料不良明细记录", "主料不良明细记录"):
                    for index, row in enumerate(workbook[sheet_name].iter_rows(min_row=3, max_col=10, values_only=True), 3):
                        batch, _, _, material, _, _, _, issue, _, date = map(clean, row)
                        if issue:
                            result.append(Observation("TU", "ZX", GLOVES, "IQC", issue, material,
                                f"{path.name} / {sheet_name}", f"H{index}", f"{sheet_name}:{batch}" if batch else "", date[:10]))
            else:
                sheet = workbook.worksheets[0]
                for index, row in enumerate(sheet.iter_rows(min_row=2, max_col=19, values_only=True), 2):
                    record, kind, _, _, _, batch, work_order, _, _, cc, color, _, _, _, qty, issue, process, _, date = row
                    stage = {"中间检验": "PQC", "成品检验": "FQC"}.get(clean(kind))
                    if stage and isinstance(qty, (int, float)) and qty > 0 and clean(issue):
                        result.append(Observation("TU", "ZX", GLOVES, stage, clean(issue), clean(process),
                            f"{path.name} / {sheet.title}", clean(record) or f"P{index}", clean(batch) or clean(work_order),
                            clean(date)[:10], clean(cc), model=extract_decathlon_model(color)))
        finally:
            workbook.close()
    return result


def read_csv_observations(data):
    reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig")))
    fields = Observation.__dataclass_fields__
    required = {"community", "factory", "family", "stage", "description", "source", "record"}
    if not required.issubset(reader.fieldnames or []):
        raise ValueError("Required CSV fields: " + ", ".join(sorted(required)))
    records = []
    for number, row in enumerate(reader, 2):
        try:
            records.append(Observation(**{name: clean(row.get(name)) for name in fields}))
        except ValueError as error:
            raise ValueError(f"CSV row {number}: {error}") from error
    return records


def csv_bytes(rows, fields=None):
    """Excel-compatible UTF-8 and literal text for spreadsheet formula prefixes."""
    if not rows and fields is None:
        return b""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields or list(rows[0]))
    writer.writeheader()
    for row in rows:
        writer.writerow({k: "'" + v if isinstance(v, str) and v.lstrip().startswith(("=", "+", "-", "@")) else v
                         for k, v in row.items()})
    return output.getvalue().encode("utf-8-sig")


class ReviewStore:
    """Append-only decisions, with optimistic version checks across sessions."""

    def __init__(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with closing(self.connect()) as db, db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS decisions (
                    kind TEXT, item TEXT, revision INTEGER, actor TEXT, at TEXT, payload TEXT,
                    PRIMARY KEY (kind, item, revision)
                );
                CREATE TABLE IF NOT EXISTS observations (id TEXT PRIMARY KEY, payload TEXT);
            """)

    def connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def latest(self, kind):
        with closing(self.connect()) as db:
            return {item: {**json.loads(payload), "actor": actor, "at": at, "revision": revision}
                    for item, revision, actor, at, payload in db.execute("""
                        SELECT d.item, d.revision, d.actor, d.at, d.payload FROM decisions d
                        JOIN (SELECT item, MAX(revision) revision FROM decisions WHERE kind=? GROUP BY item) l
                        ON d.item=l.item AND d.revision=l.revision WHERE d.kind=?
                    """, (kind, kind))}

    def write(self, kind, item, expected, actor, payload):
        actor = clean(actor)
        if not actor:
            raise ValueError("Reviewer name is required")
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute("SELECT revision, actor, payload FROM decisions WHERE kind=? AND item=? ORDER BY revision DESC LIMIT 1",
                                  (kind, item)).fetchone()
            if (previous[0] if previous else 0) != expected:
                raise ValueError("A decision has changed. Refresh and review the latest version.")
            if kind == "label" and payload["status"] in {"approved", "returned"}:
                if not previous or json.loads(previous[2])["status"] != "submitted" or normalized(previous[1]) == normalized(actor):
                    raise ValueError("A second reviewer must check the submitted annotation")
                payload = {**payload, "annotator": previous[1]}
            db.execute("INSERT INTO decisions VALUES (?, ?, ?, ?, ?, ?)",
                       (kind, item, expected + 1, actor, datetime.now(timezone.utc).isoformat(), json.dumps(payload, ensure_ascii=False)))

    def import_observations(self, observations):
        with closing(self.connect()) as db, db:
            count = db.total_changes
            db.executemany("INSERT OR IGNORE INTO observations VALUES (?, ?)",
                           ((row.id, json.dumps(asdict(row), ensure_ascii=False)) for row in observations))
            return db.total_changes - count

    def restore_browser_decisions(self, entries):
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            for kind, item, actor, at, payload in entries:
                previous = db.execute("SELECT revision, at FROM decisions WHERE kind=? AND item=? ORDER BY revision DESC LIMIT 1",
                                      (kind, item)).fetchone()
                if previous and previous[1] >= at:
                    continue
                revision = previous[0] + 1 if previous else 1
                db.execute("INSERT INTO decisions VALUES (?, ?, ?, ?, ?, ?)",
                           (kind, item, revision, actor, at, json.dumps(payload, ensure_ascii=False)))

    def observations(self):
        with closing(self.connect()) as db:
            return [Observation(**json.loads(payload)) for (payload,) in db.execute("SELECT payload FROM observations")]


def defect_types(community, saved=None):
    return {**TAXONOMY[community], **(saved or {}).get("types", {})}


def save_defect_type(store, community, saved, code, zh, en, definition):
    types = defect_types(community, saved)
    zh, en, definition = map(clean, (zh, en, definition))
    if not zh or not en:
        raise ValueError("Enter both the Chinese and English defect names.")
    if code and code not in types:
        raise ValueError("Select a valid defect type.")
    if any(item != code and (normalized(names[0]) == normalized(zh) or normalized(names[1]) == normalized(en))
           for item, names in types.items()):
        raise ValueError("A defect with this name already exists in this community.")
    code = code or f"{community}-C-{uuid4().hex[:12].upper()}"
    changes = {**saved.get("types", {}), code: (zh, en, definition)}
    store.write("taxonomy", community, saved.get("revision", 0), "defect-dictionary", {"types": changes})
    return code


def label_decision(observation, labels, outcome, reason, status, types=None):
    if status not in {"submitted", "approved", "returned", "confirmed"}:
        raise ValueError("Invalid review status")
    if outcome not in {"labeled", "insufficient", "out_of_taxonomy", "split_needed"}:
        raise ValueError("Invalid annotation outcome")
    valid = TAXONOMY[observation.community] if types is None else types
    if outcome == "labeled" and (not labels or not set(labels) <= valid.keys()):
        raise ValueError("Select valid labels for the observation's community")
    if (outcome != "labeled" or status == "returned") and not clean(reason):
        raise ValueError("Add a reason for unresolved or returned observations")
    return dict(observation=asdict(observation), labels=list(dict.fromkeys(labels)) if outcome == "labeled" else [],
                outcome=outcome, reason=clean(reason), status=status, taxonomy=TAXONOMY_VERSION)


def accepted_samples(decisions):
    return [(Observation(**item["observation"]), item) for item in decisions.values()
            if item["status"] in {"approved", "confirmed"} and item["taxonomy"] == TAXONOMY_VERSION]


def candidate_aliases(observations):
    candidates = {}
    counts = Counter()
    for obs in observations:
        counts[obs.alias_key] += 1
        draft = ZX_ALIASES.get(obs.stage, {}).get(obs.description, "") if (obs.community, obs.factory, obs.family) == ("TU", "ZX", GLOVES) else ""
        candidates.setdefault(obs.alias_key, (obs, draft))
    return [(key, obs, draft, counts[key]) for key, (obs, draft) in candidates.items()]


def link_key(stage, defect, row):
    return key_for(TAXONOMY_VERSION, GUIDE_DIGEST, stage, defect, row)


def link_candidates(saved_links=None):
    candidates = {link_key(stage, defect, row): (stage, defect, row, relation, note)
                  for stage, defect, row, relation, note in ZX_LINKS}
    for key, saved in (saved_links or {}).items():
        if "edge" in saved:
            stage, defect, row, relation, note = saved["edge"]
            if key == link_key(stage, defect, row):
                candidates[key] = (stage, defect, row, relation, note)
    return [(key, *edge) for key, edge in candidates.items()]


def report_control_links(observation, aliases, links, controls):
    """Require a reviewed alias and a reviewed edge with explicit CC applicability."""
    if (observation.community, observation.factory, observation.family) != ("TU", "ZX", GLOVES):
        return "out_of_scope", []
    alias = aliases.get(observation.alias_key, {})
    if alias.get("status") != "approved":
        return "alias_pending", []
    defect = alias["defect"]
    result = []
    for key, stage, canonical, row, relation, note in link_candidates(links):
        edge = links.get(key, {})
        if (stage == observation.stage and canonical == defect and row in controls and edge.get("status") == "approved"
                and observation.cc and observation.cc in edge.get("ccs", [])):
            result.append({**controls[row], "defect": defect, "relation": relation, "action": note,
                           "review_evidence": edge["reason"], "reviewed_at": edge["at"]})
    return ("linked" if result else "control_pending"), result


def report_control_candidates(observation, aliases, links, controls):
    status, matches = report_control_links(observation, aliases, links, controls)
    if matches or status == "out_of_scope":
        return status, matches
    alias = aliases.get(observation.alias_key, {})
    if alias.get("status") == "unresolved":
        return status, []
    defect = alias.get("defect") or ZX_ALIASES.get(observation.stage, {}).get(observation.description)
    candidates = [{**controls[row], "defect": canonical, "relation": relation, "action": note}
                  for key, stage, canonical, row, relation, note in link_candidates(links)
                  if stage == observation.stage and canonical == defect and row in controls
                  and links.get(key, {}).get("status") != "unresolved"]
    return ("candidate" if candidates else status), candidates


def _grams(text):
    text = "^" + normalized(text) + "$"
    return Counter(text[i:i+n] for n in (1, 2, 3) for i in range(len(text) - n + 1))


def _unit(vector):
    norm = math.sqrt(sum(weight**2 for weight in vector.values()))
    return {term: weight / norm for term, weight in vector.items()} if norm else {}


class TextBaseline:
    """Supervised nearest-centroid classifier using character TF-IDF."""

    def __init__(self, rows):
        examples = sorted({(normalized(obs.description), label) for obs, label in rows})
        features = [(_grams(text), label) for text, label in examples]
        df = Counter(term for grams, _ in features for term in grams)
        self.idf = {term: math.log((1 + len(features)) / (1 + count)) + 1 for term, count in df.items()}
        totals = defaultdict(Counter)
        for grams, label in features:
            totals[label].update(self.vector(grams))
        self.centroids = {label: _unit(vector) for label, vector in totals.items()}

    def vector(self, grams):
        return _unit({term: (1 + math.log(count)) * self.idf[term] for term, count in grams.items() if term in self.idf})

    def predict(self, text):
        vector = self.vector(_grams(text))
        scores = sorted(((label, sum(weight * centroid.get(term, 0) for term, weight in vector.items()))
                         for label, centroid in self.centroids.items()), key=lambda item: (-item[1], item[0]))
        if not scores or scores[0][1] < 0.45 or (len(scores) > 1 and scores[0][1] - scores[1][1] < 0.08):
            return "", scores[0][1] if scores else 0.0
        return scores[0]


EVALUATION_MINIMUMS = {"train_records": 10, "test_records": 5, "train_labels": 2, "test_descriptions": 3}


def evaluate_with_readiness(rows, holdout_factory=None):
    """Evaluate one domain at a time. Keep repeated wording and batch out of train."""
    if len({obs.domain for obs, _ in rows}) != 1:
        return dict.fromkeys(EVALUATION_MINIMUMS, 0), None
    if holdout_factory:
        test = [(obs, label) for obs, label in rows if normalized(obs.factory) == normalized(holdout_factory)]
    else:
        # Fixed holdout prevents an operator from retrying random splits until a score improves.
        test = [(obs, label) for obs, label in rows if int(key_for(normalized(obs.description))[:8], 16) % 5 == 0]
    test_ids = {obs.id for obs, _ in test}
    phrases = {normalized(obs.description) for obs, _ in test}
    batches = {(normalized(obs.factory), normalized(obs.batch)) for obs, _ in test if obs.batch}
    train = [(obs, label) for obs, label in rows if obs.id not in test_ids and normalized(obs.description) not in phrases
             and (normalized(obs.factory), normalized(obs.batch)) not in batches]
    train_labels = {label for _, label in train}
    readiness = dict(train_records=len(train), test_records=len(test), train_labels=len(train_labels), test_descriptions=len(phrases))
    if any(readiness[key] < minimum for key, minimum in EVALUATION_MINIMUMS.items()):
        return readiness, None
    model = TextBaseline(train)
    majority = Counter(label for _, label in train).most_common(1)[0][0]
    # Score unique wording/factory/label tuples so a frequently repeated phrase cannot dominate.
    unique_test = {(normalized(obs.description), normalized(obs.factory), label) for obs, label in test}
    pairs = [(expected, model.predict(text)[0]) for text, _, expected in sorted(unique_test)]
    support = Counter(expected for expected, _ in pairs)
    confusion = Counter(pairs)
    correct = sum(expected == predicted for expected, predicted in pairs)
    covered = sum(bool(predicted) for _, predicted in pairs)
    per_label = []
    for label, count in sorted(support.items()):
        tp = confusion[label, label]
        predicted = sum(n for (_, guess), n in confusion.items() if guess == label)
        per_label.append({"defect": label, "test_groups": count, "recall": tp/count, "f1": 2*tp/(predicted+count),
                          "seen_in_train": label in train_labels})
    metrics = dict(train_records=len(train), test_records=len(test), test_groups=len(pairs), accuracy=correct/len(pairs),
                   majority_accuracy=support[majority]/len(pairs), coverage=covered/len(pairs),
                   macro_recall=sum(item["recall"] for item in per_label)/len(per_label),
                   macro_f1=sum(item["f1"] for item in per_label)/len(per_label),
                   per_label=per_label, confusion=[{"actual": a, "predicted": p or "REVIEW", "groups": n}
                                                  for (a, p), n in sorted(confusion.items())])
    return readiness, metrics


def evaluate(rows, holdout_factory=None):
    return evaluate_with_readiness(rows, holdout_factory)[1]
