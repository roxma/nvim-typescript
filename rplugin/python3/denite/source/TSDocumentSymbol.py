#! /usr/bin/env python3
import sys
from os import path
sys.path.insert(1, path.dirname(__file__) + '/../../nvim-typescript')

from client import Client
from utils import get_kind
from operator import itemgetter

from .base import Base


class Source(Base):

    def __init__(self, vim):
        super().__init__(vim)

        self.name = 'TSDocumentSymbol'
        self.kind = 'file'
        self._client = Client()

    def convertToCandidate(self, symbols):
        candidates = []
        for symbol in symbols['body']['childItems']:
            candidates.append({
                'text':  symbol['text'],
                'kindIcon': get_kind(self.vim, symbol['kind']),
                'lnum':  symbol['spans'][0]['start']['line'],
                'col':  symbol['spans'][0]['start']['offset']
            })
            if 'childItems' in symbol and len(symbol['childItems']) > 0:
                for childSymbol in symbol['childItems']:
                    candidates.append({
                        'text': childSymbol['text'] + ' - ' + symbol['text'],
                        'kindIcon': get_kind(self.vim, childSymbol['kind']),
                        'lnum': childSymbol['spans'][0]['start']['line'],
                        'col': childSymbol['spans'][0]['start']['offset']
                    })
        return candidates

    def gather_candidates(self, context):
        context['is_interactive	'] = True
        symbols = self._client.getDocumentSymbols(self.vim.current.buffer.name)
        if symbols is None:
            return []
        bufname = self.vim.current.buffer.name
        candidates = self.convertToCandidate(symbols)
        padding = max(range(len(candidates)),
                      key=lambda index: candidates[index]['kindIcon']) + 1
        values = []
        for symbol in candidates:
            values.append({
                'abbr': " {0}\t{1}".format(symbol['kindIcon'].ljust(padding), symbol['text']),
                'word': symbol['text'],
                'action__line': symbol['lnum'],
                "action__path": bufname,
                "action__col": symbol['col'],
            })
        return sorted(values, key=itemgetter('action__line'))
