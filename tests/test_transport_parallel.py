import unittest
from unittest.mock import Mock, patch

from funda._parallel import _ParallelRunner
from funda._transport import _FundaTransport
from funda.constants import API_LISTING_TINY, FINGERPRINT_POOL
from funda.exceptions import FundaRequestError
from funda.headers import make_headers


TEST_URL = API_LISTING_TINY.format(tiny_id=43117443)


class FakeResponse:
    def __init__(
        self,
        status_code: int,
        *,
        headers: dict[str, str] | None = None,
        text: str = "",
    ) -> None:
        self.status_code = status_code
        self.headers = headers or {}
        self.text = text


class RetryTransport(_FundaTransport):
    def __init__(self, statuses: list[int], *, start_index: int = 0) -> None:
        super().__init__(max_retries=len(statuses) - 1, retry_backoff=0)
        self.statuses = statuses
        self.starts: list[int] = []
        self._fingerprint = FINGERPRINT_POOL[start_index]
        self._fingerprint_index = start_index

    def _send_once(self, *args, **kwargs):
        if self._fingerprint is None:
            index, fingerprint, selected_proven = self._select_fingerprint(
                kwargs["fingerprint_start_index"]
            )
            self._fingerprint_index = index
            self._fingerprint = fingerprint
            self._fingerprint_proven = self._fingerprint_proven or selected_proven
        self.starts.append(self._fingerprint_index)
        return FakeResponse(self.statuses.pop(0))


class TransportTests(unittest.TestCase):
    def setUp(self) -> None:
        for transport_type in (_FundaTransport, RetryTransport):
            transport_type._cached_fingerprint_index = None
            transport_type._last_request_at.clear()

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
        with self.assertRaises(ValueError):
            _FundaTransport(min_request_interval=-0.1)

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
        self.assertFalse(transport._fingerprint_proven)
        self.assertEqual(next_index, 1)

    def test_reset_transport_preserves_proven_fingerprint_index(self) -> None:
        transport = _FundaTransport(retry_backoff=0)
        transport._fingerprint = FINGERPRINT_POOL[3]
        transport._fingerprint_index = 3
        transport._fingerprint_proven = True

        next_index = transport._reset_transport(rotate=False)

        self.assertEqual(next_index, 3)
        self.assertTrue(transport._fingerprint_proven)

    def test_request_rotates_unproven_fingerprint_after_403(self) -> None:
        transport = RetryTransport([403, 200])
        type(transport)._cached_fingerprint_index = None

        response = transport.request("GET", TEST_URL)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(transport.starts, [0, 1])

    def test_request_keeps_proven_fingerprint_after_403(self) -> None:
        transport = RetryTransport([200, 403, 200], start_index=3)

        first = transport.request("GET", TEST_URL)
        second = transport.request("GET", TEST_URL)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(transport.starts, [3, 3, 3])
        self.assertEqual(type(transport)._cached_fingerprint_index, 3)

    def test_proven_fingerprint_stays_sticky_if_global_preference_changes(self) -> None:
        transport = RetryTransport([200, 403, 200], start_index=3)

        transport.request("GET", TEST_URL)
        type(transport)._cached_fingerprint_index = 4
        response = transport.request("GET", TEST_URL)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(transport.starts, [3, 3, 3])

    def test_proven_fingerprint_stays_sticky_for_retry_statuses(self) -> None:
        for status in (403, 429, 503):
            with self.subTest(status=status):
                transport = RetryTransport([200, status, 200], start_index=3)

                transport.request("GET", TEST_URL)
                response = transport.request("GET", TEST_URL)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(transport.starts, [3, 3, 3])

    def test_rate_limit_does_not_rotate_unproven_fingerprint(self) -> None:
        transport = RetryTransport([429, 200], start_index=3)

        response = transport.request("GET", TEST_URL)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(transport.starts, [3, 3])

    def test_akamai_rejection_uses_exponential_backoff(self) -> None:
        transport = RetryTransport([403, 403, 200])
        transport.retry_backoff = 0.5

        with patch("funda._transport.time.sleep") as sleep:
            response = transport.request("GET", TEST_URL)

        self.assertEqual(response.status_code, 200)
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [0.5, 1.0])

    def test_request_raises_after_retry_statuses_are_exhausted(self) -> None:
        with self.assertRaises(FundaRequestError):
            RetryTransport([403, 403]).request("GET", TEST_URL)

    def test_akamai_rejection_explains_ip_block(self) -> None:
        transport = RetryTransport([403])

        with patch.object(
            transport,
            "_send_once",
            return_value=FakeResponse(
                403,
                headers={"Server": "AkamaiGHost"},
                text="<title>Access Denied</title>",
            ),
        ), self.assertRaises(FundaRequestError) as ctx:
            transport.request("POST", "https://listing-search-wonen.funda.io/_msearch/template")

        self.assertIn("IP-based", str(ctx.exception))
        self.assertIn("rate or reputation block", str(ctx.exception))
        self.assertIn("retry after a cooldown", str(ctx.exception))

    def test_rate_limit_statuses_use_exponential_backoff(self) -> None:
        transport = _FundaTransport(retry_backoff=0.5)

        with patch("funda._transport.time.sleep") as sleep:
            for attempt in range(4):
                transport._sleep_backoff(attempt, status_code=403)

        self.assertEqual(
            [call.args[0] for call in sleep.call_args_list],
            [0.5, 1.0, 2.0, 4.0],
        )

    def test_pacing_can_be_disabled(self) -> None:
        transport = _FundaTransport(min_request_interval=0)

        with patch("funda._transport.time.monotonic") as monotonic, patch(
            "funda._transport.time.sleep"
        ) as sleep:
            transport._pace_request("https://listing-search-wonen.funda.io/first")

        monotonic.assert_not_called()
        sleep.assert_not_called()

    def test_pacing_is_shared_by_host_across_transports(self) -> None:
        first = _FundaTransport(min_request_interval=0.5)
        second = _FundaTransport(min_request_interval=0.5)
        type(first)._last_request_at.clear()

        with patch("funda._transport.time.monotonic", side_effect=[10.0, 10.1, 10.5]), patch(
            "funda._transport.time.sleep"
        ) as sleep:
            first._pace_request("https://listing-search-wonen.funda.io/first")
            second._pace_request("https://listing-detail-page.funda.io/second")

        sleep.assert_called_once()
        self.assertAlmostEqual(sleep.call_args.args[0], 0.4)
        self.assertEqual(set(type(first)._last_request_at), {"funda.io"})

    def test_client_defaults_to_half_second_pacing(self) -> None:
        from funda import Funda

        client = Funda()
        try:
            self.assertEqual(client.min_request_interval, 0.5)
            self.assertEqual(client.retry_backoff, 0.5)
        finally:
            client.close()

    def test_parallel_clients_preserve_request_interval(self) -> None:
        from funda import Funda

        client = Funda(min_request_interval=1.25)
        parallel = client._parallel_client()
        try:
            self.assertEqual(parallel.min_request_interval, 1.25)
            self.assertEqual(parallel._transport.min_request_interval, 1.25)
        finally:
            client.close()
            parallel.close()


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
