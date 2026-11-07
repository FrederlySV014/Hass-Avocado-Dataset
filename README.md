# Sistema de Revisión Visual y Clasificación Manual: Roña en Palta Hass

Sistema local de inspección, catalogación y clasificación manual por lotes consecutivos para el **Hass Avocado Ripening Photographic Dataset** (14.710 imágenes), desarrollado como primera etapa para la tesis de detección de defectos superficiales (**roña** / *Sphaceloma perseae*) en palta Hass aplicada al sector agroexportador de Lambayeque, Perú.

---

## 1. Resumen del Dataset e Inventario Oficial

| Métrica | Valor | Descripción |
| :--- | :--- | :--- |
| **Total de Fotografías** | **14.710** | Verificadas al 100% en disco sin archivos dañados ni corruptos |
| **Frutas Físicas Únicas** | **478** | Identificadas unívocamente mediante `fruit_id` (`{grupo}_{muestra}`) |
| **Vistas por Fruta** | **2** | Vista frontal `a` (7.355 tomas) y vista contralateral `b` (7.355 tomas) |
| **Grupos de Almacenamiento** | **3** | `T10` (8.866 fotos), `T20` (2.920 fotos), `Tam` (2.924 fotos) |
| **Estadíos de Maduración** | **5** | Índices 1 (3.568), 2 (2.228), 3 (2.756), 4 (3.294), 5 (2.864) |
| **Tamaño de Lote** | **250** | Imágenes consecutivas únicas por lote |
| **Total de Lotes** | **59** | Lotes 1 al 58 (250 fotos c/u) y Lote 59 (210 fotos) |

---

## 2. Inicio Rápido en Windows

### Opción A — Ejecución con un solo clic:
Haz doble clic en el archivo:
```bat
iniciar_visor.bat
```

### Opción B — Desde la terminal (PowerShell o CMD):
```bash
python app.py
```

Luego abre tu navegador web en:
```
http://127.0.0.1:5000/
```

*(El servidor corre de forma local y privada en tu equipo sin necesidad de conexión externa).*

---

## 3. Guía de Uso del Visor en el Navegador

### 3.1. Bandejas de Decisión y Atajos de Teclado
| Tecla | Bandeja | Significado | Comportamiento |
| :---: | :--- | :--- | :--- |
| **`R`** | **Con defecto visible** | Lesión suberosa compatible con roña | Guarda etiqueta provisional y avanza a la siguiente pendiente. |
| **`S`** | **Sin defecto visible** | No se observa la lesión objetivo en esta toma | Guarda decisión y avanza a la siguiente pendiente. |
| **`D`** | **Dudosa** | Incertidumbre visual (iluminación, sombra, lesión incipiente) | Registra para segunda revisión (cuenta como revisada para cerrar el lote). |
| **`X`** | **Descartada / No utilizable** | Imagen no evaluable | Guarda decisión directa de descarte y avanza a la siguiente pendiente. |
| **`Ctrl + Z`** | **Deshacer** | Revertir última acción | Restaura la decisión o estado previo desde la bitácora transaccional. |
| **`←` / `→`** | **Navegación** | Anterior / Siguiente imagen | Desplaza libremente la inspección dentro del lote. |

### 3.2. Controles de Inspección de Imagen (Zoom y Pan)
- **Rueda del ratón:** Acercar o alejar el zoom de forma fluida centrado en el puntero.
- **Arrastre con ratón (Pan):** Haz clic sostenido sobre la imagen para desplazarla en cualquier dirección.
- **Botones de barra:** `➕` Acercar, `➖` Alejar, `⛶ Ajustar` (vuelve al 100%), `↺ Centrar`.

### 3.3. Comparativa Multivista y Temporal de la Misma Fruta
En la barra lateral derecha verás automáticamente las demás tomas asociadas a la misma fruta (`fruit_id`):
- Permite verificar la cara contralateral (vista `b` vs vista `a`).
- Permite comparar días anteriores o posteriores (`d01` a `d26`) para discernir si una mancha es defecto o evolución de maduración natural.
- Al hacer clic en cualquier miniatura comparativa puedes examinarla de inmediato.
- **Regla estricta:** Las decisiones se guardan **únicamente para la imagen seleccionada**; ninguna etiqueta se propaga automáticamente.

