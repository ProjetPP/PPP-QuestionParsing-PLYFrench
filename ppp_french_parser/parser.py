import os
import itertools
import threading
import subprocess
from ply import lex, yacc
from nltk.corpus import wordnet
from collections import namedtuple, deque

from ppp_datamodel import Resource, Triple, Missing

class ParserException(Exception):
    pass

FORMS_ETRE = frozenset(filter(bool, '''
        suis es est sommes êtes sont étais était
        étions êtiez étaient
        '''.split(' ')))
FORMS_AVOIR = frozenset(filter(bool, '''
        ai as a avons avez ont avais avait
        avions aviez avaient
        '''.split(' ')))

class CoolLexToken(lex.LexToken):
    """LexToken with a constructor."""
    def __init__(self, type, value, lineno, lexpos):
        self.type = type
        self.value = value
        self.lineno = lineno
        self.lexpos = lexpos

def is_etre(v):
    if v.lower() in FORMS_ETRE:
        return True
    else:
        return False
def is_avoir(v):
    if v.lower() in FORMS_AVOIR:
        return True
    else:
        return False

class Nom(str):
    pass
class Pronom(str):
    pass
class Article(str):
    pass
class IntroCompl(str):
    pass
class Verbe(str):
    pass
class TokenList(tuple):
    pass
class MotInterrogatif(str):
    pass
class Hole:
    pass

tokens = ('TOKENLIST',
        'INTRO_COMPL', 
        'MOT_INTERROGATIF', 'ARTICLE', 'NOM', 'VERBE',
        'GROUPE_NOMINAL', 'PRONOM',
        )

t_ignore = ' \n'

def t_error(t):
    raise ParserException('Illegal string `%r`' % t.value)

def t_PONCTUATION(t):
    '''[^ "]*_PUNC '''
    return None

def t_MOT_INTERROGATIF(t):
    '''[^ ]*_(ADVWH|ADJWH|PROWH|DETWH) '''
    t.value = MotInterrogatif(t.value.rsplit('_', 1)[0])
    return t
def t_intro_compl_simpl(t):
    '''(de|des|du)_P[ ]'''
    t.type = 'INTRO_COMPL'
    t.value = IntroCompl(t.value.rsplit('_', 1)[0])
    return t
def t_intro_compl_apostrophe(t):
    '''d['’]'''
    t.type = 'INTRO_COMPL'
    t.value = IntroCompl('d')
    return t
def t_ARTICLE(t):
    '''[^ ]*(?<!\bde)_DET '''
    if t.value.startswith('l’') or t.value.startswith('l\''):
        # Stupid taggger:
        # * Quel_ADJWH est_V l’âge_NC de_P Obama_NPP ?_PUNC
        # * Quel_ADJWH est_V l’âge_DET d’Obama_NPP ?_PUNC
        t.type = 'GROUPE_NOMINAL'
        t.value = GroupeNominal(Article('l'), [], Nom(t.value.rsplit('_', 1)[0][2:]))
    else:
        t.value = Article(t.value.rsplit('_', 1)[0])
    return t
def t_PRONOM(t):
    '''[^ ]*(?<! des)_P[ ]'''
    t.value = Pronom(t.value.rsplit('_', 1)[0])
    return t
def t_GROUPE_NOMINAL(t): # Stupid tagger
    '''[^ ]*['’][^ ]*_(VINF|ADJ|NC) '''
    v = t.value.rsplit('_', 1)[0]
    (det, noun) = v.replace('’', '\'').split('\'', 1)
    t.value = GroupeNominal(Article(det), [], Nom(noun))
    return t
def t_NOM_complement(t):
    '''d[’'](?P<content>[^ ]*)_(N|NC|NPP)[ ]'''
    t.type = 'TOKENLIST'
    t.value = TokenList([
        LexToken('INTRO_COMPL', IntroCompl('d'), t.lineno, t.lexpos),
        LexToken('NOM', Nom(lexer.lexmatch.group('content')), t.lineno, t.lexpos),
        ])
    return t
def t_NOM(t):
    '''[^ ]*_(N|NC|NPP)[ ]'''
    assert not t.value.startswith('d’') and not t.value.startswith('d\'')
    t.value = Nom(t.value.rsplit('_', 1)[0])
    return t
