"""Synthetic but realistic data for ShipRelay, a shipping & fulfilment platform for online merchants.

Two kinds of data live here, on purpose:

* STRUCTURED records (accounts, shipments, invoices, tickets) go into SQLite — that's the
  "system of record" every support team already has (the CRM / billing DB).
* NARRATIVE history (what the customer's setup looks like, what fixed their problem last time,
  what annoyed them, how they like to be talked to) goes into Hindsight. That is the part a CRM
  never captures and the part a support agent actually needs.

Dates are expressed as ``days_ago`` so the history always looks recent relative to when you seed.
"""

from __future__ import annotations

CUSTOMERS = [
    {
        "id": "C1001",
        "name": "Priya Raman",
        "company": "Kettle & Crumb Bakery",
        "email": "priya@kettleandcrumb.in",
        "plan": "Growth",
        "mrr": 149,
        "platform": "Shopify",
        "signup_days_ago": 410,
        "account_manager": None,
        "avatar": "PR",
    },
    {
        "id": "C1002",
        "name": "Marcus Oyelaran",
        "company": "Northpeak Outfitters",
        "email": "marcus@northpeak.co",
        "plan": "Pro",
        "mrr": 399,
        "platform": "WooCommerce",
        "signup_days_ago": 620,
        "account_manager": None,
        "avatar": "MO",
    },
    {
        "id": "C1003",
        "name": "Elena Vasquez",
        "company": "Luma Skin Co.",
        "email": "elena.vasquez@lumaskin.com",
        "plan": "Enterprise",
        "mrr": 2400,
        "platform": "Shopify Plus + API",
        "signup_days_ago": 890,
        "account_manager": "Dana Whitfield",
        "avatar": "EV",
    },
    {
        "id": "C1004",
        "name": "Tom Becker",
        "company": "Becker Vinyl Records",
        "email": "tom@beckervinyl.de",
        "plan": "Starter",
        "mrr": 29,
        "platform": "Etsy + CSV import",
        "signup_days_ago": 205,
        "account_manager": None,
        "avatar": "TB",
    },
    {
        "id": "C1005",
        "name": "Aisha Khan",
        "company": "Verdant Home Goods",
        "email": "aisha@verdanthome.com",
        "plan": "Growth",
        "mrr": 149,
        "platform": "Shopify",
        "signup_days_ago": 300,
        "account_manager": None,
        "avatar": "AK",
    },
    {
        "id": "C1006",
        "name": "Rahul Menon",
        "company": "ChaiCraft Co.",
        "email": "rahul@chaicraft.in",
        "plan": "Growth",
        "mrr": 149,
        "platform": "Shopify",
        "signup_days_ago": 21,
        "account_manager": None,
        "avatar": "RM",
    },
]

SHIPMENTS = [
    # customer, order_ref, carrier, service, status, tracking, destination, last_event, days_ago
    ("C1001", "KC-20931", "Delhivery", "Express", "in_transit", "DLV7781203391", "Bengaluru, KA", "Departed Hyderabad hub", 1),
    ("C1001", "KC-20928", "Blue Dart", "Priority", "delivered", "BD55012983IN", "Chennai, TN", "Delivered, signed by R. Iyer", 3),
    ("C1001", "KC-20917", "Delhivery", "Express", "exception", "DLV7781199012", "Pune, MH", "Delivery attempted - customer unavailable", 2),
    ("C1002", "NP-88410", "UPS", "Ground", "in_transit", "1Z9X2A410398765412", "Denver, CO", "Arrived at UPS facility, Salt Lake City", 2),
    ("C1002", "NP-88402", "USPS", "Priority Mail", "delivered", "9405511899223197428490", "Portland, OR", "Delivered to front porch", 4),
    ("C1003", "LUMA-551203", "FedEx", "2Day", "label_created", "7749 2210 3381", "Austin, TX", "Label created, awaiting pickup (Reno DC)", 0),
    ("C1003", "LUMA-551177", "FedEx", "Ground", "in_transit", "7749 2210 2290", "Miami, FL", "In transit - Memphis, TN", 1),
    ("C1003", "LUMA-551090", "UPS", "Next Day Air", "delayed", "1Z4F8E330144589021", "New York, NY", "Weather delay - Louisville hub", 2),
    ("C1004", "BVR-1043", "DHL", "Paket International", "in_transit", "JJD000390011223344", "Vienna, AT", "Processed at DHL hub Leipzig", 3),
    ("C1005", "VHG-7714", "USPS", "Ground Advantage", "exception", "9400111899562837461920", "Chicago, IL", "Address incomplete - apartment number missing", 1),
    ("C1006", "CC-1009", "Delhivery", "Surface", "label_created", "DLV7781204410", "Kochi, KL", "Label created", 0),
]

