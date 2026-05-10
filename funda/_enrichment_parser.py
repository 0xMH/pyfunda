"""Parsers for auxiliary Funda endpoint payloads."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any

from funda._parse_helpers import (
    as_str,
    coalesce,
    mapping,
    normalize_object_type,
    normalize_offering_type,
    normalize_status,
    parse_area,
    parse_int,
    tiny_id_from_url,
)
from funda.listing import (
    Address,
    Areas,
    Broker,
    Listing,
    Media,
    MediaItem,
    Price,
    PropertyDetails,
    Rooms,
    Urls,
)
from funda.models import JsonDict


def parse_contact_info(data: Mapping[str, Any]) -> JsonDict:
    """Normalize the contact-block payload into a flat dict."""
    brokers = [_contact_broker(broker) for broker in _mapping_rows(data.get("contactBlockDetails"))]

    result: JsonDict = {
        "listing_id": data.get("id"),
        "tiny_id": data.get("tinyId"),
        "listing_status": data.get("listingStatus"),
        "is_viewing_planner_enabled": data.get("isViewingPlannerEnabled"),
        "brokers": brokers,
    }

    if brokers:
        primary = brokers[0]
        result.update(
            {
                "broker_id": primary["broker_id"],
                "name": primary["name"],
                "phone": primary["phone"],
                "association": primary["association"],
                "logo_url": primary["logo_url"],
                "banner_url": primary["banner_url"],
                "is_contacting_enabled": primary["is_contacting_enabled"],
                "personal_contact_info": primary["personal_contact_info"],
            }
        )

    return result


def parse_contact_form(data: Any) -> JsonDict:
    """Normalize contact-form availability entries."""
    offices = data if isinstance(data, list) else []
    primary = mapping(offices[0]) if offices else {}

    return {
        "office_id": primary.get("officeId"),
        "office_name": primary.get("officeName"),
        "is_contacting_enabled": primary.get("isContactingEnabled"),
        "is_viewing_planner_enabled": primary.get("isViewingPlannerEnabled"),
        "days": primary.get("days", []),
        "times_of_day": primary.get("timesOfDay", []),
        "offices": offices,
    }


def parse_listing_summary(data: Mapping[str, Any]) -> Listing:
    """Parse the lightweight listing-detail-summary payload."""
    identifiers = mapping(data.get("identifiers"))
    address = mapping(data.get("address"))
    fast_view = mapping(data.get("fastView"))
    price = mapping(data.get("price"))
    media = mapping(data.get("media"))
    urls = mapping(mapping(data.get("urls")).get("friendlyUrl"))
    promo = mapping(mapping(data.get("promo")).get("blikvanger"))
    tracking = mapping(mapping(data.get("tracking")).get("values"))
    brokers = data.get("brokers") if isinstance(data.get("brokers"), list) else []
    offering_type = normalize_offering_type(tracking.get("listing_offering_type"))

    photo_id = as_str(media.get("id"))
    thumbnail_url = _thumbnail_url(media.get("thumbnailBaseUrl"), photo_id)
    photo = (
        MediaItem(id=photo_id, url=thumbnail_url, thumbnail_url=thumbnail_url, raw=dict(media))
        if photo_id or thumbnail_url
        else None
    )

    parsed_brokers = tuple(_summary_broker(broker) for broker in _mapping_rows(brokers))

    return Listing(
        listing_id=as_str(coalesce(identifiers.get("tinyId"), identifiers.get("globalId"))),
        source="summary",
        global_id=parse_int(identifiers.get("globalId")),
        tiny_id=as_str(identifiers.get("tinyId")),
        offering_type=offering_type,
        address=Address(
            title=address.get("title"),
            subtitle=address.get("subTitle"),
            city=address.get("city"),
            postcode=address.get("postCode"),
            raw=dict(address),
        ),
        price=Price(
            amount=parse_int(
                coalesce(tracking.get("listing_askingprice"), price.get("numericSellingPrice"))
            ),
            formatted=coalesce(price.get("sellingPrice"), price.get("rentalPrice")),
            offering_type=offering_type,
            raw=dict(price),
        ),
        areas=Areas(
            living=parse_area(fast_view.get("livingArea")),
            plot=parse_area(fast_view.get("plotArea")),
            living_formatted=fast_view.get("livingArea"),
            plot_formatted=fast_view.get("plotArea"),
            raw=dict(fast_view),
        ),
        rooms=Rooms(bedrooms=parse_int(fast_view.get("numberOfBedrooms")), raw=dict(fast_view)),
        property_details=PropertyDetails(
            object_type=normalize_object_type(tracking.get("listing_type")),
            energy_label=fast_view.get("energyLabel"),
            status=normalize_status(tracking.get("listing_status"), offering_type),
            raw_object_type=tracking.get("listing_type"),
            raw_offering_type=tracking.get("listing_offering_type"),
            raw_status=tracking.get("listing_status"),
            raw=dict(tracking),
        ),
        urls=Urls(
            full=urls.get("fullUrl"),
            share=mapping(data.get("share")).get("url"),
            raw=dict(urls),
        ),
        media=Media(photos=(photo,) if photo else (), raw=dict(media)),
        brokers=parsed_brokers,
        highlight=promo.get("text"),
        publication_date=data.get("publicationDate"),
        raw=dict(data),
    )


def parse_similar_listings(data: Mapping[str, Any]) -> JsonDict:
    """Parse similar-listing response into globalId lists."""
    return {
        "recently_listed": _global_ids(data.get("recentlyListed")),
        "recently_sold": _global_ids(data.get("recentlySold")),
    }


def parse_market_insights(data: Mapping[str, Any]) -> JsonDict:
    """Normalize local market insight fields."""
    return {
        "city": data.get("city"),
        "neighbourhood": data.get("neighbourhood"),
        "inhabitants": data.get("inhabitants"),
        "families_with_children_pct": data.get("familiesWithChildren"),
        "avg_asking_price_per_m2": data.get("averageAskingPricePerM2"),
    }


def parse_broker_info(data: Mapping[str, Any]) -> JsonDict:
    """Normalize the broker office-page payload."""
    office = mapping(data.get("officeId"))
    description = mapping(data.get("description"))
    contact = mapping(data.get("contactDetails"))
    address = mapping(contact.get("address"))
    media = mapping(data.get("mediaReferences"))
    characteristics = mapping(data.get("characteristics"))

    return {
        "broker_id": office.get("officeNumber"),
        "uuid": office.get("id"),
        "name": data.get("displayName"),
        "affiliation": data.get("affiliation"),
        "slogan": description.get("slogan"),
        "description": description.get("description"),
        "short_description": description.get("shortDescription"),
        "email": contact.get("email"),
        "website": contact.get("websiteUrl"),
        "phone": contact.get("phoneNumber"),
        "address": {
            "street": address.get("street"),
            "number": address.get("number"),
            "addition": address.get("addition"),
            "postcode": address.get("postcode"),
            "city": address.get("location"),
        },
        "logo_urls": media.get("logoImages") or None,
        "languages": characteristics.get("languages", []),
        "services": characteristics.get("services", []),
        "certificates": characteristics.get("certificates", []),
    }


def parse_broker_listings(data: Mapping[str, Any]) -> list[JsonDict]:
    """Flatten broker listings into a list tagged by status."""
    status_map = {
        "Sold": "sold",
        "ForSale": "for_sale",
        "Purchased": "purchased",
    }
    out: list[JsonDict] = []

    for group in _mapping_rows(data.get("offering")):
        api_status = as_str(group.get("type"))
        status = status_map.get(api_status or "", api_status.lower() if api_status else None)

        for item in _mapping_rows(group.get("listings")):
            location = mapping(item.get("location"))
            address = mapping(location.get("address"))
            detail_url = as_str(item.get("detailUrl")) or ""
            out.append(
                {
                    "status": status,
                    "listing_id": item.get("listingId"),
                    "tiny_id": tiny_id_from_url(detail_url),
                    "title": _address_title(address),
                    "street": address.get("street"),
                    "house_number": address.get("number"),
                    "house_number_ext": address.get("addition") or None,
                    "postcode": address.get("postcode"),
                    "city": address.get("city"),
                    "latitude": location.get("latitude"),
                    "longitude": location.get("longitude"),
                    "price": item.get("price"),
                    "price_formatted": item.get("formattedPrice"),
                    "price_type": item.get("priceType"),
                    "price_condition": item.get("priceCondition"),
                    "publication_date": item.get("publicationDate"),
                    "transaction_date": item.get("transactionDate"),
                    "image_url": item.get("image"),
                    "detail_url": _absolute_funda_url(detail_url),
                }
            )

    return out


def parse_broker_reviews(data: Mapping[str, Any]) -> JsonDict:
    """Normalize broker review aggregate and review items."""
    scores = mapping(data.get("scores"))
    reviews = [_review(review) for review in _mapping_rows(data.get("reviews"))]

    highlighted = data.get("highlightedReview")
    return {
        "average": scores.get("average"),
        "number_of_reviews": scores.get("numberOfReviews"),
        "selectivity_percentage": scores.get("selectivityPercentage"),
        "highlight": _review(highlighted) if isinstance(highlighted, Mapping) else None,
        "reviews": reviews,
    }


def _thumbnail_url(template: Any, photo_id: str | None) -> str | None:
    if not template or not photo_id:
        return None
    return str(template).replace("{id}", photo_id).replace("{size}", "720x480")


def _global_ids(value: Any) -> list[int]:
    ids = []
    for row in _mapping_rows(value):
        global_id = parse_int(row.get("globalId"))
        if global_id is not None:
            ids.append(global_id)
    return ids


def _address_title(address: Mapping[str, Any]) -> str | None:
    street = address.get("street") or ""
    number = as_str(address.get("number")) or ""
    addition = as_str(address.get("addition"))
    title = f"{street} {number}".strip()
    if addition:
        title = f"{title}-{addition}" if number else f"{title} {addition}".strip()
    return title or None


def _absolute_funda_url(url: str) -> str | None:
    if not url:
        return None
    return f"https://www.funda.nl{url}" if url.startswith("/") else url


def _review(review_value: Mapping[str, Any]) -> JsonDict:
    review = mapping(review_value)
    score = mapping(review.get("score"))
    return {
        "date": review.get("postedDate"),
        "transaction_type": review.get("transactionType"),
        "text": review.get("text"),
        "average": score.get("average"),
        "expertise": score.get("expertise"),
        "local_market_knowledge": score.get("localMarketKnowledge"),
        "price_and_quality": score.get("priceAndQuality"),
        "service_and_guidance": score.get("serviceAndGuidance"),
    }


def _mapping_rows(value: Any) -> Iterator[Mapping[str, Any]]:
    rows = value if isinstance(value, list) else []
    for row in rows:
        if isinstance(row, Mapping):
            yield mapping(row)


def _contact_broker(broker: Mapping[str, Any]) -> JsonDict:
    return {
        "broker_id": broker.get("id"),
        "name": broker.get("displayName"),
        "phone": broker.get("phoneNumber"),
        "association": broker.get("associationCode"),
        "logo_url": broker.get("logoUrl") or None,
        "banner_url": broker.get("bannerUrl"),
        "is_contacting_enabled": broker.get("isContactingEnabled"),
        "personal_contact_info": broker.get("personalContactBlockInfo"),
    }


def _summary_broker(broker: Mapping[str, Any]) -> Broker:
    return Broker(
        id=as_str(broker.get("officeId")),
        office_id=as_str(broker.get("officeId")),
        name=broker.get("name"),
        raw=dict(broker),
    )
