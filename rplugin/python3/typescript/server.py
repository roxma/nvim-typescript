import os
import re
import json
import subprocess
import platform
import itertools

from time import time
from tempfile import NamedTemporaryFile

RELOAD_INTERVAL = 1
MAX_COMPLETION_DETAIL = 25
RESPONSE_TIMEOUT_SECONDS = 20


class Server(object):

    def __init__(self, vim):
        self.vim = vim
        # Project related
        self._project_directory = os.getcwd()
        self._sequenceid = 0
        self._environ = os.environ.copy()
        self._tsserver_handle = None

    def startServer(self):
        self._tsserver_handle = subprocess.Popen("tsserver",
                                                 env=self._environ,
                                                 stdout=subprocess.PIPE,
                                                 stdin=subprocess.PIPE,
                                                 stderr=subprocess.STDOUT,
                                                 universal_newlines=True,
                                                 shell=True,
                                                 bufsize=1)
        self.vim.out_write('Deoplete-Typescript: Server Started \n')
