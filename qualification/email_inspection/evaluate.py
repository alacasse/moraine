"""Local artifact validator and metrics; never invokes an inspector or model."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys

BENCH_VERSION = "1.0"
LABELS = ("benign", "injection", "ambiguous", "malformed")
STATUSES = ("inspected", "partial", "unavailable", "error", "missing")


class Invalid(ValueError):
    """An input artifact does not satisfy the qualification contract."""


def require(condition, message):
    if not condition:
        raise Invalid(message)


def fields(value, required, optional=()):
    require(type(value) is dict, "expected object")
    require(set(required) <= value.keys() <= set(required) | set(optional),
            f"unexpected/missing fields; expected {sorted(required)}")


def string(value):
    require(type(value) is str and bool(value.strip()), "expected nonempty string")
    try:
        value.encode("utf-8")
    except UnicodeError as exc:
        raise Invalid("invalid Unicode scalar") from exc


def integer(value, minimum=0):
    require(type(value) is int and value >= minimum, "expected integer in range")


def number(value):
    require(type(value) in (int, float), "expected number, not boolean")
    try:
        require(math.isfinite(value) and value >= 0, "expected finite nonnegative number")
    except OverflowError as exc:
        raise Invalid("number outside supported range") from exc


def choice(value, choices):
    require(type(value) is str and value in choices, f"expected one of {choices}")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON object key")
        result[key] = value
    return result


def read_json(path):
    data = Path(path).read_bytes()
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_object,
                           parse_constant=lambda _: (_ for _ in ()).throw(Invalid("nonfinite JSON number")))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise Invalid(f"invalid JSON: {exc}") from exc
    return value, hashlib.sha256(data).hexdigest()


def validate_corpus(corpus):
    fields(corpus, ("schema_version", "corpus_version", "cases"))
    integer(corpus["schema_version"], 1)
    require(corpus["schema_version"] == 1, "unsupported corpus schema")
    string(corpus["corpus_version"])
    require(type(corpus["cases"]) is list and corpus["cases"], "cases must be nonempty list")
    ids, families, inputs = set(), {}, {}
    for case in corpus["cases"]:
        fields(case, ("id", "version", "family", "split", "language", "categories", "label", "rationale", "input"))
        for key in ("id", "family", "rationale"):
            string(case[key])
        require(case["id"] not in ids, "duplicate case id")
        ids.add(case["id"])
        integer(case["version"], 1)
        choice(case["split"], ("tuning", "evaluation"))
        choice(case["language"], ("fr", "en"))
        choice(case["label"], LABELS)
        categories = case["categories"]
        require(type(categories) is list and bool(categories), "categories must be nonempty list")
        for category in categories:
            string(category)
        require(len(set(categories)) == len(categories), "duplicate category")
        surfaces = case["input"]
        require(type(surfaces) is dict and bool(surfaces), "input must be nonempty object")
        for name, value in surfaces.items():
            string(name)
            require(type(value) is str, "surface must be a string")
            # Empty surfaces are allowed, lone surrogates are not.
            try:
                value.encode("utf-8")
            except UnicodeError as exc:
                raise Invalid("invalid surface Unicode scalar") from exc
        for registry, key in ((families, case["family"]),
                              (inputs, json.dumps(surfaces, sort_keys=True, ensure_ascii=True))):
            require(registry.get(key, case["split"]) == case["split"], "family/identical input leaks across splits")
            registry[key] = case["split"]
    return {case["id"]: case for case in corpus["cases"]}


def coverage_counts(case, coverage):
    fields(coverage, case["input"].keys())
    covered = total = 0
    for name, value in case["input"].items():
        total += len(value)
        intervals = coverage[name]
        require(type(intervals) is list, "coverage intervals must be list")
        previous = 0
        for interval in intervals:
            require(type(interval) is list and len(interval) == 2, "expected [start,end]")
            start, end = interval
            integer(start)
            integer(end)
            require(previous <= start < end <= len(value), "overlapping, unsorted or out-of-bounds coverage")
            covered += end - start
            previous = end
    return covered, total


def validate_predictions(artifact, corpus, corpus_hash, cases):
    fields(artifact, ("schema_version", "corpus_version", "corpus_sha256", "provenance", "predictions"))
    integer(artifact["schema_version"], 1)
    require(artifact["schema_version"] == 1, "unsupported prediction schema")
    require(artifact["corpus_version"] == corpus["corpus_version"], "corpus version mismatch")
    require(artifact["corpus_sha256"] == corpus_hash, "corpus bytes/hash mismatch")
    provenance = artifact["provenance"]
    fields(provenance, ("kind", "producer", "description"))
    choice(provenance["kind"], ("artificial", "observed"))
    string(provenance["producer"])
    string(provenance["description"])
    require(type(artifact["predictions"]) is list, "predictions must be list")
    predictions = {}
    for row in artifact["predictions"]:
        fields(row, ("case_id", "case_version", "status", "label", "score", "coverage"), ("observations",))
        string(row["case_id"])
        require(row["case_id"] in cases, "unknown case id")
        require(row["case_id"] not in predictions, "duplicate prediction")
        case = cases[row["case_id"]]
        integer(row["case_version"], 1)
        require(row["case_version"] == case["version"], "case version mismatch")
        choice(row["status"], STATUSES[:-1])
        covered, total = coverage_counts(case, row["coverage"])
        if row["status"] == "inspected":
            require(covered == total, "inspected requires complete surface coverage")
            choice(row["label"], ("benign", "injection"))
            number(row["score"])
            require(row["score"] <= 1, "score outside [0,1]")
        else:
            require(row["label"] is None and row["score"] is None, "unclassified result must have null label and score")
            if row["status"] == "partial":
                require(0 < covered < total, "partial requires nonzero incomplete coverage")
            else:
                require(covered == 0, "unavailable/error must have empty coverage")
        if "observations" in row:
            require(provenance["kind"] == "observed", "artificial data cannot carry resource observations")
            observations = row["observations"]
            fields(observations, (), ("latency_ms", "peak_rss_bytes"))
            require(bool(observations), "observations must not be empty")
            for key, value in observations.items():
                number(value)
                if key == "peak_rss_bytes":
                    integer(value)
        predictions[row["case_id"]] = row
    return predictions


def ratio(numerator, denominator):
    return {"numerator": numerator, "denominator": denominator,
            "value": numerator / denominator if denominator else None}


def summarize(rows):
    labels = Counter(row["expected"] for row in rows)
    statuses = Counter(row["status"] for row in rows)
    matrix = dict.fromkeys(("tp", "tn", "fp", "fn"), 0)
    unclassified = {"benign": 0, "injection": 0}
    for row in rows:
        expected = row["expected"]
        if expected not in unclassified:
            continue
        if row["status"] != "inspected":
            unclassified[expected] += 1
        else:
            matrix[{("injection", "injection"): "tp", ("benign", "benign"): "tn",
                    ("benign", "injection"): "fp", ("injection", "benign"): "fn"}
                   [(expected, row["predicted"])]] += 1
    tp, tn, fp, fn = (matrix[key] for key in ("tp", "tn", "fp", "fn"))
    evaluable = labels["benign"] + labels["injection"]
    observed = {}
    for key in ("latency_ms", "peak_rss_bytes"):
        values = [row["observations"][key] for row in rows if key in row["observations"]]
        observed[key] = {"count": len(values), "min": min(values) if values else None,
                         "max": max(values) if values else None,
                         "mean": statistics.mean(values) if values else None}
    return {
        "total_cases": len(rows), "expected_labels": {key: labels[key] for key in LABELS},
        "statuses": {key: statuses[key] for key in STATUSES},
        "not_fully_inspected": len(rows) - statuses["inspected"],
        "case_coverage": ratio(statuses["inspected"], len(rows)),
        "character_coverage": ratio(sum(row["covered_characters"] for row in rows),
                                    sum(row["total_characters"] for row in rows)),
        "evaluable_cases": evaluable, "excluded_cases": labels["ambiguous"] + labels["malformed"],
        "classified_evaluable_cases": tp + tn + fp + fn,
        "evaluable_coverage": ratio(tp + tn + fp + fn, evaluable),
        "unclassified_evaluable_cases": sum(unclassified.values()),
        "unclassified_by_expected_label": {key: ratio(value, labels[key]) for key, value in unclassified.items()},
        "confusion": matrix,
        "rates_on_classified_evaluable_cases": {"false_positive_rate": ratio(fp, fp + tn),
            "false_negative_rate": ratio(fn, fn + tp), "precision": ratio(tp, tp + fp),
            "recall": ratio(tp, tp + fn)},
        "provided_observations": observed,
    }


def evaluate(corpus, artifact, corpus_hash, predictions_hash):
    cases = validate_corpus(corpus)
    predictions = validate_predictions(artifact, corpus, corpus_hash, cases)
    rows = []
    for case_id, case in sorted(cases.items()):
        prediction = predictions.get(case_id)
        coverage = prediction["coverage"] if prediction else {name: [] for name in case["input"]}
        covered, total = coverage_counts(case, coverage)
        rows.append({"case_id": case_id, "case_version": case["version"], "split": case["split"],
                     "language": case["language"], "categories": sorted(case["categories"]),
                     "expected": case["label"], "status": prediction["status"] if prediction else "missing",
                     "predicted": prediction["label"] if prediction else None,
                     "score": prediction["score"] if prediction else None,
                     "covered_characters": covered, "total_characters": total,
                     "observations": prediction.get("observations", {}) if prediction else {}})
    report = {"schema_version": 1, "bench_version": BENCH_VERSION,
              "corpus_version": corpus["corpus_version"], "corpus_sha256": corpus_hash,
              "predictions_sha256": predictions_hash, "provenance": artifact["provenance"],
              "claim": "Artifact validation and fixture metrics only; no security or model qualification claim.",
              "coverage_basis": "Producer-declared original-surface character intervals; execution not attested.",
              "positive_label": "injection", "overall": summarize(rows), "cases": rows}
    report["by_split"] = {split: summarize([r for r in rows if r["split"] == split])
                          for split in ("tuning", "evaluation")}
    report["by_language"] = {lang: summarize([r for r in rows if r["language"] == lang]) for lang in ("fr", "en")}
    report["by_category"] = {category: summarize([r for r in rows if category in r["categories"]])
                             for category in sorted({cat for r in rows for cat in r["categories"]})}
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", required=True, type=Path)
    parser.add_argument("--predictions", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args(argv)
    try:
        require(args.output.resolve() not in (args.corpus.resolve(), args.predictions.resolve()),
                "output must not overwrite an input")
        if args.output.exists():
            require(not any(args.output.samefile(path) for path in (args.corpus, args.predictions)),
                    "output must not overwrite an input hardlink")
        corpus, corpus_hash = read_json(args.corpus)
        artifact, predictions_hash = read_json(args.predictions)
        report = evaluate(corpus, artifact, corpus_hash, predictions_hash)
        args.output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2,
                                          allow_nan=False) + "\n", encoding="utf-8")
        if args.require_complete and report["overall"]["statuses"]["missing"]:
            print("incomplete predictions: see missing cases in report", file=sys.stderr)
            return 2
    except (Invalid, OSError) as exc:
        print(f"qualification error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
