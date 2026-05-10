"""Parser for listing-search API payloads."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from funda._parse_helpers import (
    as_str,
    coalesce,
    first,
    mapping,
    normalize_construction_type,
    normalize_object_type,
    normalize_offering_type,
    normalize_status,
    parse_int,
    search_title,
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
    Project,
    PropertyDetails,
    Rooms,
    Urls,
)


def parse_search_results(data: Mapping[str, Any]) -> list[Listing]:
    responses = data.get("responses") or []
    if not responses:
        return []
    hits = mapping(mapping(responses[0]).get("hits")).get("hits") or []
    return [_hit(hit) for hit in hits if isinstance(hit, Mapping)]


def _hit(hit: Mapping[str, Any]) -> Listing:
    source = mapping(hit.get("_source"))
    address_data = mapping(source.get("address"))
    global_id = parse_int(coalesce(hit.get("_id"), source.get("id")))
    path = source.get("object_detail_page_relative_url")
    tiny_id = tiny_id_from_url(path)
    offering_type = normalize_offering_type(first(source.get("offering_type")))

    return Listing(
        listing_id=tiny_id or as_str(global_id),
        source="search",
        global_id=global_id,
        tiny_id=tiny_id,
        offering_type=offering_type,
        address=_address(address_data),
        price=_price(source, offering_type),
        areas=_areas(source),
        rooms=_rooms(source),
        property_details=_property_details(source),
        urls=Urls(full=f"https://www.funda.nl{path}" if path else None, path=path),
        media=_media(source),
        brokers=_brokers(source.get("agent")),
        highlight=mapping(source.get("blikvanger")).get("text"),
        publication_date=source.get("publish_date"),
        parent_project=_project(source.get("project")),
        raw=dict(hit),
    )


def _address(address: Mapping[str, Any]) -> Address:
    return Address(
        title=search_title(address),
        street_name=address.get("street_name"),
        house_number=as_str(address.get("house_number")),
        house_number_suffix=address.get("house_number_suffix") or None,
        postcode=address.get("postal_code"),
        city=address.get("city"),
        municipality=address.get("municipality"),
        neighbourhood=address.get("neighbourhood"),
        province=address.get("province"),
        country=address.get("country"),
        is_bag_address=address.get("is_bag_address"),
        identifiers=tuple(str(identifier) for identifier in address.get("identifiers", []) if identifier is not None),
        raw=dict(address),
    )


def _price(source: Mapping[str, Any], offering_type: str | None) -> Price:
    price = mapping(source.get("price"))
    sale_amount = first(price.get("selling_price"))
    rent_amount = first(price.get("rent_price"))
    sale_range = mapping(price.get("selling_price_range"))
    rent_range = mapping(price.get("rent_price_range"))
    range_data = sale_range or rent_range
    return Price(
        amount=parse_int(coalesce(sale_amount, rent_amount)),
        offering_type=offering_type,
        condition=price.get("selling_price_condition") or price.get("rent_price_condition"),
        price_type=price.get("selling_price_type") or price.get("rent_price_type"),
        range_min=parse_int(range_data.get("gte")),
        range_max=parse_int(range_data.get("lte")),
        raw=dict(price),
    )


def _areas(source: Mapping[str, Any]) -> Areas:
    floor_range = mapping(source.get("floor_area_range"))
    plot_range = mapping(source.get("plot_area_range"))
    return Areas(
        living=parse_int(first(source.get("floor_area"))),
        plot=parse_int(first(source.get("plot_area"))),
        living_range_min=parse_int(floor_range.get("gte")),
        living_range_max=parse_int(floor_range.get("lte")),
        plot_range_min=parse_int(plot_range.get("gte")),
        plot_range_max=parse_int(plot_range.get("lte")),
        raw={
            "floor_area": source.get("floor_area"),
            "floor_area_range": dict(floor_range),
            "plot_area": source.get("plot_area"),
            "plot_area_range": dict(plot_range),
        },
    )


def _rooms(source: Mapping[str, Any]) -> Rooms:
    return Rooms(
        total=parse_int(source.get("number_of_rooms")),
        bedrooms=parse_int(source.get("number_of_bedrooms")),
        raw={
            "number_of_rooms": source.get("number_of_rooms"),
            "number_of_bedrooms": source.get("number_of_bedrooms"),
        },
    )


def _property_details(source: Mapping[str, Any]) -> PropertyDetails:
    raw_status = source.get("status")
    raw_offering_type = first(source.get("offering_type"))
    return PropertyDetails(
        object_type=normalize_object_type(source.get("object_type")),
        construction_type=normalize_construction_type(source.get("construction_type")),
        energy_label=source.get("energy_label"),
        status=normalize_status(raw_status, raw_offering_type),
        raw_object_type=source.get("object_type"),
        raw_construction_type=source.get("construction_type"),
        raw_offering_type=raw_offering_type,
        raw_status=raw_status,
        raw=dict(source),
    )


def _media(source: Mapping[str, Any]) -> Media:
    photos = tuple(MediaItem(id=as_str(photo_id)) for photo_id in source.get("thumbnail_id", []) if photo_id)
    return Media(
        photos=photos,
        available_types=tuple(source.get("available_media_types") or ()),
        raw={
            "thumbnail_id": source.get("thumbnail_id"),
            "available_media_types": source.get("available_media_types"),
        },
    )


def _brokers(agent_value: Any) -> tuple[Broker, ...]:
    agents = agent_value if isinstance(agent_value, list) else []
    return tuple(
        Broker(
            id=as_str(agent.get("id")),
            office_id=as_str(agent.get("office_id")),
            name=agent.get("name"),
            association=agent.get("association"),
            relative_url=agent.get("relative_url"),
            logo_id=as_str(agent.get("logo_id")),
            is_primary=agent.get("is_primary"),
            raw=dict(agent),
        )
        for agent in agents
        if isinstance(agent, Mapping)
    )


def _project(project_value: Any) -> Project | None:
    project = mapping(project_value)
    if not project:
        return None
    return Project(
        global_id=parse_int(project.get("id")),
        tiny_id=as_str(project.get("tiny_id")),
        title=project.get("name"),
        type=project.get("type"),
        status=project.get("status"),
        url=project.get("url"),
        price=_price(project, first(project.get("offering_type"))) if project.get("price") else None,
        address=_address(mapping(project.get("address"))) if project.get("address") else None,
        raw=dict(project),
    )