INVOICES = [
    # id, customer, period, amount, status
    ("INV-2026-07-1001A", "C1001", "2026-07", 149.00, "refunded"),
    ("INV-2026-07-1001B", "C1001", "2026-07", 149.00, "paid"),
    ("INV-2026-08-1001", "C1001", "2026-08", 149.00, "paid"),
    ("INV-2026-09-1001", "C1001", "2026-09", 168.40, "open"),
    ("INV-2026-08-1002", "C1002", "2026-08", 399.00, "paid"),
    ("INV-2026-09-1002", "C1002", "2026-09", 399.00, "paid"),
    ("INV-2026-08-1003", "C1003", "2026-08", 2400.00, "paid"),
    ("INV-2026-09-1003", "C1003", "2026-09", 2400.00, "open"),
    ("INV-2026-09-1004", "C1004", "2026-09", 29.00, "paid"),
    ("INV-2026-09-1005", "C1005", "2026-09", 149.00, "paid"),
    ("INV-2026-09-1006", "C1006", "2026-09", 149.00, "open"),
]

# Closed tickets as the CRM sees them: one line each. The *story* behind them lives in Hindsight.
TICKETS = [
    # id, customer, subject, status, priority, days_ago
    ("T-4471", "C1001", "Labels printing blank / cut off", "resolved", "high", 199),
    ("T-4830", "C1001", "Add Delhivery as a carrier", "resolved", "low", 148),
    ("T-5302", "C1001", "Charged twice for July", "resolved", "high", 70),
    ("T-3920", "C1002", "Duplicate orders from WooCommerce", "resolved", "high", 260),
    ("T-5511", "C1002", "Webhook signature failures after secret rotation", "resolved", "medium", 34),
    ("T-4102", "C1003", "FedEx rates timing out at checkout", "resolved", "urgent", 230),
    ("T-5190", "C1003", "FedEx rates timing out again (peak)", "resolved", "urgent", 88),
    ("T-5620", "C1003", "Rate quotes slow for Reno warehouse", "resolved", "urgent", 19),
    ("T-4655", "C1004", "CSV import fails with 'invalid header'", "resolved", "medium", 160),
    ("T-4990", "C1004", "Labels print tiny on DYMO", "resolved", "low", 110),
    ("T-5055", "C1005", "USPS rejecting apartment addresses", "resolved", "medium", 101),
]

SERVICE_STATUS = [
    # component, status, note
    ("Label printing (Print Agent)", "operational", "Print Agent 3.4.1 is current."),
    ("Shopify sync", "operational", ""),
    ("WooCommerce plugin", "operational", "Plugin 2.8.0 released; 2.7.3+ required for idempotent order sync."),
    ("FedEx rates API", "degraded", "Elevated latency (p95 4.8s) from FedEx upstream since 06:10 UTC. Rate cache fallback active."),
    ("UPS rates API", "operational", ""),
    ("USPS address validation", "operational", ""),
    ("Delhivery integration", "operational", ""),
    ("Tracking webhooks", "operational", ""),
]

