"""Independent review probe: invoke from the Moraine repository root."""
import importlib.util
import itertools
from pathlib import Path
import sys

spec = importlib.util.spec_from_file_location('fixture_helpers', Path('qualification/email_inspection/tests/test_evaluate.py'))
t = importlib.util.module_from_spec(spec)
spec.loader.exec_module(t)
count = 0
for truth in itertools.product(('benign', 'injection', 'ambiguous', 'malformed'), repeat=3):
    for predicted in itertools.product(('benign', 'injection', 'missing', 'partial', 'error', 'unavailable'), repeat=3):
        corpus, artifact = t.fixtures(truth)
        for row, status in zip(artifact['predictions'], predicted):
            if status in ('benign', 'injection'):
                row['label'] = status
            else:
                row.update(status=status, label=None, score=None,
                           coverage={'body': [[0, 1]] if status == 'partial' else [], 'subject': []})
        artifact['predictions'] = [row for row in artifact['predictions'] if row['status'] != 'missing']
        metrics = t.run(corpus, artifact)['overall']
        pairs = list(zip(truth, predicted))
        expected = {key: pairs.count(pair) for key, pair in {
            'tp': ('injection', 'injection'), 'tn': ('benign', 'benign'),
            'fp': ('benign', 'injection'), 'fn': ('injection', 'benign')}.items()}
        assert metrics['confusion'] == expected, (truth, predicted, metrics)
        assert metrics['unclassified_evaluable_cases'] == sum(
            actual in ('benign', 'injection') and prediction not in ('benign', 'injection')
            for actual, prediction in pairs)
        count += 1
print(f'{count} truth/prediction/status combinations passed')
for value in (sys.float_info.max, float.fromhex('0x0.0000000000001p-1022')):
    corpus, artifact = t.fixtures(('benign',) * 3)
    artifact['provenance']['kind'] = 'observed'
    for row in artifact['predictions']:
        row['observations'] = {'latency_ms': value}
    result = t.run(corpus, artifact)['overall']['provided_observations']['latency_ms']
    assert result == dict(count=3, min=value, max=value, mean=value), result
print('Extreme finite and minimum subnormal observations passed')
