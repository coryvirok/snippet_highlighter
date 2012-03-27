#!/usr/bin/python
# -*- coding: utf-8 -*-

import re
import unittest

class HighlightTestCase(unittest.TestCase):
    def test(self):
        from highlighter import highlight_doc as highlight
        doc = """A great example of Dlish's genius is their coconut macaroon cupcake: Coconut cake with light almond frosting and toasted coconut drizzled with bittersweet chocolate. Start with the first part - Coconut cake!!! Actual coconut cake, with coconut milk in the batter! The vast majority of cupcakeries in Toronto are making vanilla cupcakes and just adding a different frosting to make their different flavours. Not Dlish - their cupcakes are actually different cakes, not just different frostings.
        """
        query = 'delicious dlish cupcakes!'

        result = highlight(doc, query)
        result = result.lower()

        assert 'dlish' in result
        assert '[[highlight]]' in result
        assert '[[endhighlight]]' in result

        doc = """Each cuppie cake is $3 a pop but the vanilla on chocolate is simply put it -dlish! The store is small and classy looking and they bake in store. The icing unlike others is smooth, rich and creamy. And the cake is moist and fresh (almost too beautiful to eat). They have a wide range of flavours which they change up but my favourite is the vanilla icing on chocolate cake. :)
        """

        result = highlight(doc, 'gross')
        result = result.lower()

        assert '[[highlight]]' not in result
        assert '[[endhighlight]]' not in result

        doc = """LAWD. Best pizza ever. Oh lawd this is my happy place. Anytime I'm anywhere near San Francisco I demand a stop to this place. I was up here the week of my birthday and spent $80 on pizza. We ate two and got one to go, for the trip home. I love you, pizzeria delfina.
        Bonus points: Sitting at my table minding my bidness when a handsome dude was strolling down the street, looking very annoying, when I noticed he was carting around a full skeleton in a tote bag, on his shoulder. WTF??!?!
        """

        result = highlight(doc, 'pizza birthday')
        result = result.lower()

        assert 'pizza' in result
        assert 'birthday' in result
        assert '[[highlight]]' in result
        assert '[[endhighlight]]' in result


class ScoreIndexTestCase(unittest.TestCase):
    def test(self):
        from highlighter import score_index
        from highlighter import build_stem_index
        from highlighter import tokenize
        from highlighter import english_suffix_stemmer as stemmer
        from highlighter import build_scorecard

        regex = re.compile(r'(\W)')

        doc = "This ham sammy is the bomb!"
        tokens = tokenize(doc, regex)
        stem_lookup = dict((token, stemmer(token)) for token in tokens)
        stem_index = build_stem_index(tokens, stem_lookup)
        scorecard = build_scorecard(doc, 0.0)

        score_index(stem_index, scorecard, lambda x: 3.3)
        assert scorecard == [3.3, 3.3, 3.3, 0.0, 0.0, 3.3, 3.3, 3.3, 0.0, 3.3, 3.3, 3.3, 3.3, 3.3, 0.0, 0.0, 0.0, 0.0, 3.3, 3.3, 3.3, 0.0, 3.3, 3.3, 3.3, 3.3, 3.3]
        score_index(stem_index, scorecard, lambda x: 1.0 if len(x) > 1 else 0.0)
        assert scorecard == [4.3, 4.3, 4.3, 0.0, 0.0, 4.3, 4.3, 4.3, 0.0, 4.3, 4.3, 4.3, 4.3, 4.3, 0.0, 0.0, 0.0, 0.0, 4.3, 4.3, 4.3, 0.0, 4.3, 4.3, 4.3, 4.3, 3.3]


class BuildStemIndexTestCase(unittest.TestCase):
    def test(self):
        from highlighter import build_stem_index
        from highlighter import tokenize
        from highlighter import english_suffix_stemmer as stemmer

        regex = re.compile(' ')

        doc = "This ham sammy is the bomb!"
        tokens = tokenize(doc, regex)
        stem_lookup = dict((token, stemmer(token)) for token in tokens)

        assert build_stem_index(None, None) == {}
        assert build_stem_index('', None) == {}
        assert build_stem_index(tokens, None) == {}
        assert build_stem_index(tokens, {'This': 'dis'}) == {'dis': [(0, 4)]}
        assert build_stem_index(tokens, stem_lookup) == {'the': [(14, 17)],
                'sammy': [(7, 12)],
                'bomb!': [(17, 22)],
                'ham': [(4, 7)],
                'thi': [(0, 4)]}


class BuildScorecardTestCase(unittest.TestCase):
    def test(self):
        from highlighter import build_scorecard

        assert build_scorecard(None, None) == []
        assert build_scorecard([], None) == []
        assert build_scorecard(None, 1.0) == []
        assert build_scorecard('Hello world', None) == [0.0] * len('Hello world')
        assert build_scorecard('Hello world', 2.0) == [2.0] * len('Hello world')
        assert build_scorecard('Hello world', 'a') == ['a'] * len('Hello world')


class TokenizeTestCase(unittest.TestCase):
    def test(self):
        from highlighter import tokenize

        regex = re.compile(' ')

        assert tokenize(None, None) == []
        assert tokenize(None, '') == []
        assert tokenize('', None) == []
        assert tokenize('', '') == []
        assert tokenize('hello world', None) == []
        assert tokenize(None, regex) == []
        assert tokenize('hello world', regex) == ['hello', 'world']

        regex = re.compile(r'\W', flags=re.UNICODE)
        assert tokenize('hello,world', regex) == ['hello', 'world']
        assert tokenize('hello!world', regex) == ['hello', 'world']
        assert tokenize('hello world   ', regex) == ['hello', 'world', '', '', '']
        assert tokenize(u'goodbye sweet ☃!', regex) == [u'goodbye', u'sweet', '', '', '']
        assert tokenize(u'Yelp是涼爽', regex) == [u'Yelp是涼爽']
        assert tokenize(u'Yelp 是涼爽', regex) == [u'Yelp', u'是涼爽']


class EnglishSuffixStemmerTestCase(unittest.TestCase):
    def test(self):
        from highlighter import english_suffix_stemmer as stemmer

        assert stemmer(None) == ''
        assert stemmer(()) == ''
        assert stemmer([]) == ''
        assert stemmer({}) == ''
        assert stemmer('') == ''
        assert stemmer('  ') == ''
        assert stemmer('hello world') == 'hello world'
        assert stemmer('HELLO world') == 'hello world'
        assert stemmer('ly') == ''
        assert stemmer('created') == 'creat'
        assert stemmer('bamboozled') == 'bamboozl'
        assert stemmer(u'☃') == u'☃'
        assert stemmer(u'Yelp是涼爽') == u'yelp是涼爽'

if __name__ == '__main__':
    unittest.main()
