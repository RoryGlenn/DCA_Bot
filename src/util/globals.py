from util.log import Log
from threading import Event


class Globals:
    thread_dict = dict()
    thread_exit_event = Event()
    log_file = Log()
    name = str()


# Global variable "G" is shared between files and classes
G: Globals = Globals()
