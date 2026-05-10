import unittest
from unittest.mock import Mock

from funda._parallel import _ParallelRunner
from funda._transport import _FundaTransport
from funda.constants import API_LISTING_TINY, FINGERPRINT_POOL
from funda.exceptions import FundaRequestError
from funda.headers import make_headers


TEST_URL = API_LISTING_TINY.format(tiny_id=43117443)


class FakeResponse:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


class RetryTransport(_FundaTransport):
    def __init__(self, statuses: list[int]) -> None:
        super().__init__(max_retries=len(statuses) - 1, retry_backoff=0)
        self.statuses = statuses
        self.starts: list[int] = []
        self._fingerprint = FINGERPRINT_POOL[0]
        self._fingerprint_index = 0

    def _send_once(self, *args, **kwargs):
        self.starts.append(kwargs["fingerprint_start_index"])
        return FakeResponse(self.statuses.pop(0))


class TransportTests(unittest.TestCase):
    def test_fingerprint_pool_entries_have_required_fields(self) -> None:
        self.assertGreaterEqual(len(FINGERPRINT_POOL), 1)

        for fingerprint in FINGERPRINT_POOL:
            with self.subTest(fingerprint=fingerprint):
                self.assertIn(
                    fingerprint.kind,
                    {"tls_ja3", "curl_ja3", "curl_impersonate", "tls_client"},
                )
                if fingerprint.kind in {"tls_ja3", "curl_ja3"}:
                    self.assertTrue(fingerprint.ja3)
                elif fingerprint.kind == "curl_impersonate":
                    self.assertTrue(fingerprint.target)
                elif fingerprint.kind == "tls_client":
                    self.assertTrue(fingerprint.identifier)

    def test_search_headers_are_convertible_for_tls_client(self) -> None:
        header_list = make_headers("search")
        header_dict = dict(header_list)

        self.assertEqual(len(header_list), len(header_dict))
        self.assertEqual(header_dict["referer"], "https://www.funda.nl/")
        self.assertEqual(header_dict["accept"], "application/json")

    def test_transport_validates_retry_settings(self) -> None:
        with self.assertRaises(ValueError):
            _FundaTransport(max_retries=-1)
        with self.assertRaises(ValueError):
            _FundaTransport(retry_backoff=-0.1)

    def test_reset_transport_closes_sessions_and_rotates(self) -> None:
        transport = _FundaTransport(retry_backoff=0)
        curl_session = Mock()
        tls_session = object()
        transport._curl_session = curl_session
        transport._tls_session = tls_session
        transport._fingerprint = FINGERPRINT_POOL[0]
        transport._fingerprint_index = 0

        next_index = transport._reset_transport(rotate=True)

        curl_session.close.assert_called_once()
        self.assertIsNone(transport._curl_session)
        self.assertIsNone(transport._tls_session)
        self.assertIsNone(transport._fingerprint)
        self.assertIsNone(transport._fingerprint_index)
        self.assertEqual(next_index, 1)

    def test_request_retries_retry_status_with_next_fingerprint(self) -> None:
        transport = RetryTransport([403, 200])

        response = transport.request("GET", TEST_URL)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(transport.starts, [0, 1])

    def test_request_raises_after_retry_statuses_are_exhausted(self) -> None:
        with self.assertRaises(FundaRequestError):
            RetryTransport([403, 403]).request("GET", TEST_URL)


class ParallelRunnerTests(unittest.TestCase):
    def test_runner_reuses_thread_local_clients_and_preserves_order(self) -> None:
        class Client:
            created = 0
            closed = 0

            def __init__(self) -> None:
                type(self).created += 1
                self.id = type(self).created

            def close(self) -> None:
                type(self).closed += 1

        runner = _ParallelRunner(Client, lambda client: client.close())
        try:
            first = runner.map(lambda client, item: (client.id, item * 2), range(8), workers=4)
            second = runner.map(lambda client, item: (client.id, item * 3), range(8), workers=4)

            self.assertEqual([value for _, value in first], [item * 2 for item in range(8)])
            self.assertEqual([value for _, value in second], [item * 3 for item in range(8)])
            self.assertLessEqual(Client.created, 4)
        finally:
            runner.close()

        self.assertEqual(Client.closed, Client.created)


if __name__ == "__main__":
    unittest.main()
