import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _lib import JsonHandler, config


class handler(JsonHandler):
    def do_GET(self) -> None:
        try:
            self.send_json(200, config())
        except Exception as exc:
            self.send_json(500, {"error": f"{type(exc).__name__}: {exc}"})
