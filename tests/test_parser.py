from pprint import pprint
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
        self.assertEqual(parser.parse('Quelle est la capitale de la France ?'),
                T(R('France'), R('capitale'), M()))

    def testManyComplements(self):
        self.assertEqual(parser.parse('Qui est le président des États-Unis ?'),
                T(R('États-Unis'), R('président'), M()))
        self.assertEqual(parser.parse('Qui est la femme du président des États-Unis ?'),
                T(T(R('États-Unis'), R('président'), M()), R('femme'), M()))
        self.assertEqual(parser.parse('Qui est le mari de la femme du président des États-Unis ?'),
                T(T(T(R('États-Unis'), R('président'), M()), R('femme'), M()), R('mari'), M()))
        self.assertEqual(parser.parse('Qui sont les filles de la femme du président des États-Unis ?'),
                T(T(T(R('États-Unis'), R('président'), M()), R('femme'), M()), R('filles'), M()))
        self.assertEqual(parser.parse('Qui sont les filles du mari de la femme du président des États-Unis ?'),
                T(T(T(T(R('États-Unis'), R('président'), M()), R('femme'), M()), R('mari'), M()), R('filles'), M()))

    def testApostrophe(self):
        self.assertEqual(parser.parse('Qui a écrit l\'huître ?'),
                T(R('huître'), R('auteur'), M()))
        self.assertEqual(parser.parse('Qui est l\'auteur de Le Pain ?'),
                T(R('Pain'), R('auteur'), M()))
        self.assertEqual(parser.parse('Quel est l’âge de Obama ?'),
                T(R('Obama'), R('âge'), M()))
        self.assertEqual(parser.parse('Quel est âge d’Obama ?'),
                T(R('Obama'), R('âge'), M()))
        self.assertEqual(parser.parse('Quel est l’âge d’Obama ?'),
                T(R('Obama'), R('âge'), M()))

    def testQuotes(self):
        self.assertEqual(parser.parse('Qui a écrit « Le Petit Prince » ?'),
                T(R('Le Petit Prince'), R('auteur'), M()))

    def testLocation(self):
        self.assertEqual(parser.parse('Où est la France ?'),
                T(R('France'), R('localisation'), M()))
        self.assertEqual(parser.parse('Où est la capitale de la France ?'),
                T(T(R('France'), R('capitale'), M()), R('localisation'), M()))