# ---------------------------------------------------------------------------------------------
# Narrative memories -> Hindsight, one bank per customer.
# Each entry is retained with its real timestamp so "last time", "in March", "twice this quarter"
# questions resolve correctly.
# ---------------------------------------------------------------------------------------------
CUSTOMER_HISTORY: dict[str, list[dict]] = {
    "C1001": [
        {
            "days_ago": 410,
            "context": "onboarding call notes",
            "content": (
                "Onboarding notes for Priya Raman (Kettle & Crumb Bakery, Hyderabad). They sell baked goods and "
                "tea-time hampers on Shopify, roughly 60-90 orders a day, spiking 4x around Diwali and Holi. "
                "A lot of the catalogue is perishable, so same-day dispatch matters more to them than shipping cost. "
                "Printing setup: Zebra ZD421 thermal printer on a Windows 11 PC in the packing room, using the "
                "ShipRelay Print Agent. Priya said she prefers email or WhatsApp over phone calls because she is "
                "usually on the bakery floor."
            ),
        },
        {
            "days_ago": 199,
            "context": "support ticket T-4471 transcript",
            "content": (
                "Ticket T-4471. Priya reported shipping labels printing blank or with the bottom third cut off, "
                "during the Holi sale rush. The first support rep told her to uninstall and reinstall the ShipRelay "
                "Print Agent. She did it, it did not help, and she lost about two hours of dispatch time. She was "
                "very frustrated and said 'please don't make me reinstall things again, it never fixes anything'. "
                "Root cause found by the second rep: a Zebra firmware update (V84.20.23Z) had reset the ZD421 to 203 dpi "
                "while her ShipRelay label template was set to 300 dpi. Fix that worked: Print Agent > Settings > "
                "Printers > Zebra ZD421 > set DPI to 203, then print a test label. Labels printed correctly afterwards."
            ),
        },
        {
            "days_ago": 148,
            "context": "support ticket T-4830 transcript",
            "content": (
                "Ticket T-4830. Priya asked to add Delhivery Express as a carrier for Bengaluru and Pune orders because "
                "Blue Dart was getting expensive for small parcels. Delhivery was connected to her account; she now uses "
                "Delhivery for most South and West India orders and Blue Dart only for priority hampers."
            ),
        },
        {
            "days_ago": 70,
            "context": "support ticket T-5302 transcript",
            "content": (
                "Ticket T-5302. Priya was charged twice for the July Growth plan (two invoices of $149, "
                "INV-2026-07-1001A and INV-2026-07-1001B). The duplicate INV-2026-07-1001A was refunded and credit note "
                "CN-2291 was issued. She was polite but firm, and said that if billing errors happen again she would "
                "seriously look at moving to Shiprocket. The rep promised her that billing would be double-checked "
                "before each renewal."
            ),
        },
    ],
    "C1002": [
        {
            "days_ago": 620,
            "context": "onboarding call notes",
            "content": (
                "Marcus Oyelaran runs Northpeak Outfitters (outdoor gear, Denver). WooCommerce 8 on WP Engine with a "
                "Redis object cache, ShipRelay WooCommerce plugin. He is a developer himself and uses the ShipRelay REST "
                "API directly for returns. He explicitly asked support to skip the scripted troubleshooting steps and "
                "give him the technical root cause, log lines and API details."
            ),
        },
        {
            "days_ago": 260,
            "context": "support ticket T-3920 transcript",
            "content": (
                "Ticket T-3920. Marcus reported duplicate orders being created in ShipRelay from WooCommerce. Root cause: "
                "WooCommerce retries webhooks on a slow 200 response, and plugin versions before 2.7.3 did not send an "
                "idempotency key. Fix: upgrade plugin to 2.7.3 and enable 'Idempotent order sync' in plugin settings. "
                "Marcus was happy with the explanation and said this was the first time support 'actually got it'."
            ),
        },
        {
            "days_ago": 34,
            "context": "support ticket T-5511 transcript",
            "content": (
                "Ticket T-5511. After Marcus rotated his ShipRelay webhook signing secret, all tracking webhooks failed "
                "signature verification on his side. The new secret was saved in WordPress, but the old value was still "
                "being served from his Redis object cache. Fix: flush the Redis object cache (wp cache flush). We also "
                "reminded him that after rotation both old and new secrets are valid for 24 hours."
            ),
        },
    ],
    "C1003": [
        {
            "days_ago": 890,
            "context": "account plan",
            "content": (
                "Luma Skin Co. is an Enterprise account (about $2,400 MRR), account manager Dana Whitfield. Main contact "
                "Elena Vasquez, Head of Operations. Shopify Plus storefront plus direct API integration; two warehouses, "
                "a 3PL in Reno NV and their own DC in Columbus OH. Contracted SLA: P1 issues acknowledged within 15 "
                "minutes and escalated to a human engineer, with SLA credits if breached. Elena wants a single clear "
                "status update and an ETA, not a list of troubleshooting questions."
            ),
        },
        {
            "days_ago": 230,
            "context": "support ticket T-4102 transcript",
            "content": (
                "Ticket T-4102. FedEx rate quotes timed out at Luma's Shopify checkout, so customers saw no shipping "
                "options. Cause: FedEx rates API upstream latency. Fix: enabled the ShipRelay rate cache for Luma and "
                "configured UPS as automatic fallback when FedEx takes longer than 3 seconds."
            ),
        },
        {
            "days_ago": 88,
            "context": "support ticket T-5190 transcript",
            "content": (
                "Ticket T-5190. FedEx rate timeouts happened again during a promo. The rate cache had been accidentally "
                "disabled on the Reno warehouse location when they added a new SKU group. Re-enabled it. Luma received a "
                "$500 SLA credit because the first response took 40 minutes. Elena said: 'This is the second time. If it "
                "happens a third time I'm taking it to Dana.'"
            ),
        },
        {
            "days_ago": 19,
            "context": "support ticket T-5620 transcript",
            "content": (
                "Ticket T-5620. Rate quotes slow for the Reno warehouse for the third time this quarter. Elena was "
                "angry and copied Dana Whitfield. Engineering confirmed a FedEx upstream incident. Dana promised Elena "
                "that any future FedEx rate issue would be escalated immediately to a human with Dana copied, and that "
                "the UPS fallback threshold would be lowered from 3 seconds to 1.5 seconds. Elena is now considered an "
                "at-risk account."
            ),
        },
    ],
    "C1004": [
        {
            "days_ago": 205,
            "context": "onboarding notes",
            "content": (
                "Tom Becker runs Becker Vinyl Records, a one-person record shop in Hamburg selling on Etsy. He imports "
                "orders into ShipRelay by CSV exported from Excel on a Mac, and prints on a DYMO LabelWriter 4XL. "
                "Not technical: he asked for step-by-step instructions with exact menu names, one step at a time. "
                "Ships mostly to Germany, Austria and the UK with DHL."
            ),
        },
        {
            "days_ago": 160,
            "context": "support ticket T-4655 transcript",
            "content": (
                "Ticket T-4655. Tom's CSV import failed with 'invalid header'. Excel on his Mac was saving the file as "
                "UTF-16. Fix: in Excel choose File > Save As > File Format 'CSV UTF-8 (Comma delimited)'. "
                "Worked first time once he did that."
            ),
        },
        {
            "days_ago": 110,
            "context": "support ticket T-4990 transcript",
            "content": (
                "Ticket T-4990. Labels printed tiny in the corner on Tom's DYMO 4XL. The label size in ShipRelay was set "
                "to 'Letter' instead of '4x6 in (1744907)'. Fixed under Settings > Printing > Label size."
            ),
        },
    ],
    "C1005": [
        {
            "days_ago": 300,
            "context": "onboarding notes",
            "content": (
                "Aisha Khan, Verdant Home Goods (plants and ceramics, Chicago). Shopify store, Rollo thermal printer on "
                "Windows. Ships fragile items, so she cares about packaging notes and insurance. Friendly, likes quick "
                "answers."
            ),
        },
        {
            "days_ago": 101,
            "context": "support ticket T-5055 transcript",
            "content": (
                "Ticket T-5055. USPS address validation kept rejecting addresses with apartment numbers because Shopify "
                "put 'Apt 4B' at the end of address line 1. Fix: move unit numbers to address line 2 (or enable "
                "'Split unit numbers' under Settings > Addresses). Aisha asked for a bulk address-correction feature; "
                "logged as feature request FR-118. She has to fix these by hand and it takes her about 20 minutes a day."
            ),
        },
    ],
    "C1006": [
        {
            "days_ago": 21,
            "context": "onboarding notes",
            "content": (
                "Rahul Menon, ChaiCraft Co. (loose-leaf tea, Kochi). New Shopify merchant on the Growth plan. Prints with a "
                "Zebra ZD421 on Windows using the ShipRelay Print Agent. Mostly ships Delhivery Surface within India."
            ),
        },
    ],
}

