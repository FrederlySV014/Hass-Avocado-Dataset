import os
from PIL import Image
from typing import Optional

class ThumbnailService:
    """
    Servicio de generación y entrega de miniaturas bajo demanda con caché en disco.
    Permite cargar galerías de lotes con un consumo mínimo de memoria y ancho de banda.
    """

    def __init__(self, cache_dir: str = "data/cache/thumbnails", thumb_size: tuple = (220, 220)):
        self.cache_dir = cache_dir
        self.thumb_size = thumb_size
        os.makedirs(self.cache_dir, exist_ok=True)

    def get_thumbnail_path(self, original_path: str, image_id: str) -> Optional[str]:
        """
        Obtiene la ruta de la miniatura en caché. Si no existe, la genera y la guarda.
        """
        if not os.path.exists(original_path):
            return None

        # Nombre de archivo en caché
        cache_filename = f"thumb_{image_id}"
        if not cache_filename.lower().endswith(".jpg"):
            cache_filename += ".jpg"

        cached_path = os.path.join(self.cache_dir, cache_filename)

        if os.path.exists(cached_path):
            return cached_path

        try:
            with Image.open(original_path) as im:
                im_thumb = im.copy()
                im_thumb.thumbnail(self.thumb_size, Image.Resampling.LANCZOS)
                # Guardar JPEG optimizado
                im_thumb.save(cached_path, "JPEG", quality=80, optimize=True)
            return cached_path
        except Exception as e:
            print(f"[ERROR] No se pudo generar miniatura para {original_path}: {e}")
            # En caso de falla, fallback a la original
            return original_path
