# from os import getcwd, environ
import os
# import time
import neovim
import typescript.util
from typescript.server import Server
from logging import getLogger
logger = getLogger(__name__)


@neovim.plugin
class TypescriptHost(object):

    # Base options
    def __init__(self, vim):
        self.vim = vim
        self.calls = 0
        self.Server = Server(self.vim)

    @neovim.autocmd('BufEnter', pattern='*.ts', eval='expand("<afile>")', sync=True)
    def on_bufenter(self, filename):
        self.tsstart()

    @neovim.command('TSStart')
    def tsstart(self):
        pass
        # self.Server.startServer()

    @neovim.command('TSStop')
    def tsstop(self):
        self.vim.out_write('stopping \n')

    @neovim.command('TSRestart')
    def tsrestart(self):
        logger.debug('test')
        self.vim.out_write('restarting \n')

    @neovim.command("TSDoc", range='')
    def tsdoc(self, range):
        file = self.vim.current.buffer.name
        line = self.vim.current.window.cursor[0]
        offset = self.vim.current.window.cursor[1] + 2

        # self.vim.out_write('filenaem: ' + self.vim.current.buffer.name + '\n')
        # self.vim.out_write('line: ' + str(self.vim.current.window.cursor[0]) + '\n')
        # self.vim.out_write('offset: ' + str(self.vim.current.window.cursor[1] + 2) + '\n')
        # self.vim.out_write(buffer + '\n')
