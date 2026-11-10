import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _lib import JsonHandler, run_tool


class handler(JsonHandler):
    def do_POST(self) -> None:
        self.handle_post(run_tool)
