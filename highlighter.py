# -*- coding: utf-8 -*-
"""
Author: Cory Virok coryvirok@gmail.com
Date: 3/27/2012

Problem:
    Build a highlight_doc() function which will determine the
    most relevant portion of a document to show the user
    based on their search query. The snippet returned
    will have some markup to highlight the search terms.

Approach:
    I first score each index of the document, (each character
    position) using 1 or more scoring functions. These functions
    look to see if the word, (or stem in this case) is
    part of the search query. If it is, a positive score
    is assigned. I also implemented a rudimentary semantic
    scoring function which just looks to see if the word
    is a "positive" word. This is done under the assumption
    that the user is searching for something that they are
    interested in and we should show them positive text
    surrounding their query.

    After the document is scored, I use a sliding window
    of a configurable size to get a window score for each
    section of the document. The highest window score is
    then used as the basis for the snippet to be returned.

    Once the optimal window is calculated, I look for
    natural sentence terminators before and after the
    window boundaries. This is done under the assumption
    that a full sentence will have more context around
    the search terms and help the user get a better idea
    of how the search terms fit into the review.

    My approach has a bunch of advantages over the simple
    keyword approach, (which selects the window based on
    the number of keywords found relative to the frequency
    of those keywords in the doc.) First, it favors long
    search terms. Since my scoring method assigns a score
    to every character of the document, longer search terms
    are more relevant. This is good because longer words
    tend to be more specific to what the user is interested
    in and therefore more relevant to their search.

    Another benefit of my approach is that it uses a simple
    stemmer which will result in the highlighting of words
    like "lovely" "loves" "love" when the user searches
    for any of them.

    My approach is pretty simple and straightforward but can
    be used as the basis for a more complicated solution.
    Since you can plug in as many different scoring functions
    as you want, this method seems to be pretty flexible.

    The downside of my approach is that there is a bit of
    confusing logic related to matching up tokens and stems.
    I've organized the code around these areas fairly well
    but it could use a bit more help. Another downside is
    that I've used compiled regular expressions which are
    not thread safe.
"""

import re

_TOKENIZE_DOC_RE = re.compile(r'(\W)', flags=re.UNICODE)
_TOKENIZE_QUERY_RE = re.compile(r'\W', flags=re.UNICODE)
_STOP_WORDS = set('i/to/it/he/she/they/me/am/is/are/be/being/been/have/has/having/had/do/does/doing/did'.split('/'))
_SUFFIXES = ('s', 'ed', 'ing', 'ly')

def build_scorecard(data, starting_score):
    """
    Builds a blank scorecard which will be used to assign a "score"
    to each index of the data string.

    Args:
        data - A (unicode) string representing the text to score.
        starting_score - A float which is used as the default score for each index.

    Returns: A list containing len(data) elements, all set to starting_score
    """
    data = data or ''
    starting_score = starting_score or 0.0
    return [starting_score] * len(data)


def build_stem_index(tokens, stem_lookup):
    """
    Creates a mapping from token to (start/end) position of the token's stem
    in the list of tokens.

    Args:
        tokens - A list of strings representing the document to index
        stem_lookup - A dictionary mapping a token to its stem

    Returns: A dictionary mapping each token to the position of its stem
    in the flattened string.
        e.g. tokens = ['She', ' ', 'loves', ' ', 'salty', ' ', 'foods']
             returns {'': [(3, 4), (9, 10), (15, 16)],
                      'salty': [(10, 15)],
                      'food': [(16, 21)],
                      'love': [(4, 9)],
                      'she': [(0, 3)]}

    NOTE: All tokens are assumed to be in order and comprise the full set
    of text.
        e.g. "Hello world" should be tokenized into ['Hello', ' ', 'world']
    """
    tokens = tokens or []
    stem_lookup = stem_lookup or {}

    index = {}
    cur_pos = 0
    for token in tokens:
        token_len = len(token)
        if token:
            stem = stem_lookup.get(token)
            if stem:
                index.setdefault(stem, []).append((cur_pos, cur_pos + token_len))

        cur_pos += token_len

    return index


