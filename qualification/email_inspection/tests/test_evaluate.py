"""Hand-calculated oracles, strict artifacts, and actual CLI behavior."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("evaluate", ROOT / "evaluate.py")
bench = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench)


def fixtures(labels=("injection", "injection", "injection", "injection", "benign", "benign", "benign")):
    corpus = {"schema_version": 1, "corpus_version": "test-v1", "cases": []}
    artifact = {"schema_version": 1, "corpus_version": "test-v1", "corpus_sha256": "test-hash",
                "provenance": {"kind": "artificial", "producer": "hand oracle", "description": "No model executed."},
                "predictions": []}
    for i, label in enumerate(labels):
        case = {"id": str(i), "version": 1, "family": str(i), "split": "evaluation", "language": "fr",
                "categories": ["ordinary", "overlap"], "label": label, "rationale": "Fixture annotation",
                "input": {"body": "abcd", "subject": "éZ"}}
        corpus["cases"].append(case)
        artifact["predictions"].append({"case_id": str(i), "case_version": 1, "status": "inspected",
            "label": label if label in ("injection", "benign") else "benign", "score": .6,
            "coverage": {"body": [[0, 4]], "subject": [[0, 2]]}})
    return corpus, artifact


def run(corpus, artifact):
    return bench.evaluate(corpus, artifact, "test-hash", "predictions-hash")


class MetricsTests(unittest.TestCase):
    def test_asymmetric_matrix_and_label_inversion(self):
        corpus, artifact = fixtures()
        # Truth: 4 positives, 3 negatives. Predictions: TP=3 FN=1 FP=2 TN=1.
        predictions = ["injection", "injection", "injection", "benign", "injection", "injection", "benign"]
        for row, label in zip(artifact["predictions"], predictions):
            row["label"] = label
        report = run(corpus, artifact)
        metrics = report["overall"]
        self.assertEqual(metrics["confusion"], {"tp": 3, "fn": 1, "fp": 2, "tn": 1})
        rates = metrics["rates_on_classified_evaluable_cases"]
        self.assertEqual(rates["false_positive_rate"], {"numerator": 2, "denominator": 3, "value": 2 / 3})
        self.assertEqual(rates["false_negative_rate"], {"numerator": 1, "denominator": 4, "value": .25})
        self.assertEqual(rates["precision"]["value"], .6)
        self.assertEqual(rates["recall"]["value"], .75)
        self.assertEqual(metrics["evaluable_coverage"]["value"], 1)
        self.assertEqual(report["by_category"]["overlap"], metrics)
        self.assertEqual(report["by_language"]["fr"], metrics)
        for row in artifact["predictions"]:
            row["label"] = "benign" if row["label"] == "injection" else "injection"
        self.assertEqual(run(corpus, artifact)["overall"]["confusion"], {"tp": 1, "fn": 3, "fp": 1, "tn": 2})

    def test_omission_abstention_and_ambiguity_do_not_become_benign(self):
        corpus, artifact = fixtures(("injection", "benign", "injection", "ambiguous", "malformed"))
        artifact["predictions"].pop(0)  # Missing injection.
        for row, status in zip(artifact["predictions"], ("unavailable", "partial")):
            row.update(status=status, label=None, score=None,
                       coverage={"body": [[0, 2]] if status == "partial" else [], "subject": []})
        metrics = run(corpus, artifact)["overall"]
        self.assertEqual(metrics["statuses"], {"inspected": 2, "missing": 1, "unavailable": 1, "partial": 1, "error": 0})
        self.assertEqual(metrics["confusion"], dict(tp=0, tn=0, fp=0, fn=0))
        self.assertEqual(metrics["evaluable_cases"], 3)
        self.assertEqual(metrics["excluded_cases"], 2)
        self.assertEqual(metrics["unclassified_evaluable_cases"], 3)
        self.assertEqual(metrics["unclassified_by_expected_label"]["injection"], dict(numerator=2, denominator=2, value=1))
        self.assertEqual(metrics["case_coverage"], dict(numerator=2, denominator=5, value=.4))
        self.assertEqual(metrics["character_coverage"], dict(numerator=14, denominator=30, value=14 / 30))
        self.assertIsNone(metrics["rates_on_classified_evaluable_cases"]["recall"]["value"])

    def test_zero_denominators_empty_split_and_empty_surfaces(self):
        corpus, artifact = fixtures(("benign",))
        corpus["cases"][0]["input"] = {"body": ""}
        artifact["predictions"][0]["coverage"] = {"body": []}
        report = run(corpus, artifact)
        self.assertIsNone(report["overall"]["character_coverage"]["value"])
        self.assertEqual(report["overall"]["case_coverage"]["value"], 1)
        self.assertIsNone(report["overall"]["rates_on_classified_evaluable_cases"]["recall"]["value"])
        self.assertIsNone(report["by_split"]["tuning"]["case_coverage"]["value"])
        artifact["predictions"] = []
        self.assertEqual(run(corpus, artifact)["overall"]["statuses"]["missing"], 1)

    def test_real_declared_observations_have_separate_denominators(self):
        corpus, artifact = fixtures()
        artifact["provenance"]["kind"] = "observed"
        artifact["predictions"][0]["observations"] = {"latency_ms": 10, "peak_rss_bytes": 100}
        artifact["predictions"][1]["observations"] = {"latency_ms": 30}
        summary = run(corpus, artifact)["overall"]["provided_observations"]
        self.assertEqual(summary["latency_ms"], dict(count=2, min=10, max=30, mean=20))
        self.assertEqual(summary["peak_rss_bytes"], dict(count=1, min=100, max=100, mean=100))

    def test_deterministic_independent_of_prediction_order(self):
        corpus, artifact = fixtures()
        first = run(corpus, artifact)
        artifact["predictions"].reverse()
        self.assertEqual(first, run(corpus, artifact))


class ValidationTests(unittest.TestCase):
    def test_bad_prediction_shapes_types_versions_and_values(self):
        corpus, artifact = fixtures()
        mutations = [
            lambda a: a.update(schema_version=True),
            lambda a: a.update(corpus_version="stale"),
            lambda a: a.update(corpus_sha256="stale"),
            lambda a: a.update(extra=True),
            lambda a: a.update(predictions={}),
            lambda a: a["predictions"].append(copy.deepcopy(a["predictions"][0])),
            lambda a: a["predictions"][0].update(case_id="unknown"),
            lambda a: a["predictions"][0].update(case_version=True),
            lambda a: a["predictions"][0].update(case_version=2),
            lambda a: a["predictions"][0].update(status="missing"),
            lambda a: a["predictions"][0].update(status=[]),
            lambda a: a["predictions"][0].update(label="safe"),
            lambda a: a["predictions"][0].update(label=None),
            lambda a: a["predictions"][0].update(score=None),
            lambda a: a["predictions"][0].update(score=True),
            lambda a: a["predictions"][0].update(score=float("nan")),
            lambda a: a["predictions"][0].update(score=float("inf")),
            lambda a: a["predictions"][0].update(score=10**400),
            lambda a: a["predictions"][0].update(score=-.1),
            lambda a: a["predictions"][0].update(score=1.1),
            lambda a: a["predictions"][0].update(status="unavailable"),
            lambda a: a["predictions"][0].update(status="partial", label=None, score=None),
            lambda a: a["predictions"][0].update(observations={"latency_ms": 10}),
        ]
        for mutation in mutations:
            changed = copy.deepcopy(artifact)
            mutation(changed)
            with self.subTest(artifact=changed), self.assertRaises(bench.Invalid):
                run(corpus, changed)

    def test_invalid_coverage_and_truncation(self):
        corpus, artifact = fixtures()
        bad = [{"body": [[0, 3]], "subject": [[0, 2]]},  # Missing tail.
               {"body": [[0, 4]], "subject": []},  # Missing metadata.
               {"body": [[0, 4]]},
               {"body": [[0, 3], [2, 4]], "subject": [[0, 2]]},
               {"body": [[2, 4], [0, 2]], "subject": [[0, 2]]},
               {"body": [[False, 4]], "subject": [[0, 2]]},
               {"body": [[0, 5]], "subject": [[0, 2]]},
               {"body": [[0, 0]], "subject": []}]
        for coverage in bad:
            artifact["predictions"][0]["coverage"] = coverage
            with self.subTest(coverage=coverage), self.assertRaises(bench.Invalid):
                run(corpus, artifact)
        artifact["predictions"][0]["coverage"] = {"body": [[0, 2], [2, 4]], "subject": [[0, 2]]}
        run(corpus, artifact)  # Adjacent intervals cover the surface.

    def test_invalid_corpus_and_split_leakage(self):
        corpus, artifact = fixtures()
        mutations = [lambda c: c.update(cases=[]), lambda c: c.update(schema_version=True),
            lambda c: c["cases"][0].update(version=False), lambda c: c["cases"][0].update(input={}),
            lambda c: c["cases"][0].update(input={"body": None}),
            lambda c: c["cases"][0].update(input={"body": "\ud800"}),
            lambda c: c["cases"][0].update(categories=["x", "x"]),
            lambda c: c["cases"][0].update(label="safe"),
            lambda c: c["cases"][0].update(id="1"),
            lambda c: c["cases"][0].update(split="tuning"),  # Identical input in other split.
        ]
        for mutation in mutations:
            changed = copy.deepcopy(corpus)
            mutation(changed)
            with self.subTest(corpus=changed), self.assertRaises(bench.Invalid):
                run(changed, artifact)
        corpus["cases"][0].update(input={"body": "unique"}, split="tuning", family="1")
        with self.assertRaisesRegex(bench.Invalid, "leaks"):
            bench.validate_corpus(corpus)

    def test_invalid_observations(self):
        corpus, artifact = fixtures()
        artifact["provenance"]["kind"] = "observed"
        for observations in ({}, {"latency_ms": True}, {"latency_ms": -1}, {"latency_ms": float("inf")},
                             {"latency_ms": float("nan")}, {"peak_rss_bytes": 1.5}, {"other": 2}):
            artifact["predictions"][0]["observations"] = observations
            with self.subTest(observations=observations), self.assertRaises(bench.Invalid):
                run(corpus, artifact)

    def test_json_duplicates_nonfinite_and_invalid_encoding(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            for data in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}', b'\xff', b'not json'):
                path.write_bytes(data)
                with self.subTest(data=data), self.assertRaises(bench.Invalid):
                    bench.read_json(path)


class CLITests(unittest.TestCase):
    def test_finite_extreme_observations_do_not_overflow_mean(self):
        corpus, artifact = fixtures(("injection", "benign", "benign"))
        artifact["provenance"]["kind"] = "observed"
        for row in artifact["predictions"]:
            row["observations"] = {"latency_ms": sys.float_info.max}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cpath, ppath, out = (root / name for name in ("corpus.json", "predictions.json", "report.json"))
            cpath.write_text(json.dumps(corpus), encoding="utf-8")
            artifact["corpus_sha256"] = hashlib.sha256(cpath.read_bytes()).hexdigest()
            ppath.write_text(json.dumps(artifact), encoding="utf-8")
            result = subprocess.run([sys.executable, str(ROOT / "evaluate.py"), "--corpus", str(cpath),
                                     "--predictions", str(ppath), "--output", str(out)], capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(out.read_text())
            self.assertEqual(report["overall"]["provided_observations"]["latency_ms"],
                             dict(count=3, min=sys.float_info.max, max=sys.float_info.max, mean=sys.float_info.max))
            self.assertEqual(report["by_split"]["tuning"]["provided_observations"]["latency_ms"]["count"], 0)

    def test_real_cli_missing_invalid_preservation_and_same_path(self):
        corpus, artifact = fixtures()
        artifact["predictions"].pop()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cpath, ppath, out = (root / name for name in ("corpus.json", "predictions.json", "report.json"))
            cpath.write_text(json.dumps(corpus), encoding="utf-8")
            artifact["corpus_sha256"] = hashlib.sha256(cpath.read_bytes()).hexdigest()
            ppath.write_text(json.dumps(artifact), encoding="utf-8")
            command = [sys.executable, str(ROOT / "evaluate.py"), "--corpus", str(cpath),
                       "--predictions", str(ppath), "--output", str(out)]
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
            before = out.read_bytes()
            self.assertEqual(json.loads(before)["overall"]["statuses"]["missing"], 1)
            self.assertEqual(subprocess.run(command + ["--require-complete"], capture_output=True).returncode, 2)
            self.assertEqual(before, out.read_bytes())
            artifact["predictions"][0]["case_version"] = 42
            ppath.write_text(json.dumps(artifact), encoding="utf-8")
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 2)
            self.assertEqual(before, out.read_bytes())
            original = cpath.read_bytes()
            self.assertEqual(subprocess.run(command[:-1] + [str(cpath)], capture_output=True).returncode, 2)
            self.assertEqual(original, cpath.read_bytes())

    def test_shipped_corpus_and_artificial_report_reproduce(self):
        corpus, chash = bench.read_json(ROOT / "corpus.json")
        artifact, phash = bench.read_json(ROOT / "examples/artificial-predictions.json")
        report = bench.evaluate(corpus, artifact, chash, phash)
        expected, _ = bench.read_json(ROOT / "examples/artificial-report.json")
        self.assertEqual(report, expected)
        self.assertEqual(artifact["provenance"]["kind"], "artificial")
        self.assertGreater(report["overall"]["confusion"]["fp"], 0)
        self.assertGreater(report["overall"]["confusion"]["fn"], 0)
        self.assertGreater(report["overall"]["not_fully_inspected"], 0)
        self.assertTrue(all(not row["observations"] for row in report["cases"]))
        for split in ("tuning", "evaluation"):
            selected = [c for c in corpus["cases"] if c["split"] == split]
            self.assertEqual({c["language"] for c in selected}, {"fr", "en"})
        self.assertGreaterEqual(sum(len(c["input"].get("body", "")) >= 12000 for c in corpus["cases"]), 2)


if __name__ == "__main__":
    unittest.main()
