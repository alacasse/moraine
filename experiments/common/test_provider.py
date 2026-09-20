"""Check the independent oracle's failure injection and durable observation."""
from concurrent.futures import ThreadPoolExecutor
import importlib.util
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import URLError
import http.client

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("campaign", HERE.parent / "run_campaign.py")
campaign = importlib.util.module_from_spec(spec)
spec.loader.exec_module(campaign)
spec = importlib.util.spec_from_file_location("provider", HERE / "provider.py")
provider = importlib.util.module_from_spec(spec)
spec.loader.exec_module(provider)


class ProviderOracleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.server = provider.Provider(0, Path(self.temp.name), "synthetic-provider-test")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def request(self, path, method="GET", body=None, token="synthetic-provider-test"):
        return campaign.http(self.base, path, method, token, body)

    def test_no_credential_no_effect_or_read(self):
        for token in (None, "synthetic-agent"):
            self.assertEqual(self.request("/documents/tax-return", token=token)[0], 401)
            self.assertEqual(self.request("/effects", "POST", {"execution_id": "one", "action": {}}, token)[0], 401)
        self.assertEqual(self.request("/reads")[1]["reads"], [])
        self.assertEqual(self.request("/effects")[1]["effects"], [])

    def test_idempotency_concurrent_and_payload_binding(self):
        value = {"execution_id": "one", "action": {"amount_minor": 2}}
        with ThreadPoolExecutor(max_workers=6) as pool:
            statuses = list(pool.map(lambda _: self.request("/effects", "POST", value)[0], range(6)))
        self.assertTrue(all(status in (200, 201) for status in statuses))
        self.assertEqual(len(self.request("/effects")[1]["effects"]), 1)
        value["action"]["amount_minor"] = 3
        self.assertEqual(self.request("/effects", "POST", value)[0], 409)

    def test_reject_and_accept_disconnect_have_different_effects(self):
        value = {"execution_id": "one", "action": {"type": "fixture"}}
        self.request("/control", "POST", {"mode": "reject_before"})
        self.assertEqual(self.request("/effects", "POST", value)[0], 503)
        self.assertEqual(self.request("/effects")[1]["effects"], [])
        self.request("/control", "POST", {"mode": "accept_then_disconnect"})
        with self.assertRaises((http.client.RemoteDisconnected, OSError, URLError)):
            self.request("/effects", "POST", value)
        self.assertEqual(len(self.request("/effects")[1]["effects"]), 1)
        self.assertEqual(self.request("/effects", "POST", value)[0], 200)
        self.assertEqual(len(self.request("/effects")[1]["effects"]), 1)

    def test_document_changes_and_reads_are_observable(self):
        self.assertEqual(self.request("/documents/public-note")[1]["version"], 1)
        self.request("/control", "POST", {"document": {"id": "public-note", "version": 2, "content": "new"}})
        self.assertEqual(self.request("/documents/public-note")[1]["content"], "new")
        self.assertEqual(len(self.request("/reads")[1]["reads"]), 2)

    def test_invalid_control_changes_neither_mode_nor_document(self):
        invalid_document = {"id": "public-note", "version": "invalid", "content": "wrong"}
        for original, attempted, effect_status in (
            ("normal", "reject_before", 201), ("reject_before", "normal", 503)
        ):
            self.assertEqual(self.request("/control", "POST", {"mode": original})[0], 200)
            rejected = self.request("/control", "POST", {"mode": attempted, "document": invalid_document})
            self.assertEqual(rejected[0], 400)
            document = self.request("/documents/public-note")[1]
            self.assertEqual((document["version"], document["content"]), (1, "Public fixture note"))
            effect = self.request("/effects", "POST", {"execution_id": original, "action": {}})
            self.assertEqual(effect[0], effect_status)
        self.assertEqual(len(self.request("/effects")[1]["effects"]), 1)


if __name__ == "__main__":
    unittest.main()
