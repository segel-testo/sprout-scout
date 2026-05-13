# Sprout Scout — Security Review

Audit date: 2026-05-13. Scope: backend (`/api/*`) only. Status of every item: **open** — to be addressed in a follow-up pass.

Anchor facts:

- Public, anonymous API. Zero auth. Zero rate limiting.
- Scaleway Serverless Container, `fr-par`: 256 MB / 100 mvCPU / `max_scale=5`.
- Scaleway free pool: 400 000 GB-s memory + 200 000 vCPU-s / month.
- Cache backend: Scaleway Object Storage (S3), 1-week TTL.
- `SCAN_RESTAURANT_CAP = 500` per scan request; `SCAN_CONCURRENCY = 8` per stream.
- PDF body capped at 10 MB; **HTML body is uncapped**.
- `services/safe_fetch.py` blocks private / loopback / link-local / reserved / multicast / unspecified IPs. Does **not** restrict public IPs.

---

## 1. Cost / abuse vectors

### 1.1 No rate limit on the SSE scan endpoints

`GET /api/restaurants/scan?...` and `GET /api/restaurants/scan-by-radius?...` each fire up to 500 outbound HTTP requests (plus redirects, same-host menu-link crawl, PDF GETs). Anyone can open these endpoints in a loop or iterate input space:

- Iterate all 10 000 Austrian 4-digit zips → ~5 M outbound scans on first pass; cache resets weekly.
- Reopen the same SSE stream in a loop; *cache* protects external sites only after the first miss.

**Direct Scaleway billing impact: bounded.** `max_scale=5 × 100 mvCPU` means the container saturates before bills climb. Sustained spam fits inside the free vCPU pool (200 000 vCPU-s/month) and free memory pool (400 000 GB-s/month). Net: pure compute spam can't really cost money on the current config — the bottleneck is container saturation, not billing.

**Real downstream risks:**

- **Overpass API abuse.** Each unique cache miss POSTs to `overpass-api.de` (free shared resource). Iterating zips floods Overpass from one IP → they ban our IP → live users get 503s.
- **DDoS amplification via OSM.** OSM `website` tags are attacker-editable. An attacker can plant a `website` tag pointing at any public URL and have our backend hammer it. `safe_fetch` blocks private IPs but does **nothing** for public-IP amplification. Same for menu-link crawl: a malicious homepage advertising 4 menu paths gets our backend to GET 5 URLs per "scan."
- **Reflective scanning of paid third-party APIs.** If an OSM `website` tag points at a metered API, our backend pulls it on every cache miss.

### 1.2 Cache poisoning is cheap but low-impact

Each unique scan key writes one ~1 KB object to S3. 5 M objects ≈ 5 GB → within the 75 GB free Object Storage allowance. Scaleway Object Storage requests are effectively free. Storage cost ≈ €0. Listed for completeness only.

---

## 2. Resource exhaustion (container DoS)

### 2.1 No size cap on initial HTML fetch — OOM vector

`scanner._dispatch`:

```python
response = await safe_get(client, website)
...
html = response.text  # whole body into RAM, no cap
```

Same in `_crawl_menu_links` (`sub_html = response.text`). Attacker controls the URL via OSM → serves a 500 MB HTML stream → container OOMs (256 MB ceiling). Only PDFs have a size cap (`MAX_PDF_BYTES = 10 MB`).

### 2.2 Threadpool starvation

On a 100 mvCPU box, `os.cpu_count()` reports 1 → the default `asyncio.to_thread` pool is ~5 threads. Currently shared by:

- S3 cache reads/writes (`services/cache.py` async wrappers).
- PDF parsing (`pdfplumber` in `services/adapters/pdf.py`).
- DNS resolution inside `safe_fetch._resolve_safe`.

Under load the event loop blocks waiting for a thread. Mitigations: enlarge the executor, or move S3 to `aioboto3` (added dep).

