# Evaluation

Evaluation date: 2026-09-19. The measurements below are real runs against the live public APIs from the development machine. They are not fixtures or estimates.

## Method

- Sequential run: resolve the query, build one uncached profile, clear the profile/source cache, then continue with the next query.
- Load run: build Korea University, Seoul National University, KAIST, Nazarbayev University, and University of Cambridge simultaneously in one process.
- `first` is time from starting `/profile/{id}` until the first `photo` SSE event. `done` is time until the `done` event.
- Tier columns are `verified / likely / unconfirmed`. Category columns are `campus / dorms / classrooms / libraries / city`.
- A known date in the final run means a normalized `date_taken`; upload-only dates are counted separately by the evaluator and are never presented as capture dates.
- Flickr and Mapillary were disabled because their keys were not present. Openverse ran anonymously. Local OpenCLIP was enabled with cached ViT-B-32 weights.
- The manual relevance check reviewed 31 of the 42 selected sequential photos: every result from Korea, Seoul, Cambridge and AUCA, plus five KAIST and one Nazarbayev image before Wikimedia returned HTTP 429 to the review downloader.

## Baseline

The baseline predates separate capture/upload fields. Its “known date” and “2024+” columns use the old `published_at`, which sometimes contained an upload date. They are included to document the actual before run, but they cannot be compared as capture-date coverage.

| Query | Photos | Tiers V/L/U | Categories C/D/Cl/L/Ci | Legacy known date | Apparent 2024+ | First | Done | Source errors |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Korea University | 136 | 0/1/135 | 121/0/1/3/11 | 99.3% | 1.5% | 1.22 s | 8.74 s | none recorded |
| Seoul National University | 138 | 0/7/131 | 107/1/6/18/6 | 97.8% | 11.6% | 3.31 s | 9.33 s | none recorded |
| KAIST | 101 | 0/0/101 | 81/0/1/5/14 | 100% | 3.0% | 2.46 s | 8.59 s | none recorded |
| Nazarbayev University | 69 | 0/4/65 | 56/0/0/0/13 | 95.7% | 36.2% | 2.41 s | 8.35 s | none recorded |
| University of Cambridge | 357 | 1/5/351 | 341/0/2/14/0 | 100% | 3.4% | 4.16 s | 10.19 s | none recorded |
| American University of Central Asia | 6 | 0/1/5 | 6/0/0/0/0 | 83.3% | 0% | 2.57 s | 8.55 s | none recorded |

The baseline returned large candidate pools as profile photos, including hundreds of unconfirmed results. That made the count high but did not meet the jury's reliability rule.

## Final sequential run

| Query | Photos | Tiers V/L/U | Categories C/D/Cl/L/Ci | Known taken | Taken 2024+ | Median age | Junk spot-check | First | Done | Source errors |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Korea University | 8 | 5/3/0 | 6/0/2/0/0 | 100% | 0% | 15 y | 0/8 | 2.32 s | 19.89 s | none |
| Seoul National University | 10 | 9/1/0 | 6/1/1/2/0 | 100% | 0% | 11 y | 0/10 | 2.34 s | 14.29 s | OSM timeout |
| KAIST | 10 | 10/0/0 | 6/0/2/2/0 | 100% | 0% | 7 y | 0/5 | 2.32 s | 13.28 s | none |
| Nazarbayev University | 7 | 6/1/0 | 5/0/2/0/0 | 100% | 0% | 8 y | 0/1 | 1.43 s | 17.50 s | none |
| University of Cambridge | 6 | 0/6/0 | 6/0/0/0/0 | 0% | 0% | unknown | 0/6 | 2.35 s | 9.14 s | official site 403; OSM connection error; Commons timeout |
| American University of Central Asia | 1 | 1/0/0 | 1/0/0/0/0 | 100% | 0% | 21 y | 0/1 | 1.81 s | 11.45 s | none |

Overall manual unrelated-image rate was **0/31 (0%)**. Two Cambridge results are street views that are relevant to Cambridge city context but remain in `campus` because Openverse did not provide usable geodata; this is a category ambiguity, not an unrelated-image pass. The final selector displayed no unconfirmed photos. AUCA therefore reports one reliable campus photo instead of filling the profile with unrelated Openverse matches.

No selected photo in this keyless run had a trustworthy capture date in 2024 or later. Recent-first requests and ranking were active, but recent candidates either were absent or failed the reliability/visual checks. The interface reports this per category and shows the best older reliable photos with their dates.

## Five-profile load run

| Query | Photos | Tiers V/L/U | Categories C/D/Cl/L/Ci | First | Done | Source errors |
|---|---:|---:|---:|---:|---:|---|
| Korea University | 6 | 3/3/0 | 6/0/0/0/0 | 2.12 s | 12.45 s | none |
| Seoul National University | 10 | 9/1/0 | 6/1/1/2/0 | 2.31 s | 9.91 s | OSM timeout |
| KAIST | 10 | 10/0/0 | 6/0/2/2/0 | 2.46 s | 13.57 s | none |
| Nazarbayev University | 7 | 6/1/0 | 5/0/2/0/0 | 2.65 s | 13.91 s | none |
| University of Cambridge | 6 | 0/6/0 | 6/0/0/0/0 | 2.80 s | 13.91 s | official site 403; OSM 504; Commons timeout |

Every profile produced its first photo within 2.8 seconds and completed within 13.91 seconds. The server-wide source limits prevented the earlier near-empty multi-profile Commons failure for four profiles. Cambridge still hit the source's 7.5-second budget and fell back to six visually checked Openverse results; the error is exposed in `source_status`.

The recorded baseline five-profile run completed in 8.43–9.48 seconds with 69–357 mostly unconfirmed photos per profile. The final run is slower because it performs reliable date parsing, pHash grouping, batched OpenCLIP checks, and trust-first selection, but remains well below 30 seconds and no longer treats the candidate pool as verified output.

## Resolution cases

| Query | Result | Time |
|---|---|---:|
| `Koera Univrsity` | resolved to Korea University (`Q39997`), correction `korea university` | 2.07 s |
| `Visual Campus Nonexistent University 98741` | `not_found`; no profile built | 1.95 s |

## Remaining limits

- Flickr and Mapillary coverage is unavailable until `FLICKR_API_KEY` and `MAPILLARY_TOKEN` are configured.
- Anonymous Openverse is limited to 20 results per request and is used only as enrichment. Client credentials raise its allowance.
- Official sites can still reject requests with HTTP 403. Their unknown-license images are link-only and visually checked when the image endpoint permits access.
- Commons and OSM can time out under upstream load. Partial results and errors are shown honestly; caches reduce repeat pressure.
- Source metadata for older Commons files is much richer than for recent campus photos in the tested universities. A zero 2024+ share means no recent reliable photo was found, not that an upload date was treated as capture time.
