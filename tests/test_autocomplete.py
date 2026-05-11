import unittest

from funda._autocomplete import LocationAutocomplete
from funda.constants import (
    LOCATION_AUTOCOMPLETE_AREA_TYPES,
    LOCATION_AUTOCOMPLETE_TEMPLATE_ID,
)
from funda.parsing import parse_location_suggestions


AUTOCOMPLETE_RESPONSE = {
    "hits": {
        "hits": [
            {
                "_id": "almere/wijk-overig-almere-poort-0",
                "_score": 14019.095,
                "_source": {
                    "parent_areas": [
                        {
                            "name": "Almere",
                            "geo_identifier": "gemeente-almere",
                            "area_type": "municipality",
                        }
                    ],
                    "parent": {
                        "name": "Almere",
                        "geo_identifier": "gemeente-almere",
                        "area_type": "municipality",
                    },
                    "synonyms": [
                        "Overig Almere Poort",
                        "Wijk Overig Almere Poort",
                    ],
                    "centroid": "52.35011243088991,5.15976276416359",
                    "name": "Overig Almere Poort",
                    "id": "almere/wijk-overig-almere-poort-0",
                    "geo_identifier": "almere/wijk-overig-almere-poort",
                    "area_type": "wijk",
                },
            }
        ]
    }
}


class AutocompleteTests(unittest.TestCase):
    def test_payload_matches_funda_searchbox_template(self) -> None:
        payload = LocationAutocomplete("almere poor").to_payload()

        self.assertEqual(payload["id"], LOCATION_AUTOCOMPLETE_TEMPLATE_ID)
        self.assertEqual(payload["params"]["value"], "almere poor")
        self.assertEqual(payload["params"]["timeout"], "3s")
        self.assertEqual(payload["params"]["size"], 10)
        self.assertFalse(payload["params"]["use_sort"])
        self.assertEqual(payload["params"]["sort"], [])
        self.assertEqual(payload["params"]["exclude"], [])
        self.assertEqual(
            payload["params"]["area_types"],
            list(LOCATION_AUTOCOMPLETE_AREA_TYPES),
        )

    def test_payload_can_limit_area_types_for_vague_area_searches(self) -> None:
        payload = LocationAutocomplete(
            "amsterdam west",
            area_types=("city", "municipality", "neighborhood", "wijk"),
            size=5,
        ).to_payload()

        self.assertEqual(payload["params"]["size"], 5)
        self.assertEqual(
            payload["params"]["area_types"],
            ["city", "municipality", "neighborhood", "wijk"],
        )

    def test_invalid_payload_values_fail_before_network(self) -> None:
        with self.assertRaises(ValueError):
            LocationAutocomplete("").to_payload()
        with self.assertRaises(ValueError):
            LocationAutocomplete("amsterdam", size=0).to_payload()

    def test_parse_location_suggestions_maps_geo_hits(self) -> None:
        suggestions = parse_location_suggestions(AUTOCOMPLETE_RESPONSE)

        self.assertEqual(len(suggestions), 1)
        suggestion = suggestions[0]
        self.assertEqual(suggestion.id, "almere/wijk-overig-almere-poort-0")
        self.assertEqual(suggestion.name, "Overig Almere Poort")
        self.assertEqual(suggestion.area_type, "wijk")
        self.assertEqual(suggestion.parent.name, "Almere")
        self.assertEqual(suggestion.parent_areas[0].area_type, "municipality")
        self.assertEqual(suggestion.synonyms[1], "Wijk Overig Almere Poort")
        self.assertEqual(suggestion.location.latitude, 52.35011243088991)
        self.assertEqual(suggestion.location.longitude, 5.15976276416359)
        self.assertEqual(suggestion.score, 14019.095)
        self.assertEqual(suggestion.label, "Overig Almere Poort, Almere")


if __name__ == "__main__":
    unittest.main()
