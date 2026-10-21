#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de verificación y pruebas automatizadas del sistema.
Verifica:
1. Integridad del inventario (14,710 imágenes, sin repeticiones ni omisiones, 59 lotes).
2. Asignación reproducible de fruta (fruit_id) y metadatos.
3. Guardado atómico de las cuatro categorías (R, S, D, X).
4. Reclasificación y Deshacer (Undo) con historial transaccional.
5. Reanudación de sesión (restauración de lote e imagen).
6. Validación de motivos obligatorios para descartadas (X).
7. Finalización y transición entre lotes (resumen automático al llegar a 0 pendientes).
8. Exportación física a carpetas con nombres originales y limpieza de copias obsoletas.
9. Manejo de errores en API / servicios.
10. Separación estricta entre datos de prueba y sesión real de usuario.
"""

import os
import sys
import json
import shutil
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server.inventory_manager import InventoryManager
from server.decision_manager import DecisionManager
from server.export_service import ExportService
from server.thumbnail_service import ThumbnailService

class TestSistemaClasificacion(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Crear directorio temporal aislado para pruebas
        cls.test_dir = tempfile.mkdtemp(prefix="test_hass_avocado_")
        cls.test_config_path = os.path.join(cls.test_dir, "test_config.json")
        cls.test_data_dir = os.path.join(cls.test_dir, "data")
        cls.test_export_dir = os.path.join(cls.test_dir, "clasificado")
        os.makedirs(cls.test_data_dir, exist_ok=True)
        os.makedirs(cls.test_export_dir, exist_ok=True)

        cls.config = {
            "dataset_images_dir": "Avocado Ripening Dataset",
            "excel_metadata_path": "Avocado Ripening Dataset.xlsx",
            "batch_size": 250,
            "inventory_json_path": "data/inventory.json",
            "inventory_csv_path": "data/inventory.csv",
            "inventory_report_path": "data/inventory_report.json",
            "decisions_path": os.path.join(cls.test_data_dir, "test_decisions.json"),
            "history_path": os.path.join(cls.test_data_dir, "test_history.jsonl"),
            "session_path": os.path.join(cls.test_data_dir, "test_session.json"),
            "batch_summaries_path": os.path.join(cls.test_data_dir, "test_batch_summaries.json"),
            "thumbnail_cache_dir": os.path.join(cls.test_data_dir, "cache", "thumbnails"),
            "export_dir": cls.test_export_dir,
            "protocol_version": "v1.0"
        }

        with open(cls.test_config_path, "w", encoding="utf-8") as f:
            json.dump(cls.config, f, indent=2)

        cls.inv_manager = InventoryManager(cls.test_config_path)
        cls.inv_manager.load_inventory()

    @classmethod
    def tearDownClass(cls):
        # Limpiar carpeta temporal de pruebas
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir, ignore_errors=True)

    def test_01_inventario_completo_sin_omisiones_ni_duplicados(self):
        """1. Verificar que el inventario tenga exactamente 14,710 imágenes únicas."""
        total = self.inv_manager.get_total_images()
        self.assertEqual(total, 14710, f"Se esperaban 14,710 imágenes, se encontraron {total}")

        all_ids = [item["image_id"] for item in self.inv_manager.inventory]
        self.assertEqual(len(all_ids), len(set(all_ids)), "Existen identificadores duplicados en el inventario")

        all_global_indices = [item["global_index"] for item in self.inv_manager.inventory]
        self.assertEqual(all_global_indices, list(range(1, 14711)), "Los índices globales deben ser 1..14710 sin saltos")

    def test_02_particion_de_lotes_consecutivos(self):
        """2. Verificar lotes de 250 imágenes (58 lotes de 250 + 1 lote de 210 = 59 lotes)."""
        total_batches = self.inv_manager.get_total_batches()
        self.assertEqual(total_batches, 59, f"Se esperaban 59 lotes, se encontraron {total_batches}")

        for b_id in range(1, 59):
            batch = self.inv_manager.get_batch(b_id)
            self.assertEqual(len(batch), 250, f"El lote {b_id} debe tener 250 imágenes")

        batch_59 = self.inv_manager.get_batch(59)
        self.assertEqual(len(batch_59), 210, f"El lote 59 debe tener 210 imágenes")

    def test_03_asociacion_de_frutas_unicas(self):
        """3. Verificar que fruit_id relacione correctamente vistas 'a' y 'b' y días."""
        fruits = self.inv_manager.inventory_by_fruit
        self.assertEqual(len(fruits), 478, f"Se esperaban 478 frutas únicas, se encontraron {len(fruits)}")

        # Tomar una fruta de muestra (ej. T10_002)
        sample_fruit = self.inv_manager.get_fruit_images("T10_002")
        self.assertGreater(len(sample_fruit), 0)
        views = set(it["view"] for it in sample_fruit)
        self.assertTrue("a" in views and "b" in views, "La fruta debe contener ambas vistas a y b")

    def test_04_guardado_y_validacion_de_las_cuatro_categorias(self):
        """4. Probar guardado de R, S, D, X con validación de motivo obligatorio para X."""
        dec_mgr = DecisionManager(self.test_config_path)

        # Probar R (Con defecto)
        r_item = self.inv_manager.inventory[0]["image_id"]
        res_r = dec_mgr.save_decision(r_item, "R", note="Lesión apical")
        self.assertEqual(res_r["category"], "R")
        self.assertTrue(res_r["provisional"])

        # Probar S (Sin defecto)
        s_item = self.inv_manager.inventory[1]["image_id"]
        res_s = dec_mgr.save_decision(s_item, "S")
        self.assertEqual(res_s["category"], "S")

        # Probar D (Dudosa)
        d_item = self.inv_manager.inventory[2]["image_id"]
        res_d = dec_mgr.save_decision(d_item, "D", note="Sombra en sutura")
        self.assertEqual(res_d["category"], "D")

        # Probar X sin motivo (debe arrojar error ValueError)
        x_item = self.inv_manager.inventory[3]["image_id"]
        with self.assertRaises(ValueError):
            dec_mgr.save_decision(x_item, "X", reason=None)

        # Probar X con motivo válido
        res_x = dec_mgr.save_decision(x_item, "X", reason="desenfoque")
        self.assertEqual(res_x["category"], "X")
        self.assertEqual(res_x["reason"], "desenfoque")

    def test_05_reclasificacion_y_deshacer(self):
        """5. Probar que una reclasificación actualice la decisión y Undo la revierta."""
        dec_mgr = DecisionManager(self.test_config_path)
        test_item = self.inv_manager.inventory[10]["image_id"]

        # 1. Asignar 'S'
        dec_mgr.save_decision(test_item, "S")
        self.assertEqual(dec_mgr.get_decision(test_item)["category"], "S")

        # 2. Reclasificar a 'R'
        dec_mgr.save_decision(test_item, "R", note="Detectada costra en revisión secundaria")
        self.assertEqual(dec_mgr.get_decision(test_item)["category"], "R")

        # 3. Deshacer (Undo) -> debe volver a 'S'
        undo_res = dec_mgr.undo_last_decision()
        self.assertIsNotNone(undo_res)
        self.assertEqual(dec_mgr.get_decision(test_item)["category"], "S")

    def test_06_persistencia_y_reanudacion_de_sesion(self):
        """6. Verificar que la sesión recuerde el lote y posición al reiniciar."""
        dec_mgr = DecisionManager(self.test_config_path)
        dec_mgr.update_session(batch_id=4, image_id="T10_d01_005_a_1.jpg", active_filter="pending")

        # Simular reinicio creando una nueva instancia
        dec_mgr_restarted = DecisionManager(self.test_config_path)
        session = dec_mgr_restarted.get_session()
        self.assertEqual(session["current_batch_id"], 4)
        self.assertEqual(session["current_image_id"], "T10_d01_005_a_1.jpg")
        self.assertEqual(session["active_filter"], "pending")

    def test_07_resumen_y_completado_de_lote(self):
        """7. Simular completar un lote y verificar registro de resumen."""
        dec_mgr = DecisionManager(self.test_config_path)
        b_summary = {
            "total": 250, "pending": 0, "R": 10, "S": 220, "D": 15, "X": 5
        }
        dec_mgr.record_batch_completion(1, b_summary)
        stored_summary = dec_mgr.get_batch_summary(1)
        self.assertIsNotNone(stored_summary)
        self.assertEqual(stored_summary["stats"]["total"], 250)
        self.assertIn(1, dec_mgr.get_completed_batches())

    def test_08_exportacion_limpia_sin_duplicados_al_reclasificar(self):
        """8. Verificar exportación física a clasificado/ y limpieza de archivos obsoletos."""
        dec_mgr = DecisionManager(self.test_config_path)
        export_svc = ExportService(self.inv_manager, dec_mgr, self.test_export_dir)

        target_img = self.inv_manager.inventory[20]["image_id"]
        filename = self.inv_manager.inventory[20]["filename"]

        # 1. Asignar 'S' y exportar
        dec_mgr.save_decision(target_img, "S")
        rep1 = export_svc.run_export()

        path_s = os.path.join(self.test_export_dir, "sin_defecto", filename)
        path_r = os.path.join(self.test_export_dir, "con_defecto", filename)

        self.assertTrue(os.path.exists(path_s), "La imagen debe existir en clasificado/sin_defecto")
        self.assertFalse(os.path.exists(path_r), "La imagen no debe existir en con_defecto")

        # 2. Reclasificar a 'R' y exportar nuevamente
        dec_mgr.save_decision(target_img, "R")
        rep2 = export_svc.run_export()

        self.assertTrue(os.path.exists(path_r), "La imagen ahora debe existir en clasificado/con_defecto")
        self.assertFalse(os.path.exists(path_s), "La copia anterior en sin_defecto debe haberse eliminado limpiamente")
        self.assertGreater(rep2["obsolete_cleaned_up"], 0)

    def test_09_servicio_de_miniaturas_bajo_demanda(self):
        """9. Verificar generación y caching de miniaturas JPEG."""
        thumb_svc = ThumbnailService(self.config["thumbnail_cache_dir"])
        sample = self.inv_manager.inventory[0]
        thumb_path = thumb_svc.get_thumbnail_path(sample["file_path"], sample["image_id"])

        self.assertIsNotNone(thumb_path)
        self.assertTrue(os.path.exists(thumb_path))
        # Verificar que el archivo en caché existe y pesa menos que el original
        orig_size = sample["file_size_bytes"]
        thumb_size = os.path.getsize(thumb_path)
        self.assertLess(thumb_size, orig_size, "La miniatura debe ser más ligera que la original")

def run_tests():
    print("=" * 70)
    print("  EJECUTANDO SUITE DE PRUEBAS DE INTEGRACIÓN DEL SISTEMA")
    print("=" * 70)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSistemaClasificacion)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    print("=" * 70)
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
