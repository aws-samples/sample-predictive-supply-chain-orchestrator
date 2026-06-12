import json
import os
import uuid
from datetime import datetime
from flask import Blueprint, jsonify, request
from typing import Dict, Any
import structlog
from botocore.exceptions import ClientError

from api import state

logger = structlog.get_logger()

purchase_orders_bp = Blueprint("purchase_orders", __name__)


@purchase_orders_bp.route("/api/purchase-requisitions", methods=["POST"])
def create_purchase_requisitions() -> tuple[Dict[str, Any], int]:
    """Create purchase requisitions from optimization solution."""
    try:
        data = request.get_json()

        # Validate required fields
        if not data.get("solution_name") or not data.get("allocations") or not data.get("requester"):
            return jsonify({"error": "Missing required fields: solution_name, allocations, requester"}), 400

        # Generate PR IDs (one per supplier)
        suppliers: Dict[str, list] = {}
        for allocation in data["allocations"]:
            supplier_id = allocation["supplier_id"]
            if supplier_id not in suppliers:
                suppliers[supplier_id] = []
            suppliers[supplier_id].append(allocation)

        pr_ids = []
        total_value = 0

        for supplier_id, allocations in suppliers.items():
            pr_id = f"PR-2026-{str(len(state._local_pr_store) + len(pr_ids) + 1).zfill(3)}"
            pr_value = sum(a["quantity"] * a["unit_price"] for a in allocations)
            total_value += pr_value

            pr_data = {
                "pr_id": pr_id,
                "supplier_id": supplier_id,
                "solution_name": data["solution_name"],
                "requester": data["requester"],
                "status": "pending_approval",
                "line_items": allocations,
                "total_value": pr_value,
                "created_at": datetime.now().isoformat(),
                "notes": data.get("notes", ""),
            }

            # Write to S3 if available
            s3 = state._get_s3_client()
            if s3 and state.S3_BUCKET:
                try:
                    s3.put_object(
                        Bucket=state.S3_BUCKET,
                        Key=f"{state.S3_PREFIX}{pr_id}.json",
                        Body=json.dumps(pr_data, default=str),
                        ContentType="application/json",
                    )
                    pr_data["storage"] = "s3"
                    logger.info("pr_written_to_s3", pr_id=pr_id, bucket=state.S3_BUCKET)
                except (ClientError, ConnectionError, OSError) as s3_err:
                    logger.warning("pr_s3_write_failed", pr_id=pr_id, error=str(s3_err))
                    pr_data["storage"] = "in-memory"
            else:
                pr_data["storage"] = "in-memory"

            state._local_pr_store[pr_id] = pr_data
            pr_ids.append(pr_id)

            logger.info(
                "pr_created",
                pr_id=pr_id,
                supplier_id=supplier_id,
                value=pr_value,
                items_count=len(allocations),
            )

        response = {
            "pr_ids": pr_ids,
            "total_prs": len(pr_ids),
            "total_value": total_value,
            "status": "pending_approval",
            "solution_name": data["solution_name"],
            "requester": data["requester"],
            "created_at": datetime.now().isoformat(),
        }

        logger.info(
            "prs_created_successfully",
            total_prs=len(pr_ids),
            total_value=total_value,
        )

        return jsonify(response), 201

    except (ValueError, KeyError, TypeError) as e:
        logger.error("create_prs_failed", error=str(e))
        return jsonify({"error": str(e)}), 500


@purchase_orders_bp.route("/api/purchase-requisitions", methods=["GET"])
def get_purchase_requisitions() -> tuple[Dict[str, Any], int]:
    """Get all purchase requisitions."""
    try:
        status_filter = request.args.get("status")
        requester_filter = request.args.get("requester")

        # Merge local and agent PR stores
        all_prs = dict(state._local_pr_store)
        if state._pr_store:
            all_prs.update(state._pr_store)

        # Try reading from S3 if available and local store is empty
        s3 = state._get_s3_client()
        if s3 and state.S3_BUCKET and not all_prs:
            try:
                resp = s3.list_objects_v2(Bucket=state.S3_BUCKET, Prefix=state.S3_PREFIX, MaxKeys=100)
                for obj in resp.get("Contents", []):
                    pr_obj = s3.get_object(Bucket=state.S3_BUCKET, Key=obj["Key"])
                    pr_data = json.loads(pr_obj["Body"].read())
                    all_prs[pr_data.get("pr_id", obj["Key"])] = pr_data
            except (ConnectionError, OSError) as s3_err:
                logger.warning("s3_list_prs_failed", error=str(s3_err))

        prs = list(all_prs.values())

        if status_filter:
            prs = [p for p in prs if p.get("status") == status_filter]
        if requester_filter:
            prs = [p for p in prs if p.get("requester") == requester_filter]

        logger.info("get_prs_request", status_filter=status_filter, total=len(prs))

        return jsonify({
            "purchase_requisitions": prs,
            "total": len(prs),
        }), 200

    except (ValueError, KeyError, TypeError) as e:
        logger.error("get_prs_failed", error=str(e))
        return jsonify({"error": str(e)}), 500


