import unittest

from funda import (
    Address,
    Characteristic,
    CharacteristicSection,
    Listing,
    Price,
    SalesHistory,
)


class ListingModelTests(unittest.TestCase):
    def test_listing_properties_are_pythonic_attributes(self) -> None:
        listing = Listing(
            global_id=7762080,
            tiny_id="43117443",
            address=Address(title="Reehorst 13", city="Luttenberg", postcode="8105 SZ"),
            price=Price(amount=695000, formatted="695.000 k.k."),
        )

        self.assertEqual(listing.id, "43117443")
        self.assertEqual(listing.title, "Reehorst 13")
        self.assertEqual(listing.city, "Luttenberg")
        self.assertEqual(listing.postcode, "8105 SZ")
        self.assertEqual(listing.price.amount, 695000)
        self.assertIn("Reehorst 13", repr(listing))

    def test_to_dict_drops_raw_by_default(self) -> None:
        listing = Listing(raw={"raw": True}, address=Address(raw={"raw": True}))

        data = listing.to_dict()
        self.assertNotIn("raw", data)
        self.assertNotIn("raw", data["address"])

        raw_data = listing.to_dict(include_raw=True)
        self.assertIn("raw", raw_data)
        self.assertIn("raw", raw_data["address"])

    def test_sales_history_exposes_common_rows(self) -> None:
        history = SalesHistory(
            rows=(
                Characteristic(label="Verkoopdatum", value="10 mei 2026"),
                Characteristic(label="Looptijd", value="3 maanden"),
            )
        )

        self.assertEqual(history.sale_date, "10 mei 2026")
        self.assertEqual(history.time_on_market, "3 maanden")

    def test_characteristic_lookup_walks_nested_items(self) -> None:
        listing = Listing(
            characteristics=(
                CharacteristicSection(
                    items=(
                        Characteristic(
                            label="Buitenruimte",
                            children=(Characteristic(label="Tuin", value="Achtertuin"),),
                        ),
                    )
                ),
            )
        )

        self.assertEqual(listing.characteristic("tuin"), "Achtertuin")


if __name__ == "__main__":
    unittest.main()
