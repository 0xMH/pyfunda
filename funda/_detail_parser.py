"""Parser for listing-detail API payloads."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from funda._parse_helpers import (
    as_str,
    coalesce,
    fallback_url,
    mapping,
    media_url,
    normalize_construction_type,
    normalize_object_type,
    normalize_offering_type,
    normalize_status,
    parse_area,
    parse_bool,
    parse_float,
    parse_int,
    parse_rooms,
)
from funda.listing import (
    Address,
    Areas,
    Broker,
    Characteristic,
    CharacteristicSection,
    GeoLocation,
    Insights,
    JsonDict,
    Label,
    Listing,
    Media,
    MediaItem,
    Price,
    Project,
    PropertyDetails,
    Rooms,
    SalesHistory,
    Urls,
)


def parse_listing(data: Mapping[str, Any]) -> Listing:
    """Parse the listing-detail API payload."""

    identifiers = mapping(data.get("Identifiers"))
    address_data = mapping(data.get("AddressDetails"))
    ads = mapping(mapping(data.get("Advertising")).get("TargetingOptions"))
    fast_view = mapping(data.get("FastView"))
    sections = _characteristic_sections(data.get("KenmerkSections"))
    values = _characteristic_values(sections)

    global_id = parse_int(coalesce(identifiers.get("GlobalId"), ads.get("globalid")))
    tiny_id = as_str(coalesce(identifiers.get("TinyId"), ads.get("tinyid")))
    offering_type = normalize_offering_type(data.get("OfferingType"))

    return Listing(
        listing_id=tiny_id or as_str(global_id),
        source="detail",
        global_id=global_id,
        tiny_id=tiny_id,
        offering_type=offering_type,
        address=_address(address_data, ads),
        price=_price(data, offering_type),
        areas=_areas(data, ads, fast_view, values),
        rooms=_rooms(ads, fast_view, values),
        property_details=_property_details(data, ads, fast_view, values),
        location=_location(data),
        urls=_urls(data, address_data, global_id, tiny_id, offering_type),
        media=_media(data.get("Media")),
        brokers=_brokers(data),
        labels=_labels(data.get("Labels")),
        description=mapping(data.get("ListingDescription")).get("Description"),
        description_title=mapping(data.get("ListingDescription")).get("Title"),
        highlight=_highlight(data),
        publication_date=data.get("PublicationDate"),
        characteristics=sections,
        sales_history=_sales_history(data.get("SalesHistory")),
        parent_project=_project(data.get("ParentProject")),
        insights=_insights(data.get("ObjectInsights")),
        raw=dict(data),
    )


def _address(address: Mapping[str, Any], ads: Mapping[str, Any]) -> Address:
    return Address(
        title=address.get("Title"),
        subtitle=address.get("SubTitle"),
        house_number=as_str(address.get("HouseNumber")),
        house_number_suffix=address.get("HouseNumberExtension") or None,
        postcode=address.get("PostCode"),
        city=address.get("City"),
        municipality=ads.get("gemeente"),
        neighbourhood=address.get("NeighborhoodName"),
        neighbourhood_identifier=address.get("NeighborhoodIdentifier"),
        province=address.get("Province"),
        country=address.get("Country"),
        is_international=address.get("IsInternational"),
        raw=dict(address),
    )


def _price(data: Mapping[str, Any], offering_type: str | None) -> Price:
    price = mapping(data.get("Price"))
    amount = coalesce(price.get("NumericSellingPrice"), price.get("NumericRentalPrice"))
    formatted = coalesce(price.get("SellingPrice"), price.get("RentalPrice"))
    return Price(
        amount=parse_int(amount),
        formatted=formatted,
        offering_type=offering_type,
        is_auction=bool(price.get("IsAuction")),
        raw=dict(price),
    )


def _areas(
    data: Mapping[str, Any],
    ads: Mapping[str, Any],
    fast_view: Mapping[str, Any],
    values: Mapping[str, Any],
) -> Areas:
    return Areas(
        living=coalesce(
            parse_int(ads.get("woonoppervlakte")),
            parse_area(values.get("Wonen")),
            parse_area(fast_view.get("LivingArea")),
        ),
        plot=coalesce(
            parse_int(ads.get("perceeloppervlakte")),
            parse_area(values.get("Perceel")),
            parse_area(fast_view.get("PlotArea")),
        ),
        other_indoor=parse_area(values.get("Overige inpandige ruimte")),
        building_bound_outdoor=parse_area(values.get("Gebouwgebonden buitenruimte")),
        external_storage=parse_area(values.get("Externe bergruimte")),
        volume=parse_area(values.get("Inhoud")),
        living_formatted=fast_view.get("LivingArea"),
        plot_formatted=fast_view.get("PlotArea"),
        raw={
            "fast_view": dict(fast_view),
            "advertising": dict(ads),
            "kenmerk_sections": data.get("KenmerkSections") or [],
        },
    )


def _rooms(
    ads: Mapping[str, Any],
    fast_view: Mapping[str, Any],
    values: Mapping[str, Any],
) -> Rooms:
    return Rooms(
        total=parse_int(ads.get("aantalkamers")) or parse_rooms(values.get("Aantal kamers")),
        bedrooms=parse_int(fast_view.get("NumberOfBedrooms")),
        bathrooms_description=values.get("Aantal badkamers"),
        floors_description=values.get("Aantal woonlagen"),
        located_on=values.get("Gelegen op"),
        raw={"fast_view": dict(fast_view), "advertising": dict(ads)},
    )


def _property_details(
    data: Mapping[str, Any],
    ads: Mapping[str, Any],
    fast_view: Mapping[str, Any],
    values: Mapping[str, Any],
) -> PropertyDetails:
    raw_status = coalesce(values.get("Status"), ads.get("status"))
    return PropertyDetails(
        object_type=normalize_object_type(data.get("ObjectType")),
        construction_type=normalize_construction_type(data.get("ConstructionType")),
        construction_year=parse_int(ads.get("bouwjaar")) or parse_int(values.get("Bouwjaar")),
        building_type=values.get("Soort bouw"),
        house_type=coalesce(ads.get("soortwoning"), values.get("Soort woonhuis"), values.get("Soort appartement")),
        energy_label=fast_view.get("EnergyLabel") or ads.get("energieklasse"),
        status=normalize_status(raw_status, data.get("OfferingType")),
        raw_object_type=data.get("ObjectType"),
        raw_construction_type=data.get("ConstructionType"),
        raw_offering_type=data.get("OfferingType"),
        raw_status=raw_status,
        features=_features(ads),
        raw={"detail": dict(data), "advertising": dict(ads)},
    )


def _location(data: Mapping[str, Any]) -> GeoLocation:
    coords = mapping(data.get("Coordinates"))
    return GeoLocation(
        latitude=parse_float(coords.get("Latitude")),
        longitude=parse_float(coords.get("Longitude")),
        google_maps_url=data.get("GoogleMapsObjectUrl"),
        raw=dict(coords),
    )


def _urls(
    data: Mapping[str, Any],
    address: Mapping[str, Any],
    global_id: int | None,
    tiny_id: str | None,
    offering_type: str | None,
) -> Urls:
    urls = mapping(data.get("Urls"))
    friendly = mapping(urls.get("FriendlyUrl"))
    path = friendly.get("RelativeUrl")
    full = friendly.get("FullUrl") or fallback_url(address, tiny_id or as_str(global_id), offering_type)
    return Urls(
        full=full,
        path=path,
        share=mapping(data.get("Share")).get("Url"),
        raw=dict(urls),
    )


def _media(media_value: Any) -> Media:
    media = mapping(media_value)
    brochure = mapping(media.get("Brochure"))
    return Media(
        photos=_media_items(media.get("Photos")),
        floorplans=_media_items(coalesce(media.get("FloorPlan"), media.get("LegacyFloorPlan"))),
        photos_360=_media_items(coalesce(media.get("Photos360"), media.get("LegacyPhotos360"))),
        videos=_media_items(media.get("Videos")),
        virtual_tours=_media_items(media.get("VirtualTour")),
        brochure_url=brochure.get("CdnUrl") or brochure.get("Url"),
        layout=dict(mapping(media.get("Layout"))),
        raw=dict(media),
    )


def _media_items(group_value: Any) -> tuple[MediaItem, ...]:
    group = mapping(group_value)
    parsed = []
    for item_value in group.get("Items") or []:
        item = mapping(item_value)
        item_id = as_str(item.get("Id"))
        thumbnail_id = as_str(item.get("ThumbnailId")) or item_id
        parsed.append(
            MediaItem(
                id=item_id,
                display_name=item.get("DisplayName"),
                url=media_url(group.get("MediaBaseUrl"), item_id),
                thumbnail_url=media_url(group.get("ThumbnailBaseUrl"), thumbnail_id),
                embed_url=item.get("EmbedUrl"),
                raw=dict(item),
            )
        )
    return tuple(parsed)


def _brokers(data: Mapping[str, Any]) -> tuple[Broker, ...]:
    values = mapping(mapping(data.get("Tracking")).get("Values"))
    brokers = tuple(
        Broker(
            id=as_str(coalesce(broker.get("broker_id"), broker.get("id"))),
            association=broker.get("broker_association") or broker.get("association"),
            is_primary=broker.get("is_primary"),
            raw=dict(broker),
        )
        for broker in values.get("brokers") or []
        if isinstance(broker, Mapping)
    )
    if brokers:
        return brokers
    broker_id = coalesce(values.get("main_broker_id"), values.get("broker_id"))
    if broker_id is None:
        return ()
    return (
        Broker(
            id=as_str(broker_id),
            association=values.get("main_broker_association") or values.get("broker_association"),
            is_primary=True,
            raw=dict(values),
        ),
    )


def _labels(labels: Any) -> tuple[Label, ...]:
    rows = labels if isinstance(labels, list) else []
    return tuple(
        Label(text=label.get("Text"), type=label.get("Type"), raw=dict(label))
        for label in rows
        if isinstance(label, Mapping)
    )


def _characteristic_sections(sections_value: Any) -> tuple[CharacteristicSection, ...]:
    sections = sections_value if isinstance(sections_value, list) else []
    return tuple(
        CharacteristicSection(
            title=section.get("Title"),
            items=_characteristics(section.get("KenmerkenList"), section.get("Title")),
            raw=dict(section),
        )
        for section in sections
        if isinstance(section, Mapping)
    )


def _characteristics(items_value: Any, section_title: str | None) -> tuple[Characteristic, ...]:
    items = items_value if isinstance(items_value, list) else []
    return tuple(
        Characteristic(
            section=section_title,
            id=item.get("Id"),
            label=item.get("Label"),
            value=item.get("Value"),
            label_style=item.get("LabelStyle"),
            children=_characteristics(item.get("KenmerkenList"), section_title),
            raw=dict(item),
        )
        for item in items
        if isinstance(item, Mapping)
    )


def _characteristic_values(sections: tuple[CharacteristicSection, ...]) -> JsonDict:
    values: JsonDict = {}
    for section in sections:
        for root in section.items:
            for item in root.walk():
                if item.label and item.value is not None:
                    values[item.label] = item.value
    return values


def _sales_history(sales_history_value: Any) -> SalesHistory | None:
    history = mapping(sales_history_value)
    if not history:
        return None
    rows = tuple(
        Characteristic(label=row.get("Label"), value=row.get("Value"), raw=dict(row))
        for row in history.get("Rows", [])
        if isinstance(row, Mapping)
    )
    return SalesHistory(title=history.get("Title"), rows=rows, raw=dict(history))


def _project(project_value: Any) -> Project | None:
    project = mapping(project_value)
    if not project:
        return None
    return Project(
        global_id=parse_int(project.get("GlobalId")),
        title=project.get("Title"),
        city=project.get("City"),
        type=project.get("Type"),
        url=project.get("Url"),
        raw=dict(project),
    )


def _insights(insights_value: Any) -> Insights | None:
    insights = mapping(insights_value)
    if not insights:
        return None
    return Insights(
        views=parse_int(insights.get("Views")),
        saves=parse_int(insights.get("Saves")),
        raw=dict(insights),
    )


def _features(ads: Mapping[str, Any]) -> JsonDict:
    names = {
        "tuin": "has_garden",
        "balkon": "has_balcony",
        "zonnepanelen": "has_solar_panels",
        "warmtepomp": "has_heat_pump",
        "dakterras": "has_roof_terrace",
        "parkeergelegenheidopeigenterrein": "has_parking_on_site",
        "parkeergelegenheidopafgeslotenterrein": "has_parking_enclosed",
        "openhuis": "has_open_house",
        "energiezuinig": "is_energy_efficient",
        "monumentalestatus": "is_monument",
        "rijksmonument": "is_national_monument",
        "kluswoning": "is_fixer_upper",
    }
    return {feature: parse_bool(ads.get(raw_name)) for raw_name, feature in names.items()}


def _highlight(data: Mapping[str, Any]) -> str | None:
    return mapping(mapping(data.get("Promo")).get("Blikvanger")).get("Text")
