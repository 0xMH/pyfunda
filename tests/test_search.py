import json
import unittest

from funda.search import _Search


class SearchTests(unittest.TestCase):
    def test_buy_search_builds_expected_filters(self) -> None:
        params = _Search.from_filters(
            "amsterdam",
            min_price=200000,
            max_price=500000,
            min_area=50,
            min_bedrooms=2,
            sort="newest",
        ).to_params()

        self.assertEqual(params["selected_area"], ["amsterdam"])
        self.assertEqual(params["price"]["selling_price"], {"from": 200000, "to": 500000})
        self.assertEqual(params["floor_area"], {"from": 50})
        self.assertEqual(params["bedrooms"], {"from": 2})
        self.assertEqual(params["sort"], {"field": "publish_date_utc", "order": "desc"})

    def test_rent_and_sold_categories_map_to_funda_payload(self) -> None:
        rent = _Search.from_filters("amsterdam", category="rent", max_price=2500).to_params()
        sold = _Search.from_filters("amsterdam", category="sold").to_params()

        self.assertEqual(rent["offering_type"], "rent")
        self.assertEqual(rent["price"]["rent_price"], {"to": 2500})
        self.assertEqual(sold["offering_type"], "buy")
        self.assertEqual(sold["availability"], ["unavailable"])

    def test_radius_search_uses_nearest_indexed_radius(self) -> None:
        params = _Search.from_filters("haarlem", radius_km=7).to_params()

        self.assertEqual(params["radius_search"]["id"], "haarlem-0")
        self.assertEqual(params["radius_search"]["path"], "area_with_radius.5")

    def test_construction_year_maps_to_overlapping_periods(self) -> None:
        params = _Search.from_filters(
            "amsterdam",
            min_construction_year=1995,
            max_construction_year=2005,
        ).to_params()

        self.assertEqual(
            params["construction_period"],
            ["from_1991_to_2000", "from_2001_to_2010"],
        )

    def test_invalid_filters_fail_before_network(self) -> None:
        with self.assertRaises(TypeError):
            _Search.from_filters("amsterdam", does_not_exist=True)
        with self.assertRaises(ValueError):
            _Search.from_filters("amsterdam", min_price=10, max_price=1)
        with self.assertRaises(ValueError):
            _Search.from_filters(["amsterdam", "haarlem"], radius_km=5).to_params()
        with self.assertRaises(ValueError):
            _Search.from_filters("amsterdam", category="lease").to_params()
        with self.assertRaises(ValueError):
            _Search.from_filters("amsterdam", sort="popular").to_params()

    def test_search_payload_is_ndjson_template_request(self) -> None:
        payload = _Search.from_filters("amsterdam").to_payload()
        lines = payload.splitlines()

        self.assertEqual(len(lines), 2)
        self.assertIn("listings-wonen-searcher", json.loads(lines[0])["index"])
        self.assertIn("search_result_", json.loads(lines[1])["id"])


if __name__ == "__main__":
    unittest.main()
