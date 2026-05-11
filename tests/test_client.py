import unittest
from unittest.mock import patch

from funda import Funda, FundaRequestError, Listing, LocationSuggestion


class FakeResponse:
    def __init__(self, status_code: int, payload=None, text: str = "") -> None:
        self.status_code = status_code
        self.payload = payload
        self.text = text

    def json(self):
        return self.payload


class FakeTransport:
    def __init__(self, *responses: FakeResponse) -> None:
        self.responses = list(responses)
        self.get_urls: list[str] = []
        self.posts: list[tuple[str, str | None, object | None]] = []

    def get(self, url: str, *, profile: str = "listing"):
        self.get_urls.append(url)
        return self.responses.pop(0)

    def post(self, url: str, *, profile: str = "listing", data=None, json_data=None):
        self.posts.append((url, data, json_data))
        return self.responses.pop(0)

    def close(self) -> None:
        pass


class FundaClientTests(unittest.TestCase):
    def client(self, *responses: FakeResponse) -> Funda:
        client = Funda()
        client._transport = FakeTransport(*responses)
        return client

    def test_listing_accepts_ids_and_funda_urls(self) -> None:
        client = Funda()

        self.assertEqual(client._listing_id_from_input(43117443), "43117443")
        self.assertEqual(client._listing_id_from_input("7762080"), "7762080")
        self.assertEqual(
            client._listing_id_from_input(
                "https://www.funda.nl/detail/koop/amsterdam/house/43117443/"
            ),
            "43117443",
        )
        self.assertEqual(
            client._listing_id_from_input("https://www.funda.nl/koop/amsterdam/huis-43117443/"),
            "43117443",
        )

    def test_listing_uses_tiny_url_then_global_fallback(self) -> None:
        client = self.client(FakeResponse(404), FakeResponse(200, {"id": 1}))
        expected = Listing(global_id=7762080, tiny_id="43117443")

        with patch("funda.funda.parse_listing", return_value=expected):
            listing = client.listing(43117443)

        self.assertIs(listing, expected)
        self.assertIn("/tinyId/43117443", client._transport.get_urls[0])
        self.assertTrue(client._transport.get_urls[1].endswith("/43117443"))

    def test_listing_distinguishes_missing_from_rejected(self) -> None:
        with self.assertRaises(LookupError):
            self.client(FakeResponse(404), FakeResponse(404)).listing(43117443)

        with self.assertRaises(FundaRequestError):
            self.client(FakeResponse(403)).listing(43117443)

    def test_search_posts_payload_and_parses_results(self) -> None:
        client = self.client(FakeResponse(200, {"responses": []}))
        expected = [Listing(global_id=1)]

        with patch("funda.funda.parse_search_results", return_value=expected):
            results = client.search("amsterdam", max_price=500000)

        self.assertEqual(results, expected)
        url, payload, json_data = client._transport.posts[0]
        self.assertIn("_msearch/template", url)
        self.assertIsNone(json_data)
        self.assertIn("search_result_", payload)

    def test_autocomplete_posts_json_payload_and_parses_results(self) -> None:
        client = self.client(FakeResponse(200, {"hits": {"hits": []}}))
        expected = [LocationSuggestion(id="amsterdam/wijk-slotermeer-west-0")]

        with patch("funda.funda.parse_location_suggestions", return_value=expected):
            results = client.autocomplete(
                "amsterdam west",
                size=5,
                area_types=["city", "municipality", "neighborhood", "wijk"],
            )

        self.assertEqual(results, expected)
        url, payload, json_data = client._transport.posts[0]
        self.assertIn("geo-wonen-alias-prod/_search/template", url)
        self.assertIsNone(payload)
        self.assertEqual(json_data["id"], "searchbox_20250805")
        self.assertEqual(json_data["params"]["value"], "amsterdam west")
        self.assertEqual(json_data["params"]["size"], 5)
        self.assertEqual(
            json_data["params"]["area_types"],
            ["city", "municipality", "neighborhood", "wijk"],
        )

    def test_enrichment_methods_share_json_error_handling(self) -> None:
        client = self.client(
            FakeResponse(200, {"contactBlockDetails": [{"id": 24716, "displayName": "Broker"}]}),
            FakeResponse(200, []),
            FakeResponse(500, {}),
        )

        self.assertEqual(client.contact_info(Listing(global_id=7988952))["name"], "Broker")
        with self.assertRaises(LookupError):
            client.contact_form(7988952)
        with self.assertRaises(FundaRequestError):
            client.broker_info(24716)

    def test_resolvers_accept_listing_or_numeric_input(self) -> None:
        listing = Listing(global_id=7988952)
        client = Funda()

        self.assertEqual(client._resolve_global_id(listing), 7988952)
        self.assertEqual(client._resolve_global_id(7988952), 7988952)

    def test_market_insights_slugs_city_and_neighbourhood(self) -> None:
        client = self.client(
            FakeResponse(
                200,
                {
                    "city": "Den Haag",
                    "neighbourhood": "Centrum Noord",
                    "averageAskingPricePerM2": 5975,
                },
            )
        )

        insights = client.market_insights("Den Haag", "Centrum Noord")

        self.assertEqual(insights["avg_asking_price_per_m2"], 5975)
        self.assertIn("/den-haag/centrum-noord", client._transport.get_urls[0])


if __name__ == "__main__":
    unittest.main()