### 3.4. Flujo por Lotes de 250 Imágenes
1. Inicias en el Lote 1. El visor te posiciona en la primera imagen pendiente.
2. Cada vez que pulsas `R`, `S`, `D` o confirmas `X`, la decisión se persiste atómicamente y el visor avanza a la siguiente imagen pendiente del lote.
3. Cuando el contador de pendientes del lote llega a **0**, aparece el banner verde: **"¡Lote completado al 100%!"**.
4. Haz clic en **"Continuar al Siguiente Lote ▶"** para pasar al Lote 2 sin necesidad de reiniciar el servidor.
5. Puedes regresar a cualquier lote anterior en cualquier momento mediante el selector desplegable.

### 3.5. Fase 2: Curación y Balanceo de Clases (R vs S)
Una vez completada la clasificación general inicial, se accede a la pestaña superior **"⚖️ FASE 2: Curación y Balanceo R vs S"**:
- **Objetivo:** Repasar y depurar exclusivamente las fotografías de las clases activas (**Con Defecto Visible [R]** y **Sin Defecto Visible [S]**) para conseguir un balance equitativo exacto de **1.500 fotos por grupo** (Total: 3.000 imágenes equilibradas para entrenamiento YOLO).
- **Selector de Pool:** Permite alternar entre repasar el grupo `R` (actualmente 2.400 fotos, sobrando 900) o el grupo `S` (actualmente 1.555 fotos, sobrando 55).
- **Monitor de Meta y Balance en Tiempo Real:** Muestra el objetivo configurado (`1.500 R / 1.500 S`), la cantidad de fotos sobrantes a descartar para alcanzar la meta en cada pool, el porcentaje relativo y el aviso dinámico de meta alcanzada.
- **Rondas Sucesivas de Repaso (`🔄 Iniciar Nueva Ronda`):** Permite reiniciar las marcas de revisión de las fotos activas en cualquier momento para repetir el flujo de filtrado desde la foto #1, manteniendo intactas todas las imágenes ya descartadas (X).
- **Tres Botones de Decisión y Corrección en Fase 2:**
  - **`MANTENER FOTO`** (Atajos: `M`, `Enter`, `Espacio`): Confirma la imagen en el conjunto balanceado actual y avanza a la siguiente.
  - **`PASAR A SIN DEFECTO (S)` / `PASAR A CON DEFECTO (R)`** (Atajos: `S` o `C` si estás en R; `R` o `C` si estás en S): Reclasifica la imagen y la transfiere al grupo opuesto, corrigiendo fotos sanas que fueron erróneamente marcadas con defecto (o viceversa) y actualizando el balance en tiempo real.
  - **`DESCARTAR FOTO`** (Atajos: `X`, `Supr`): Desplaza inmediatamente la foto al grupo general de descartadas (`X`), disminuyendo el pool y actualizando los contadores de balance en tiempo real.
- **Deshacer Persistente (`Ctrl + Z` o botón `↺ Deshacer`):** Revierte al instante cualquier acción (mantenida, transferida o descartada), recuperando la fotografía en orden cronológico inverso.

---

## 4. Exportación Física a Carpetas

Puedes ejecutar la exportación en cualquier momento:
- Desde el botón **`📁 Exportar`** en la cabecera del visor web.
- O mediante el script CLI:
  ```bash
  python exportar.py
  ```

Las fotografías revisadas se copian sin alteraciones a:
- `clasificado/con_defecto/` (R)
- `clasificado/sin_defecto/` (S)
- `clasificado/dudosas/` (D)
- `clasificado/descartadas/` (X)

### Garantías de Exportación:
- **Nombres y bytes originales:** Se utiliza copia exacta binaria (`shutil.copy2`), conservando metadatos y resolución original (800x800).
- **Cero pendientes exportadas:** Las imágenes no revisadas nunca son copiadas.
- **Limpieza de copias obsoletas al reclasificar:** Si una imagen clasificada como `S` se reclasifica luego como `R`, el exportador la mueve a `con_defecto/` y elimina su copia anterior en `sin_defecto/` para impedir duplicidades.
- **Informes generados:** `clasificado/export_report.json` y `clasificado/export_manifest.json`.

---

## 5. Arquitectura del Proyecto

