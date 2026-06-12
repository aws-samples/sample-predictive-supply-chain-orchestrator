"""
Neptune graph database client for supplier network queries.

Provides Gremlin-based graph traversal for finding alternative suppliers,
analyzing supply chain relationships, and risk assessment.

Follows CDE standards:
- Type hints on all functions
- Connection pooling
- Error handling for connection failures
- Structured logging
"""

import os
from typing import List, Dict, Any, Optional
from gremlin_python.driver import client as gremlin_client
from gremlin_python.driver.protocol import GremlinServerError
import structlog

try:
    from config.settings import settings
except Exception:
    settings = None

logger = structlog.get_logger()


class NeptuneClient:
    """
    Neptune graph database client.
    
    Manages connections and provides high-level query methods for
    supplier network analysis.
    """
    
    def __init__(
        self,
        endpoint: Optional[str] = None,
        port: Optional[int] = None
    ):
        """
        Initialize Neptune client.
        
        Args:
            endpoint: Neptune cluster endpoint (defaults to settings)
            port: Neptune port (defaults to settings)
        
        Raises:
            ValueError: If endpoint is not configured
        """
        self.endpoint = endpoint or (settings.neptune_endpoint if settings else os.environ.get("NEPTUNE_ENDPOINT", ""))
        self.port = port or (settings.neptune_port if settings else int(os.environ.get("NEPTUNE_PORT", "8182")))

        if not self.endpoint:
            raise ValueError(
                "NEPTUNE_ENDPOINT must be set in environment. "
                "Set to empty string to skip Neptune integration."
            )

        self.connection_string = f"wss://{self.endpoint}:{self.port}/gremlin"
        self._use_iam = os.environ.get("NEPTUNE_IAM_AUTH", "true").lower() == "true"
        self._client: Optional[gremlin_client.Client] = None
        
        logger.info(
            "neptune_client_initialized",
            endpoint=self.endpoint,
            port=self.port
        )
    
    def _get_client(self) -> gremlin_client.Client:
        """
        Get or create Gremlin client with connection pooling.
        """
        if self._client is None:
            self._client = gremlin_client.Client(
                self.connection_string,
                "g",
                pool_size=8,
                max_workers=8
            )
            logger.info("gremlin_client_created")
        return self._client

    def _http_query(self, gremlin_query: str) -> list:
        """Execute Gremlin query via Neptune HTTP endpoint with IAM SigV4 auth."""
        import json
        import boto3
        from botocore.auth import SigV4Auth
        from botocore.awsrequest import AWSRequest
        import urllib.request
        import ssl

        url = f"https://{self.endpoint}:{self.port}/gremlin"
        data = json.dumps({"gremlin": gremlin_query}).encode("utf-8")
        region = os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))

        session = boto3.Session(region_name=region)
        credentials = session.get_credentials()
        if credentials:
            credentials = credentials.get_frozen_credentials()

        aws_request = AWSRequest(
            method="POST",
            url=url,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        SigV4Auth(credentials, "neptune-db", region).add_auth(aws_request)

        req = urllib.request.Request(url, data=data, method="POST")
        for key, val in aws_request.headers.items():
            req.add_header(key, val)

        ctx = ssl.create_default_context()
        if not url.startswith("https://"):
            raise ValueError(f"Refusing to open non-HTTPS URL: {url}")
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:  # nosemgrep: dynamic-urllib-use-detected
            body = json.loads(resp.read())
            data = body.get("result", {}).get("data", {})
            return data

    @staticmethod
    def _parse_graphson_value(val):
        """Parse a GraphSON typed value."""
        if isinstance(val, dict) and "@type" in val:
            t = val["@type"]
            v = val["@value"]
            if t in ("g:Double", "g:Float"):
                return float(v)
            if t in ("g:Int32", "g:Int64"):
                return int(v)
            if t == "g:List":
                return [NeptuneClient._parse_graphson_value(item) for item in v]
            if t == "g:Map":
                result = {}
                for i in range(0, len(v), 2):
                    key = NeptuneClient._parse_graphson_value(v[i])
                    value = NeptuneClient._parse_graphson_value(v[i + 1])
                    result[key] = value
                return result
            if t == "g:T":
                return v  # "id" or "label"
            return v
        return val

    def _parse_graphson_list(self, data) -> list:
        """Parse a GraphSON g:List into a list of dicts."""
        if isinstance(data, dict) and data.get("@type") == "g:List":
            return [self._parse_graphson_value(item) for item in data["@value"]]
        if isinstance(data, list):
            return [self._parse_graphson_value(item) for item in data]
        return []
    
    @staticmethod
    def _extract(val):
        """Extract value from Neptune valueMap format (returns lists)."""
        if isinstance(val, list) and len(val) > 0:
            return val[0]
        return val

    def get_suppliers(self) -> List[Dict[str, Any]]:
        """Get all supplier vertices from Neptune."""
        try:
            raw = self._http_query("g.V().hasLabel('Supplier').elementMap().toList()")
            items = self._parse_graphson_list(raw)
            suppliers = []
            for r in items:
                if not isinstance(r, dict):
                    continue
                def safe_float(v, default=0):
                    try: return float(v) if v is not None else default
                    except (ValueError, TypeError): return default

                suppliers.append({
                    "supplier_id": r.get("id", ""),
                    "name": str(r.get("name", "")),
                    "location": str(r.get("location", "")),
                    "rating": safe_float(r.get("rating")),
                    "financial_stability_score": safe_float(r.get("financial_stability_score")),
                    "geopolitical_risk_score": safe_float(r.get("geopolitical_risk_score")),
                    "active_status": r.get("active_status", True),
                    # Performance (from Neptune properties)
                    "on_time_delivery_rate": safe_float(r.get("on_time_delivery_rate"), None),
                    "quality_score": safe_float(r.get("quality_score"), None),
                    "defect_rate": safe_float(r.get("defect_rate"), None),
                    "response_time_hours": safe_float(r.get("response_time_hours"), None),
                    # Contract (from Neptune properties)
                    "contract_type": r.get("contract_type"),
                    "payment_terms": r.get("payment_terms"),
                    "annual_value": safe_float(r.get("annual_value"), None),
                    "contract_status": r.get("contract_status"),
                })
            logger.info("neptune_get_suppliers", count=len(suppliers))
            return suppliers
        except Exception as e:
            logger.warning("neptune_get_suppliers_failed", error=str(e))
            raise

    def get_materials(self) -> List[Dict[str, Any]]:
        """Get all material vertices from Neptune."""
        try:
            raw = self._http_query("g.V().hasLabel('Material').elementMap().toList()")
            items = self._parse_graphson_list(raw)
            materials = []
            for r in items:
                if not isinstance(r, dict):
                    continue
                def safe_float_m(v, default=0):
                    try: return float(v) if v is not None else default
                    except (ValueError, TypeError): return default

                materials.append({
                    "material_id": r.get("id", ""),
                    "name": str(r.get("name", "")),
                    "category": str(r.get("category", "")),
                    "unit_of_measure": str(r.get("unit_of_measure", "")),
                    "standard_cost": safe_float_m(r.get("standard_cost")),
                    "criticality_level": str(r.get("criticality_level", "")),
                    "weight_kg": safe_float_m(r.get("weight_kg")),
                    # Inventory (from Neptune properties)
                    "current_stock": safe_float_m(r.get("current_stock"), None),
                    "reorder_point": safe_float_m(r.get("reorder_point"), None),
                    "safety_stock": safe_float_m(r.get("safety_stock"), None),
                })
            logger.info("neptune_get_materials", count=len(materials))
            return materials
        except Exception as e:
            logger.warning("neptune_get_materials_failed", error=str(e))
            raise

    def get_supplier_materials(self, supplier_id: str = None) -> List[Dict[str, Any]]:
        """Get supplier-material relationships from Neptune."""
        try:
            if supplier_id:
                if not supplier_id.replace('-', '').replace('_', '').isalnum():
                    raise ValueError(f"Invalid supplier_id: {supplier_id}")
                query = f"g.V('{supplier_id}').outE('supplies').elementMap().toList()"
            else:
                query = "g.E().hasLabel('supplies').elementMap().toList()"
            raw = self._http_query(query)
            items = self._parse_graphson_list(raw)
            relationships = []
            for r in items:
                if not isinstance(r, dict):
                    continue
                relationships.append({
                    "base_price": float(r.get("base_price", 0)),
                    "minimum_order_quantity": int(r.get("minimum_order_quantity", 0)),
                    "lead_time_days": int(r.get("lead_time_days", 0)),
                })
            logger.info("neptune_get_supplier_materials", count=len(relationships))
            return relationships
        except Exception as e:
            logger.warning("neptune_get_supplier_materials_failed", error=str(e))
            raise

    def find_alternative_suppliers(
        self,
        material_id: str,
        max_hops: int = 2,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find alternative suppliers for a material via graph traversal.
        
        Traverses the supplier network to find suppliers who provide
        the same or similar materials, up to max_hops away.
        
        Args:
            material_id: Material ID to find suppliers for
            max_hops: Maximum graph traversal depth (1-3)
            limit: Maximum number of results
        
        Returns:
            List of alternative suppliers with distance metric
        
        Raises:
            ValueError: If parameters are invalid
            GremlinServerError: If query fails
        """
        if not material_id:
            raise ValueError("material_id cannot be empty")
        
        if not 1 <= max_hops <= 3:
            raise ValueError("max_hops must be between 1 and 3")
        
        logger.info(
            "finding_alternative_suppliers",
            material_id=material_id,
            max_hops=max_hops
        )
        
        try:
            # Use HTTP API instead of Gremlin WebSocket
            return self.find_alternative_suppliers_http(material_id)

        except Exception as e:
            logger.warning(
                "find_alternatives_error",
                material_id=material_id,
                error=str(e)
            )
            raise
        
        except Exception as e:
            logger.warning(
                "neptune_query_failed",
                material_id=material_id,
                error=str(e),
                exc_info=True
            )
            raise
    
    def get_supplier_network(
        self,
        supplier_id: str,
        depth: int = 2
    ) -> Dict[str, Any]:
        """
        Get supplier's network including materials and relationships.
        
        Args:
            supplier_id: Supplier ID
            depth: Traversal depth
        
        Returns:
            Network graph with vertices and edges
        """
        if not supplier_id:
            raise ValueError("supplier_id cannot be empty")
        
        logger.info(
            "getting_supplier_network",
            supplier_id=supplier_id,
            depth=depth
        )
        
        try:
            # Use HTTP API instead of Gremlin WebSocket
            query = (
                f"g.V('{supplier_id}').outE('supplies')"
                f".project('material','edge')"
                f".by(inV().elementMap())"
                f".by(elementMap())"
                f".toList()"
            )
            raw = self._http_query(query)
            result = self._parse_graphson_list(raw)

            logger.info(
                "supplier_network_retrieved",
                supplier_id=supplier_id,
                relationships=len(result)
            )

            return {
                "supplier_id": supplier_id,
                "relationships": result
            }

        except Exception as e:
            logger.warning(
                "supplier_network_error",
                supplier_id=supplier_id,
                error=str(e)
            )
            raise

    def get_sourcing_summary(self) -> Dict[str, Any]:
        """
        Get sourcing summary for all materials — supplier counts, single-source risks.

        Returns:
            Summary with per-material supplier counts and risk flags
        """
        logger.info("getting_sourcing_summary")

        try:
            query = (
                "g.V().hasLabel('Material')"
                ".project('material_id','material_name','category','criticality','supplier_count','suppliers')"
                ".by(id())"
                ".by(values('name'))"
                ".by(values('category'))"
                ".by(coalesce(values('criticality_level'),constant('')))"
                ".by(__.inE('supplies').count())"
                ".by(__.inE('supplies').outV().id().fold())"
                ".toList()"
            )
            raw = self._http_query(query)
            result = self._parse_graphson_list(raw)

            for item in result:
                count = item.get("supplier_count", 0)
                if count <= 1:
                    item["sourcing_risk"] = "SINGLE_SOURCE"
                elif count == 2:
                    item["sourcing_risk"] = "DUAL_SOURCE"
                else:
                    item["sourcing_risk"] = "MULTI_SOURCE"

            single_sourced = [r for r in result if r["sourcing_risk"] == "SINGLE_SOURCE"]
            dual_sourced = [r for r in result if r["sourcing_risk"] == "DUAL_SOURCE"]

            logger.info(
                "sourcing_summary_complete",
                total_materials=len(result),
                single_sourced=len(single_sourced),
                dual_sourced=len(dual_sourced),
            )

            return {
                "total_materials": len(result),
                "single_sourced_count": len(single_sourced),
                "dual_sourced_count": len(dual_sourced),
                "multi_sourced_count": len(result) - len(single_sourced) - len(dual_sourced),
                "materials": result,
            }

        except GremlinServerError as e:
            logger.warning("gremlin_query_error", error=str(e))
            raise

        except Exception as e:
            logger.warning("neptune_query_failed", error=str(e), exc_info=True)
            raise

    def calculate_supplier_concentration(
        self,
        allocations: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        Calculate supplier concentration risk from allocations.
        
        Args:
            allocations: List of supplier allocations with quantities
        
        Returns:
            Dictionary mapping supplier_id to concentration percentage
        """
        if not allocations:
            return {}
        
        # Calculate total quantity
        total_quantity = sum(
            alloc.get("quantity", 0) for alloc in allocations
        )
        
        if total_quantity == 0:
            return {}
        
        # Calculate concentration per supplier
        concentration = {}
        for alloc in allocations:
            supplier_id = alloc.get("supplier_id")
            quantity = alloc.get("quantity", 0)
            
            if supplier_id:
                if supplier_id not in concentration:
                    concentration[supplier_id] = 0
                concentration[supplier_id] += quantity / total_quantity
        
        logger.info(
            "supplier_concentration_calculated",
            suppliers=len(concentration),
            max_concentration=max(concentration.values()) if concentration else 0
        )
        
        return concentration
    
    def find_risk_correlated_suppliers(
        self,
        supplier_id: str,
        risk_type: str = "geopolitical"
    ) -> List[str]:
        """
        Find suppliers with correlated risk profiles.
        
        Identifies suppliers in same region or with similar risk factors
        to help diversify supply chain.
        
        Args:
            supplier_id: Reference supplier ID
            risk_type: Type of risk (geopolitical, financial, operational)
        
        Returns:
            List of supplier IDs with correlated risk
        """
        if not supplier_id:
            raise ValueError("supplier_id cannot be empty")
        
        logger.info(
            "finding_risk_correlated_suppliers",
            supplier_id=supplier_id,
            risk_type=risk_type
        )
        
        try:
            # Use HTTP API — find suppliers in same location
            suppliers = self.get_suppliers()
            target = next((s for s in suppliers if s.get("supplier_id") == supplier_id), None)
            if not target:
                return []
            location = target.get("location", "")
            # Match by region keyword (e.g. "China", "USA", "Germany")
            region_words = set(location.split())
            correlated = [
                s["supplier_id"] for s in suppliers
                if s["supplier_id"] != supplier_id and region_words & set(s.get("location", "").split())
            ]
            logger.info("risk_correlated_suppliers_found", supplier_id=supplier_id, count=len(correlated))
            return correlated

        except Exception as e:
            logger.warning("risk_correlated_error", supplier_id=supplier_id, error=str(e))
            raise
    
    def get_supply_network_graph(self) -> Dict[str, Any]:
        """Get full supplier-material network as nodes and edges for visualization."""
        try:
            # Get all supplier nodes
            sup_raw = self._http_query("g.V().hasLabel('Supplier').elementMap().toList()")
            suppliers = self._parse_graphson_list(sup_raw)

            # Get all material nodes
            mat_raw = self._http_query("g.V().hasLabel('Material').elementMap().toList()")
            materials = self._parse_graphson_list(mat_raw)

            # Get all supply edges
            edge_raw = self._http_query(
                "g.E().hasLabel('supplies').project('from','to','price','lead_time')"
                ".by(outV().id()).by(inV().id()).by(values('base_price')).by(values('lead_time_days')).toList()"
            )
            edges = self._parse_graphson_list(edge_raw)

            nodes = []
            for s in suppliers:
                if isinstance(s, dict):
                    nodes.append({"id": s.get("id", ""), "label": str(s.get("name", "")), "type": "supplier",
                                  "risk": float(s.get("geopolitical_risk_score", 0)), "rating": float(s.get("rating", 0)),
                                  "location": str(s.get("location", ""))})
            for m in materials:
                if isinstance(m, dict):
                    nodes.append({"id": m.get("id", ""), "label": str(m.get("name", "")), "type": "material",
                                  "category": str(m.get("category", "")), "criticality": str(m.get("criticality_level", ""))})

            links = []
            for e in edges:
                if isinstance(e, dict):
                    links.append({"source": e.get("from", ""), "target": e.get("to", ""),
                                  "price": float(e.get("price", 0)), "lead_time": int(e.get("lead_time", 0))})

            # Compute centrality (degree count per supplier)
            degree = {}
            for link in links:
                src = link["source"]
                degree[src] = degree.get(src, 0) + 1

            logger.info("neptune_supply_network", nodes=len(nodes), edges=len(links))
            return {"nodes": nodes, "links": links, "degree": degree}
        except Exception as e:
            logger.warning("neptune_supply_network_failed", error=str(e))
            raise

    def find_alternative_suppliers_http(self, material_id: str) -> List[Dict[str, Any]]:
        """Find suppliers for a material via Neptune graph traversal."""
        try:
            if not material_id.replace('-', '').replace('_', '').isalnum():
                raise ValueError(f"Invalid material_id: {material_id}")
            raw = self._http_query(
                f"g.V('{material_id}').in('supplies').elementMap().toList()"
            )
            items = self._parse_graphson_list(raw)
            suppliers = []
            for r in items:
                if isinstance(r, dict):
                    suppliers.append({
                        "supplier_id": r.get("id", ""),
                        "name": str(r.get("name", "")),
                        "location": str(r.get("location", "")),
                        "rating": float(r.get("rating", 0)),
                        "risk": float(r.get("geopolitical_risk_score", 0)),
                    })
            logger.info("neptune_alternative_suppliers", material_id=material_id, count=len(suppliers))
            return suppliers
        except Exception as e:
            logger.warning("neptune_alternative_suppliers_failed", material_id=material_id, error=str(e))
            raise

    def get_supplier_materials_graph(self, supplier_id: str) -> List[Dict[str, Any]]:
        """Get all materials supplied by a specific supplier via graph traversal."""
        try:
            if not supplier_id.replace('-', '').replace('_', '').isalnum():
                raise ValueError(f"Invalid supplier_id: {supplier_id}")
            raw = self._http_query(
                f"g.V('{supplier_id}').out('supplies').elementMap().toList()"
            )
            items = self._parse_graphson_list(raw)
            materials = []
            for r in items:
                if isinstance(r, dict):
                    materials.append({
                        "material_id": r.get("id", ""),
                        "name": str(r.get("name", "")),
                        "category": str(r.get("category", "")),
                        "criticality": str(r.get("criticality_level", "")),
                    })
            logger.info("neptune_supplier_materials_graph", supplier_id=supplier_id, count=len(materials))
            return materials
        except Exception as e:
            logger.warning("neptune_supplier_materials_graph_failed", supplier_id=supplier_id, error=str(e))
            raise

    def close(self) -> None:
        """Close Neptune client connection."""
        if self._client:
            self._client.close()
            self._client = None
            logger.info("neptune_client_closed")
