import unittest

from funda import Listing
from funda._enrichment_parser import (
    parse_broker_info,
    parse_broker_listings,
    parse_broker_reviews,
    parse_contact_form,
    parse_contact_info,
    parse_listing_summary,
    parse_market_insights,
    parse_similar_listings,
)


class EnrichmentParserTests(unittest.TestCase):
    def test_contact_info_hoists_primary_broker(self) -> None:
        parsed = parse_contact_info(
            {
                "id": "7988952",
                "tinyId": "43333315",
                "listingStatus": "Available",
                "contactBlockDetails": [
                    {
                        "id": 24716,
                        "displayName": "Example Makelaars",
                        "phoneNumber": "020-1234567",
                        "associationCode": "NVM",
                        "isContactingEnabled": True,
                    }
                ],
            }
        )

        self.assertEqual(parsed["broker_id"], 24716)
        self.assertEqual(parsed["name"], "Example Makelaars")
        self.assertEqual(parsed["phone"], "020-1234567")
        self.assertEqual(len(parsed["brokers"]), 1)

    def test_contact_form_hoists_primary_office(self) -> None:
        parsed = parse_contact_form(
            [
                {
                    "officeId": 24716,
                    "officeName": "Example Makelaars",
                    "days": ["Monday"],
                    "timesOfDay": ["Morning"],
                    "isContactingEnabled": True,
                }
            ]
        )

        self.assertEqual(parsed["office_id"], 24716)
        self.assertEqual(parsed["days"], ["Monday"])
        self.assertEqual(parsed["times_of_day"], ["Morning"])

    def test_listing_summary_returns_listing(self) -> None:
        parsed = parse_listing_summary(
            {
                "identifiers": {"globalId": 7985628, "tinyId": "43333315"},
                "address": {
                    "title": "Semarangstraat 13",
                    "city": "Amsterdam",
                    "postCode": "1095 GA",
                },
                "fastView": {"livingArea": 72, "numberOfBedrooms": 3, "energyLabel": "C"},
                "price": {"sellingPrice": "650000"},
                "media": {
                    "id": "photo-1",
                    "thumbnailBaseUrl": "https://cdn.example/{id}/{size}.jpg",
                },
                "brokers": [{"officeId": 24716, "name": "Example Makelaars"}],
                "urls": {"friendlyUrl": {"fullUrl": "https://www.funda.nl/detail/43333315/"}},
                "tracking": {
                    "values": {
                        "listing_askingprice": 650000,
                        "listing_type": "Apartment",
                        "listing_offering_type": "Sale",
                        "listing_status": "Available",
                    }
                },
            }
        )

        self.assertIsInstance(parsed, Listing)
        self.assertEqual(parsed.source, "summary")
        self.assertEqual(parsed.global_id, 7985628)
        self.assertEqual(parsed.title, "Semarangstraat 13")
        self.assertEqual(parsed.price.amount, 650000)
        self.assertEqual(parsed.living_area, 72)
        self.assertEqual(parsed.broker.id, "24716")

    def test_similar_market_and_broker_payloads(self) -> None:
        similar = parse_similar_listings(
            {
                "recentlyListed": [{"globalId": "1"}, {"globalId": None}, "bad"],
                "recentlySold": [{"globalId": 2}],
            }
        )
        insights = parse_market_insights(
            {
                "city": "Amsterdam",
                "neighbourhood": "Twiske-West",
                "inhabitants": 2510,
                "familiesWithChildren": 43.96,
                "averageAskingPricePerM2": 5975,
            }
        )
        info = parse_broker_info(
            {
                "officeId": {"officeNumber": 24716, "id": "uuid"},
                "displayName": "Example Makelaars",
                "contactDetails": {"email": "info@example.nl"},
            }
        )
        listings = parse_broker_listings(
            {
                "offering": [
                    {
                        "type": "Sold",
                        "listings": [
                            {
                                "listingId": 123,
                                "detailUrl": "/detail/koop/amsterdam/main-1/43333315/",
                                "location": {"address": {"street": "Main", "number": "1"}},
                            }
                        ],
                    }
                ]
            }
        )
        reviews = parse_broker_reviews(
            {"scores": {"average": 9.3}, "reviews": [{"score": {"average": 9}, "text": "Good"}]}
        )

        self.assertEqual(similar, {"recently_listed": [1], "recently_sold": [2]})
        self.assertEqual(insights["avg_asking_price_per_m2"], 5975)
        self.assertEqual(info["broker_id"], 24716)
        self.assertEqual(listings[0]["status"], "sold")
        self.assertEqual(listings[0]["tiny_id"], "43333315")
        self.assertEqual(reviews["reviews"][0]["average"], 9)


if __name__ == "__main__":
    unittest.main()