```
Hass Avocado Ripening Photographic Dataset/
│
├── Avocado Ripening Dataset/             # Carpeta original (14.710 imágenes JPG)
├── Avocado Ripening Dataset.xlsx         # Base de datos original con metadatos
│
├── config.json                           # Configuración central del sistema
├── PROTOCOLO_REVISION.md                 # Protocolo técnico de revisión visual (v1.0)
├── README.md                             # Este manual técnico
├── app.py                                # Punto de entrada para el servidor web
├── iniciar_visor.bat                     # Script de inicio rápido en Windows
├── generar_inventario.py                 # Script CLI de auditoría/generación de inventario
├── exportar.py                           # Script CLI para exportación física
├── verificar_sistema.py                  # Suite de pruebas automatizadas del flujo completo
│
├── data/
│   ├── inventory.json                    # Inventario oficial ordenado (14.710 items, 59 lotes)
│   ├── inventory.csv                     # Inventario exportable para Excel / Pandas
│   ├── inventory_report.json             # Estadísticas globales del dataset
│   ├── decisions.json                    # Registro persistente de decisiones del usuario
│   ├── history.jsonl                     # Bitácora transaccional (auditoría y deshacer)
│   ├── session.json                      # Estado de sesión (lote actual, imagen actual)
│   └── cache/thumbnails/                # Miniaturas cacheadas bajo demanda
│
├── clasificado/                          # Destino de exportación organizada
│   ├── con_defecto/                      # Fotografías de bandeja R
│   ├── sin_defecto/                      # Fotografías de bandeja S
│   ├── dudosas/                          # Fotografías de bandeja D
│   └── descartadas/                      # Fotografías de bandeja X
│
├── server/
│   ├── app.py                            # Servidor Flask REST en 127.0.0.1:5000
│   ├── inventory_manager.py              # Lógica de orden reproducible y partición
│   ├── decision_manager.py               # Gestión atómica de decisiones y sesiones
│   ├── export_service.py                 # Sincronización limpia de carpetas
│   └── thumbnail_service.py              # Optimización y caching de miniaturas
│
├── static/
│   ├── css/style.css                     # Interfaz moderna con modo oscuro y micro-animaciones
│   └── js/app.js                         # Controlador frontend: zoom, atajos, comparación
│
└── templates/
    └── index.html                        # Plantilla HTML5 del visor
```

---

## 6. Preparación para la Futura Etapa YOLO

El inventario ya incorpora el identificador canónico **`fruit_id`** (ej. `T10_002`, `T20_001`, `Tam_009`).  
Cuando inicies la fase de delimitación con cajas delimitadoras (*bounding boxes*):
1. Las imágenes de la bandeja `clasificado/con_defecto/` serán anotadas con cajas localizando **exclusivamente las costras o lesiones**, no el contorno completo del fruto.
2. Las imágenes `clasificado/sin_defecto/` actuarán como imágenes negativas de fondo (*background samples*).
3. Las imágenes dudosas (`D`) y descartadas (`X`) quedarán excluidas de los conjuntos de entrenamiento final.
4. **Particionamiento libre de fuga de datos:** Al dividir el conjunto en `train`, `val` y `test`, el agrupamiento se realizará por `fruit_id` (`GroupKFold`), asegurando que todas las vistas (`a`, `b`) y todos los días de una misma fruta permanezcan estrictamente en una sola partición.
5. El mismo esquema de `fruit_id` y metadatos de procedencia se aplicará a las futuras fotografías de campo recolectadas en Lambayeque.

---

## 7. Verificación del Sistema

La suite automatizada `verificar_sistema.py` valida:
- [x] Inventario completo con 14.710 imágenes únicas sin saltos ni duplicados.
- [x] Partición exacta en 59 lotes (58 lotes de 250 imágenes + 1 lote de 210 imágenes).
- [x] Asociación consistente de 478 frutas únicas (`fruit_id`).
- [x] Asignación y persistencia atómica de las cuatro bandejas (R, S, D, X).
- [x] Descarte ágil directo e inmediato (X) sin bloquear el flujo.
- [x] Historial auditable para deshacer (`Ctrl+Z`) y reclasificación.
- [x] Reanudación de sesión al reiniciar el servidor.
- [x] Detección de lote completado y registro de resumen.
- [x] Exportación física con preservación de nombres originales y limpieza de duplicados.
- [x] Caché de miniaturas bajo demanda para alto rendimiento.
- [x] Separación estricta entre pruebas y datos reales de clasificación.
