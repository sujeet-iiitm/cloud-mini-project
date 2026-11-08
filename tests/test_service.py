"""Unit tests for the inference service endpoints, headers, fault injection, and schema validation."""
import json
import os
import unittest

from service.app import (
    app,
    healthz,
    readyz,
    parse,
    ParseRequest,
    validate_against_schema,
    startup_event
)


class TestService(unittest.TestCase):
    def setUp(self):
        # Ensure fresh clean startup state
        startup_event()

    def test_healthz_endpoint(self):
        """Verify /healthz returns status 200 as long as the process is alive."""
        res = healthz()
        self.assertEqual(res, {"status": "alive"})

    def test_readyz_endpoint(self):
        """Verify /readyz returns status code 200 after startup."""
        res = readyz()
        self.assertEqual(res.status_code, 200)

    def test_parse_valid_command(self):
        """Verify /parse returns HTTP 200, exactly the 4 required keys, and headers."""
        req = ParseRequest(text="set an alarm for seven thirty am tomorrow")
        res = parse(req)
        self.assertEqual(res.status_code, 200)

        data = json.loads(res.body.decode("utf-8"))
        self.assertEqual(set(data.keys()), {"intent", "date", "time", "place"})
        self.assertEqual(data["intent"], "alarm_set")
        self.assertEqual(data["time"], "seven thirty am")
        self.assertEqual(data["date"], "tomorrow")
        self.assertIsNone(data["place"])

        # Check response headers
        headers_lower = {k.lower(): v for k, v in res.headers.items()}
        self.assertIn("x-model-version", headers_lower)
        self.assertIn("x-served-by", headers_lower)

    def test_fault_injection(self):
        """Verify that with FAULT_INJECT=1, /parse returns HTTP 500 with exact error body."""
        os.environ["FAULT_INJECT"] = "1"
        try:
            req = ParseRequest(text="what is the weather in london")
            res = parse(req)
            self.assertEqual(res.status_code, 500)
            data = json.loads(res.body.decode("utf-8"))
            self.assertEqual(data, {"error": "invalid_model_output"})

            headers_lower = {k.lower(): v for k, v in res.headers.items()}
            self.assertIn("x-model-version", headers_lower)
            self.assertIn("x-served-by", headers_lower)
        finally:
            os.environ["FAULT_INJECT"] = "0"

    def test_schema_validation_rules(self):
        """Verify schema validation enforces exactly four keys and recognized intents."""
        valid_obj = {"intent": "weather_query", "date": None, "time": None, "place": "london"}
        self.assertTrue(validate_against_schema(valid_obj))

        # Missing required key
        self.assertFalse(validate_against_schema({"intent": "weather_query", "date": None, "time": None}))

        # Extra disallowed key
        self.assertFalse(validate_against_schema({**valid_obj, "extra": "forbidden"}))

        # Disallowed intent
        self.assertFalse(validate_against_schema({**valid_obj, "intent": "nonexistent_intent"}))

        # Non-string slot value
        self.assertFalse(validate_against_schema({**valid_obj, "place": 12345}))


if __name__ == "__main__":
    unittest.main()
