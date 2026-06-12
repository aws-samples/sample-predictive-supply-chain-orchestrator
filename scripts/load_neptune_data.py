#!/usr/bin/env python3
"""
Load all CSV supply chain data into Neptune graph database.

Adds to existing Supplier/Material vertices and supplies edges:
- Supplier performance metrics (as properties on Supplier vertices)
- Defect tracking (as Defect vertices + edges)
- Contracts (as properties on Supplier vertices)
- Volume tiers (as properties on supplies edges)
- Inventory levels (as properties on Material vertices)

Run via: python3 scripts/load_neptune_data.py
Requires VPC access to Neptune (run from EC2/Lambda or use SSM).
"""

import csv
import json
import os
import sys
import urllib.request
import ssl

import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

NEPTUNE_ENDPOINT = os.environ.get("NEPTUNE_ENDPOINT", "")
NEPTUNE_PORT = int(os.environ.get("NEPTUNE_PORT", "8182"))
REGION = os.environ.get("AWS_REGION", "us-east-1")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def gremlin_query(query_str):
    """Execute a Gremlin query via Neptune HTTP endpoint with SigV4 auth."""
    url = f"https://{NEPTUNE_ENDPOINT}:{NEPTUNE_PORT}/gremlin"
    data = json.dumps({"gremlin": query_str}).encode("utf-8")

    session = boto3.Session(region_name=REGION)
    creds = session.get_credentials().get_frozen_credentials()

    aws_req = AWSRequest(
        method="POST", url=url, data=data,
        headers={"Content-Type": "application/json"},
    )
    SigV4Auth(creds, "neptune-db", REGION).add_auth(aws_req)

    req = urllib.request.Request(url, data=data, method="POST")
    for k, v in aws_req.headers.items():
        req.add_header(k, v)

    ctx = ssl.create_default_context()
    if not url.startswith("https://"):
        raise ValueError(f"Refusing to open non-HTTPS URL: {url}")
    with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:  # nosemgrep: dynamic-urllib-use-detected
        return json.loads(resp.read())


def escape_gremlin(val):
    """Escape a string for Gremlin query."""
    if val is None:
        return ""
    return str(val).replace("'", "\\'").replace('"', '\\"')


def load_supplier_performance():
    """Add latest performance metrics as properties on Supplier vertices."""
    print("Loading supplier performance...")
    path = os.path.join(DATA_DIR, "supplier_performance.csv")
    if not os.path.exists(path):
        print(f"  SKIP: {path} not found")
        return

    # Group by supplier, keep latest period
    latest = {}
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sid = row["supplier_id"]
            period = row["measurement_period"]
            if sid not in latest or period > latest[sid]["measurement_period"]:
                latest[sid] = row

    count = 0
    for sid, row in latest.items():
        q = (
            f"g.V('{sid}')"
            f".property(single, 'on_time_delivery_rate', {float(row['on_time_delivery_rate'])})"
            f".property(single, 'quality_score', {float(row['quality_score'])})"
            f".property(single, 'defect_rate', {float(row['defect_rate'])})"
            f".property(single, 'cost_variance', {float(row['cost_variance'])})"
            f".property(single, 'response_time_hours', {int(row['response_time_hours'])})"
            f".property(single, 'performance_period', '{escape_gremlin(row['measurement_period'])}')"
        )
        try:
            gremlin_query(q)
            count += 1
        except Exception as e:
            print(f"  ERROR {sid}: {e}")

    print(f"  Loaded performance for {count} suppliers")


def load_contracts():
    """Add contract details as properties on Supplier vertices."""
    print("Loading contracts...")
    path = os.path.join(DATA_DIR, "supplier_contracts.csv")
    if not os.path.exists(path):
        print(f"  SKIP: {path} not found")
        return

    count = 0
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            # Contract supplier IDs use SUP001 format, normalize to SUP-001
            sid = row["supplier_id"]
            if "-" not in sid:
                sid = sid[:3] + "-" + sid[3:]

            q = (
                f"g.V('{sid}')"
                f".property(single, 'contract_id', '{escape_gremlin(row['contract_id'])}')"
                f".property(single, 'contract_type', '{escape_gremlin(row['contract_type'])}')"
                f".property(single, 'contract_start', '{escape_gremlin(row['start_date'])}')"
                f".property(single, 'contract_end', '{escape_gremlin(row['end_date'])}')"
                f".property(single, 'annual_value', {float(row['annual_value'])})"
                f".property(single, 'payment_terms', '{escape_gremlin(row['payment_terms'])}')"
                f".property(single, 'volume_commitment', '{escape_gremlin(row['volume_commitment'])}')"
                f".property(single, 'contract_status', '{escape_gremlin(row['status'])}')"
            )
            try:
                gremlin_query(q)
                count += 1
            except Exception as e:
                print(f"  ERROR {sid}: {e}")

    print(f"  Loaded contracts for {count} suppliers")