def t_quotes(t):
    '''"_PUNC (?P<content>[^"]*) "_PUNC'''
    t.type = 'NOM'
    c = lexer.lexmatch.group('content')
    t.value = Nom(' '.join(x.rsplit('_', 1)[0] for x in c.split(' ')).strip())
    return t
def t_VERBE(t):
    '''[^ -]*_(V|VPP)[ ]'''
    t.value = Verbe(t.value.rsplit('_', 1)[0])
    return t
def t_verbe_sujet(t):
    '''[^ ]*-[^ ]*_VPP '''
    t.type = 'TOKENLIST'
    t.value = t.value.rsplit('_', 1)[0]
    (verb, noun) = t.value.split('-', 1)
    t.value = TokenList([
        CoolLexToken('VERBE', Verbe(verb), t.lineno, t.lexpos),
        CoolLexToken('PRONOM', Nom(noun), t.lineno, t.lexpos),
        ])
    return t

class DecomposingLexer:
    def __init__(self):
        self._backend = lex.lex()
        self._buffer = deque()

    def input(self, s):
        self._backend.input(s)

    def _token(self):
        if self._buffer:
            return self._buffer.popleft()
        else:
            token = self._backend.token()
            if token and isinstance(token.value, TokenList):
                self._buffer.extend(token.value[1:])
                return token.value[0]
            else:
                return token

    def token(self):
        t = self._token()
        assert not isinstance(t, TokenList), t
        return t

    @property
    def lexmatch(self):
        return self._backend.lexmatch

lexer = DecomposingLexer()

precedence = (
        ('right', 'INTRO_COMPL'),
        )

class GroupeNominal(namedtuple('_GN', 'article qualificateurs nom')):
    pass

def det_to_resource(det):
    det = det.lower()
    if det in ('mon', 'ma', 'mes', 'me', 'je', 'moi'):
        return Resource('moi')
    elif det in ('ton', 'ta', 'tes', 'te', 'tu', 'toi'):
        return Resource('toi')
    elif det in ('son', 'sa', 'ses', 'lui', 'elle', 'il', 'iel'):
        return Resource('ellui')
    else:
        return None
def gn_to_subject(gn):
    if gn.article:
        return det_to_resource(gn.article)
    else:
        return None
def gn_to_triple(gn):
    if gn.qualificateurs:
        # TODO
        return Triple(
                gn_to_triple(gn.qualificateurs[0]),
                Resource(gn.nom),
                Missing())
    elif gn_to_subject(gn):
        return Triple(
                gn_to_subject(gn),
                Resource(gn.nom),
                Missing())
    else:
        return Resource(gn.nom)

def noun_to_predicate(noun):
    l = wordnet.synsets(noun, pos='n', lang='fra')
    fr_nouns = itertools.chain.from_iterable(
            x.lemma_names('fra') for x in l)
    fr_nouns = list(fr_nouns)
    if fr_nouns:
        return Resource(fr_nouns[0]) # TODO multiple
    else:
        return Resource(noun)
def verb_to_predicate(verb):
    l = wordnet.synsets(verb, lang='fra')
    # XXX maybe add pos='v'? (note: wouldn't work for others than infinitive)
    lemmas = itertools.chain.from_iterable(
            x.lemmas() for x in l if x.pos() == 'v' or True)
    drf = itertools.chain.from_iterable(
            x.derivationally_related_forms() for x in lemmas)
    nouns = (
            x for x in drf
            if x.synset().pos() == 'n')
    fr_nouns = itertools.chain.from_iterable(
            x.synset().lemma_names('fra') for x in nouns)
    fr_nouns = list(fr_nouns)
    if fr_nouns:
        return Resource(fr_nouns[0]) # TODO multiple
    else:
        return Resource(verb)

def p_verbe_simple(t):
    '''verbe : VERBE'''
    t[0] = t[1]
def p_verbe_compose(t):
    '''verbe : VERBE VERBE'''
    if is_etre(t[1]) or is_avoir(t[1]):
        t[0] = Verbe(t[2])
    else:
        assert False

