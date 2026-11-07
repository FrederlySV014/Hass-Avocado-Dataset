import os
import json
import datetime
from typing import Dict, Any, Optional, List, Tuple

VALID_CATEGORIES = {"R", "S", "D", "X"}
VALID_DISCARD_REASONS = {
    "desenfoque",
    "deterioro que impide evaluar",
    "superficie relevante oculta",
    "archivo corrupto",
    "otro"
}

class DecisionManager:
    """
    Gestor atómico y persistente de las decisiones de clasificación manual.
    Garantiza:
    - Escrituras atómicas a disco (sin datos incompletos).
    - Historial transaccional para Deshacer (Undo) y Reclasificación.
    - Prevención de decisiones duplicadas por pulsaciones repetidas (debounce/idempotencia).
    - Validación de motivos obligatorios para descartadas (X).
    - Estado de sesión para reanudar lote e imagen al reiniciar.
    - Auditoría de resumen por lote al completarse.
    """

    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.decisions_path = self.config.get("decisions_path", "data/decisions.json")
        self.history_path = self.config.get("history_path", "data/history.jsonl")
        self.session_path = self.config.get("session_path", "data/session.json")
        self.summaries_path = self.config.get("batch_summaries_path", "data/batch_summaries.json")
        self.protocol_version = self.config.get("protocol_version", "v1.0")

        self.decisions: Dict[str, Dict[str, Any]] = {}
        self.batch_summaries: Dict[str, Dict[str, Any]] = {}
        self.session_state: Dict[str, Any] = {
            "current_batch_id": 1,
            "current_image_id": None,
            "active_filter": "all",
            "active_phase": "phase1",
            "phase2_category": "R",
            "phase2_image_id": None,
            "last_updated": datetime.datetime.utcnow().isoformat() + "Z"
        }

        self._load_decisions()
        self._load_batch_summaries()
        self._load_session()
        self._build_undo_stack()

    def _build_undo_stack(self) -> None:
        """
        Reconstruye la pila en memoria de acciones reversibles a partir de la bitácora history.jsonl.
        Permite deshacer múltiples pasos consecutivos de manera persistente tras reinicios.
        """
        self.undo_stack: List[Dict[str, Any]] = []
        if not os.path.exists(self.history_path):
            return
        try:
            with open(self.history_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    entry = json.loads(line)
                    action = entry.get("action")
                    if action in ("classify", "reclassify", "phase2_keep", "phase2_discard", "phase2_transfer"):
                        self.undo_stack.append(entry)
                    elif action == "undo":
                        if self.undo_stack:
                            self.undo_stack.pop()
        except Exception as e:
            print(f"[ERROR] Error al reconstruir undo_stack desde {self.history_path}: {e}")

    def _load_config(self) -> Dict[str, Any]:
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _load_decisions(self) -> None:
        if os.path.exists(self.decisions_path):
            try:
                with open(self.decisions_path, "r", encoding="utf-8") as f:
                    self.decisions = json.load(f)
            except Exception as e:
                print(f"[ERROR] Error al leer {self.decisions_path}: {e}")
                self.decisions = {}
        else:
            self.decisions = {}

    def _load_batch_summaries(self) -> None:
        if os.path.exists(self.summaries_path):
            try:
                with open(self.summaries_path, "r", encoding="utf-8") as f:
                    self.batch_summaries = json.load(f)
            except Exception:
                self.batch_summaries = {}
        else:
            self.batch_summaries = {}

    def _load_session(self) -> None:
        if os.path.exists(self.session_path):
            try:
                with open(self.session_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.session_state.update(data)
            except Exception:
                pass

    def _save_decisions_atomic(self) -> None:
        tmp_path = self.decisions_path + ".tmp"
        os.makedirs(os.path.dirname(self.decisions_path) or ".", exist_ok=True)
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(self.decisions, f, indent=2, ensure_ascii=False)
        # Reemplazo atómico en Windows
        if os.path.exists(self.decisions_path):
            os.replace(tmp_path, self.decisions_path)
        else:
            os.rename(tmp_path, self.decisions_path)

    def _save_session_atomic(self) -> None:
        tmp_path = self.session_path + ".tmp"
        os.makedirs(os.path.dirname(self.session_path) or ".", exist_ok=True)
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(self.session_state, f, indent=2, ensure_ascii=False)
        if os.path.exists(self.session_path):
            os.replace(tmp_path, self.session_path)
        else:
            os.rename(tmp_path, self.session_path)

    def _save_batch_summaries_atomic(self) -> None:
        tmp_path = self.summaries_path + ".tmp"
        os.makedirs(os.path.dirname(self.summaries_path) or ".", exist_ok=True)
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(self.batch_summaries, f, indent=2, ensure_ascii=False)
        if os.path.exists(self.summaries_path):
            os.replace(tmp_path, self.summaries_path)
        else:
            os.rename(tmp_path, self.summaries_path)

    def _append_history(self, action_record: Dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(self.history_path) or ".", exist_ok=True)
        with open(self.history_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(action_record, ensure_ascii=False) + "\n")

    def save_decision(
        self,
        image_id: str,
        category: str,
        note: str = "",
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Registra o actualiza la decisión de una imagen.
        """
        category = category.strip().upper()
        if category not in VALID_CATEGORIES:
            raise ValueError(f"Categoría inválida '{category}'. Debe ser una de: {sorted(list(VALID_CATEGORIES))}")

        now_iso = datetime.datetime.utcnow().isoformat() + "Z"
        prev_decision = self.decisions.get(image_id)

        # Evitar escrituras idénticas repetidas en una ráfaga (debounce lógico)
        if prev_decision and prev_decision.get("category") == category and \
           prev_decision.get("note") == note and prev_decision.get("reason") == reason:
            return prev_decision

        decision_data = {
            "image_id": image_id,
            "category": category,
            "timestamp": now_iso,
            "note": note.strip() if note else "",
            "reason": reason.strip() if reason else None,
            "protocol_version": self.protocol_version,
            "provisional": True
        }

        self.decisions[image_id] = decision_data
        self._save_decisions_atomic()

        # Registro en bitácora de auditoría
        history_entry = {
            "action": "reclassify" if prev_decision else "classify",
            "image_id": image_id,
            "timestamp": now_iso,
            "previous_state": prev_decision,
            "new_state": decision_data
        }
        self._append_history(history_entry)
        self.undo_stack.append(history_entry)

        return decision_data

    def undo_last_decision(self, steps: int = 1) -> Optional[Dict[str, Any]]:
        """
        Revierte hasta `steps` acciones de la pila de deshacer de manera consecutiva.
        Restaura el estado previo en decisions.json y registra cada evento 'undo' en history.jsonl.
        """
        if steps < 1:
            steps = 1

        if not self.undo_stack:
            return None

        undone_entries = []
        last_image_id = None
        last_restored_state = None
        now_iso = datetime.datetime.utcnow().isoformat() + "Z"

        for _ in range(steps):
            if not self.undo_stack:
                break

            entry_to_undo = self.undo_stack.pop()
            image_id = entry_to_undo["image_id"]
            prev_state = entry_to_undo.get("previous_state")

            if prev_state:
                self.decisions[image_id] = prev_state
            else:
                if image_id in self.decisions:
                    del self.decisions[image_id]

            undo_record = {
                "action": "undo",
                "image_id": image_id,
                "timestamp": now_iso,
                "undone_entry": entry_to_undo,
                "restored_state": prev_state
            }
            self._append_history(undo_record)

            undone_entries.append({
                "image_id": image_id,
                "restored_state": prev_state
            })
            last_image_id = image_id
            last_restored_state = prev_state

        if not undone_entries:
            return None

        self._save_decisions_atomic()

        return {
            "image_id": last_image_id,
            "restored_state": last_restored_state,
            "undone_count": len(undone_entries),
            "undone_items": undone_entries,
            "remaining_undo_count": len(self.undo_stack)
        }

    def get_decision(self, image_id: str) -> Optional[Dict[str, Any]]:
        return self.decisions.get(image_id)

    def get_all_decisions(self) -> Dict[str, Dict[str, Any]]:
        return self.decisions

    def update_session(
        self,
        batch_id: Optional[int] = None,
        image_id: Optional[str] = None,
        active_filter: Optional[str] = None,
        active_phase: Optional[str] = None,
        phase2_category: Optional[str] = None,
        phase2_image_id: Optional[str] = None
    ) -> None:
        if batch_id is not None:
            self.session_state["current_batch_id"] = int(batch_id)
        if image_id is not None:
            self.session_state["current_image_id"] = image_id
        if active_filter is not None:
            self.session_state["active_filter"] = active_filter
        if active_phase is not None:
            self.session_state["active_phase"] = active_phase
        if phase2_category is not None:
            self.session_state["phase2_category"] = phase2_category
        if phase2_image_id is not None:
            self.session_state["phase2_image_id"] = phase2_image_id
        self.session_state["last_updated"] = datetime.datetime.utcnow().isoformat() + "Z"
        self._save_session_atomic()

    def mark_phase2_keep(self, image_id: str) -> Dict[str, Any]:
        """
        Confirma que la imagen se mantiene en su categoría actual (R o S) durante la Fase 2.
        """
        now_iso = datetime.datetime.utcnow().isoformat() + "Z"
        current = self.decisions.get(image_id)
        if not current:
            raise ValueError(f"No existe decisión previa para {image_id}")

        prev_decision = dict(current)
        current["phase2_reviewed"] = True
        current["phase2_action"] = "kept"
        current["phase2_timestamp"] = now_iso

        self.decisions[image_id] = current
        self._save_decisions_atomic()

        history_entry = {
            "action": "phase2_keep",
            "image_id": image_id,
            "timestamp": now_iso,
            "previous_state": prev_decision,
            "new_state": dict(current)
        }
        self._append_history(history_entry)
        self.undo_stack.append(history_entry)
        return current

    def mark_phase2_discard(self, image_id: str, note: str = "") -> Dict[str, Any]:
        """
        Descarta la imagen en la Fase 2 de balanceo, moviéndola al grupo general de descartadas ('X').
        """
        now_iso = datetime.datetime.utcnow().isoformat() + "Z"
        current = self.decisions.get(image_id)
        if not current:
            raise ValueError(f"No existe decisión previa para {image_id}")

        prev_decision = dict(current)
        decision_data = {
            "image_id": image_id,
            "category": "X",
            "timestamp": now_iso,
            "note": note.strip() if note else current.get("note", ""),
            "reason": "descarte_fase2_balanceo",
            "protocol_version": self.protocol_version,
            "provisional": False,
            "phase2_reviewed": True,
            "phase2_action": "discarded",
            "phase2_previous_category": current.get("category"),
            "phase2_timestamp": now_iso
        }

        self.decisions[image_id] = decision_data
        self._save_decisions_atomic()

        history_entry = {
            "action": "phase2_discard",
            "image_id": image_id,
            "timestamp": now_iso,
            "previous_state": prev_decision,
            "new_state": decision_data
        }
        self._append_history(history_entry)
        self.undo_stack.append(history_entry)
        return decision_data

    def mark_phase2_transfer(
        self,
        image_id: str,
        target_category: Optional[str] = None,
        note: str = ""
    ) -> Dict[str, Any]:
        """
        Reclasifica una imagen en Fase 2 transfiriéndola entre los grupos 'R' y 'S'.
        Corrige clasificaciones erróneas previas (ej. frutas sanas asignadas por error a 'R').
        """
        current = self.decisions.get(image_id)
        if not current:
            raise ValueError(f"No existe decisión previa para {image_id}")

        curr_cat = current.get("category", "R")
        if not target_category:
            target_cat = "S" if curr_cat == "R" else "R"
        else:
            target_cat = target_category.strip().upper()

        if target_cat not in ("R", "S"):
            raise ValueError(f"Categoría de transferencia inválida: '{target_cat}'. Solo se permite transferir a 'R' o 'S'")

        now_iso = datetime.datetime.utcnow().isoformat() + "Z"
        prev_decision = dict(current)

        decision_data = {
            "image_id": image_id,
            "category": target_cat,
            "timestamp": now_iso,
            "note": note.strip() if note else current.get("note", ""),
            "reason": None,
            "protocol_version": self.protocol_version,
            "provisional": True,
            "phase2_reviewed": True,
            "phase2_action": "transferred",
            "phase2_previous_category": curr_cat,
            "phase2_timestamp": now_iso
        }

        self.decisions[image_id] = decision_data
        self._save_decisions_atomic()

        history_entry = {
            "action": "phase2_transfer",
            "image_id": image_id,
            "timestamp": now_iso,
            "previous_state": prev_decision,
            "new_state": decision_data
        }
        self._append_history(history_entry)
        self.undo_stack.append(history_entry)
        return decision_data

    def get_session(self) -> Dict[str, Any]:
        return self.session_state

    def start_phase2_new_round(self, category: Optional[str] = None) -> Dict[str, Any]:
        """
        Inicia una nueva ronda de depuración y curación en Fase 2.
        Reinicia las marcas 'phase2_reviewed' a False para las imágenes activas en R y/o S,
        permitiendo una nueva pasada consecutiva desde la foto #1 hasta alcanzar la meta de 1500 por clase.
        NO afecta a las imágenes descartadas (X) ni a las dudosas (D).
        """
        now_iso = datetime.datetime.utcnow().isoformat() + "Z"
        if category and category.strip().upper() in ("R", "S", "D"):
            target_cats = {category.strip().upper()}
        else:
            target_cats = {"R", "S"}

        reset_count = 0
        for img_id, dec in self.decisions.items():
            if dec.get("category") in target_cats:
                dec["phase2_reviewed"] = False
                dec["phase2_action"] = None
                dec["phase2_round_reset_at"] = now_iso
                reset_count += 1

        self._save_decisions_atomic()

        history_entry = {
            "action": "phase2_new_round",
            "categories": list(target_cats),
            "reset_count": reset_count,
            "timestamp": now_iso
        }
        self._append_history(history_entry)

        # Resetear sesión al inicio del pool
        self.session_state["phase2_image_id"] = None
        self._save_session_atomic()

        return {
            "reset_count": reset_count,
            "categories": list(target_cats),
            "timestamp": now_iso
        }

    def record_batch_completion(self, batch_id: int, summary: Dict[str, Any]) -> None:
        str_id = str(batch_id)
        self.batch_summaries[str_id] = {
            "batch_id": batch_id,
            "completed_at": datetime.datetime.utcnow().isoformat() + "Z",
            "stats": summary
        }
        self._save_batch_summaries_atomic()

    def get_batch_summary(self, batch_id: int) -> Optional[Dict[str, Any]]:
        return self.batch_summaries.get(str(batch_id))

    def get_completed_batches(self) -> List[int]:
        return [int(k) for k in self.batch_summaries.keys()]
