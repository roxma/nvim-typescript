# ============================================================================
# FILE: __init__.py
# AUTHOR: Shougo Matsushita <Shougo.Matsu at gmail.com>
# License: MIT license
# ============================================================================
import os
import re

from glob import glob


import neovim
from typescript.typescript import TypescriptHost


@neovim.plugin
class TypscriptHandler(object):

    def __init__(self, vim):
        self.__vim = vim
        self.__tsHandle = TypescriptHost(self.__vim)
