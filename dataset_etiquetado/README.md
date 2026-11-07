# Dataset de Paltas Hass Curado y Balanceado (3,000 Imágenes)

## 📌 Propósito
Este conjunto de datos ha sido cuidadosamente filtrado, curado y balanceado mediante un proceso en dos fases a partir del catálogo original de 14,710 fotografías. Está optimizado para la fase de **etiquetado de defectos (roña)** y el posterior entrenamiento de modelos de visión por computador (ej. YOLOv8 / YOLOv11 / RT-DETR).

## 📊 Estructura y Balance de Clases
- **Total de Imágenes:** 3,000
- **Relación de Balance:** 1:1 exacta (1,500 : 1,500)
- **Tamaño en Disco:** 90.97 MB
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

*Generado automáticamente el 2026-11-07T02:49:52.677582Z.*