def load_defects():
    """Add defects as new vertices + edges in the graph."""
    print("Loading defects...")
    path = os.path.join(DATA_DIR, "defects.csv")
    if not os.path.exists(path):
        print(f"  SKIP: {path} not found")
        return

    count = 0
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            defect_id = row["defect_id"]
            sid = row["supplier_id"]
            mid = row["material_id"]

            # Create Defect vertex
            q = (
                f"g.addV('Defect').property(id, '{defect_id}')"
                f".property('defect_id', '{defect_id}')"
                f".property('severity', '{escape_gremlin(row['severity'])}')"
                f".property('category', '{escape_gremlin(row['category'])}')"
                f".property('quantity_affected', {int(row['quantity_affected'])})"
                f".property('defect_date', '{escape_gremlin(row['defect_date'])}')"
                f".property('description', '{escape_gremlin(row['description'])}')"
                f".property('root_cause', '{escape_gremlin(row['root_cause'])}')"
                f".property('status', '{escape_gremlin(row['status'])}')"
                f".property('recall_initiated', '{escape_gremlin(row['recall_initiated'])}')"
            )
            try:
                gremlin_query(q)
            except Exception as e:
                if "already exists" not in str(e).lower():
                    print(f"  ERROR creating {defect_id}: {e}")
                    continue

            # Edge: Supplier -[reported_defect]-> Defect
            edge_id = f"{sid}-defect-{defect_id}"
            q = (
                f"g.V('{sid}').addE('reported_defect').to(g.V('{defect_id}'))"
                f".property(id, '{edge_id}')"
            )
            try:
                gremlin_query(q)
            except Exception:
                pass  # Edge may already exist

            # Edge: Defect -[affects_material]-> Material
            edge_id2 = f"{defect_id}-affects-{mid}"
            q = (
                f"g.V('{defect_id}').addE('affects_material').to(g.V('{mid}'))"
                f".property(id, '{edge_id2}')"
            )
            try:
                gremlin_query(q)
            except Exception:
                pass

            count += 1

    print(f"  Loaded {count} defects with edges")


def load_inventory():
    """Add inventory levels as properties on Material vertices."""
    print("Loading inventory levels...")
    path = os.path.join(DATA_DIR, "inventory_levels.csv")
    if not os.path.exists(path):
        print(f"  SKIP: {path} not found")
        return

    count = 0
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            mid = row.get("material_id", "")
            if not mid:
                continue
            stock = row.get("current_stock", row.get("quantity_on_hand", "0"))
            reorder = row.get("reorder_point", "0")
            safety = row.get("safety_stock", "0")

            q = (
                f"g.V('{mid}')"
                f".property(single, 'current_stock', {int(float(stock))})"
                f".property(single, 'reorder_point', {int(float(reorder))})"
                f".property(single, 'safety_stock', {int(float(safety))})"
            )
            try:
                gremlin_query(q)
                count += 1
            except Exception as e:
                print(f"  ERROR {mid}: {e}")

    print(f"  Loaded inventory for {count} materials")


def load_volume_tiers():
    """Add volume tier info as properties on supplies edges."""
    print("Loading volume tiers...")
    path = os.path.join(DATA_DIR, "volume_tiers.csv")
    if not os.path.exists(path):
        print(f"  SKIP: {path} not found")
        return

    # Group tiers by supplier_material_id
    tiers = {}
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sm_id = row.get("supplier_material_id", "")
            if sm_id not in tiers:
                tiers[sm_id] = []
            tiers[sm_id].append({
                "min_qty": int(row.get("min_quantity", 0)),
                "max_qty": row.get("max_quantity", ""),
                "price": float(row.get("unit_price", 0)),
                "discount": row.get("discount_pct", "0"),
            })

    # We need to map SM-XXX to supplier_id + material_id
    # SM IDs follow pattern: SM-001 through SM-041
    # Load supplier_materials to get the mapping
    sm_path = os.path.join(DATA_DIR, "supplier_materials.csv")
    sm_map = {}
    if os.path.exists(sm_path):
        with open(sm_path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                sm_map[row.get("supplier_material_id", "")] = (
                    row.get("supplier_id", ""),
                    row.get("material_id", ""),
                )

    count = 0
    for sm_id, tier_list in tiers.items():
        mapping = sm_map.get(sm_id)
        if not mapping:
            continue
        sid, mid = mapping

        # Store as JSON string property on the supplies edge
        tier_json = json.dumps(tier_list)
        edge_id = f"{sid}-supplies-{mid}"
        q = (
            f"g.E('{edge_id}')"
            f".property('volume_tiers', '{escape_gremlin(tier_json)}')"
            f".property('tier_count', {len(tier_list)})"
        )
        try:
            gremlin_query(q)
            count += 1
        except Exception as e:
            print(f"  ERROR {edge_id}: {e}")

    print(f"  Loaded volume tiers for {count} supplier-material edges")


def verify():
    """Verify the data load."""
    print("\nVerification:")
    r = gremlin_query("g.V().hasLabel('Supplier').has('quality_score').count().toList()")
    print(f"  Suppliers with performance: {r['result']['data']}")

    r = gremlin_query("g.V().hasLabel('Supplier').has('contract_id').count().toList()")
    print(f"  Suppliers with contracts: {r['result']['data']}")

    r = gremlin_query("g.V().hasLabel('Defect').count().toList()")
    print(f"  Defect vertices: {r['result']['data']}")

    r = gremlin_query("g.E().hasLabel('reported_defect').count().toList()")
    print(f"  Defect edges: {r['result']['data']}")

    r = gremlin_query("g.V().hasLabel('Material').has('current_stock').count().toList()")
    print(f"  Materials with inventory: {r['result']['data']}")

    r = gremlin_query("g.E().hasLabel('supplies').has('volume_tiers').count().toList()")
    print(f"  Edges with volume tiers: {r['result']['data']}")


if __name__ == "__main__":
    if not NEPTUNE_ENDPOINT:
        print("ERROR: NEPTUNE_ENDPOINT env var required")
        sys.exit(1)
    print(f"Neptune: ***:{NEPTUNE_PORT}")
    print(f"Data dir: {DATA_DIR}\n")

    load_supplier_performance()
    load_contracts()
    load_defects()
    load_inventory()
    load_volume_tiers()
    verify()

    print("\nDone!")
