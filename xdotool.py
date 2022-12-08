import os
import subprocess

class XdotoolWrapper:
    def __init__(self, display, uuid):
        self.display = display
        self.uuid = uuid
        self.xdotool_env = os.environ.copy()
        self.xdotool_env["DISPLAY"] = display
        searched_window = self._exec(["search", str(uuid)])
        self.window_id = int(searched_window.stdout.readline().strip())

    def _exec(self, arguments):
        return subprocess.Popen(
            ["xdotool", *arguments],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            close_fds=True,
            #env=self.xdotool_env
        )

    def activate(self):
        return self._exec(["windowactivate", str(self.window_id)])
    
    def scroll_down(self):
        return self._exec(["click", "--window", str(self.window_id), "5"])

    def page_up(self):
        return self._exec(["key", "--window", str(self.window_id), "Page_Up"])

    def size(self, width, height):
        return self._exec(["windowsize", str(self.window_id), str(width), str(height)])
