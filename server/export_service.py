import os
import shutil
import json
import datetime
from typing import Dict, Any, List, Optional
from server.inventory_manager import InventoryManager
from server.decision_manager import DecisionManager

CATEGORY_DIRS = {
    "R": "con_defecto",
    "S": "sin_defecto",
    "D": "dudosas",
    "X": "descartadas"
}

class ExportService:
    """
    Servicio de exportación y sincronización limpia del dataset clasificado.
    Copia imágenes con sus nombres originales y contenido binario intacto.
    Garantiza que una imagen reclasificada sea removida de su carpeta anterior,
    impidiendo la duplicación en múltiples bandejas.
    """

    def __init__(
        self,
        inventory_manager: InventoryManager,
        decision_manager: DecisionManager,
        export_root: str = "clasificado"
    ):
        self.inventory_manager = inventory_manager
        self.decision_manager = decision_manager
        self.export_root = export_root

    def run_export(self) -> Dict[str, Any]:
        os.makedirs(self.export_root, exist_ok=True)
        for cat_dir in CATEGORY_DIRS.values():
            os.makedirs(os.path.join(self.export_root, cat_dir), exist_ok=True)

        decisions = self.decision_manager.get_all_decisions()
        inventory = self.inventory_manager.inventory_by_id

        copied_count = {cat: 0 for cat in CATEGORY_DIRS.keys()}
        moved_or_removed_count = 0
        errors = []
        exported_records = []

        now_iso = datetime.datetime.utcnow().isoformat() + "Z"

        for image_id, decision in decisions.items():
            category = decision.get("category")
            if category not in CATEGORY_DIRS:
                continue

            inv_item = inventory.get(image_id)
            if not inv_item:
                errors.append({
                    "image_id": image_id,
                    "error": "Imagen no encontrada en el inventario"
                })
                continue

            src_path = inv_item.get("file_path", "")
            if not os.path.exists(src_path):
                errors.append({
                    "image_id": image_id,
                    "category": category,
                    "error": f"Archivo de origen no existe: {src_path}"
                })
                continue

            filename = inv_item.get("filename", image_id)
            target_subfolder = CATEGORY_DIRS[category]
            target_dest = os.path.join(self.export_root, target_subfolder, filename)

            # Limpiar copias obsoletas en las otras 3 categorías para evitar duplicados al reclasificar
            for other_cat, other_folder in CATEGORY_DIRS.items():
                if other_cat != category:
                    obsolete_dest = os.path.join(self.export_root, other_folder, filename)
                    if os.path.exists(obsolete_dest):
                        try:
                            os.remove(obsolete_dest)
                            moved_or_removed_count += 1
                        except Exception as e:
                            errors.append({
                                "image_id": image_id,
                                "error": f"Error al remover copia obsoleta en {other_folder}: {e}"
                            })

            # Copiar si no existe o si el archivo destino difiere en tamaño/fecha
            try:
                # shutil.copy2 copia bytes exactos preservando metadata original
                shutil.copy2(src_path, target_dest)
                copied_count[category] += 1
                exported_records.append({
                    "image_id": image_id,
                    "filename": filename,
                    "category": category,
                    "destination": f"{self.export_root}/{target_subfolder}/{filename}".replace("\\", "/"),
                    "fruit_id": inv_item.get("fruit_id"),
                    "note": decision.get("note", ""),
                    "reason": decision.get("reason", "")
                })
            except Exception as e:
                errors.append({
                    "image_id": image_id,
                    "category": category,
                    "error": f"Error al copiar archivo a {target_dest}: {e}"
                })

        report = {
            "timestamp": now_iso,
            "export_root": self.export_root,
            "total_decisions_found": len(decisions),
            "total_exported": sum(copied_count.values()),
            "by_category": {
                "R_con_defecto": copied_count["R"],
                "S_sin_defecto": copied_count["S"],
                "D_dudosas": copied_count["D"],
                "X_descartadas": copied_count["X"]
            },
            "obsolete_cleaned_up": moved_or_removed_count,
            "errors_count": len(errors),
            "errors": errors
        }

        # Guardar reporte de exportación
        report_path = os.path.join(self.export_root, "export_report.json")
        with open(report_path, "w", encoding="utf-8") as rf:
            json.dump(report, rf, indent=2, ensure_ascii=False)

        # Guardar manifiesto detallado de exportación
        manifest_path = os.path.join(self.export_root, "export_manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as mf:
            json.dump(exported_records, mf, indent=2, ensure_ascii=False)

        return report
