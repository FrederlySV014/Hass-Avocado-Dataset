# Protocolo de Revisión Visual y Clasificación Manual: Roña en Palta Hass

**Versión del Protocolo:** v1.0  
**Fecha de emisión:** Octubre 2026  
**Contexto de Aplicación:** Proyecto de Tesis — Detección superficial de roña en palta Hass mediante visión por computador y YOLO, agroexportación Lambayeque.

---

## 1. Objetivo y Alcance

Este protocolo define los criterios técnicos y visuales para la inspección manual, imagen por imagen, del conjunto fotográfico (*Hass Avocado Ripening Photographic Dataset*) y futuras colecciones de campo en Lambayeque. Su finalidad es clasificar de forma reproducible y confiable cada fotografía en una de las cuatro bandejas de trabajo:

- **R — Con defecto objetivo visible (Provisional)**
- **S — Sin defecto objetivo visible**
- **D — Dudosa (Requiere segunda revisión)**
- **X — Descartada / No utilizable**

---

## 2. Definición del Defecto Objetivo: Roña (*Sphaceloma perseae* / Roña del palto)

La **roña** o sarna del palto es una alteración superficial originada en etapas tempranas del fruto:
- **Aspecto visual:** Lesiones de tipo suberoso, costroso o acorchado, de tono marrón claro, canela, ocráceo o pardo rojizo.
- **Relieve y textura:** Sobresale ligeramente sobre la rugosidad natural del exocarpio de la Hass, presentando aspecto áspero o agrietado.
- **Distribución:** Puede presentarse como manchas pequeñas dispersas (punteaduras acorchadas) o placas confluentes de contorno irregular.

### Reglas críticas de exclusión visual:
1. **No confundir con el oscurecimiento por maduración:**  
   La transición fisiológica de la palta Hass (de verde brillante a violáceo/negro en estadios 3, 4 y 5) **NO es roña**. Las costras de roña mantienen textura suberosa diferenciable del brillo o tono ceroso de la maduración natural.
2. **No confundir con rozamiento por viento (wind scar) o lenticelas prominentes:**  
   El rozamiento por fricción suele ser plano y grisáceo/pálido. Las lenticelas son micropuntos uniformes normales de la epidermis.
3. **No juzgar por el nombre del archivo ni por el día de experimento:**  
   La clasificación debe basarse estrictamente en la evidencia visual observable en la fotografía que se está examinando.
4. **No fijar un tamaño máximo o mínimo arbitrario:**  
   Tanto lesiones pequeñas aisladas compatibles como grandes placas continuas son registradas como R si exhiben el patrón acorchado típico.

---

## 3. Criterios para las Cuatro Bandejas

### Bandeja R — Con defecto objetivo visible (Etiqueta Provisional)
- **Definición:** Se identifica con claridad visual al menos una lesión superficial compatible con roña en la porción visible del fruto.
- **Carácter provisional:** Toda asignación es provisional hasta la posterior etapa de delimitación por cajas delimitadoras (*bounding boxes*) y validación agronómica cruzada.
- **Notas opcionales:** Si la lesión se localiza en una zona específica (ápice, pedúnculo, zona ecuatorial), puede anotarse en el campo de texto libre.

### Bandeja S — Sin defecto objetivo visible
- **Definición:** En la superficie visible de esta toma fotográfica **no se observa** sintomatología compatible con roña.
- **Alcance estricto:**  
  *Importante:* Marcar una imagen como S **no certifica** que la fruta entera esté completamente sana en su cara oculta, ni que carezca de otros defectos fitosanitarios. Simplemente certifica que en la imagen actual no hay presencia visible del defecto objetivo.
- **Presencia de otros defectos:** Si el fruto presenta otro defecto (por ejemplo daño mecánico menor evidente o cambio de color normal) que no impide observar la piel y confirma que no hay roña, se clasifica como **S**.

### Bandeja D — Dudosa (Segunda Revisión)
- **Definición:** No existe certeza visual suficiente para asignar R ni S.
- **Causas típicas:**
  - Mancha o relieve atípico que podría ser roña incipiente o rozamiento mecánico dudoso.
  - Sombra proyectada o reflejo de iluminación que dificulta distinguir el relieve de la lesión.
  - Fruto en estado muy avanzado de madurez (negro arrugado) donde la textura superficial se confunde.
- **Regla de integridad:** **Nunca fuerces una decisión hacia R o S para reducir el porcentaje de dudosas.** Las dudosas protegen la calidad del dataset y son el insumo directo para la sesión de segunda revisión especializada.

### Bandeja X — Descartada / No utilizable
- **Definición:** La fotografía no permite evaluar adecuadamente la superficie del fruto o cae fuera de los estándares de inspección (desenfoque severo, deterioro masivo, oclusión relevante, archivo dañado, etc.).
- **Flujo de selección ágil:** Se asigna de forma directa e inmediata con la tecla **`X`** o el botón correspondiente, sin requerir la selección de un motivo para no ralentizar el ritmo de revisión. Si se desea dejar alguna observación puntual, se puede ingresar libremente en el campo de notas.

---

## 4. Manejo Temporal y Multivista de la Fruta

1. **Independencia de decisión por imagen:**  
   Cada fotografía (por ejemplo vista `a` del día 1) se evalúa y clasifica de forma independiente. **No se propagan etiquetas automáticamente** a la vista contralateral `b` ni a días posteriores.
2. **Uso de la herramienta de comparación:**  
   El visor permite inspeccionar las tomas de la misma fruta (identificada por `fruit_id`).  
   - Si una lesión visible en el día 5 también estaba en el día 1 pero con menor contraste, puedes cotejarla.
   - Si la lesión sólo es visible en la cara `a` y oculta en la cara `b`, la cara `a` será R y la cara `b` podrá ser S. **Esto no es un error:** refleja la realidad tridimensional del fruto.
3. **Agrupación para modelos de IA posteriores:**  
   Aunque las decisiones son por imagen, todas las fotos de un mismo `fruit_id` pertenecen a la misma entidad física y deben mantenerse unidas en las particiones de entrenamiento, validación o testeo de YOLO.

---

## 5. Control de Calidad y Reclasificación

- **Deshacer:** Disponible mediante `Ctrl+Z` o botón en interfaz.
- **Reclasificación:** Si tras revisar otras vistas o avanzar en el lote decides cambiar una clasificación anterior, puedes regresar y cambiarla en cualquier momento.
- **Sincronización:** Toda reclasificación actualiza inmediatamente el registro central `decisions.json` y el historial auditable, garantizando que ninguna imagen quede duplicada en las exportaciones.