def score_index(stem_index, scorecard, score_fn):
    """
    Increments each index of the scorecard using the score_fn. For each index,
    the score_fn is passed in the stemmed word at that position and the score
    is added to the existing score at that position.

    Args:
        stem_index - An index built using the build_stem_index() function
        scorecard - A scorecard built using the build_scorecard() function
        score_fn - A function that takes in a stemmed word and returns a float

    Returns: None

    NOTE: This function modifies scorecard
    """

    if None in (stem_index, scorecard, score_fn):
        raise ValueError('one or more parameters are invalid')

    for stem, locations in stem_index.iteritems():
        for start, end in locations:
            score = score_fn(stem)
            for i in xrange(start, start + len(stem)):
                scorecard[i] += score


def get_window_scores(scorecard, window_size):
    """
    Goes through scorecard using a sliding window of size window_size and
    sums up the scores for all locations within the window. The list of
    each window and it's score is returned.

    Args:
        scorecard - A scorecard built using the build_scorecard() function and
            scored using score_index().
        window_size - An int defining how large of a sliding window to use
            while calculating the score.

    Returns: A list of tuples containing the score, start and end index of the window.
        e.g. [(score, start_index_of_window, end_index_of_window), (...), ...]
    """
    ret = []
    scorecard_len = len(scorecard)
    cur_index = 0
    end_index = cur_index + window_size

    while end_index < scorecard_len:
        ret.append((sum(scorecard[cur_index:end_index]), cur_index, end_index))
        cur_index += 1
        end_index += 1

    return ret


def tokenize(term, regex):
    """
    Args:
        term - A string to be tokenized
        regex - A compiled regular expression object, @see re module

    Returns: A list of tokens based on the regex.
    """
    if not term or not regex:
        return []

    return regex.split(term)


def english_suffix_stemmer(val):
    """
    Args:
        val - A string to generate a stem from

    Returns: A string representing the stem of val

    @see http://xapian.org/docs/stemming.html

    NOTE: python has a sweet implementation of Porter stemmer, below
        is a super simplified version
    """
    ret = ''
    val = val or ''
    val = val.lower().strip()

    for suffix in _SUFFIXES:
        if val.endswith(suffix):
            val = val[:-len(suffix)]
            break

    if val in _STOP_WORDS:
        val = ''

    return val


def find_best_terminal_token(start_index, tokens, sentence_terminals, direction=1):
    """
    Given an index into the data string, this function will return the
    index into the token list which corresponds to a "natural" boundary
    in the data string. i.e. a sentence terminal like "!" or "."

    Args:
        start_index - An int defining the index into the data string,
            (the data string is just ''.join(tokens))
        tokens - A list of strings generated using the tokenize() function
        sentence_terminals - A set or dict or list containing the terminal
            characters to look for when attempting to find a natural
            boundary in the data.
        direction - An in defining which direction to look for the terminal
            in. This value should only be either -1 for reverse order or
            1 for forward.

    Returns: An int corresponding to the index in the tokens list for the
        most natural boundary.
    """
    if direction not in (-1, 1):
        raise Exception('Invalid direction, must be either -1 or 1')

    token_index = data_index_to_token_index(start_index, tokens)

    min_token_index = 0
    max_token_index = len(tokens) - 1

    while token_index > min_token_index and token_index < max_token_index:
        token_index += direction
        if tokens[token_index] in sentence_terminals:
            if direction == -1:
                return token_index + 1
            else:
                break

    return token_index


def data_index_to_token_index(data_index, tokens):
    """
    Maps a data index to a token index. Data indices correspond to
    an index in the raw data used to generate the tokens.

    Args:
        data_index - An int index into the data. (data is just ''.join(tokens))
        tokens - A list containing a string, generated from the tokenize() function

    Returns: An int index into the tokens list
    """
    index = 0
    for token_index, token in enumerate(tokens):
        token_len = len(token)
        if data_index >= index and data_index <= index + token_len:
            return token_index
        index += token_len

    return None


