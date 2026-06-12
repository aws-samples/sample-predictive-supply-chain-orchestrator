"""
Neptune data migration script.

Loads CSV data into Neptune graph database with upsert logic.
Creates supplier and material vertices, and "supplies" edges.

Follows CDE standards:
- Type hints
- Error handling
- Structured logging
- CLI arguments
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional

import structlog
from gremlin_python.driver.protocol import GremlinServerError

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.csv_reader import CSVDataReader
from data.neptune_client import NeptuneClient

logger = structlog.get_logger()


class NeptuneMigration:
    """Neptune data migration manager."""

    def __init__(
        self,
        neptune_endpoint: str,
        csv_dir: str,
        dry_run: bool = False
    ):
        """
        Initialize migration.

        Args:
            neptune_endpoint: Neptune cluster endpoint
            csv_dir: Directory containing CSV files
            dry_run: If True, validate but don't write to Neptune
        """
        self.neptune_endpoint = neptune_endpoint
        self.csv_dir = csv_dir
        self.dry_run = dry_run

        self.data_reader = CSVDataReader(csv_dir)
        self.neptune_client = NeptuneClient(endpoint=neptune_endpoint)

        logger.info(
            "migration_initialized",
            neptune_endpoint=neptune_endpoint,
            csv_dir=csv_dir,
            dry_run=dry_run
        )

    def migrate(self) -> Dict[str, int]:
        """
        Execute full migration.

        Returns:
            Dictionary with counts of created/updated entities

        Raises:
            ValueError: If migration fails
        """
        logger.info("migration_started")

        stats = {
            "suppliers_created": 0,
            "suppliers_updated": 0,
            "materials_created": 0,
            "materials_updated": 0,
            "edges_created": 0,
            "edges_updated": 0,
            "errors": 0
        }

        try:
            # Load data from CSV
            suppliers = self.data_reader.get_suppliers()
            materials = self.data_reader.get_materials()
            supplier_materials = self.data_reader.get_supplier_materials()

            logger.info(
                "data_loaded",
                suppliers=len(suppliers),
                materials=len(materials),
                relationships=len(supplier_materials)
            )

            if self.dry_run:
                logger.info("dry_run_mode_validation_only")
                return stats

            # Create supplier vertices
            for supplier in suppliers:
                try:
                    created = self._upsert_supplier(supplier)
                    if created:
                        stats["suppliers_created"] += 1
                    else:
                        stats["suppliers_updated"] += 1
                except Exception as e:
                    logger.error(
                        "supplier_upsert_failed",
                        supplier_id=supplier.supplier_id,
                        error=str(e)
                    )
                    stats["errors"] += 1

            # Create material vertices
            for material in materials:
                try:
                    created = self._upsert_material(material)
                    if created:
                        stats["materials_created"] += 1
                    else:
                        stats["materials_updated"] += 1
                except Exception as e:
                    logger.error(
                        "material_upsert_failed",
                        material_id=material.material_id,
                        error=str(e)
                    )
                    stats["errors"] += 1

            # Create "supplies" edges
            for sm in supplier_materials:
                try:
                    created = self._upsert_supplies_edge(sm)
                    if created:
                        stats["edges_created"] += 1
                    else:
                        stats["edges_updated"] += 1
                except Exception as e:
                    logger.error(
                        "edge_upsert_failed",
                        supplier_id=sm.supplier_id,
                        material_id=sm.material_id,
                        error=str(e)
                    )
                    stats["errors"] += 1

            logger.info("migration_complete", **stats)
            return stats

        except Exception as e:
            logger.error("migration_failed", error=str(e), exc_info=True)
            raise ValueError(f"Migration failed: {e}")

        finally:
            self.neptune_client.close()

    def _upsert_supplier(self, supplier) -> bool:
        """
        Upsert supplier vertex.

        Args:
            supplier: Supplier model

        Returns:
            True if created, False if updated
        """
        client = self.neptune_client._get_client()

        # Check if supplier exists
        check_query = """
        g.V().has('supplier', 'id', supplier_id).count()
        """
        bindings = {"supplier_id": supplier.supplier_id}
        count = client.submit(check_query, bindings).all().result()[0]

        if count > 0:
            # Update existing
            update_query = """
            g.V().has('supplier', 'id', supplier_id)
             .property('name', name)
             .property('location', location)
             .property('rating', rating)
             .property('financial_stability_score', financial_stability_score)
             .property('geopolitical_risk_score', geopolitical_risk_score)
             .property('active_status', active_status)
            """
            bindings.update({
                "name": supplier.name,
                "location": supplier.location,
                "rating": supplier.rating,
                "financial_stability_score": supplier.financial_stability_score,
                "geopolitical_risk_score": supplier.geopolitical_risk_score,
                "active_status": supplier.active_status
            })
            client.submit(update_query, bindings).all().result()
            return False
        else:
            # Create new
            create_query = """
            g.addV('supplier')
             .property('id', supplier_id)
             .property('name', name)
             .property('location', location)
             .property('rating', rating)
             .property('financial_stability_score', financial_stability_score)
             .property('geopolitical_risk_score', geopolitical_risk_score)
             .property('active_status', active_status)
            """
            bindings.update({
                "name": supplier.name,
                "location": supplier.location,
                "rating": supplier.rating,
                "financial_stability_score": supplier.financial_stability_score,
                "geopolitical_risk_score": supplier.geopolitical_risk_score,
                "active_status": supplier.active_status
            })
            client.submit(create_query, bindings).all().result()
            return True

    def _upsert_material(self, material) -> bool:
        """
        Upsert material vertex.

        Args:
            material: Material model

        Returns:
            True if created, False if updated
        """
        client = self.neptune_client._get_client()

        # Check if material exists
        check_query = """
        g.V().has('material', 'id', material_id).count()
        """
        bindings = {"material_id": material.material_id}
        count = client.submit(check_query, bindings).all().result()[0]

        if count > 0:
            # Update existing
            update_query = """
            g.V().has('material', 'id', material_id)
             .property('name', name)
             .property('category', category)
             .property('standard_cost', standard_cost)
             .property('criticality_level', criticality_level)
            """
            bindings.update({
                "name": material.name,
                "category": material.category,
                "standard_cost": material.standard_cost,
                "criticality_level": material.criticality_level
            })
            client.submit(update_query, bindings).all().result()
            return False
        else:
            # Create new
            create_query = """
            g.addV('material')
             .property('id', material_id)
             .property('name', name)
             .property('category', category)
             .property('standard_cost', standard_cost)
             .property('criticality_level', criticality_level)
            """
            bindings.update({
                "name": material.name,
                "category": material.category,
                "standard_cost": material.standard_cost,
                "criticality_level": material.criticality_level
            })
            client.submit(create_query, bindings).all().result()
            return True

    def _upsert_supplies_edge(self, supplier_material) -> bool:
        """
        Upsert "supplies" edge between supplier and material.

        Args:
            supplier_material: SupplierMaterial model

        Returns:
            True if created, False if updated
        """
        client = self.neptune_client._get_client()

        # Check if edge exists
        check_query = """
        g.V().has('supplier', 'id', supplier_id)
         .outE('supplies')
         .where(inV().has('material', 'id', material_id))
         .count()
        """
        bindings = {
            "supplier_id": supplier_material.supplier_id,
            "material_id": supplier_material.material_id
        }
        count = client.submit(check_query, bindings).all().result()[0]

        if count > 0:
            # Update existing edge
            update_query = """
            g.V().has('supplier', 'id', supplier_id)
             .outE('supplies')
             .where(inV().has('material', 'id', material_id))
             .property('base_price', base_price)
             .property('lead_time_days', lead_time_days)
             .property('minimum_order_quantity', minimum_order_quantity)
            """
            bindings.update({
                "base_price": supplier_material.base_price,
                "lead_time_days": supplier_material.lead_time_days,
                "minimum_order_quantity": supplier_material.minimum_order_quantity
            })
            client.submit(update_query, bindings).all().result()
            return False
        else:
            # Create new edge
            create_query = """
            g.V().has('supplier', 'id', supplier_id).as('s')
             .V().has('material', 'id', material_id).as('m')
             .addE('supplies').from('s').to('m')
             .property('base_price', base_price)
             .property('lead_time_days', lead_time_days)
             .property('minimum_order_quantity', minimum_order_quantity)
            """
            bindings.update({
                "base_price": supplier_material.base_price,
                "lead_time_days": supplier_material.lead_time_days,
                "minimum_order_quantity": supplier_material.minimum_order_quantity
            })
            client.submit(create_query, bindings).all().result()
            return True


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate CSV data to Neptune graph database"
    )
    parser.add_argument(
        "--neptune-endpoint",
        required=True,
        help="Neptune cluster endpoint (e.g., my-cluster.cluster-xxx.us-east-1.neptune.amazonaws.com)"
    )
    parser.add_argument(
        "--csv-dir",
        default="data",
        help="Directory containing CSV files (default: data)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate data without writing to Neptune"
    )

    args = parser.parse_args()

    # Configure logging
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer()
        ]
    )

    try:
        migration = NeptuneMigration(
            neptune_endpoint=args.neptune_endpoint,
            csv_dir=args.csv_dir,
            dry_run=args.dry_run
        )

        stats = migration.migrate()

        print("\n=== Migration Complete ===")
        print(f"Suppliers created: {stats['suppliers_created']}")
        print(f"Suppliers updated: {stats['suppliers_updated']}")
        print(f"Materials created: {stats['materials_created']}")
        print(f"Materials updated: {stats['materials_updated']}")
        print(f"Edges created: {stats['edges_created']}")
        print(f"Edges updated: {stats['edges_updated']}")
        print(f"Errors: {stats['errors']}")

        if stats["errors"] > 0:
            sys.exit(1)

    except Exception as e:
        logger.error("migration_cli_failed", error=str(e), exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
