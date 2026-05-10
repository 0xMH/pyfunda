import os
import unittest

from funda import Funda


@unittest.skipUnless(os.environ.get("PYFUNDA_LIVE") == "1", "set PYFUNDA_LIVE=1")
class LiveFundaSmokeTests(unittest.TestCase):
    def test_core_listing_search_and_parallel_paths(self) -> None:
        with Funda(timeout=30) as client:
            listing = client.listing(43117443)
            results = client.search("amsterdam", max_price=500000)
            ids = [item.global_id for item in results[:4] if item.global_id]
            details = client.listings(ids, workers=4)
            pages = list(
                client.iter_search(
                    "amsterdam",
                    max_price=500000,
                    max_pages=2,
                    workers=2,
                )
            )

        self.assertEqual(listing.global_id, 7762080)
        self.assertEqual(len(results), 15)
        self.assertEqual([item.global_id for item in details], ids)
        self.assertEqual(len(pages), 30)

    def test_enrichment_endpoints(self) -> None:
        with Funda(timeout=30) as client:
            listing = client.listing(43117443)
            summary = client.listing_summary(listing)
            similar = client.similar_listings(listing)
            contact = client.contact_info(listing)
            form = client.contact_form(listing)
            market = client.market_insights(listing)
            broker = client.broker_info(listing)
            broker_listings = client.broker_listings(listing)
            broker_reviews = client.broker_reviews(listing)

        self.assertEqual(summary.global_id, listing.global_id)
        self.assertIn("recently_sold", similar)
        self.assertEqual(contact["broker_id"], 16122)
        self.assertEqual(form["office_id"], 16122)
        self.assertIn("avg_asking_price_per_m2", market)
        self.assertEqual(broker["broker_id"], 16122)
        self.assertGreater(len(broker_listings), 0)
        self.assertGreater(broker_reviews["number_of_reviews"], 0)


if __name__ == "__main__":
    unittest.main()