def print_scorecard(scorecard, data):
    """
    Helper/debug function to print out the data and it scorecard,
    lined up by column. Prints to stdout.

    Args:
        scorecard - A scorecard generated via the build_scorecard() function
        data - The data used to generate the scorecard

    Returns: None
    """
    print 'score: %.2f' % sum(scorecard)
    print ' '.join(map(lambda x: '%4s' % x, list(data)))
    print ' '.join(map(lambda x: '%.2f' % x, scorecard))


def highlight_doc(doc, query):
    """
    Given a document and a query string, return a highlighted snippet
    containing the most relevant portion of the document.

    Args:
        doc - A string containing the data in which to search for
            query terms.
        query - A string containing the raw query

    Returns: A string containing all or part of the original doc
        string with markup potentially added to highlight query terms.

    Approach:
    1. Tokenize the doc, (all characters in the doc must be a part of a token)
    2. Build a stem index based on the tokens
    3. Tokenize the query and build a simple scoring function to match query words
    4. Build a scorecard
    5. Score every index with the query match scorer
    6. Score every index with the sentiment scorer
    7. Build the window score list and pick highest window score
    8. Find the best starting index for the window
    9. Find the best ending index for the window
    10. Add in ellipses to start if starting token does not come after a sentence boundary
    11. Add in ellipses to end if the ending token is not the end of a sentence
    10. Return the highlighted buffer from best start and end points and add in HIGHLIGHT markup
    """
    stemmer = english_suffix_stemmer
    positive_stems = map(stemmer, ('love', 'awesome', 'great', 'super', 'delicious', 'best'))
    sentence_terminals = set(('.', ';', '!', '?'))

    doc_tokens = tokenize(doc, _TOKENIZE_DOC_RE)
    query_tokens = [token for token in tokenize(query, _TOKENIZE_QUERY_RE) if token]

    stem_lookup = dict((token, stemmer(token)) for token in doc_tokens + query_tokens)
    stem_index = build_stem_index(doc_tokens, stem_lookup)

    query_stems = set(stem_lookup[token] for token in query_tokens)

    query_match_score_fn = lambda stem: 1.0 if stem in query_stems else 0.0
    sentiment_score_fn = lambda stem: 0.1 if stem in positive_stems else 0.0

    scorecard = build_scorecard(doc, 0.0)

    score_index(stem_index, scorecard, query_match_score_fn)
    score_index(stem_index, scorecard, sentiment_score_fn)

    # For debugging, uncomment if you want to see how the document is scored
    #print_scorecard(scorecard, doc)

    scored_windows = get_window_scores(scorecard, 20)
    scored_windows.sort(key=lambda item: -item[0])
    top_scored_window = scored_windows[0]

    starting_token_index = find_best_terminal_token(top_scored_window[1],
                                                    doc_tokens,
                                                    sentence_terminals,
                                                    direction=-1)

    ending_token_index = find_best_terminal_token(top_scored_window[2],
                                                  doc_tokens,
                                                  sentence_terminals,
                                                  direction=1)

    optimal_token_range = doc_tokens[starting_token_index:ending_token_index + 1]
    pre_start_token = doc_tokens[starting_token_index - 1] if starting_token_index > 1 else None
    post_end_token = doc_tokens[ending_token_index + 1] if ending_token_index < len(doc_tokens) - 1 else None

    if pre_start_token is not None and pre_start_token in sentence_terminals:
        optimal_token_range.insert(0, '...')

    if post_end_token is not None and post_end_token not in sentence_terminals:
        optimal_token_range.append('...')

    markup_buffer = []
    for token in optimal_token_range:
        if stem_lookup.get(token) in query_stems:
            markup_buffer.append('[[HIGHLIGHT]]')
            markup_buffer.append(token)
            markup_buffer.append('[[ENDHIGHLIGHT]]')
        else:
            markup_buffer.append(token)

    return ''.join(markup_buffer)


if __name__ == '__main__':
    print "I LOVE FRIED chickens!!! " \
                    "Stephanie HATES fried chicken! " \
                    u"Love that Çhicken delicious!"
    print highlight_doc("I LOVE FRIED chickens!!! " \
                        "Stephanie HATES fried chicken! " \
                        u"Love that Çhicken delicious!",
                        'fried chicken')
