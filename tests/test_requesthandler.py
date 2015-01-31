from ppp_datamodel import Missing, Triple, Resource, Sentence
from ppp_datamodel.communication import Request, TraceItem, Response
from ppp_libmodule.tests import PPPTestCase
from ppp_french_parser import app

class TestFrenchParser(PPPTestCase(app)):
    config_var = 'PPP_FRENCHPARSER_CONFIG'
    config = '{"class_path": "stanford-postagger-full-2014-10-26/stanford-postagger.jar"}'
    def testBasics(self):
        q = Request('1', 'fr', Sentence('Quelle est la date de naissance d’Obama ?'), {}, [])
        r = self.request(q)
        self.assertEqual(len(r), 1, r)
        self.assertEqual(r[0].tree, Triple(Resource('Obama'),
                Resource('date de naissance'), Missing()))

    def testEnglish(self):
        q = Request('1', 'en', Sentence('Quelle est la date de naissance d’Obama ?'), {}, [])
        r = self.request(q)
        self.assertEqual(len(r), 0, r)

