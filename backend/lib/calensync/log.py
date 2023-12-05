import io
import logging
import os

logging.basicConfig(format='%(asctime)s - %(levelname)s::%(filename)s:%(lineno)d::%(message)s')
root_logger = logging.getLogger("calensync")


def get_logger(name):
    logger = root_logger.getChild(name)
    if os.environ.get("LOG") == "DEBUG":
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    return logger


class StringLogger(io.TextIOBase):
    def __init__(self):
        self.virtual_stream = io.StringIO()

    def write(self, __s: str) -> int:
        self.virtual_stream.write(__s)
        return len(__s)

    def get_current_content(self) -> str:
        pos = self.virtual_stream.tell()
        self.virtual_stream.seek(0)
        content = self.virtual_stream.read()
        self.virtual_stream.seek(pos)
        return content
