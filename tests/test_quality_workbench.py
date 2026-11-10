from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from quality_graph import GLOVES, Observation, ReviewStore, accepted_samples
from quality_workbench_ui import _apply, progress_by_gate, work_queue


class WorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.rows = [Observation("TU", "ZX", GLOVES, gate, name, source="fixture", record=str(index))
                     for index, (gate, name) in enumerate([("IQC", "来料异常"), ("PQC", "缝份不匀"), ("FQC", "内里爆口")])]
        self.t = lambda zh, en: en

    def test_progress_separates_trainable_uncertain_and_legacy_pending(self):
        a, b, c = self.rows
        decisions = {a.id: {"status": "submitted", "labels": []}, b.id: {"status": "approved", "labels": ["TU-001"]},
                     c.id: {"status": "submitted", "labels": ["TU-002"]}}
        gates = progress_by_gate(self.rows, decisions)
        self.assertEqual([row["stage"] for row in gates], ["PQC", "FQC"])
        self.assertEqual([row["total"] for row in gates], [1, 1])
        self.assertEqual([row["trainable"] for row in gates], [1, 0])
        self.assertEqual(work_queue(self.rows, decisions, ""), [c])

    def test_save_accepts_a_label_and_undo_restores_its_queue_position(self):
        a, b, _ = self.rows
        with TemporaryDirectory() as folder:
            store = ReviewStore(Path(folder) / "reviews.sqlite3")
            settings = {"query": "", "cursor": 1}
            event = {"action": "answer", "id": b.id, "revision": 0, "choice": "TU-001"}
            _apply(event, self.rows, {}, self.rows, b, {}, settings, store, self.t)
            decisions = store.latest("label")
            self.assertEqual(accepted_samples(decisions)[0][1]["labels"], ["TU-001"])
            self.assertNotIn(b, work_queue(self.rows, decisions, ""))
            _apply({"action": "undo"}, self.rows, decisions, [a], a, {}, settings, store, self.t)
            latest = store.latest("label")
            self.assertEqual(accepted_samples(latest), [])
            self.assertEqual(work_queue(self.rows, latest, "")[settings["cursor"]], b)

    def test_answer_checks_record_revision_and_uncertain_is_not_trainable(self):
        a = self.rows[1]
        with TemporaryDirectory() as folder:
            store = ReviewStore(Path(folder) / "reviews.sqlite3")
            settings = {"query": "", "cursor": 0}
            event = {"action": "answer", "id": a.id, "revision": 1, "choice": "unsure"}
            with self.assertRaisesRegex(ValueError, "record changed"):
                _apply(event, self.rows, {}, self.rows, a, {}, settings, store, self.t)
            event["revision"] = 0
            _apply(event, self.rows, {}, self.rows, a, {}, settings, store, self.t)
            gate = progress_by_gate(self.rows, store.latest("label"))[0]
            self.assertEqual((gate["uncertain"], gate["trainable"]), (1, 0))
