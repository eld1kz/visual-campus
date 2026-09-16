from dataclasses import dataclass, field


@dataclass
class SourceHit:
    """One organisation as returned by a single source, before merging."""

    source: str
    name: str
    aliases: list[str] = field(default_factory=list)
    city: str | None = None
    country: str | None = None
    lat: float | None = None
    lng: float | None = None
    website: str | None = None
    ror_id: str | None = None
    wikidata_ids: list[str] = field(default_factory=list)
    commons_category: str | None = None
    # ROR affiliation matcher picked this org with high confidence
    chosen: bool = False
    # Number of Wikipedia/Wikimedia sitelinks: a proxy for how well-known the org is
    sitelinks: int = 0
