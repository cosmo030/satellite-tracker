"""HTTP routes for the catalog: groups, satellite search and details, element sets."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, Response, status

from sattrack.catalog.domain import ImageWidth, OrbitClass, SatelliteFilters
from sattrack.catalog.repository import CatalogRepository
from sattrack.catalog.schemas import (
    AboutOut,
    ElementSetOut,
    GroupOut,
    SatelliteDetailOut,
    SatelliteOut,
    SatellitePageOut,
)
from sattrack.catalog.service import (
    AboutNotFoundError,
    CatalogService,
    GroupNotFoundError,
    ImageNotFoundError,
    SatelliteNotFoundError,
)
from sattrack.shared.web import SessionDep

# Element sets change at most every 2 hours (CelesTrak's update cycle); clients revalidate
# with the ETag after this many seconds.
ELEMENTS_MAX_AGE_SECONDS = 300
# Images are refreshed weekly at most.
IMAGE_MAX_AGE_SECONDS = 604_800
GROUP_SLUG_PATTERN = r"^[a-z0-9-]{1,50}$"

router = APIRouter(prefix="/api/v1", tags=["catalog"])


def get_catalog_service(session: SessionDep) -> CatalogService:
    return CatalogService(CatalogRepository(session))


CatalogServiceDep = Annotated[CatalogService, Depends(get_catalog_service)]


@router.get("/groups", response_model=list[GroupOut], summary="List satellite groups")
def list_groups(service: CatalogServiceDep) -> list[GroupOut]:
    return [GroupOut.from_domain(group) for group in service.list_groups()]


@router.get(
    "/satellites",
    response_model=SatellitePageOut,
    summary="Search and filter satellites",
)
def search_satellites(
    service: CatalogServiceDep,
    q: Annotated[
        str | None,
        Query(min_length=1, max_length=100, description="Name fragment or NORAD ID"),
    ] = None,
    group: Annotated[str | None, Query(pattern=GROUP_SLUG_PATTERN)] = None,
    orbit_class: OrbitClass | None = None,
    country: Annotated[
        str | None, Query(pattern=r"^[A-Z0-9/]{1,10}$", description="CelesTrak owner code")
    ] = None,
    launch_year: Annotated[int | None, Query(ge=1957, le=2100)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
) -> SatellitePageOut:
    filters = SatelliteFilters(
        query=q.strip() if q else None,
        group=group,
        orbit_class=orbit_class,
        country=country,
        launch_year=launch_year,
    )
    page = service.search_satellites(filters, limit, offset)
    return SatellitePageOut(
        items=[SatelliteOut.from_domain(s) for s in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get(
    "/satellites/{norad_id}",
    response_model=SatelliteDetailOut,
    summary="Satellite metadata and latest element set",
    responses={404: {"description": "Unknown NORAD ID"}},
)
def get_satellite(
    service: CatalogServiceDep,
    norad_id: Annotated[int, Path(ge=1, le=999_999_999)],
) -> SatelliteDetailOut:
    try:
        detail = service.get_satellite(norad_id)
    except SatelliteNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    elements = detail.latest_elements
    return SatelliteDetailOut(
        satellite=SatelliteOut.from_domain(detail.satellite),
        latest_elements=ElementSetOut.from_domain(elements) if elements else None,
        has_about=detail.has_about,
        has_image=detail.has_image,
    )


@router.get(
    "/satellites/{norad_id}/about",
    response_model=AboutOut,
    summary="Description, purpose and image credit from Wikimedia",
    description=(
        "Content from Wikidata (CC0), English Wikipedia (CC BY-SA 4.0) and Wikimedia Commons "
        "(per-file licenses). Show the attribution fields with the content."
    ),
    responses={404: {"description": "No description for this object"}},
)
def get_about(
    service: CatalogServiceDep,
    norad_id: Annotated[int, Path(ge=1, le=999_999_999)],
) -> AboutOut:
    try:
        info = service.get_about(norad_id)
    except AboutNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return AboutOut.from_domain(info, image_path=f"{router.prefix}/satellites/{norad_id}/image")


@router.get(
    "/satellites/{norad_id}/image",
    summary="The object's image (JPEG or PNG), 480 or 960 px wide",
    description="Served from this API; supports ETag / If-None-Match.",
    response_class=Response,
    responses={
        200: {"content": {"image/jpeg": {}, "image/png": {}}},
        304: {"description": "Not modified"},
        404: {"description": "No image for this object"},
    },
)
def get_image(
    service: CatalogServiceDep,
    norad_id: Annotated[int, Path(ge=1, le=999_999_999)],
    w: Annotated[ImageWidth, Query(description="Width in pixels: 480 or 960")],
    if_none_match: Annotated[str | None, Header()] = None,
) -> Response:
    try:
        image = service.get_image(norad_id, w)
    except ImageNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    headers = {
        "ETag": f'"{image.sha256}"',
        "Cache-Control": f"public, max-age={IMAGE_MAX_AGE_SECONDS}",
    }
    if if_none_match == headers["ETag"]:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)
    return Response(content=image.data, media_type=image.mime, headers=headers)


@router.get(
    "/elements",
    response_model=list[ElementSetOut],
    summary="Latest element sets for every satellite in a group",
    description="Clients propagate these with SGP4. Supports ETag / If-None-Match.",
    responses={304: {"description": "Not modified"}, 404: {"description": "Unknown group"}},
)
def group_elements(
    service: CatalogServiceDep,
    response: Response,
    group: Annotated[str, Query(pattern=GROUP_SLUG_PATTERN)],
    limit: Annotated[int, Query(ge=1, le=20_000)] = 5_000,
    offset: Annotated[int, Query(ge=0)] = 0,
    if_none_match: Annotated[str | None, Header()] = None,
) -> list[ElementSetOut] | Response:
    try:
        etag = f'"{service.group_elements_etag(group, limit, offset)}"'
        cache_headers = {
            "ETag": etag,
            "Cache-Control": f"public, max-age={ELEMENTS_MAX_AGE_SECONDS}",
        }
        if if_none_match == etag:
            return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=cache_headers)
        element_sets = service.group_elements(group, limit, offset)
    except GroupNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    response.headers.update(cache_headers)
    return [ElementSetOut.from_domain(e) for e in element_sets]
