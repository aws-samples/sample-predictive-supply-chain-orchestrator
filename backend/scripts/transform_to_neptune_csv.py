"""
Transform application CSVs to Neptune Gremlin CSV format.

Creates separate vertex and edge files for Neptune bulk loader.
"""

import csv
from pathlib import Path
from typing import List, Dict


def transform_suppliers_to_vertices(input_csv: str, output_csv: str) -> int:
    """Transform suppliers.csv to Neptune vertex format."""
    with open(input_csv, 'r', encoding="utf-8") as infile, open(output_csv, 'w', newline='', encoding="utf-8") as outfile:
        reader = csv.DictReader(infile)
        
        # Neptune vertex format: ~id, ~label, properties
        writer = csv.writer(outfile)
        writer.writerow([
            '~id', '~label', 
            'name:String', 'rating:Double', 'location:String',
            'financial_stability_score:Double', 'geopolitical_risk_score:Double',
            'active_status:Bool'
        ])
        
        count = 0
        for row in reader:
            writer.writerow([
                row['supplier_id'],
                'Supplier',
                row['name'],
                row['rating'],
                row['location'],
                row['financial_stability_score'],
                row['geopolitical_risk_score'],
                row['active_status'].lower()
            ])
            count += 1
        
        return count


def transform_materials_to_vertices(input_csv: str, output_csv: str) -> int:
    """Transform materials.csv to Neptune vertex format."""
    with open(input_csv, 'r', encoding="utf-8") as infile, open(output_csv, 'w', newline='', encoding="utf-8") as outfile:
        reader = csv.DictReader(infile)
        
        writer = csv.writer(outfile)
        writer.writerow([
            '~id', '~label',
            'name:String', 'category:String', 'unit_of_measure:String',
            'standard_cost:Double', 'criticality_level:String', 'weight_kg:Double'
        ])
        
        count = 0
        for row in reader:
            writer.writerow([
                row['material_id'],
                'Material',
                row['name'],
                row['category'],
                row['unit_of_measure'],
                row['standard_cost'],
                row['criticality_level'],
                row['weight_kg']
            ])
            count += 1
        
        return count


def transform_supplier_materials_to_edges(input_csv: str, output_csv: str) -> int:
    """Transform supplier_materials.csv to Neptune edge format."""
    with open(input_csv, 'r', encoding="utf-8") as infile, open(output_csv, 'w', newline='', encoding="utf-8") as outfile:
        reader = csv.DictReader(infile)
        
        # Neptune edge format: ~id, ~from, ~to, ~label, properties
        writer = csv.writer(outfile)
        writer.writerow([
            '~id', '~from', '~to', '~label',
            'base_price:Double', 'minimum_order_quantity:Int',
            'lead_time_days:Int', 'effective_date:Date'
        ])
        
        count = 0
        for row in reader:
            edge_id = f"{row['supplier_id']}-supplies-{row['material_id']}"
            writer.writerow([
                edge_id,
                row['supplier_id'],
                row['material_id'],
                'supplies',
                row['base_price'],
                row['minimum_order_quantity'],
                row['lead_time_days'],
                row['effective_date']
            ])
            count += 1
        
        return count


def main():
    """Transform all CSVs to Neptune format."""
    input_dir = Path('data')
    output_dir = Path('data/neptune-format')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("Transforming CSVs to Neptune format...")
    
    # Transform vertices
    suppliers_count = transform_suppliers_to_vertices(
        str(input_dir / 'suppliers.csv'),
        str(output_dir / 'suppliers-vertices.csv')
    )
    print(f"✓ Transformed {suppliers_count} suppliers to vertices")
    
    materials_count = transform_materials_to_vertices(
        str(input_dir / 'materials.csv'),
        str(output_dir / 'materials-vertices.csv')
    )
    print(f"✓ Transformed {materials_count} materials to vertices")
    
    # Transform edges
    edges_count = transform_supplier_materials_to_edges(
        str(input_dir / 'supplier_materials.csv'),
        str(output_dir / 'supplies-edges.csv')
    )
    print(f"✓ Transformed {edges_count} supplier-material relationships to edges")
    
    print(f"\nNeptune CSV files created in: {output_dir}")
    print("Upload these files to S3 and use Neptune bulk loader")


if __name__ == '__main__':
    main()
