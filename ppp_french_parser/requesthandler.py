"""Request handler of the module."""

import functools
from ppp_datamodel import Sentence, TraceItem, Response
from ppp_libmodule.exceptions import ClientError

from .parser import parse as _parse

@functools.lru_cache(256)
def parse(s):
    return _parse(s)


class RequestHandler:
    def __init__(self, request):
        self.request = request

    def answer(self):
        if self.request.language == 'fr' and \
                isinstance(self.request.tree, Sentence):
            tree = parse(self.request.tree.value)
            meas = {}
            trace = self.request.trace + [TraceItem('PLYFrenchParser', tree, meas)]
            return [Response('fr', tree, meas, trace)]
        else:
            return []
