# -*- coding: utf-8 -*-

# For debugging, use this command to start neovim:
#
# NVIM_PYTHON_LOG_FILE=nvim.log NVIM_PYTHON_LOG_LEVEL=INFO nvim
#
#
# Please register source before executing any other code, this allow cm_core to
# read basic information about the source without loading the whole module, and
# modules required by this module
from cm import register_source, getLogger, Base

register_source(name='typescript',
                priority=9,
                abbreviation='ts',
                word_pattern=r'[$\w]+',
                scoping=True,
                scopes=['typescript'],
                early_cache=1,
                cm_refresh_patterns=[r'\.', r'::'],)

import os
import subprocess
import glob
import re
import sys

sys.path.insert(1, os.path.dirname(__file__) + '/../../rplugin/python3/nvim-typescript')
from utils import getKind, convert_completion_data, convert_detailed_completion_data
from client import Client
from tempfile import NamedTemporaryFile
from time import time

logger = getLogger(__name__)

RELOAD_INTERVAL = 1
RESPONSE_TIMEOUT_SECONDS = 20

class Source(Base):

    def __init__(self, nvim):
        super(Source, self).__init__(nvim)

        self._max_completion_detail = self.nvim.vars[
                "nvim_typescript#max_completion_detail"]

        client = Client()
        client.serverPath = self.nvim.vars["nvim_typescript#server_path"]
        client.start()

        self._client = client

    def reload(self, filepath, src):
        """
        send a reload request
        """

        tmpfile = NamedTemporaryFile(mode='w', delete=False)
        tmpfile.write(src)
        tmpfile.close()

        self._client.reload(filepath, tmpfile.name)

        os.unlink(tmpfile.name)

    def cm_refresh(self, info, ctx, *args):

        lnum = ctx['lnum']
        col = ctx['col']
        base = ctx['base']
        filepath = ctx['filepath']
        startcol = ctx['startcol']

        src = self.get_src(ctx)

        self._client.open(filepath)
        self.reload(filepath, src)

        data = self._client.completions(
            file=filepath,
            line=lnum,
            offset=col,
            prefix=base
        )
        
        logger.info("completion data: %s", data)

        if len(data) == 0:
            return []

        matches = []
        if len(data) > self._max_completion_detail:
            filtered = []
            for entry in data:
                if entry["kind"] != "warning":
                    filtered.append(entry)
            matches = [convert_completion_data(e, self.nvim) for e in filtered]
            self.complete(info, ctx, startcol, matches)
            return

        names = []
        maxNameLength = 0

        for entry in data:
            if entry["kind"] != "warning":
                names.append(entry["name"])
                maxNameLength = max(maxNameLength, len(entry["name"]))

        detailed_data = self._client.completion_entry_details(
            file=self.relative_file(),
            line=context["position"][1],
            offset=context["complete_position"] + 1,
            entry_names=names
        )

        if len(detailed_data) == 0:
            return

        matches = [convert_detailed_completion_data(e, self.nvim, isDeoplete=True) for e in detailed_data]
        self.complete(info, ctx, startcol, matches)
