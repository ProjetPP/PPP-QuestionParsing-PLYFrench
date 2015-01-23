import tempfile
import subprocess
from ply import lex, yacc
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
class Verbe(str):
    pass
class VerbeSujet(namedtuple('_VS', 'verbe sujet')):
    pass
class MotInterrogatif(str):
    pass
class Hole:
    pass

tokens = ('MOT_INTERROGATIF', 'DETERMINANT', 'NOM_COMMUN', 'VERBE',
        'VERBE_SUJET',
        )

t_ignore = ' \n'

def t_error(t):
    raise ParserException('Illegal string `%r`' % t.value)

def t_PONCTUATION(t):
    '''[^ ]*_PUNC '''
    return None

def t_MOT_INTERROGATIF(t):
    '''[^ ]*_ADJWH '''
    t.value = MotInterrogatif(t.value.rsplit('_', 1)[0])
    return t
def t_DETERMINANT(t):
    '''[^ ]*_DET '''
    t.value = Determinant(t.value.rsplit('_', 1)[0])
    return t
def t_NOM_COMMUN(t):
    '''[^ ]*_NC '''
    t.value = Nom(t.value.rsplit('_', 1)[0])
    return t
def t_VERBE(t):
    '''[^ ]*_V[ ]'''
    t.value = Verbe(t.value.rsplit('_', 1)[0])
    return t
def t_VERBE_SUJET(t):
    '''[^ ]*-[^ ]*_VPP '''
    t.value = t.value.rsplit('_', 1)[0]
    (verb, noun) = t.value.split('-', 1)
    t.value = VerbeSujet(Verbe(verb), Nom(noun))
    return t

lexer = lex.lex()

class GroupeNominal(namedtuple('_GN', 'determinant adjectifs nom')):
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
        # TODO
        return det
def gn_to_resource(gn):
    return Resource(gn.nom)
def gn_to_subject(gn):
    return det_to_subject(gn.determinant)
def verbe_to_resource(v):
    return Resource(v)

def p_groupe_nominal(t):
    '''groupe_nominal : DETERMINANT NOM_COMMUN'''
    t[0] = GroupeNominal(t[1], [], t[2])

def p_question_verb_first(t):
    '''question : MOT_INTERROGATIF VERBE groupe_nominal'''
    word = t[1].lower()
    if word in ('quel', 'quelle'):
        if is_etre(t[2]):
            t[0] = Triple(gn_to_subject(t[3]), gn_to_resource(t[3]), Missing())
        else:
            t[0] = Triple(gn_to_resource(t[3]), verbe_to_resource(t[2]), Missing())
    else:
        assert False, word

def p_question_noun_first(t):
    '''question : MOT_INTERROGATIF NOM_COMMUN VERBE_SUJET'''
    word = t[1].lower()
    if word in ('quel', 'quelle'):
        if is_avoir(t[3].verbe) or is_etre(t[3].verbe):
            t[0] = Triple(det_to_subject(t[3].sujet), Resource(t[2]),
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

parser = yacc.yacc(start='question', debug=0, write_tables=0)

tagger_options = [
        '/usr/lib/jvm/java-8-openjdk-amd64/bin/java', '-mx300m',
        '-classpath', 'stanford-postagger-full-2014-10-26/stanford-postagger.jar',
        'edu.stanford.nlp.tagger.maxent.MaxentTagger', '-model',
        'stanford-postagger-full-2014-10-26/models/french.tagger', '-textFile',
        ]
def tag(s):
    with tempfile.NamedTemporaryFile('w') as fd:
        fd.write(s)
        fd.seek(0)
        s = subprocess.check_output(tagger_options + [fd.name],
                stderr=subprocess.DEVNULL)
    return s.decode()

def to_datamodel(t):
    return t

def parse(s):
    return to_datamodel(parser.parse(tag(s) + ' ', lexer=lexer))
