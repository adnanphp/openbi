"""OpenBI Phase I — Kafka producer.

Emits synthetic order events to the `orders` topic at a configurable rate.
Each event mimics a real point-of-sale order with customer, product,
amount, and timestamp.

Run (as a one-shot or long-running service):
    python -m streaming.producer                     # 1 event/sec, forever
    python -m streaming.producer --rate 100          # 100 events/sec
    python -m streaming.producer --count 10000       # 10K events then exit
    python -m streaming.producer --bootstrap kafka:9092
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
import uuid
from datetime import datetime, timezone

from kafka import KafkaProducer


TOPIC = "orders"

CATEGORIES = ["Furniture", "Office Supplies", "Technology"]
SUB_CATEGORIES = {
    "Furniture": ["Chairs", "Tables", "Bookcases", "Furnishings"],
    "Office Supplies": ["Binders", "Paper", "Storage", "Art", "Labels"],
    "Technology": ["Phones", "Accessories", "Machines", "Copiers"],
}
REGIONS = ["East", "West", "Central", "South"]
SEGMENTS = ["Consumer", "Corporate", "Home Office"]
SHIP_MODES = ["Standard Class", "Second Class", "First Class", "Same Day"]


def make_event() -> dict:
    """Generate one synthetic order event."""
    category = random.choice(CATEGORIES)
    sub = random.choice(SUB_CATEGORIES[category])
    quantity = random.randint(1, 14)
    unit_price = round(random.uniform(5.0, 800.0), 2)
    discount = round(random.choice([0.0, 0.0, 0.0, 0.1, 0.15, 0.2, 0.3]), 2)
    sales = round(quantity * unit_price * (1 - discount), 2)
    # profit margin ~ 5–25% — sometimes negative (returns/promos)
    margin = random.uniform(-0.1, 0.25)
    profit = round(sales * margin, 2)

    return {
        "event_id":       str(uuid.uuid4()),
        "event_time":     datetime.now(timezone.utc).isoformat(),
        "order_id":       f"RT-{uuid.uuid4().hex[:12]}",
        "customer_id":    f"C-{random.randint(10000, 99999)}",
        "customer_name":  f"Customer {random.randint(1, 5000)}",
        "segment":        random.choice(SEGMENTS),
        "category":       category,
        "sub_category":   sub,
        "product_id":     f"P-{random.randint(1000, 9999)}",
        "region":         random.choice(REGIONS),
        "ship_mode":      random.choice(SHIP_MODES),
        "quantity":       quantity,
        "sales":          sales,
        "discount":       discount,
        "profit":         profit,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bootstrap", default="localhost:9092")
    ap.add_argument("--topic", default=TOPIC)
    ap.add_argument("--rate", type=float, default=1.0,
                    help="events per second (float)")
    ap.add_argument("--count", type=int, default=0,
                    help="stop after N events (0 = forever)")
    args = ap.parse_args()

    print(f"▶ Connecting to Kafka at {args.bootstrap}")
    producer = KafkaProducer(
        bootstrap_servers=args.bootstrap,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8") if k else None,
        linger_ms=50,
        acks="all",
        retries=3,
    )

    print(f"▶ Producing to topic '{args.topic}' at {args.rate} events/sec")
    delay = 1.0 / args.rate if args.rate > 0 else 0
    sent = 0
    t0 = time.time()
    try:
        while True:
            event = make_event()
            producer.send(args.topic, key=event["order_id"], value=event)
            sent += 1
            if sent % 100 == 0 or sent == 1:
                elapsed = time.time() - t0
                rate = sent / elapsed if elapsed > 0 else 0
                print(f"  sent {sent:>8,} events  ({rate:,.1f}/s)")
            if args.count and sent >= args.count:
                break
            time.sleep(delay)
    except KeyboardInterrupt:
        print("\n  interrupted")
    finally:
        producer.flush(timeout=10)
        producer.close()
        print(f"\n✓ sent {sent:,} events in {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