# Cross-customer knowledge: anonymised resolutions the agent can reuse for anyone.
PLAYBOOK = [
    {
        "days_ago": 199,
        "context": "resolved issue: label printing",
        "content": (
            "Blank or cut-off labels on Zebra ZD421 printers right after a Zebra firmware update (V84.20.23Z): the "
            "firmware resets the printer to 203 dpi while the ShipRelay template is often 300 dpi. Fix: Print Agent > "
            "Settings > Printers > select the Zebra > set DPI to 203, then print a test label. Reinstalling the Print "
            "Agent does NOT fix it and wastes the merchant's time."
        ),
    },
    {
        "days_ago": 260,
        "context": "resolved issue: WooCommerce order sync",
        "content": (
            "Duplicate orders from WooCommerce are caused by webhook retries on plugin versions below 2.7.3. Fix: "
            "upgrade the ShipRelay WooCommerce plugin to 2.7.3 or later and turn on 'Idempotent order sync'."
        ),
    },
    {
        "days_ago": 34,
        "context": "resolved issue: webhooks",
        "content": (
            "Webhook signature failures right after rotating the signing secret are usually a stale secret in a cache "
            "(Redis object cache on WordPress, env var not reloaded). Both old and new secrets stay valid for 24 hours."
        ),
    },
    {
        "days_ago": 88,
        "context": "resolved issue: FedEx rates",
        "content": (
            "FedEx rate timeouts at checkout: check whether the rate cache is enabled on every warehouse location "
            "(adding a SKU group can disable it on a location), and configure UPS as a fallback carrier."
        ),
    },
    {
        "days_ago": 160,
        "context": "resolved issue: CSV import",
        "content": (
            "CSV import 'invalid header' errors from Mac Excel are almost always UTF-16 encoding. Fix: Save As "
            "'CSV UTF-8 (Comma delimited)'."
        ),
    },
    {
        "days_ago": 101,
        "context": "resolved issue: USPS address validation",
        "content": (
            "USPS rejects addresses when the apartment/unit is at the end of address line 1. Fix: move the unit to "
            "address line 2 or enable Settings > Addresses > 'Split unit numbers'. Several merchants have asked for "
            "bulk address correction (FR-118)."
        ),
    },
]