def p_groupe_nominal_nom(t):
    '''groupe_nominal : NOM'''
    t[0] = GroupeNominal(None, [], t[1])
def p_groupe_nominal_gn(t):
    '''groupe_nominal : GROUPE_NOMINAL'''
    t[0] = t[1]
def p_groupe_nominal_simple(t):
    '''groupe_nominal_simple : ARTICLE NOM'''
    t[0] = GroupeNominal(t[1], [], t[2])
def p_groupe_nominal_base(t):
    '''groupe_nominal : groupe_nominal_simple'''
    t[0] = t[1]
def p_groupe_nominal_det_nom_compl(t):
    '''groupe_nominal : groupe_nominal INTRO_COMPL groupe_nominal'''
    if t[1].nom.lower() in ('date', 'lieu') and t[3].qualificateurs:
        # Compress stuff like « date de naissance »
        t[0] = GroupeNominal(t[1].article, t[3].qualificateurs,
                '%s de %s' % (t[1].nom, t[3].nom))
    else:
        t[0] = GroupeNominal(t[1].article, [t[3]], t[1].nom)

def p_question_verb_first(t):
    '''question : MOT_INTERROGATIF verbe groupe_nominal'''
    word = t[1].lower()
    if word in ('quel', 'quelle', 'qui'):
        if is_etre(t[2]):
            t[0] = gn_to_triple(t[3]) 
        else:
            t[0] = Triple(
                    gn_to_triple(t[3]),
                    verb_to_predicate(t[2]),
                    Missing())
    elif word in ('où',):
        if is_etre(t[2]):
            t[0] = Triple(
                    gn_to_triple(t[3]),
                    Resource('localisation'),
                    Missing())
        else:
            assert False, t[2]
    else:
        assert False, word

def p_question_noun_first(t):
    '''question : MOT_INTERROGATIF NOM VERBE PRONOM'''
    word = t[1].lower()
    if word in ('quel', 'quelle', 'qui'):
        if is_avoir(t[3]) or is_etre(t[3]):
            t[0] = Triple(
                    det_to_resource(t[4]),
                    noun_to_predicate(t[2]),
                    Missing())
        else:
            assert False, t[3]
    else:
        assert False, word

def p_error(t):
    if t is None:
        raise ParserException('Unknown PLY error.')
    else:
        raise ParserException("Syntax error at '%s' (%s)" % 
                (t.value, t.type))

parser = yacc.yacc(start='question', write_tables=0)

interpreters = [
        '/usr/lib/jvm/java-8-openjdk-amd64/jre/bin/java',
        '/usr/lib/jvm/java-8-oracle/bin/java',
        '/usr/local/bin/java',
        '/usr/bin/java',
        ]

tagger_options = [
        '-mx300m',
        '-classpath', 'stanford-postagger-full-2014-10-26/stanford-postagger.jar',
        'edu.stanford.nlp.tagger.maxent.MaxentTagger', '-model',
        'stanford-postagger-full-2014-10-26/models/french.tagger',
        ]
class Tagger:
    """Runs an instance of a POS tagger and provides it through the 'tag'
    method.
    Thread-safe."""
    def __init__(self):
        self.lock = threading.Lock()
        self.process = None

    def select_interpreter(self):
        for interpreter in interpreters:
            if os.path.isfile(interpreter):
                return [interpreter]
        else:
            ['/usr/bin/env', 'java']
    def start(self):
        interpreter = self.select_interpreter()
        print('Using interpreter: %s' % interpreter)
        self.process = subprocess.Popen(
                interpreter + tagger_options,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=None,
                universal_newlines=True)

    def tag(self, s):
        with self.lock:
            if not self.process:
                self.start()
            try:
                self.process.stdin.write('')
            except IOError:
                self.start()
            self.process.stdin.write(s + '\n')
            self.process.stdin.flush()
            return self.process.stdout.readline()

tagger = Tagger()

def parse(s):
    s = tagger.tag(s) + ' '
    """
    # Useful for debugging the lexer
    lexer.input(s)
    while True:
        tok = lexer.token()
        if not tok:
            break
        else:
            print(tok)"""
    return parser.parse(s, lexer=lexer)
