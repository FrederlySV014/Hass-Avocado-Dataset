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
        """4. Probar guardado de R, S, D, X directamente sin requerir motivo para X."""
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

        # Probar X sin motivo (se descarta de forma ágil e inmediata)
        x_item = self.inv_manager.inventory[3]["image_id"]
        res_x = dec_mgr.save_decision(x_item, "X")
        self.assertEqual(res_x["category"], "X")
        self.assertIsNone(res_x["reason"])

        # Probar categoría inválida
        with self.assertRaises(ValueError):
            dec_mgr.save_decision(x_item, "Z")

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

    def test_10_fase2_mantener_y_descartar_balanceo(self):
        """10. Verificar Fase 2: Mantener, Descartar a grupo general y Deshacer."""
        dec_mgr = DecisionManager(self.test_config_path)
        target_img = self.inv_manager.inventory[30]["image_id"]

        # 1. Asignar 'R' inicialmente
        dec_mgr.save_decision(target_img, "R")
        self.assertEqual(dec_mgr.get_decision(target_img)["category"], "R")

        # 2. Mantener en Fase 2
        res_keep = dec_mgr.mark_phase2_keep(target_img)
        self.assertEqual(res_keep["category"], "R")
        self.assertTrue(res_keep["phase2_reviewed"])
        self.assertEqual(res_keep["phase2_action"], "kept")

        # 3. Descartar en Fase 2 -> pasa directamente a 'X'
        res_disc = dec_mgr.mark_phase2_discard(target_img, note="Descarte por balanceo")
        self.assertEqual(res_disc["category"], "X")
        self.assertEqual(res_disc["reason"], "descarte_fase2_balanceo")
        self.assertEqual(dec_mgr.get_decision(target_img)["category"], "X")

        # 4. Deshacer (Undo) -> vuelve a 'R'
        undo_res = dec_mgr.undo_last_decision()
        self.assertIsNotNone(undo_res)
        self.assertEqual(dec_mgr.get_decision(target_img)["category"], "R")

        # 5. Persistencia de sesión de Fase 2
        dec_mgr.update_session(active_phase="phase2", phase2_category="R", phase2_image_id=target_img)
        session = dec_mgr.get_session()
        self.assertEqual(session["active_phase"], "phase2")
        self.assertEqual(session["phase2_category"], "R")

    def test_11_deshacer_multiple_consecutivo(self):
        """11. Probar deshacer múltiple consecutivo (5 o más pasos) en reversa."""
        dec_mgr = DecisionManager(self.test_config_path)
        test_images = [self.inv_manager.inventory[i]["image_id"] for i in range(20, 26)]

        # Registrar estado inicial como 'R' para 6 imágenes
        for img in test_images:
            dec_mgr.save_decision(img, "R")
            self.assertEqual(dec_mgr.get_decision(img)["category"], "R")

        # Simular descarte rápido consecutivo de 5 imágenes en Fase 2
        discarded_sequence = test_images[:5]
        for img in discarded_sequence:
            dec_mgr.mark_phase2_discard(img, note="Descarte rápido")
            self.assertEqual(dec_mgr.get_decision(img)["category"], "X")

        # Deshacer 5 veces consecutivas (una por una)
        for i in reversed(range(5)):
            target_img = discarded_sequence[i]
            undo_res = dec_mgr.undo_last_decision(steps=1)
            self.assertIsNotNone(undo_res)
            self.assertEqual(undo_res["image_id"], target_img)
            self.assertEqual(dec_mgr.get_decision(target_img)["category"], "R")

        # Verificar que tras reiniciar el gestor, la pila y decisiones se mantengan íntegras
        dec_mgr_restarted = DecisionManager(self.test_config_path)
        for img in discarded_sequence:
            self.assertEqual(dec_mgr_restarted.get_decision(img)["category"], "R")

    def test_12_api_undo_tolerancia_tipos_y_fase2(self):
        """12. Verificar que /api/undo no falle con tipos no numéricos (ej. eventos DOM) y restaure Fase 2."""
        import server.app as sapp
        orig_dec_mgr = sapp.dec_manager
        try:
            test_dec_mgr = DecisionManager(self.test_config_path)
            sapp.dec_manager = test_dec_mgr
            client = sapp.app.test_client()

            # Clasificar y descartar una imagen de prueba
            t_img = self.inv_manager.inventory[30]["image_id"]
            test_dec_mgr.save_decision(t_img, "R")
            test_dec_mgr.mark_phase2_discard(t_img)
            self.assertEqual(test_dec_mgr.get_decision(t_img)["category"], "X")

            # Probar con objeto simulando PointerEvent ({})
            res_dict = client.post("/api/undo", json={"steps": {}})
            self.assertEqual(res_dict.status_code, 200, f"Fallo al enviar steps={{}}: {res_dict.data}")
            self.assertEqual(test_dec_mgr.get_decision(t_img)["category"], "R")

            # Probar de nuevo con string numérico y cuerpo vacío
            test_dec_mgr.mark_phase2_discard(t_img)
            res_str = client.post("/api/undo", json={"steps": "1"})
            self.assertEqual(res_str.status_code, 200)
            self.assertEqual(test_dec_mgr.get_decision(t_img)["category"], "R")

            test_dec_mgr.mark_phase2_discard(t_img)
            res_empty = client.post("/api/undo", json={})
            self.assertEqual(res_empty.status_code, 200)
            self.assertEqual(test_dec_mgr.get_decision(t_img)["category"], "R")
        finally:
            sapp.dec_manager = orig_dec_mgr

    def test_13_fase2_transferencia_entre_grupos_r_y_s(self):
        """13. Probar reclasificación y transferencia entre grupos 'R' y 'S' en Fase 2 y su reversión con Undo."""
        import server.app as sapp
        orig_dec_mgr = sapp.dec_manager
        try:
            test_dec_mgr = DecisionManager(self.test_config_path)
            sapp.dec_manager = test_dec_mgr
            client = sapp.app.test_client()

            test_img = self.inv_manager.inventory[35]["image_id"]
            # 1. Foto clasificada inicialmente como 'R' por error
            test_dec_mgr.save_decision(test_img, "R")
            self.assertEqual(test_dec_mgr.get_decision(test_img)["category"], "R")

            # 2. Reclasificarla y transferirla a 'S' (Sin defecto)
            res_action = client.post("/api/phase2/action", json={
                "image_id": test_img,
                "action": "transfer",
                "category": "R"
            })
            self.assertEqual(res_action.status_code, 200)
            self.assertEqual(test_dec_mgr.get_decision(test_img)["category"], "S")
            self.assertEqual(test_dec_mgr.get_decision(test_img)["phase2_action"], "transferred")

            # 3. Deshacer la transferencia (debe volver a 'R')
            undo_res = client.post("/api/undo", json={"steps": 1})
            self.assertEqual(undo_res.status_code, 200)
            self.assertEqual(test_dec_mgr.get_decision(test_img)["category"], "R")

            # 4. Transferir en sentido inverso (S -> R)
            test_dec_mgr.save_decision(test_img, "S")
            res_to_r = client.post("/api/phase2/action", json={
                "image_id": test_img,
                "action": "transfer",
                "category": "S"
            })
            self.assertEqual(res_to_r.status_code, 200)
            self.assertEqual(test_dec_mgr.get_decision(test_img)["category"], "R")
        finally:
            sapp.dec_manager = orig_dec_mgr

    def test_14_fase2_nueva_ronda_y_meta_1500(self):
        """14. Probar reinicio de ronda en Fase 2 y cálculo de metas hacia 1,500 fotos por grupo."""
        import server.app as sapp
        orig_dec_mgr = sapp.dec_manager
        try:
            test_dec_mgr = DecisionManager(self.test_config_path)
            sapp.dec_manager = test_dec_mgr
            client = sapp.app.test_client()

            img_r = self.inv_manager.inventory[40]["image_id"]
            img_s = self.inv_manager.inventory[41]["image_id"]
            img_x = self.inv_manager.inventory[42]["image_id"]

            test_dec_mgr.save_decision(img_r, "R")
            test_dec_mgr.mark_phase2_keep(img_r)

            test_dec_mgr.save_decision(img_s, "S")
            test_dec_mgr.mark_phase2_keep(img_s)

            test_dec_mgr.save_decision(img_x, "R")
            test_dec_mgr.mark_phase2_discard(img_x)

            self.assertTrue(test_dec_mgr.get_decision(img_r)["phase2_reviewed"])
            self.assertTrue(test_dec_mgr.get_decision(img_s)["phase2_reviewed"])
            self.assertEqual(test_dec_mgr.get_decision(img_x)["category"], "X")

            # Iniciar nueva ronda vía API
            res_reset = client.post("/api/phase2/reset_round", json={"category": None})
            self.assertEqual(res_reset.status_code, 200)

            # Verificar que R y S se reiniciaron a phase2_reviewed=False para una nueva pasada
            self.assertFalse(test_dec_mgr.get_decision(img_r)["phase2_reviewed"])
            self.assertFalse(test_dec_mgr.get_decision(img_s)["phase2_reviewed"])

            # Verificar que la descartada (X) NO fue afectada
            self.assertEqual(test_dec_mgr.get_decision(img_x)["category"], "X")

            # Verificar cálculo de pool y meta 1500
            res_pool = client.get("/api/phase2/pool?category=R&filter=all")
            self.assertEqual(res_pool.status_code, 200)
            data = res_pool.get_json()
            self.assertEqual(data["stats"]["target_goal"], 1500)
        finally:
            sapp.dec_manager = orig_dec_mgr

    def test_15_revision_pool_dudosas(self):
        """
        15. Probar carga del Pool D (Dudosas), reclasificación hacia R o S, descarte hacia X y reversión con Undo.
        """
        import server.app as sapp
        orig_dec_mgr = sapp.dec_manager
        try:
            test_dec_mgr = DecisionManager(self.test_config_path)
            sapp.dec_manager = test_dec_mgr
            client = sapp.app.test_client()

            initial_d = sum(1 for d in test_dec_mgr.get_all_decisions().values() if d.get("category") == "D")
            # Configurar tres imágenes como dudosas (D)
            img_d1 = self.inv_manager.inventory[50]["image_id"]
            img_d2 = self.inv_manager.inventory[51]["image_id"]
            img_d3 = self.inv_manager.inventory[52]["image_id"]
            test_dec_mgr.save_decision(img_d1, "D")
            test_dec_mgr.save_decision(img_d2, "D")
            test_dec_mgr.save_decision(img_d3, "D")

            # 1. Cargar Pool D por API
            res_pool = client.get("/api/phase2/pool?category=D&filter=all")
            self.assertEqual(res_pool.status_code, 200)
            pool_data = res_pool.get_json()
            self.assertEqual(pool_data["category"], "D")
            self.assertEqual(pool_data["stats"]["total_d"], initial_d + 3)
            self.assertEqual(len(pool_data["items"]), initial_d + 3)

            # 2. Reclasificar dudosa 1 como Con Defecto (R)
            res_to_r = client.post("/api/phase2/action", json={
                "image_id": img_d1,
                "action": "transfer",
                "target_category": "R",
                "category": "D"
            })
            self.assertEqual(res_to_r.status_code, 200)
            self.assertEqual(test_dec_mgr.get_decision(img_d1)["category"], "R")
            self.assertEqual(test_dec_mgr.get_decision(img_d1)["phase2_previous_category"], "D")

            # 3. Reclasificar dudosa 2 como Sin Defecto (S)
            res_to_s = client.post("/api/phase2/action", json={
                "image_id": img_d2,
                "action": "transfer",
                "target_category": "S",
                "category": "D"
            })
            self.assertEqual(res_to_s.status_code, 200)
            self.assertEqual(test_dec_mgr.get_decision(img_d2)["category"], "S")

            # 4. Descartar dudosa 3 hacia X
            res_discard = client.post("/api/phase2/action", json={
                "image_id": img_d3,
                "action": "discard",
                "category": "D"
            })
            self.assertEqual(res_discard.status_code, 200)
            self.assertEqual(test_dec_mgr.get_decision(img_d3)["category"], "X")

            # Ahora en Pool D deben quedar initial_d imágenes
            res_pool_after = client.get("/api/phase2/pool?category=D&filter=all")
            self.assertEqual(len(res_pool_after.get_json()["items"]), initial_d)
            self.assertEqual(res_pool_after.get_json()["stats"]["total_d"], initial_d)

            # 5. Deshacer el descarte de la imagen 3 (debe volver a D)
            res_undo = client.post("/api/undo", json={"steps": 1})
            self.assertEqual(res_undo.status_code, 200)
            undo_data = res_undo.get_json()
            self.assertEqual(undo_data["image_id"], img_d3)
            self.assertEqual(test_dec_mgr.get_decision(img_d3)["category"], "D")

            # 6. Deshacer las transferencias de img_d2 e img_d1
            client.post("/api/undo", json={"steps": 2})
            self.assertEqual(test_dec_mgr.get_decision(img_d2)["category"], "D")
            self.assertEqual(test_dec_mgr.get_decision(img_d1)["category"], "D")
        finally:
            sapp.dec_manager = orig_dec_mgr

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
