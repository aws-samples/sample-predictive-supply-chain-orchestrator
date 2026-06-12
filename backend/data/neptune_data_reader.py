"""
Neptune data reader with caching and validation.

Reads procurement data from Amazon Neptune graph database and returns Pydantic models.
Implements in-memory caching for performance using HTTP endpoint with SigV4 auth.

Follows CDE standards:
- Type hints
- Error handling
- Pydantic validation
- Structured logging
"""

import os
import json
import boto3
from typing import List, Optional, Dict, Any
from functools import lru_cache
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import urllib.request
import ssl
from datetime import datetime, date
import structlog

# Import Pydantic models from csv_reader
from data.csv_reader import (
    Supplier,
    Material,
    SupplierMaterial,
    VolumeTier,
    SupplierPerformance,
    SupplierContract
)

logger = structlog.get_logger()


class NeptuneDataReader:
    """
    Neptune data reader with caching.

    Reads procurement data from Neptune graph database via HTTP/Gremlin queries
    with SigV4 authentication. Validates data using Pydantic models.
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        port: Optional[int] = None
    ):
        """
        Initialize Neptune data reader.

        Args:
            endpoint: Neptune cluster endpoint (defaults to NEPTUNE_ENDPOINT env var)
            port: Neptune port (defaults to NEPTUNE_PORT env var or 8182)

        Raises:
            ValueError: If endpoint is not configured
        """
        self.endpoint = endpoint or os.environ.get("NEPTUNE_ENDPOINT", "")
        self.port = port or int(os.environ.get("NEPTUNE_PORT", "8182"))

        if not self.endpoint:
            raise ValueError(
                "NEPTUNE_ENDPOINT must be set in environment or passed to constructor."
            )

        self.region = os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))

        # Cache for non-lru_cache methods
        self._cache: Dict[str, Any] = {}

        logger.info(
            "neptune_data_reader_initialized",
            endpoint=self.endpoint,
            port=self.port,
            region=self.region
        )

    def _http_query(self, gremlin_query: str) -> Any:
        """
        Execute Gremlin query via Neptune HTTP endpoint with IAM SigV4 auth.

        Args:
            gremlin_query: Gremlin query string

        Returns:
            Raw query result data from Neptune

        Raises:
            Exception: If query fails
        """
        url = f"https://{self.endpoint}:{self.port}/gremlin"
        data = json.dumps({"gremlin": gremlin_query}).encode("utf-8")

        # Get AWS credentials
        session = boto3.Session(region_name=self.region)
        credentials = session.get_credentials()
        if credentials:
            credentials = credentials.get_frozen_credentials()

        # Create AWS request with SigV4 auth
        aws_request = AWSRequest(
            method="POST",
            url=url,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        SigV4Auth(credentials, "neptune-db", self.region).add_auth(aws_request)

        # Execute HTTP request
        req = urllib.request.Request(url, data=data, method="POST")
        for key, val in aws_request.headers.items():
            req.add_header(key, val)

        ctx = ssl.create_default_context()
        try:
            if not url.startswith("https://"):
                raise ValueError(f"Refusing to open non-HTTPS URL: {url}")
            with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:  # nosemgrep: dynamic-urllib-use-detected
                body = json.loads(resp.read())
                data = body.get("result", {}).get("data", {})
                return data
        except Exception as e:
            logger.warning("neptune_http_query_failed", error=str(e), query=gremlin_query[:100])
            raise

    def _parse_results(self, raw: Any) -> List[Dict[str, Any]]:
        """
        Parse GraphSON results into plain Python dictionaries.

        Handles GraphSON g:List and g:Map structures, converting typed values
        to plain Python types.

        Args:
            raw: Raw GraphSON data from Neptune

        Returns:
            List of plain dictionaries
        """
        def parse_value(val: Any) -> Any:
            """Recursively parse GraphSON typed values."""
            if isinstance(val, dict) and "@type" in val:
                t = val["@type"]
                v = val["@value"]

                if t in ("g:Double", "g:Float"):
                    return float(v)
                if t in ("g:Int32", "g:Int64"):
                    return int(v)
                if t == "g:List":
                    return [parse_value(item) for item in v]
                if t == "g:Map":
                    result = {}
                    for i in range(0, len(v), 2):
                        key = parse_value(v[i])
                        value = parse_value(v[i + 1])
                        result[key] = value
                    return result
                if t == "g:T":
                    return v  # "id" or "label"
                return v
            return val

        # Handle top-level g:List structure
        if isinstance(raw, dict) and raw.get("@type") == "g:List":
            return [parse_value(item) for item in raw["@value"]]
        if isinstance(raw, list):
            return [parse_value(item) for item in raw]

        return []

    @lru_cache(maxsize=1)
    def get_suppliers(self) -> List[Supplier]:
        """
        Read and cache suppliers from Neptune.

        Returns:
            List of validated Supplier models

        Raises:
            ValueError: If validation fails
        """
        logger.info("reading_suppliers_from_neptune")

        try:
            # Query Neptune for all Supplier vertices
            raw = self._http_query("g.V().hasLabel('Supplier').elementMap().toList()")
            items = self._parse_results(raw)

            suppliers = []
            for item in items:
                if not isinstance(item, dict):
                    logger.warning("skipping_non_dict_supplier", item=str(item)[:100])
                    continue

                try:
                    # Helper to safely convert values
                    def safe_str(v, default=""):
                        return str(v) if v is not None else default

                    def safe_float(v, default=0.0):
                        try:
                            return float(v) if v is not None else default
                        except (ValueError, TypeError):
                            return default

                    def safe_int(v, default=0):
                        try:
                            return int(v) if v is not None else default
                        except (ValueError, TypeError):
                            return default

                    def safe_bool(v, default=True):
                        if isinstance(v, bool):
                            return v
                        if isinstance(v, str):
                            return v.upper() in ("TRUE", "1", "YES")
                        return default

                    # Build supplier dict matching Pydantic model
                    supplier_data = {
                        "supplier_id": safe_str(item.get("id")),
                        "name": safe_str(item.get("name")),
                        "location": safe_str(item.get("location")),
                        "rating": safe_float(item.get("rating")),
                        "lead_time_days": safe_int(item.get("lead_time_days"), 1),
                        "payment_terms": safe_str(item.get("payment_terms")),
                        "financial_stability_score": safe_float(item.get("financial_stability_score")),
                        "geopolitical_risk_score": safe_float(item.get("geopolitical_risk_score")),
                        "active_status": safe_bool(item.get("active_status")),
                        "contact_email": safe_str(item.get("contact_email")),
                        "contact_phone": safe_str(item.get("contact_phone"))
                    }

                    suppliers.append(Supplier(**supplier_data))

                except Exception as e:
                    logger.warning(
                        "skipping_invalid_supplier",
                        error=str(e),
                        item=str(item)[:100]
                    )
                    continue

            logger.info("suppliers_loaded_from_neptune", count=len(suppliers))
            return suppliers

        except Exception as e:
            logger.warning("suppliers_load_from_neptune_failed", error=str(e))
            raise ValueError(f"Failed to load suppliers from Neptune: {e}")

    @lru_cache(maxsize=1)
    def get_materials(self) -> List[Material]:
        """
        Read and cache materials from Neptune.

        Returns:
            List of validated Material models

        Raises:
            ValueError: If validation fails
        """
        logger.info("reading_materials_from_neptune")

        try:
            # Query Neptune for all Material vertices
            raw = self._http_query("g.V().hasLabel('Material').elementMap().toList()")
            items = self._parse_results(raw)

            materials = []
            for item in items:
                if not isinstance(item, dict):
                    logger.warning("skipping_non_dict_material", item=str(item)[:100])
                    continue

                try:
                    # Helper to safely convert values
                    def safe_str(v, default=""):
                        return str(v) if v is not None else default

                    def safe_float(v, default=0.0):
                        try:
                            return float(v) if v is not None else default
                        except (ValueError, TypeError):
                            return default

                    # Build material dict matching Pydantic model
                    material_data = {
                        "material_id": safe_str(item.get("id")),
                        "name": safe_str(item.get("name")),
                        "category": safe_str(item.get("category")),
                        "unit_of_measure": safe_str(item.get("unit_of_measure")),
                        "standard_cost": safe_float(item.get("standard_cost"), 0.01),
                        "criticality_level": safe_str(item.get("criticality_level")),
                        "weight_kg": safe_float(item.get("weight_kg"), 0.01)
                    }

                    materials.append(Material(**material_data))

                except Exception as e:
                    logger.warning(
                        "skipping_invalid_material",
                        error=str(e),
                        item=str(item)[:100]
                    )
                    continue

            logger.info("materials_loaded_from_neptune", count=len(materials))
            return materials

        except Exception as e:
            logger.warning("materials_load_from_neptune_failed", error=str(e))
            raise ValueError(f"Failed to load materials from Neptune: {e}")

    @lru_cache(maxsize=1)
    def get_supplier_materials(self) -> List[SupplierMaterial]:
        """
        Read and cache supplier-material relationships from Neptune.

        Queries edges labeled 'supplies' with source and target vertex IDs.

        Returns:
            List of validated SupplierMaterial models

        Raises:
            ValueError: If validation fails
        """
        logger.info("reading_supplier_materials_from_neptune")

        try:
            # Query Neptune for all 'supplies' edges with source and target IDs
            raw = self._http_query(
                "g.E().hasLabel('supplies').project('edge','src','dst')"
                ".by(elementMap()).by(outV().id()).by(inV().id()).toList()"
            )
            items = self._parse_results(raw)

            supplier_materials = []
            for item in items:
                if not isinstance(item, dict):
                    logger.warning("skipping_non_dict_supplier_material", item=str(item)[:100])
                    continue

                try:
                    # Extract edge properties and vertex IDs
                    edge_props = item.get("edge", {})
                    supplier_id = item.get("src", "")
                    material_id = item.get("dst", "")

                    # Helper to safely convert values
                    def safe_str(v, default=""):
                        return str(v) if v is not None else default

                    def safe_float(v, default=0.0):
                        try:
                            return float(v) if v is not None else default
                        except (ValueError, TypeError):
                            return default

                    def safe_int(v, default=0):
                        try:
                            return int(v) if v is not None else default
                        except (ValueError, TypeError):
                            return default

                    def safe_date(v, default=None):
                        """Parse date from string or return date object."""
                        if isinstance(v, date):
                            return v
                        if isinstance(v, str):
                            try:
                                return datetime.strptime(v, "%Y-%m-%d").date()
                            except ValueError:
                                try:
                                    # Try alternative format
                                    return datetime.fromisoformat(v).date()
                                except ValueError:
                                    return default or date.today()
                        return default or date.today()

                    # Build supplier_material dict matching Pydantic model
                    supplier_material_data = {
                        "supplier_material_id": safe_str(edge_props.get("id")),
                        "supplier_id": safe_str(supplier_id),
                        "material_id": safe_str(material_id),
                        "base_price": safe_float(edge_props.get("base_price"), 0.01),
                        "currency": safe_str(edge_props.get("currency"), "USD"),
                        "effective_date": safe_date(edge_props.get("effective_date")),
                        "minimum_order_quantity": safe_int(edge_props.get("minimum_order_quantity"), 1),
                        "lead_time_days": safe_int(edge_props.get("lead_time_days"), 1),
                        "quality_certification": safe_str(edge_props.get("quality_certification")),
                        "sustainability_score": safe_float(edge_props.get("sustainability_score")),
                        "carbon_footprint_kg": safe_float(edge_props.get("carbon_footprint_kg"))
                    }

                    supplier_materials.append(SupplierMaterial(**supplier_material_data))

                except Exception as e:
                    logger.warning(
                        "skipping_invalid_supplier_material",
                        error=str(e),
                        item=str(item)[:100]
                    )
                    continue

            logger.info("supplier_materials_loaded_from_neptune", count=len(supplier_materials))
            return supplier_materials

        except Exception as e:
            logger.warning("supplier_materials_load_from_neptune_failed", error=str(e))
            raise ValueError(f"Failed to load supplier materials from Neptune: {e}")

    # Simple lookup methods (filter cached data)

    def get_supplier_by_id(self, supplier_id: str) -> Optional[Supplier]:
        """
        Get supplier by ID.

        Args:
            supplier_id: Supplier ID (e.g., SUP-001)

        Returns:
            Supplier model or None if not found
        """
        suppliers = self.get_suppliers()
        for supplier in suppliers:
            if supplier.supplier_id == supplier_id:
                return supplier
        return None

    def get_material_by_id(self, material_id: str) -> Optional[Material]:
        """
        Get material by ID.

        Args:
            material_id: Material ID (e.g., MAT-BAT-001)

        Returns:
            Material model or None if not found
        """
        materials = self.get_materials()
        for material in materials:
            if material.material_id == material_id:
                return material
        return None

    def get_suppliers_for_material(self, material_id: str) -> List[SupplierMaterial]:
        """
        Get all suppliers that can provide a material.

        Args:
            material_id: Material ID (e.g., MAT-BAT-001)

        Returns:
            List of SupplierMaterial relationships
        """
        supplier_materials = self.get_supplier_materials()
        return [
            sm for sm in supplier_materials
            if sm.material_id == material_id
        ]

    # Neptune query methods with caching

    def get_performance_history(self, supplier_id: str) -> List[SupplierPerformance]:
        """
        Get all performance records for a supplier.

        Queries Neptune supplier vertex properties for performance metrics.
        Returns records sorted by measurement_period descending (most recent first).

        Args:
            supplier_id: Supplier ID (e.g., SUP-001)

        Returns:
            List of SupplierPerformance models sorted by measurement_period
        """
        cache_key = f"perf_{supplier_id}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        logger.info("reading_performance_history_from_neptune", supplier_id=supplier_id)

        try:
            # Query Neptune for supplier vertex properties
            query = f"g.V('{supplier_id}').elementMap().toList()"
            raw = self._http_query(query)
            items = self._parse_results(raw)

            if not items or len(items) == 0:
                logger.warning("no_performance_data_for_supplier", supplier_id=supplier_id)
                self._cache[cache_key] = []
                return []

            # Neptune stores performance as properties on Supplier vertices
            # Extract performance metrics from vertex properties
            performance_records = []
            for item in items:
                if not isinstance(item, dict):
                    continue

                try:
                    def safe_str(v, default=""):
                        return str(v) if v is not None else default

                    def safe_float(v, default=0.0):
                        try:
                            return float(v) if v is not None else default
                        except (ValueError, TypeError):
                            return default

                    def safe_int(v, default=0):
                        try:
                            return int(v) if v is not None else default
                        except (ValueError, TypeError):
                            return default

                    # Build performance record
                    # Use current month as measurement_period if not stored
                    measurement_period = safe_str(
                        item.get("measurement_period"),
                        datetime.now().strftime("%Y-%m")
                    )

                    performance_data = {
                        "performance_id": f"PERF-{supplier_id}-{measurement_period}",
                        "supplier_id": supplier_id,
                        "measurement_period": measurement_period,
                        "on_time_delivery_rate": safe_float(item.get("on_time_delivery_rate"), 95.0),
                        "quality_score": safe_float(item.get("quality_score"), 8.0),
                        "defect_rate": safe_float(item.get("defect_rate"), 0.5),
                        "cost_variance": safe_float(item.get("cost_variance"), 0.0),
                        "response_time_hours": safe_int(item.get("response_time_hours"), 24)
                    }

                    performance_records.append(SupplierPerformance(**performance_data))

                except Exception as e:
                    logger.warning(
                        "skipping_invalid_performance_record",
                        error=str(e),
                        supplier_id=supplier_id
                    )
                    continue

            # Sort by measurement_period descending
            performance_records.sort(key=lambda p: p.measurement_period, reverse=True)

            self._cache[cache_key] = performance_records
            logger.info(
                "performance_history_loaded_from_neptune",
                supplier_id=supplier_id,
                count=len(performance_records)
            )
            return performance_records

        except Exception as e:
            logger.error(
                "performance_history_load_from_neptune_failed",
                error=str(e),
                supplier_id=supplier_id
            )
            # Return empty list on error (graceful degradation)
            self._cache[cache_key] = []
            return []

    def get_latest_performance(self, supplier_id: str) -> Optional[SupplierPerformance]:
        """
        Get latest performance record for a supplier.

        Args:
            supplier_id: Supplier ID (e.g., SUP-001)

        Returns:
            Latest SupplierPerformance model or None
        """
        history = self.get_performance_history(supplier_id)
        return history[0] if history else None

    def get_contract_for_supplier(self, supplier_id: str) -> Optional[SupplierContract]:
        """
        Get active contract for a supplier.

        Queries Neptune supplier vertex properties for contract information.

        Args:
            supplier_id: Supplier ID (e.g., SUP-001)

        Returns:
            SupplierContract model or None if no active contract
        """
        cache_key = f"contract_{supplier_id}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        logger.info("reading_contract_from_neptune", supplier_id=supplier_id)

        try:
            # Query Neptune for supplier vertex properties
            query = f"g.V('{supplier_id}').elementMap().toList()"
            raw = self._http_query(query)
            items = self._parse_results(raw)

            if not items or len(items) == 0:
                logger.warning("no_contract_data_for_supplier", supplier_id=supplier_id)
                self._cache[cache_key] = None
                return None

            item = items[0]
            if not isinstance(item, dict):
                self._cache[cache_key] = None
                return None

            try:
                def safe_str(v, default=""):
                    return str(v) if v is not None else default

                def safe_float(v, default=0.0):
                    try:
                        return float(v) if v is not None else default
                    except (ValueError, TypeError):
                        return default

                def safe_date(v, default=None):
                    """Parse date from string or return date object."""
                    if isinstance(v, date):
                        return v
                    if isinstance(v, str):
                        try:
                            return datetime.strptime(v, "%Y-%m-%d").date()
                        except ValueError:
                            try:
                                return datetime.fromisoformat(v).date()
                            except ValueError:
                                return default or date.today()
                    return default or date.today()

                # Build contract from supplier properties
                contract_type = safe_str(item.get("contract_type"), "Standard")
                payment_terms = safe_str(item.get("payment_terms"), "Net 30")
                annual_value = safe_float(item.get("annual_value"), 100000.0)

                # Only return contract if we have meaningful contract data
                if not item.get("contract_type"):
                    logger.info("no_contract_properties_for_supplier", supplier_id=supplier_id)
                    self._cache[cache_key] = None
                    return None

                contract_data = {
                    "contract_id": f"CONTRACT-{supplier_id}",
                    "supplier_id": supplier_id,
                    "contract_type": contract_type,
                    "start_date": safe_date(item.get("contract_start_date")),
                    "end_date": safe_date(item.get("contract_end_date")),
                    "annual_value": annual_value,
                    "payment_terms": payment_terms,
                    "volume_commitment": safe_str(item.get("volume_commitment"), "None"),
                    "price_adjustment_clause": safe_str(item.get("price_adjustment_clause"), ""),
                    "sustainability_clause": safe_str(item.get("sustainability_clause"), ""),
                    "status": safe_str(item.get("contract_status"), "Active"),
                    "renewal_option": safe_str(item.get("renewal_option"), "")
                }

                contract = SupplierContract(**contract_data)
                self._cache[cache_key] = contract
                logger.info("contract_loaded_from_neptune", supplier_id=supplier_id)
                return contract

            except Exception as e:
                logger.warning(
                    "invalid_contract_data",
                    error=str(e),
                    supplier_id=supplier_id
                )
                self._cache[cache_key] = None
                return None

        except Exception as e:
            logger.error(
                "contract_load_from_neptune_failed",
                error=str(e),
                supplier_id=supplier_id
            )
            self._cache[cache_key] = None
            return None

    def get_volume_tiers_for_supplier_material(
        self, supplier_material_id: str
    ) -> List[VolumeTier]:
        """
        Get volume discount tiers for a supplier-material relationship.

        Queries Neptune edge property 'volume_tiers' (stored as JSON string).

        Args:
            supplier_material_id: SupplierMaterial ID (e.g., SM-001)

        Returns:
            List of VolumeTier models sorted by min_quantity
        """
        cache_key = f"tiers_{supplier_material_id}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        logger.info(
            "reading_volume_tiers_from_neptune",
            supplier_material_id=supplier_material_id
        )

        try:
            # Query Neptune for edge with this ID
            query = f"g.E('{supplier_material_id}').elementMap().toList()"
            raw = self._http_query(query)
            items = self._parse_results(raw)

            if not items or len(items) == 0:
                logger.warning(
                    "no_volume_tiers_for_supplier_material",
                    supplier_material_id=supplier_material_id
                )
                self._cache[cache_key] = []
                return []

            item = items[0]
            if not isinstance(item, dict):
                self._cache[cache_key] = []
                return []

            # Extract volume_tiers property (stored as JSON string)
            volume_tiers_json = item.get("volume_tiers")
            if not volume_tiers_json:
                logger.info(
                    "no_volume_tiers_property",
                    supplier_material_id=supplier_material_id
                )
                self._cache[cache_key] = []
                return []

            # Parse JSON
            try:
                if isinstance(volume_tiers_json, str):
                    tiers_data = json.loads(volume_tiers_json)
                else:
                    tiers_data = volume_tiers_json

                if not isinstance(tiers_data, list):
                    logger.warning(
                        "volume_tiers_not_a_list",
                        supplier_material_id=supplier_material_id
                    )
                    self._cache[cache_key] = []
                    return []

                volume_tiers = []
                for tier_dict in tiers_data:
                    try:
                        # Add supplier_material_id if not present
                        if "supplier_material_id" not in tier_dict:
                            tier_dict["supplier_material_id"] = supplier_material_id

                        # Generate tier_id if not present
                        if "tier_id" not in tier_dict:
                            tier_level = tier_dict.get("tier_level", 1)
                            tier_dict["tier_id"] = f"{supplier_material_id}-T{tier_level}"

                        volume_tiers.append(VolumeTier(**tier_dict))

                    except Exception as e:
                        logger.warning(
                            "skipping_invalid_volume_tier",
                            error=str(e),
                            tier=str(tier_dict)[:100]
                        )
                        continue

                # Sort by min_quantity
                volume_tiers.sort(key=lambda t: t.min_quantity)

                self._cache[cache_key] = volume_tiers
                logger.info(
                    "volume_tiers_loaded_from_neptune",
                    supplier_material_id=supplier_material_id,
                    count=len(volume_tiers)
                )
                return volume_tiers

            except json.JSONDecodeError as e:
                logger.error(
                    "volume_tiers_json_parse_failed",
                    error=str(e),
                    supplier_material_id=supplier_material_id
                )
                self._cache[cache_key] = []
                return []

        except Exception as e:
            logger.error(
                "volume_tiers_load_from_neptune_failed",
                error=str(e),
                supplier_material_id=supplier_material_id
            )
            self._cache[cache_key] = []
            return []

    def get_supplier_defect_score(self, supplier_id: str) -> float:
        """
        Calculate a defect risk score (0-10) for a supplier.

        Queries Neptune for defect records connected to supplier via 'has_defect' edges.
        Considers: severity weighting, open vs resolved status, and recall history.

        Severity weights: CRITICAL=3.0, MAJOR=2.0, MINOR=1.0
        Status multipliers: OPEN=1.5, RESOLVED=0.8, CLOSED=0.5
        Recall multiplier: 1.5 if recall_initiated

        Args:
            supplier_id: Supplier ID (e.g., SUP-001)

        Returns:
            Defect score (0-10), capped at 10.0. Returns 0.0 if no defects.
        """
        cache_key = f"defect_score_{supplier_id}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        logger.info("calculating_defect_score_from_neptune", supplier_id=supplier_id)

        try:
            # Query Neptune for defect records
            query = f"g.V('{supplier_id}').outE('has_defect').inV().elementMap().toList()"
            raw = self._http_query(query)
            items = self._parse_results(raw)

            if not items or len(items) == 0:
                logger.info("no_defects_for_supplier", supplier_id=supplier_id)
                self._cache[cache_key] = 0.0
                return 0.0

            # Weight and multiplier configurations
            severity_weights = {"CRITICAL": 3.0, "MAJOR": 2.0, "MINOR": 1.0}
            status_multiplier = {"OPEN": 1.5, "RESOLVED": 0.8, "CLOSED": 0.5}

            total_score = 0.0
            defect_count = 0

            for item in items:
                if not isinstance(item, dict):
                    continue

                try:
                    severity = str(item.get("severity", "MINOR")).upper()
                    status = str(item.get("status", "RESOLVED")).upper()
                    recall_initiated = item.get("recall_initiated", False)

                    # Convert string boolean if needed
                    if isinstance(recall_initiated, str):
                        recall_initiated = recall_initiated.upper() in ("TRUE", "1", "YES")

                    # Calculate score for this defect
                    base = severity_weights.get(severity, 1.0)
                    status_mult = status_multiplier.get(status, 1.0)
                    recall_mult = 1.5 if recall_initiated else 1.0

                    defect_score = base * status_mult * recall_mult
                    total_score += defect_score
                    defect_count += 1

                except Exception as e:
                    logger.warning(
                        "skipping_invalid_defect_record",
                        error=str(e),
                        supplier_id=supplier_id
                    )
                    continue

            # Cap at 10.0
            final_score = min(10.0, total_score)

            self._cache[cache_key] = final_score
            logger.info(
                "defect_score_calculated",
                supplier_id=supplier_id,
                defect_count=defect_count,
                score=final_score
            )
            return final_score

        except Exception as e:
            logger.error(
                "defect_score_calculation_failed",
                error=str(e),
                supplier_id=supplier_id
            )
            # Return 0.0 on error (graceful degradation)
            self._cache[cache_key] = 0.0
            return 0.0
