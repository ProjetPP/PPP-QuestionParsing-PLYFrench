import os
import itertools
import threading
import subprocess
from ply import lex, yacc
from nltk.corpus import wordnet
from collections import namedtuple

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

# from https://web.archive.org/web/20140724023431/http://www.computing.dcu.ie/~acahill/tagset.html
"""
tags = {
        'CC': 'COORDINATING_CONJUNCTION',
        'CD': 'CARDINAL_NUMBER',
        'DT': 'DETERMINER',
        'EX': 'EXISTENTIAL_THERE',
        'FW': 'FOREIGN_WORD',
        'IN': 'P_OR_S_CONJUNCTION', # PREPOSITION_OR_SUBORDINATING_CONJUNCTION
        'JJ': 'ADJECTIVE',
        'JJR': 'COMPARATIVE_ADJECTIVE',
        'JJS': 'SUPERLATIVE_ADJECTIVE',
        'LS': 'LIST_ITEM_MARKER',
        'MD': 'MODAL',
        'NN': 'PLURAL_NOUN',
        'NNP': 'PROPER_SINGULAR_NOUN',
        'NNPS': 'PROPER_PLURAL_NOUN',
        'NNS': 'PROPER_NOUN',
        'PDT': 'PREDETERMINER',
        'POS': 'POSSESSIVE_ENDING',
        'PRP': 'PERSONAL_PRONOUN',
        'PRP$': 'POSSIVE_PRONOUN',
        'RB': 'ADVERBE',
        'RBR': 'COMPARATIVE_ADVERB',
        'RP': 'PARTICLE',
        'SYM': 'SYMBOL',
        'TO': 'TO',
        'UH': 'INTERJECTION',
        'VB': 'BASE_VERB',
        'VBD': 'PAST_VERB',
        'VBG': 'GERUND_VERB',
        'VBN': 'PAST_PARTICIPLE_VERB',
        'VBP': 'SINGULAR_VERB',
        'VBZ': 'SINGULAR_VERB',
        'WDT': 'WH_DETERMINER',
        'WP': 'WH_PRONOUN',
        'WP$': 'POSSESSIVE_WH_PRONOUN',
        'WRB': 'WH_ADVERB',
        }
"""

"""
tags = {
        'ADJWH': 'MOT_INTERROGATIF',
        'DET': 'DETERMINANT',
        'NC': 'NOM_COMMUN',
        'V': 'VERBE',
        #'PUNC': 'PONCTUATION',
       }
"""

class Nom(str):
    pass
class Determinant(str):
    pass
class IntroCompl(str):
    pass
class Verbe(str):
    pass
class VerbeSujet(namedtuple('_VS', 'verbe sujet')):
    pass
class MotInterrogatif(str):
    pass
class Hole:
    pass

tokens = ('MOT_INTERROGATIF', 'DETERMINANT', 'NOM', 'VERBE',
        'VERBE_SUJET', 'INTRO_COMPL', 'GROUPE_NOMINAL',
        )

t_ignore = ' \n'

def t_error(t):
    raise ParserException('Illegal string `%r`' % t.value)

def t_PONCTUATION(t):
    '''[^ "]*_PUNC '''
    return None

def t_MOT_INTERROGATIF(t):
    '''[^ ]*_(ADVWH|ADJWH|PROWH) '''
    t.value = MotInterrogatif(t.value.rsplit('_', 1)[0])
    return t
def t_DETERMINANT(t):
    '''[^ ]*_DET '''
    t.value = Determinant(t.value.rsplit('_', 1)[0])
    return t
def t_NOM(t):
    '''[^ ]*_(N|NC|NPP)[ ]'''
    t.value = Nom(t.value.rsplit('_', 1)[0])
    return t
def t_quotes(t):
    '''"_PUNC (?P<content>[^"]*) "_PUNC'''
    t.type = 'NOM'
    c = lexer.lexmatch.group('content')
    t.value = ' '.join(x.rsplit('_', 1)[0] for x in c.split(' ')).strip()
    return t
def t_VERBE(t):
    '''[^ -]*_(V|VPP)[ ]'''
    t.value = Verbe(t.value.rsplit('_', 1)[0])
    return t
def t_VERBE_SUJET(t):
    '''[^ ]*-[^ ]*_VPP '''
    t.value = t.value.rsplit('_', 1)[0]
    (verb, noun) = t.value.split('-', 1)
    t.value = VerbeSujet(Verbe(verb), Nom(noun))
    return t
def t_INTRO_COMPL(t):
    '''[^ ]*_P '''
    t.value = IntroCompl(t.value.rsplit('_', 1)[0])
    return t
def t_GROUPE_NOMINAL(t): # Stupid tagger
    '''[^ ]*['’][^ ]*_(VINF|ADJ) '''
    t.value = t.value.rsplit('_', 1)[0]
    (det, noun) = t.value.replace('’', '\'').split('\'', 1)
    t.value = GroupeNominal(Determinant(det), [], Nom(noun))
    return t

lexer = lex.lex()

precedence = (
        ('right', 'INTRO_COMPL'),
        )

class GroupeNominal(namedtuple('_GN', 'determinant qualificateurs nom')):
    pass

def det_to_subject(det):
    det = det.lower()
    if det in ('mon', 'ma', 'mes', 'me', 'je', 'moi'):
        return Resource('je')
    elif det in ('ton', 'ta', 'tes', 'te', 'tu', 'toi'):
        return Resource('toi')
    elif det in ('son', 'sa', 'ses', 'lui', 'elle', 'il', 'iel'):
        return Resource('iel')
    else:
        return None
def gn_to_subject(gn):
    if gn.determinant:
        return det_to_subject(gn.determinant)
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
    '''groupe_nominal_simple : DETERMINANT NOM'''
    t[0] = GroupeNominal(t[1], [], t[2])
def p_groupe_nominal_base(t):
    '''groupe_nominal : groupe_nominal_simple'''
    t[0] = t[1]
def p_groupe_nominal_det_nom_compl(t):
    '''groupe_nominal : groupe_nominal INTRO_COMPL groupe_nominal'''
    t[0] = GroupeNominal(t[1].determinant, [t[3]], t[1].nom)

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
    '''question : MOT_INTERROGATIF NOM VERBE_SUJET'''
    word = t[1].lower()
    if word in ('quel', 'quelle', 'qui'):
        if is_avoir(t[3].verbe) or is_etre(t[3].verbe):
            t[0] = Triple(det_to_subject(t[3].sujet),
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
        for interpreter in interpreters:
            if os.path.isfile(interpreter):
                self.start(interpreter)
                break
        else:
            self.start('/usr/bin/env java')
    def start(self, interpreter):
        print('Using interpreter: %s' % interpreter)
        self.process = subprocess.Popen(
                [interpreter] + tagger_options,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=None,
                universal_newlines=True)

    def tag(self, s):
        with self.lock:
            self.process.stdin.write(s + '\n')
            self.process.stdin.flush()
            return self.process.stdout.readline()

tagger = Tagger()

def to_datamodel(t):
    return t

def parse(s):
    s = tagger.tag(s) + ' '
    """
    lexer.input(s)
    while True:
        tok = lexer.token()
        if not tok:
            break
        else:
            print(tok)"""
    return to_datamodel(parser.parse(s, lexer=lexer))
