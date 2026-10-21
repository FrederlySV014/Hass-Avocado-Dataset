#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script CLI para generar y auditar el inventario del dataset de paltas Hass.
Crea data/inventory.json, data/inventory.csv y data/inventory_report.json.
"""

import sys
import os
import json

# Asegurar path de importación
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from server.inventory_manager import InventoryManager

def main():
    print("=" * 70)
    print("  GENERADOR Y AUDITOR DE INVENTARIO - HASS AVOCADO DATASET")
    print("=" * 70)
    
    manager = InventoryManager("config.json")
    print("\nProcesando imágenes en disco y metadatos de Excel...")
    report = manager.generate_inventory(force=True)
    
    print("\n[OK] Inventario generado exitosamente:")
    print(f"  • Total de imágenes catalogadas: {report['total_images']:,}")
    print(f"  • Total de frutas únicas:        {report['total_fruits']}")
    print(f"  • Tamaño de lote estándar:       {report['batch_size']} imágenes")
    print(f"  • Total de lotes consecutivos:   {report['total_batches']}")
    print(f"  • Tamaño del último lote:        {report['last_batch_count']} imágenes")
    print("\nDistribución por Grupo de Almacenamiento:")
    for grp, cnt in report["groups_distribution"].items():
        print(f"  • {grp}: {cnt:,} fotografías")
    print("\nDistribución por Vista:")
    for view, cnt in report["views_distribution"].items():
        print(f"  • Vista '{view}': {cnt:,} fotografías")
    print("\nDistribución por Maduración (Ripening Index 1..5):")
    for rip, cnt in sorted(report["ripening_distribution"].items()):
        print(f"  • Índice {rip}: {cnt:,} fotografías")
    print("\nArchivos creados:")
    print("  • data/inventory.json")
    print("  • data/inventory.csv")
    print("  • data/inventory_report.json")
    print("=" * 70)

if __name__ == "__main__":
    main()