### 2.3 Slow-loris on the scanner

Attacker hosts a URL that drips bytes within the 20s `SCAN_PER_RESTAURANT_TIMEOUT`. Each occupies one of the 8 semaphore slots until timeout. 8 slow URLs × N concurrent SSE streams = full DoS of legitimate scans. `httpx` has a single `timeout=20` covering connect+read+write+pool, so the attacker can still extract the full 20s.

### 2.4 Unbounded concurrent SSE streams

Nothing caps how many simultaneous SSE connections one IP can open. Each opens its own `httpx.AsyncClient` (32 max_connections, 16 keepalive). 100 streams = 3 200 sockets attempted; container OOMs / hits FD limits long before that.

---

## 3. Smaller smells

- **Error SSE leaks exception strings.** `routers/restaurants.scan_one` returns `str(e)`, forwarded as the `reason` field of the `error` SSE event. httpx exceptions sometimes include full URLs / redirect chains — minor info disclosure about which target hosts our backend hit.
- **DNS-rebinding window in `safe_fetch`.** Already documented as accepted residual risk in `todos.md` #15. Real but low priority.
- **Cache writes are fire-and-trust.** If `aset_namespaced` raises (S3 outage), the otherwise-successful scan surfaces as an `error` SSE because `scan_one` catches all exceptions and emits its message.
- **No CSP and no SRI on the frontend.** Already noted in `todos.md` (deferred follow-up under #20).
- **CORS is a browser-side guard only.** Anyone with `curl` ignores it. Not a cost-protection layer.

---

## 4. Planned mitigations

Ordered by cost-impact ÷ effort. Each is independently shippable.

| # | Mitigation | Why | Effort |
|---|---|---|---|
| A | **Per-IP rate limit on `/restaurants/scan*`** (e.g. `slowapi`: ~5 SSE starts / minute / IP, ~30 / hour / IP). | Kills mass-zip iteration and amplification. Highest impact. | ~15 min |
| B | **Cap HTML body size in `safe_fetch` / scanner** (e.g. 2 MB). Use `client.stream(...)` and abort past the cap. | Closes the OOM vector in §2.1. | ~30 min |
| C | **Cap concurrent SSE connections globally** (e.g. one semaphore in `_stream_scan` of size 4); reject extras with 503. | Bounds worst case under attack. | ~10 min |
| D | **Tighten error-SSE message** (fixed string instead of `str(e)`). | Stops leaking internal target hostnames. | ~2 min |
| E | *Optional* — Cloudflare in front of `api.sprout-scout.at` (free plan). | IP-level rate limiting, bot detection, geo-blocking outside AT/EU. €0 cost, DNS change only. | DNS change |
| F | *Optional* — drop `max_scale` from 5 to 2 or 3. | Provable cost ceiling below the Scaleway free pool. Trade-off: slightly more queueing for legitimate spikes. | settings change |

### GDPR notes for the mitigations

- **(A) Rate limiting by IP** is lawful under GDPR Art. 6(1)(f) (legitimate interest: service abuse prevention) as long as IPs are not persisted beyond the rate-limit window. In-memory only (the `slowapi` default) is the cleanest path; no addition to the privacy notice required beyond what's already there.
- **(D) Error message tightening** removes a minor info-disclosure surface but introduces nothing new.
- **(E) Cloudflare** would add a sub-processor under GDPR. Would require a privacy-notice update naming Cloudflare and the data category (IP, request metadata). Defer until a real attack happens.
- **(B), (C), (F)** are server-internal — no GDPR surface change.

---

## Suggested order when picked up

1. **A** (rate limit) — biggest blast-radius reducer, simplest.
2. **D** (error message) — trivial, lump it into the same PR as A.
3. **B** (HTML size cap) — closes the OOM vector.
4. **C** (global SSE semaphore) — belt-and-suspenders.
5. **E / F** — decide based on whether real abuse traffic materializes.
