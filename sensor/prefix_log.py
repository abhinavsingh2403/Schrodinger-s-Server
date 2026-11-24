"""Append privacy-preserving prefix evidence on the sensor reactor thread."""
import json
import logging
import os
from datetime import datetime, timezone

from gatekeeper.visitor_memory import derive_visitor_id


class PrefixLog:
    def __init__(self, path):
        self.path = path
        self.salt = os.urandom(32)
        self.seq = {}

    def append(self, sid, **fields):
        if not self.path:
            return
        try:
            key = derive_visitor_id(str(sid), self.salt)
            now = datetime.now(timezone.utc).isoformat()
            if "event" in fields:
                self.seq[key] = self.seq.get(key, 0) + 1
                fields["seq"] = self.seq[key]
            else:
                fields["last_seq"] = self.seq[key]
            record = json.dumps(dict(session=key, observed_at=now, **fields), allow_nan=False)
            with open(self.path, "a", encoding="utf8") as out:
                out.write(record + "\n")
            if fields.get("event") == "cowrie.session.closed":
                del self.seq[key]
        except Exception:
            self.path = None
            logging.getLogger(__name__).warning("Prefix logging disabled after write failure")
