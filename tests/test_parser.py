import unittest
from ppp_datamodel import Resource, Triple, Missing

from ppp_french_parser import parser

class ParserTestCase(unittest.TestCase):
    def testBase(self):
        self.assertEqual(parser.parse('Quel est ton nom ?'),
                Triple(Resource('toi'), Resource('nom'), Missing()))
        self.assertEqual(parser.parse('Quel âge as-tu ?'),
                Triple(Resource('toi'), Resource('âge'), Missing()))
