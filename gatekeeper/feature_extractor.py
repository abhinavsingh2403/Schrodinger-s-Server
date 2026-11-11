"""
feature_extractor.py: Unified feature extraction with strict offline and live parity.

Per AGENTS.md Rule 10 & EXPERIMENT0.md Section 4:
- Identical code path for live sensor events and offline log batches
- Cumulative stage features (S1 through S5)
- No leakage from future session events
- No raw passwords, raw attacker IPs, or instance identifiers
"""

from __future__ import annotations

import re
from typing import Any


class SessionFeatureExtractor:
    """Extracts stage-by-stage cumulative features from a stream of Cowrie events.

    Supports both live Cowrie event streams and raw flat-record events from data_all.zip.
    """

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        """Reset internal accumulator for a new session."""
        self.client_version: str = ""
        self.hassh: str = ""
        self.kex_algs: list[str] = []
        self.key_algs: list[str] = []
        self.ciphers: list[str] = []
        self.macs: list[str] = []
        self.compressions: list[str] = []
        self.auth_attempts: int = 0
        self.failed_logins: int = 0
        self.auth_success: bool = False
        self.has_pty: bool = False
        self.term_width: int = 0
        self.term_height: int = 0
        self.is_exec: bool = False
        self.commands: list[str] = []
        self.ts_login: str | None = None
        self.ts_cmd1: str | None = None

    @staticmethod
    def _to_list(val: Any) -> list[str]:
        if isinstance(val, list):
            return [str(x) for x in val]
        if isinstance(val, str) and val.strip():
            return [x.strip() for x in val.split(",") if x.strip()]
        return []

    def ingest_event(self, event: dict[str, Any]) -> None:
        """Process a single Cowrie event dict and update cumulative state.

        Handles live events and raw data_all.zip flat records.
        """
        event_id = str(event.get("eventid", "") or "")

        # Top-level field ingestion (data_all flat schema compatibility)
        if event.get("version"):
            self.client_version = str(event.get("version", ""))
        if event.get("hassh"):
            self.hassh = str(event.get("hassh", ""))

        if event.get("width") or event.get("height"):
            self.has_pty = True
            try:
                self.term_width = int(event.get("width", 0) or 0)
                self.term_height = int(event.get("height", 0) or 0)
            except (ValueError, TypeError):
                pass

        if event.get("kexAlgs"):
            self.kex_algs = self._to_list(event.get("kexAlgs"))
        if event.get("keyAlgs"):
            self.key_algs = self._to_list(event.get("keyAlgs"))
        if event.get("encCS"):
            self.ciphers = self._to_list(event.get("encCS"))
        if event.get("macCS"):
            self.macs = self._to_list(event.get("macCS"))
        if event.get("compCS"):
            self.compressions = self._to_list(event.get("compCS"))

        # Event-specific parsing
        if event_id == "cowrie.client.version":
            if event.get("version"):
                self.client_version = str(event.get("version", ""))

        elif event_id == "cowrie.client.kex":
            if event.get("kexAlgs"):
                self.kex_algs = self._to_list(event.get("kexAlgs"))
            if event.get("keyAlgs"):
                self.key_algs = self._to_list(event.get("keyAlgs"))
            if event.get("encCS"):
                self.ciphers = self._to_list(event.get("encCS"))
            if event.get("macCS"):
                self.macs = self._to_list(event.get("macCS"))
            if event.get("compCS"):
                self.compressions = self._to_list(event.get("compCS"))

        elif event_id == "cowrie.login.failed":
            self.auth_attempts += 1
            self.failed_logins += 1

        elif event_id == "cowrie.login.success":
            self.auth_attempts += 1
            self.auth_success = True
            if "ts" in event and self.ts_login is None:
                self.ts_login = str(event["ts"])

        elif event_id == "cowrie.client.size":
            self.has_pty = True
            try:
                self.term_width = int(event.get("width", 0) or 0)
                self.term_height = int(event.get("height", 0) or 0)
            except (ValueError, TypeError):
                pass

        elif event_id in ("cowrie.command.input", "cowrie.command.failed"):
            cmd = str(event.get("input", "") or "")
            if not self.commands and "ts" in event:
                self.ts_cmd1 = str(event["ts"])
            self.commands.append(cmd)

    def extract_stage_features(self, stage: str) -> dict[str, float | int]:
        """Extract cumulative numeric features for a given stage ('S1', 'S2', 'S3', 'S4', 'S5').

        Stage k features only access information accumulated up to stage k.
        """
        ver = self.client_version.lower()

        # S1 Handshake features
        feats: dict[str, float | int] = {
            "s1_ver_len": len(self.client_version),
            "s1_has_hassh": 1 if self.hassh else 0,
            "s1_is_openssh": 1 if "openssh" in ver else 0,
            "s1_is_libssh": 1 if "libssh" in ver else 0,
            "s1_is_paramiko": 1 if "paramiko" in ver else 0,
            "s1_kex_count": len(self.kex_algs),
            "s1_cipher_count": len(self.ciphers),
            "s1_mac_count": len(self.macs),
            "s1_comp_count": len(self.compressions),
        }
        if stage == "S1":
            return feats

        # S2 Authentication features
        feats.update({
            "s2_auth_attempts": self.auth_attempts,
            "s2_failed_logins": self.failed_logins,
            "s2_has_success": 1 if self.auth_success else 0,
        })
        if stage == "S2":
            return feats

        # S3 Session Start features
        feats.update({
            "s3_has_pty": 1 if self.has_pty else 0,
            "s3_term_width": self.term_width,
            "s3_term_height": self.term_height,
            "s3_is_exec": 1 if self.is_exec else 0,
        })
        if stage == "S3":
            return feats

        # S4 First Command features
        cmd1 = self.commands[0] if self.commands else ""
        feats.update({
            "s4_cmd1_len": len(cmd1),
            "s4_cmd1_has_pipe": 1 if "|" in cmd1 else 0,
            "s4_cmd1_has_redirect": 1 if (">" in cmd1 or "<" in cmd1) else 0,
            "s4_cmd1_has_chain": 1 if ("&&" in cmd1 or ";" in cmd1) else 0,
        })
        if stage == "S4":
            return feats

        # S5 First Three Commands features
        cmds_3 = self.commands[:3]
        total_len = sum(len(c) for c in cmds_3)
        unique_cmds = len(set(cmds_3))
        feats.update({
            "s5_cmd_count": len(cmds_3),
            "s5_cmd_mean_len": (total_len / len(cmds_3)) if cmds_3 else 0.0,
            "s5_unique_ratio": (unique_cmds / len(cmds_3)) if cmds_3 else 0.0,
        })
        return feats


def extract_session_features_from_events(
    events: list[dict[str, Any]],
    stage: str,
) -> dict[str, float | int]:
    """Convenience functional extractor for a session event list."""
    extractor = SessionFeatureExtractor()
    for ev in events:
        extractor.ingest_event(ev)
    return extractor.extract_stage_features(stage)
