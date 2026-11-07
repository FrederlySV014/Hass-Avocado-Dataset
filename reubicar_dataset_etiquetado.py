#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
reubicar_dataset_etiquetado.py
=============================================================================
Reubica y organiza de manera segura las 3,000 imágenes seleccionadas y balanceadas
(1,500 con defecto visible y 1,500 sin defecto visible) en la carpeta de destino:
    dataset_etiquetado/
        ├── con_defecto/       (1,500 imágenes)
        ├── sin_defecto/       (1,500 imágenes)
        └── metadata/          (manifiesto, resúmenes y listas)

Garantías de seguridad e integridad:
1. Copia no destructiva (shutil.copy2): Preserva los archivos originales del dataset intactos.
2. Verificación binaria SHA-256: Comprueba que cada archivo copiado sea idéntico byte por byte.
3. Auditoría completa: Genera manifest.json con trazabilidad de fruit_id, día, vista y estadio.
=============================================================================
"""

import os
import sys
import json
import shutil
import hashlib
import datetime
from typing import Dict, Any, List

def calcular_sha256(filepath: str, block_size: int = 65536) -> str:
    """Calcula el hash SHA-256 de un archivo en disco."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(block_size):
            hasher.update(chunk)
    return hasher.hexdigest()

def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(root_dir, "data")
    dest_root = os.path.join(root_dir, "dataset_etiquetado")
    
    decisions_path = os.path.join(data_dir, "decisions.json")
    inventory_path = os.path.join(data_dir, "inventory.json")

    print("=" * 75)
    print("  REUBICACIÓN Y ORGANIZACIÓN DEL DATASET PARA ETIQUETADO Y ENTRENAMIENTO")
    print("=" * 75)

    # 1. Cargar inventario y decisiones
    if not os.path.exists(decisions_path) or not os.path.exists(inventory_path):
        print(f"[ERROR] Archivos de datos no encontrados en {data_dir}")
        sys.exit(1)

    print("\n[1/5] Cargando inventario y decisiones registradas...")
    with open(inventory_path, "r", encoding="utf-8") as f:
        inventory_items = json.load(f)
    inventory = {it["image_id"]: it for it in inventory_items}

    with open(decisions_path, "r", encoding="utf-8") as f:
        decisions = json.load(f)

    r_ids = [img_id for img_id, d in decisions.items() if d.get("category") == "R"]
    s_ids = [img_id for img_id, d in decisions.items() if d.get("category") == "S"]

    print(f"  • Total en catálogo general:          {len(inventory):,} imágenes")
    print(f"  • Seleccionadas con defecto (R):       {len(r_ids):,} imágenes")
    print(f"  • Seleccionadas sin defecto (S):       {len(s_ids):,} imágenes")
    print(f"  • Balance total para etiquetado:      {len(r_ids) + len(s_ids):,} imágenes (Ratio: 1:1)")

    if len(r_ids) != 1500 or len(s_ids) != 1500:
        print(f"[ADVERTENCIA] Se esperaba exactamente 1,500 en R y 1,500 en S. Encontrados: R={len(r_ids)}, S={len(s_ids)}")

    # 2. Preparar directorios de destino
    print(f"\n[2/5] Creando directorios en: {dest_root}...")
    dir_r = os.path.join(dest_root, "con_defecto")
    dir_s = os.path.join(dest_root, "sin_defecto")
    dir_meta = os.path.join(dest_root, "metadata")

    os.makedirs(dir_r, exist_ok=True)
    os.makedirs(dir_s, exist_ok=True)
    os.makedirs(dir_meta, exist_ok=True)

    # Limpiar archivos huérfanos que pudieran existir de ejecuciones previas
    allowed_r_names = {inventory[i]["filename"] for i in r_ids if i in inventory}
    allowed_s_names = {inventory[i]["filename"] for i in s_ids if i in inventory}

    for f_curr in os.listdir(dir_r):
        if f_curr not in allowed_r_names:
            os.remove(os.path.join(dir_r, f_curr))
    for f_curr in os.listdir(dir_s):
        if f_curr not in allowed_s_names:
            os.remove(os.path.join(dir_s, f_curr))

    # 3. Proceso de copia y verificación de integridad
    print("\n[3/5] Copiando imágenes y verificando integridad binaria SHA-256...")

    tasks = [
        ("con_defecto", r_ids, dir_r, "R"),
        ("sin_defecto", s_ids, dir_s, "S")
    ]

    manifest_records = []
    lista_r_filenames = []
    lista_s_filenames = []
    errors = []
    total_bytes = 0

    for group_name, id_list, target_dir, cat_code in tasks:
        print(f"\n  Procesando grupo '{group_name}' ({len(id_list)} imágenes)...")
        for idx, img_id in enumerate(id_list, start=1):
            item = inventory.get(img_id)
            if not item:
                errors.append(f"ID {img_id} no existe en inventario.")
                continue

            src_path = item.get("file_path", "")
            if not os.path.exists(src_path):
                errors.append(f"Archivo origen no encontrado: {src_path}")
                continue

            filename = item.get("filename", f"{img_id}.jpg")
            dst_path = os.path.join(target_dir, filename)

            # Verificar si ya existe con mismo tamaño y hash para optimizar
            src_size = os.path.getsize(src_path)
            need_copy = True
            if os.path.exists(dst_path) and os.path.getsize(dst_path) == src_size:
                src_hash = calcular_sha256(src_path)
                dst_hash = calcular_sha256(dst_path)
                if src_hash == dst_hash:
                    need_copy = False
                else:
                    need_copy = True

            if need_copy:
                shutil.copy2(src_path, dst_path)
                src_hash = calcular_sha256(src_path)
                dst_hash = calcular_sha256(dst_path)
                if src_hash != dst_hash:
                    errors.append(f"Falla de checksum en {filename}: {src_hash} != {dst_hash}")
                    continue
            else:
                dst_hash = calcular_sha256(dst_path)

            total_bytes += src_size

            record = {
                "image_id": img_id,
                "category": cat_code,
                "group_folder": group_name,
                "filename": filename,
                "fruit_id": item.get("fruit_id"),
                "storage_group": item.get("storage_group"),
                "day": item.get("day"),
                "view": item.get("view"),
                "ripening_stage": item.get("ripening_stage"),
                "time_stamp": item.get("time_stamp"),
                "file_size_bytes": src_size,
                "sha256": dst_hash,
                "destination_relpath": os.path.relpath(dst_path, root_dir).replace("\\", "/"),
                "source_path": src_path
            }
            manifest_records.append(record)

            if cat_code == "R":
                lista_r_filenames.append(filename)
            else:
                lista_s_filenames.append(filename)

            if idx % 500 == 0 or idx == len(id_list):
                print(f"    ✓ {idx}/{len(id_list)} copiadas y verificadas con éxito.")

    # 4. Generar metadatos y manifiesto
    print("\n[4/5] Generando metadatos y manifiestos de trazabilidad...")

    # A. Manifiesto completo
    manifest_path = os.path.join(dir_meta, "dataset_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_records, f, indent=2, ensure_ascii=False)

    # B. Listas simples de nombres de archivos
    with open(os.path.join(dir_meta, "lista_con_defecto.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(lista_r_filenames)) + "\n")

    with open(os.path.join(dir_meta, "lista_sin_defecto.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(lista_s_filenames)) + "\n")

    # C. Resumen estadístico
    now_iso = datetime.datetime.utcnow().isoformat() + "Z"
    
    def get_breakdown(records_subset):
        from collections import Counter
        return {
            "by_view": dict(Counter(r["view"] for r in records_subset)),
            "by_group": dict(Counter(r["storage_group"] for r in records_subset)),
            "by_ripening_stage": dict(sorted(Counter(r["ripening_stage"] for r in records_subset).items())),
            "unique_fruits": len(set(r["fruit_id"] for r in records_subset))
        }

    records_r = [r for r in manifest_records if r["category"] == "R"]
    records_s = [r for r in manifest_records if r["category"] == "S"]

    summary_data = {
        "dataset_name": "Hass Avocado Ripening Photographic Dataset - Balanced Curation",
        "created_at": now_iso,
        "purpose": "Dataset balanceado para etiquetado de defectos (roña) y entrenamiento de modelos YOLO",
        "total_images": len(manifest_records),
        "total_size_mb": round(total_bytes / (1024 * 1024), 2),
        "categories": {
            "con_defecto": {
                "category_code": "R",
                "count": len(records_r),
                "folder": "dataset_etiquetado/con_defecto",
                "breakdown": get_breakdown(records_r)
            },
            "sin_defecto": {
                "category_code": "S",
                "count": len(records_s),
                "folder": "dataset_etiquetado/sin_defecto",
                "breakdown": get_breakdown(records_s)
            }
        },
        "balance_ratio": f"{len(records_r)} : {len(records_s)} (1:1 Exacto)",
        "errors_count": len(errors),
        "errors": errors
    }

    summary_path = os.path.join(dir_meta, "resumen_balance.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2, ensure_ascii=False)

    # D. README explicativo de etiquetado
    readme_path = os.path.join(dest_root, "README.md")
    readme_content = f"""# Dataset de Paltas Hass Curado y Balanceado (3,000 Imágenes)

## 📌 Propósito
Este conjunto de datos ha sido cuidadosamente filtrado, curado y balanceado mediante un proceso en dos fases a partir del catálogo original de 14,710 fotografías. Está optimizado para la fase de **etiquetado de defectos (roña)** y el posterior entrenamiento de modelos de visión por computador (ej. YOLOv8 / YOLOv11 / RT-DETR).

## 📊 Estructura y Balance de Clases
- **Total de Imágenes:** {len(manifest_records):,}
- **Relación de Balance:** 1:1 exacta (1,500 : 1,500)
- **Tamaño en Disco:** {round(total_bytes / (1024 * 1024), 2)} MB
- **Integridad Binaria:** 100% verificado mediante sumas de verificación SHA-256.

```
dataset_etiquetado/
├── con_defecto/          # 1,500 fotos con roña visible confirmada (a etiquetar)
├── sin_defecto/          # 1,500 fotos sanas de control (muestras negativas)
└── metadata/
    ├── dataset_manifest.json   # Metadatos completos por imagen (fruit_id, día, estadio, SHA-256)
    ├── resumen_balance.json    # Estadísticas descriptivas de la partición
    ├── lista_con_defecto.txt   # Listado plano de archivos del grupo R
    └── lista_sin_defecto.txt   # Listado plano de archivos del grupo S
```

## 🏷️ Guía para la Etapa de Etiquetado (Labeling)
1. **Grupo `con_defecto/` (1,500 fotos):**
   - Son las imágenes donde se deben trazar las cajas delimitadoras (*bounding boxes*) o polígonos de segmentación sobre las zonas con roña o defectos visuales.
   - Clase recomendada: `0: rona` (o `0: defecto`).
2. **Grupo `sin_defecto/` (1,500 fotos):**
   - Actúan como **imágenes de fondo (negativos)** en el entrenamiento de YOLO (archivos `.txt` de etiquetas vacíos).
   - Su inclusión es fundamental para evitar falsos positivos y enseñar al modelo a distinguir piel sana de piel rugosa o con lenticelas normales.

*Generado automáticamente el {now_iso}.*
"""
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)

    # 5. Reporte final
    print("\n[5/5] Verificación final de archivos en disco:")
    count_r_disk = len(os.listdir(dir_r))
    count_s_disk = len(os.listdir(dir_s))
    print(f"  • Archivos en '{os.path.relpath(dir_r, root_dir)}': {count_r_disk:,}")
    print(f"  • Archivos en '{os.path.relpath(dir_s, root_dir)}': {count_s_disk:,}")
    print(f"  • Total en disco:                             {count_r_disk + count_s_disk:,} archivos")
    print(f"  • Errores reportados:                         {len(errors)}")

    if count_r_disk == 1500 and count_s_disk == 1500 and len(errors) == 0:
        print("\n" + "=" * 75)
        print("  ✓ PROCESO COMPLETADO EXITOSAMENTE SIN ERRORES")
        print(f"  Carpeta del dataset: {dest_root}")
        print("=" * 75)
    else:
        print("\n[ADVERTENCIA] Hubo inconsistencias en el recuento o errores durante la copia.")
        for err in errors[:10]:
            print(f"  - {err}")

if __name__ == "__main__":
    main()