@purchase_orders_bp.route("/api/purchase-requisitions/<pr_id>", methods=["GET"])
def get_purchase_requisition(pr_id: str) -> tuple[Dict[str, Any], int]:
    """Get purchase requisition by ID."""
    try:
        logger.info("get_pr_by_id", pr_id=pr_id)

        # Check local stores
        pr_data = state._local_pr_store.get(pr_id) or state._pr_store.get(pr_id)

        # Try S3 if not found locally
        if not pr_data:
            s3 = state._get_s3_client()
            if s3 and state.S3_BUCKET:
                try:
                    obj = s3.get_object(Bucket=state.S3_BUCKET, Key=f"{state.S3_PREFIX}{pr_id}.json")
                    pr_data = json.loads(obj["Body"].read())
                except (ConnectionError, OSError) as _s3_err:
                    pass

        if pr_data:
            return jsonify(pr_data), 200

        return jsonify({"error": "PR not found"}), 404

    except (ValueError, KeyError, TypeError) as e:
        logger.error("get_pr_by_id_failed", pr_id=pr_id, error=str(e))
        return jsonify({"error": str(e)}), 500


@purchase_orders_bp.route("/api/purchase-requisitions/<pr_id>/approve", methods=["POST"])
def approve_purchase_requisition(pr_id: str) -> tuple[Dict[str, Any], int]:
    """Approve a purchase requisition."""
    try:
        data = request.get_json()
        approver = data.get("approver", "unknown")

        logger.info("pr_approved", pr_id=pr_id, approver=approver)

        return jsonify({
            "pr_id": pr_id,
            "status": "approved",
            "approved_by": approver,
            "approved_at": datetime.now().isoformat(),
            "message": "PR approved successfully. In production, this would trigger PO creation in ERP.",
        }), 200

    except (ValueError, KeyError, TypeError) as e:
        logger.error("approve_pr_failed", pr_id=pr_id, error=str(e))
        return jsonify({"error": str(e)}), 500


@purchase_orders_bp.route("/api/purchase-requisitions/export-sap", methods=["POST"])
def export_sap_odata() -> tuple[Dict[str, Any], int]:
    """Export purchase requisitions as SAP OData JSON and write to S3."""
    try:
        data = request.get_json()
        solution_name = data.get("solution_name", "Unknown")
        allocations = data.get("allocations", [])
        requester = data.get("requester", "procurement@voltcycle.com")

        if not allocations:
            return jsonify({"error": "No allocations provided"}), 400

        # Group by supplier
        by_supplier: Dict[str, list] = {}
        for alloc in allocations:
            sid = alloc.get("supplier_id", "UNKNOWN")
            by_supplier.setdefault(sid, []).append(alloc)

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        s3_prefix = f"sap-exports/{solution_name.replace(' ', '-').lower()}-{timestamp}/"

        odata_documents = []
        s3_keys: list[str] = []

        for idx, (supplier_id, items) in enumerate(by_supplier.items()):
            pr_number = 10020000 + idx + 1
            supplier_name = items[0].get("supplier_name", supplier_id)

            # Build SAP OData JSON (API_PURCHASEREQ_PROCESS_SRV format)
            odata_items = []
            for item_idx, item in enumerate(items):
                delivery_date = (datetime.now() + __import__("datetime").timedelta(
                    days=item.get("lead_time_days", 30)
                )).strftime("%Y-%m-%dT00:00:00")

                odata_items.append({
                    "PurchaseRequisitionItem": str((item_idx + 1) * 10).zfill(5),
                    "PurchaseRequisitionItemText": item.get("material_name", ""),
                    "Material": item.get("material_id", ""),
                    "Plant": "1100",
                    "RequestedQuantity": str(item.get("quantity", 0)),
                    "BaseUnit": "EA",
                    "PurchaseRequisitionPrice": str(item.get("unit_price", 0)),
                    "PurReqnItemCurrency": "USD",
                    "DeliveryDate": delivery_date,
                    "FixedSupplier": supplier_id,
                    "PurchasingOrganization": "1000",
                    "PurchasingGroup": "001",
                    "AccountAssignmentCategory": "K",
                })

            odata_doc = {
                "__metadata": {
                    "uri": f"A_PurchaseRequisitionHeader('{pr_number}')",
                    "type": "API_PURCHASEREQ_PROCESS_SRV.A_PurchaseRequisitionHeaderType",
                },
                "PurchaseRequisition": str(pr_number),
                "PurchaseRequisitionType": "NB",
                "PurReqnDescription": f"{solution_name} - {supplier_name}",
                "Requester": requester,
                "to_PurchaseReqnItem": {"results": odata_items},
            }

            odata_documents.append(odata_doc)

            # Write to S3
            s3 = state._get_s3_client()
            s3_key = f"{s3_prefix}PR-{pr_number}-{supplier_id}.json"
            if s3 and state.S3_BUCKET:
                try:
                    s3.put_object(
                        Bucket=state.S3_BUCKET,
                        Key=s3_key,
                        Body=json.dumps(odata_doc, indent=2, default=str),
                        ContentType="application/json",
                    )
                    s3_keys.append(s3_key)
                    logger.info("sap_odata_written", key=s3_key)
                except (ClientError, ConnectionError, OSError) as s3_err:
                    logger.warning("sap_odata_s3_failed", key=s3_key, error=str(s3_err))

        response = {
            "export_id": f"{solution_name.replace(' ', '-').lower()}-{timestamp}",
            "solution_name": solution_name,
            "total_documents": len(odata_documents),
            "s3_prefix": s3_prefix,
            "s3_keys": s3_keys,
            "odata_documents": odata_documents,
            "created_at": datetime.now().isoformat(),
        }

        logger.info("sap_odata_exported", total=len(odata_documents), prefix=s3_prefix)
        return jsonify(response), 201

    except (ValueError, KeyError, TypeError) as e:
        logger.error("sap_odata_export_failed", error=str(e))
        return jsonify({"error": str(e)}), 500
