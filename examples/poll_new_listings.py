"""Poll for new listings by incrementing IDs.

This bypasses Funda's ES search index which can lag behind by hours.
"""

import json
from pathlib import Path

from funda import Funda


STATE_FILE = Path("last_seen_id.json")


def load_last_id() -> int | None:
    """Load the last seen ID from state file."""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text()).get("last_id")
    return None


def save_last_id(last_id: int) -> None:
    """Save the last seen ID to state file."""
    STATE_FILE.write_text(json.dumps({"last_id": last_id}))


def main():
    f = Funda()

    # Get starting point
    last_id = load_last_id()
    if last_id is None:
        # First run: get latest from ES
        last_id = f.get_latest_id()
        print(f"First run, starting from ES latest: {last_id}")
    else:
        print(f"Resuming from saved ID: {last_id}")

    # Poll for new listings
    max_id = last_id
    count = 0

    for listing in f.poll_new_listings(since_id=last_id):
        count += 1
        gid = listing["global_id"]
        max_id = max(max_id, gid)

        print(f"New: {listing['title']}, {listing['city']}")
        print(f"     €{listing['price']:,} - {listing.get('living_area', '?')} m²")
        print(f"     {listing['url']}")
        print()

    # Save state for next run
    if count > 0:
        save_last_id(max_id)
        print(f"Found {count} new listings. Saved last ID: {max_id}")
    else:
        print("No new listings found.")


if __name__ == "__main__":
    main()
