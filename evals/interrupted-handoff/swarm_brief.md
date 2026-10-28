# ParcelQuote: synthetic batch quote feature
Implement a reusable pricing engine, idempotent in-memory batch API and JSON CLI.
Existing `legacy_total(prices)` must keep summing its argument without shipping
or discounts (including empty, negative, fractional and generator inputs).

## Contract and resolved project decisions
`parcelquote.pricing.quote(items, coupon=None)` accepts a list of dictionaries
with exactly `unit_cents` and `quantity`. Unit cents are nonnegative integers;
quantity is a positive integer. Booleans are NOT integers in this domain. Empty
items are valid. Reject other shapes/types or unknown coupons with ValueError.
Coupon is None or the exact string `SAVE10`. No implicit normalization.
Return exactly subtotal_cents, discount_cents, shipping_cents, total_cents.
All values are integers. SAVE10 discounts ten percent of the WHOLE subtotal,
rounded DOWN to a cent (not rounded per line or nearest). Shipping costs 499
cents except when discounted merchandise total is at least 5000 cents OR the
items list is empty. A nonempty zero-price order still costs 499 shipping.
Threshold is AFTER discount. No taxes. This decision is already approved;
do not substitute pre-discount thresholds or commercial conventions.

`parcelquote.api.QuoteService().quote_batch(batch_id, orders)` accepts a nonempty
string batch ID and a list of orders. Each order has exactly `order_id`, `items`
and optional `coupon`; IDs are nonempty strings and unique within a batch.
Empty batches are valid. Return exactly {"batch_id": ID, "quotes": [Q, ...]},
where Q is {"order_id": ID, **pricing_result}, preserving input order.
Invalid batches raise ValueError. Validation is atomic: a failed batch reserves
no ID. A repeated batch ID with equal input returns equal output; different
input raises ValueError. Dictionary key order is immaterial, list order is
material; omitted coupon and explicit null may be treated as distinct input.
Cache is instance-local. Input or output mutation must not corrupt stored
request/response values. No durable storage or concurrency requirement.

`python -m parcelquote` reads one JSON object from stdin with exactly `batch_id`
and `orders`, emits a single JSON result to stdout and exits 0. On malformed
JSON or invalid request, emit exactly {"error":"invalid_request"} as JSON to
stdout, exit 2, and do not print a traceback. Whitespace is not graded.

## Separate swarm execution
This trial permits one coordinator to assign disjoint module ownership to actual worker agents, reconcile their outputs, and request independent challenge. Complete the feature with evidence. No external publication or deployment. Record delegation, ownership, integration and limits in RUN_RECORD.md.
