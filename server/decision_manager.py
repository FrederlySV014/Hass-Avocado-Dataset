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
            "last_updated": datetime.datetime.utcnow().isoformat() + "Z"
        }

        self._load_decisions()
        self._load_batch_summaries()
        self._load_session()

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
                    self.session_state = json.load(f)
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

        if category == "X":
            if not reason or not reason.strip():
                raise ValueError("Para la categoría 'X (Descartada)', el motivo es obligatorio.")

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

        return decision_data

    def undo_last_decision(self) -> Optional[Dict[str, Any]]:
        """
        Revierte la última acción del historial auditable.
        """
        if not os.path.exists(self.history_path):
            return None

        # Leer última línea de historial
        lines = []
        with open(self.history_path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]

        if not lines:
            return None

        last_entry = json.loads(lines[-1])
        # Solo revertir acciones normales de clasificación/reclasificación
        if last_entry.get("action") == "undo":
            # Si el último fue un undo, buscar la entrada anterior efectiva si fuera necesario,
            # pero más seguro: revertir lo que hizo el último registro
            pass

        image_id = last_entry["image_id"]
        prev_state = last_entry.get("previous_state")

        if prev_state:
            self.decisions[image_id] = prev_state
        else:
            if image_id in self.decisions:
                del self.decisions[image_id]

        self._save_decisions_atomic()

        # Registrar el evento de Undo en el historial
        now_iso = datetime.datetime.utcnow().isoformat() + "Z"
        undo_record = {
            "action": "undo",
            "image_id": image_id,
            "timestamp": now_iso,
            "undone_entry": last_entry,
            "restored_state": prev_state
        }
        self._append_history(undo_record)

        return {
            "image_id": image_id,
            "restored_state": prev_state
        }

    def get_decision(self, image_id: str) -> Optional[Dict[str, Any]]:
        return self.decisions.get(image_id)

    def get_all_decisions(self) -> Dict[str, Dict[str, Any]]:
        return self.decisions

    def update_session(self, batch_id: int, image_id: Optional[str] = None, active_filter: str = "all") -> None:
        self.session_state["current_batch_id"] = int(batch_id)
        if image_id is not None:
            self.session_state["current_image_id"] = image_id
        if active_filter:
            self.session_state["active_filter"] = active_filter
        self.session_state["last_updated"] = datetime.datetime.utcnow().isoformat() + "Z"
        self._save_session_atomic()

    def get_session(self) -> Dict[str, Any]:
        return self.session_state

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
