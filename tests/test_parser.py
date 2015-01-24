import unittest
from ppp_datamodel import Resource as R
from ppp_datamodel import Triple as T
from ppp_datamodel import Missing as M

from ppp_french_parser import parser

class ParserTestCase(unittest.TestCase):
    def testBase(self):
        self.assertEqual(parser.parse('Quel est ton nom ?'),
                T(R('toi'), R('nom'), M()))
        self.assertEqual(parser.parse('Quel âge as-tu ?'),
                T(R('toi'), R('âge'), M()))
        self.assertEqual(parser.parse('Qui est président de la France ?'),
                T(R('France'), R('président'), M()))
        self.assertEqual(parser.parse('Qui est le président de la France ?'),
                T(R('France'), R('président'), M()))
