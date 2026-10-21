#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script CLI para ejecutar la exportación física del dataset clasificado.
Organiza las imágenes en:
  clasificado/con_defecto/
  clasificado/sin_defecto/
  clasificado/dudosas/
  clasificado/descartadas/
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from server.inventory_manager import InventoryManager
from server.decision_manager import DecisionManager
from server.export_service import ExportService

def main():
    print("=" * 70)
    print("  EXPORTADOR DE FOTOGRAFÍAS CLASIFICADAS - HASS AVOCADO DATASET")
    print("=" * 70)

    inv = InventoryManager("config.json")
    inv.load_inventory()

    dec = DecisionManager("config.json")
    exp = ExportService(inv, dec, "clasificado")

    print("\nIniciando sincronización y copia de imágenes a carpetas de clasificación...")
    report = exp.run_export()

    print("\n[OK] Exportación finalizada exitosamente:")
    print(f"  • Total de imágenes exportadas:      {report['total_exported']}")
    print(f"  • Con defecto objetivo (R):          {report['by_category']['R_con_defecto']}")
    print(f"  • Sin defecto objetivo (S):          {report['by_category']['S_sin_defecto']}")
    print(f"  • Dudosas (D):                       {report['by_category']['D_dudosas']}")
    print(f"  • Descartadas (X):                   {report['by_category']['X_descartadas']}")
    print(f"  • Copias obsoletas limpiadas:        {report['obsolete_cleaned_up']}")
    print(f"  • Errores encontrados:               {report['errors_count']}")

    if report["errors_count"] > 0:
        print("\nDetalle de errores:")
        for err in report["errors"][:5]:
            print(f"  - {err}")

    print("\nUbicación de exportación:")
    print("  • clasificado/con_defecto/")
    print("  • clasificado/sin_defecto/")
    print("  • clasificado/dudosas/")
    print("  • clasificado/descartadas/")
    print("  • clasificado/export_report.json")
    print("  • clasificado/export_manifest.json")
    print("=" * 70)

if __name__ == "__main__":
    main()
