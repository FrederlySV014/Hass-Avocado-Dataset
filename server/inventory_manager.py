import os
import json
import pandas as pd
from typing import Dict, List, Any, Optional

class InventoryManager:
    """
    Gestor de inventario y partición en lotes para el dataset fotográfico.
    Garantiza orden determinista y reproducible, cálculo de fruit_id único
    y segmentación en lotes consecutivos de tamaño configurado (ej. 250).
    """

    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.inventory: List[Dict[str, Any]] = []
        self.inventory_by_id: Dict[str, Dict[str, Any]] = {}
        self.inventory_by_batch: Dict[int, List[Dict[str, Any]]] = {}
        self.inventory_by_fruit: Dict[str, List[Dict[str, Any]]] = {}

    def _load_config(self) -> Dict[str, Any]:
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "dataset_images_dir": "Avocado Ripening Dataset",
            "excel_metadata_path": "Avocado Ripening Dataset.xlsx",
            "batch_size": 250,
            "inventory_json_path": "data/inventory.json",
            "inventory_csv_path": "data/inventory.csv",
            "inventory_report_path": "data/inventory_report.json",
            "protocol_version": "v1.0"
        }

    def generate_inventory(self, force: bool = False) -> Dict[str, Any]:
        """
        Construye el inventario a partir de los archivos en disco y el archivo Excel.
        Si ya existe y force=False, carga el existente.
        """
        json_path = self.config.get("inventory_json_path", "data/inventory.json")
        if not force and os.path.exists(json_path):
            self.load_inventory()
            report_path = self.config.get("inventory_report_path", "data/inventory_report.json")
            if os.path.exists(report_path):
                with open(report_path, "r", encoding="utf-8") as rf:
                    return json.load(rf)

        os.makedirs("data", exist_ok=True)
        img_dir = self.config.get("dataset_images_dir", "Avocado Ripening Dataset")
        excel_path = self.config.get("excel_metadata_path", "Avocado Ripening Dataset.xlsx")
        batch_size = int(self.config.get("batch_size", 250))

        if not os.path.exists(img_dir):
            raise FileNotFoundError(f"Carpeta de imágenes no encontrada: {img_dir}")
        if not os.path.exists(excel_path):
            raise FileNotFoundError(f"Archivo Excel no encontrado: {excel_path}")

        # Leer archivos físicos
        disk_files = [f for f in os.listdir(img_dir) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
        disk_set = set(disk_files)

        # Leer Excel
        df_excel = pd.read_excel(excel_path)
        
        # Mapear nombres base sin extensión a registros del Excel
        excel_meta = {}
        for _, row in df_excel.iterrows():
            fname = str(row["File Name"]).strip()
            excel_meta[fname] = {
                "time_stamp": str(row.get("Time Stamp", "")),
                "storage_group": str(row.get("Storage Group", "")).strip(),
                "sample": int(row.get("Sample", 0)),
                "day": int(row.get("Day of Experiment", 0)),
                "ripening_stage": int(row.get("Ripening Index Classification", 0))
            }

        records = []
        corrupted_or_missing = []

        for fname in disk_files:
            stem, ext = os.path.splitext(fname)
            fpath = os.path.join(img_dir, fname)
            fsize = os.path.getsize(fpath)

            # Metadata fallback desde el nombre si no estuviese en Excel
            # Formato estándar: {storage}_{day}_{sample}_{view}_{ripening} (ej: T20_d01_001_a_1)
            parts = stem.split("_")
            meta = excel_meta.get(stem, None)

            if meta:
                storage_group = meta["storage_group"]
                sample = meta["sample"]
                day = meta["day"]
                ripening_stage = meta["ripening_stage"]
                time_stamp = meta["time_stamp"]
            else:
                storage_group = parts[0] if len(parts) > 0 else "UNKNOWN"
                day = int(parts[1].replace("d", "")) if len(parts) > 1 and parts[1].startswith("d") else 0
                sample = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
                ripening_stage = int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else 0
                time_stamp = ""

            view = parts[3].lower() if len(parts) > 3 else "unknown"
            fruit_id = f"{storage_group}_{sample:03d}"

            records.append({
                "filename": fname,
                "original_stem": stem,
                "file_path": f"{img_dir}/{fname}".replace("\\", "/"),
                "file_size_bytes": fsize,
                "storage_group": storage_group,
                "sample": sample,
                "fruit_id": fruit_id,
                "day": day,
                "view": view,
                "ripening_stage": ripening_stage,
                "time_stamp": time_stamp,
                "is_valid": (fsize > 0)
            })

        # Ordenamiento reproducible:
        # 1. Storage Group ('T10', 'T20', 'Tam')
        # 2. Sample (número entero de fruta)
        # 3. Day of Experiment (día 1..26)
        # 4. View ('a', 'b')
        # 5. Filename
        records.sort(key=lambda r: (
            r["storage_group"],
            r["sample"],
            r["day"],
            r["view"],
            r["filename"]
        ))

        # Asignar índices y lotes consecutivos
        total = len(records)
        inventory_items = []
        for idx, item in enumerate(records, start=1):
            batch_id = ((idx - 1) // batch_size) + 1
            batch_index = ((idx - 1) % batch_size) + 1
            item["global_index"] = idx
            item["batch_id"] = batch_id
            item["batch_index"] = batch_index
            item["image_id"] = item["filename"]  # Identificador único oficial
            inventory_items.append(item)

        self.inventory = inventory_items
        self._index_inventory()

        # Guardar inventory.json
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.inventory, f, indent=2, ensure_ascii=False)

        # Guardar inventory.csv
        csv_path = self.config.get("inventory_csv_path", "data/inventory.csv")
        df_out = pd.DataFrame(self.inventory)
        df_out.to_csv(csv_path, index=False, encoding="utf-8")

        # Generar reporte estadístico
        report = self._build_report(total, batch_size)
        report_path = self.config.get("inventory_report_path", "data/inventory_report.json")
        with open(report_path, "w", encoding="utf-8") as rf:
            json.dump(report, rf, indent=2, ensure_ascii=False)

        return report

    def _build_report(self, total: int, batch_size: int) -> Dict[str, Any]:
        total_batches = ((total - 1) // batch_size) + 1 if total > 0 else 0
        fruits = set(item["fruit_id"] for item in self.inventory)
        groups = {}
        views = {}
        ripening_counts = {}
        batches_info = {}

        for item in self.inventory:
            g = item["storage_group"]
            groups[g] = groups.get(g, 0) + 1

            v = item["view"]
            views[v] = views.get(v, 0) + 1

            rip = item["ripening_stage"]
            ripening_counts[rip] = ripening_counts.get(rip, 0) + 1

            b_id = item["batch_id"]
            if b_id not in batches_info:
                batches_info[b_id] = {
                    "batch_id": b_id,
                    "count": 0,
                    "first_image": item["filename"],
                    "last_image": item["filename"],
                    "fruit_ids": set()
                }
            batches_info[b_id]["count"] += 1
            batches_info[b_id]["last_image"] = item["filename"]
            batches_info[b_id]["fruit_ids"].add(item["fruit_id"])

        # Convertir sets para JSON
        batch_list = []
        for b_id in sorted(batches_info.keys()):
            info = batches_info[b_id]
            batch_list.append({
                "batch_id": b_id,
                "count": info["count"],
                "first_image": info["first_image"],
                "last_image": info["last_image"],
                "unique_fruits": len(info["fruit_ids"])
            })

        return {
            "total_images": total,
            "total_fruits": len(fruits),
            "batch_size": batch_size,
            "total_batches": total_batches,
            "last_batch_count": total % batch_size if (total % batch_size != 0) else batch_size,
            "groups_distribution": groups,
            "views_distribution": views,
            "ripening_distribution": ripening_counts,
            "batches_summary": batch_list
        }

    def load_inventory(self) -> None:
        """Carga el inventario persistido en memoria."""
        json_path = self.config.get("inventory_json_path", "data/inventory.json")
        if not os.path.exists(json_path):
            self.generate_inventory(force=True)
            return

        with open(json_path, "r", encoding="utf-8") as f:
            self.inventory = json.load(f)

        self._index_inventory()

    def _index_inventory(self) -> None:
        self.inventory_by_id = {item["image_id"]: item for item in self.inventory}
        self.inventory_by_batch = {}
        self.inventory_by_fruit = {}

        for item in self.inventory:
            b_id = item["batch_id"]
            if b_id not in self.inventory_by_batch:
                self.inventory_by_batch[b_id] = []
            self.inventory_by_batch[b_id].append(item)

            f_id = item["fruit_id"]
            if f_id not in self.inventory_by_fruit:
                self.inventory_by_fruit[f_id] = []
            self.inventory_by_fruit[f_id].append(item)

    def get_image(self, image_id: str) -> Optional[Dict[str, Any]]:
        return self.inventory_by_id.get(image_id)

    def get_batch(self, batch_id: int) -> List[Dict[str, Any]]:
        return self.inventory_by_batch.get(batch_id, [])

    def get_fruit_images(self, fruit_id: str) -> List[Dict[str, Any]]:
        return self.inventory_by_fruit.get(fruit_id, [])

    def get_total_batches(self) -> int:
        return len(self.inventory_by_batch)

    def get_total_images(self) -> int:
        return len(self.inventory)
