# !/usr/bin/env python
# -*- coding: utf-8 -*-

import io
import os
import re
from itertools import chain
from collections import defaultdict

from wn.constants import *
from wn.info import InformationContentSimilarities
from wn.path import WordNetPaths
from wn.morphy import morphy
from wn.omw import OpenMultilingualWordNet
from wn.reader import fix_inconsistent_line
from wn.reader import parse_wordnet_line
from wn.reader import parse_index_line
from wn.reader import parse_lemma_pos_index
from wn.reader import parse_sense_key
from wn.utils import WordNetError, FakeSynset


# Abusing builtins here but this is the only way I can think of.
# A index that provides the file offset

# Map from lemma -> pos -> synset_index -> offset
__builtins__['_lemma_pos_offset_map'] = defaultdict(dict)
# A cache so we don't have to reconstuct synsets
# Map from pos -> offset -> synset
__builtins__['_synset_offset_cache'] = defaultdict(dict)

# A cache to store the wordnet data of multiple languages
__builtins__['_lang_to_offsets_to_lemma'] = defaultdict(dict)
__builtins__['_lang_to_lemmas_to_offsets'] = defaultdict(dict)

# Map from sensekey -> count
__builtins__['_lemmakey_to_count'] = {}

__version__ = '0.0.21'

class WordNet(WordNetPaths, InformationContentSimilarities, OpenMultilingualWordNet):
    def __init__(self, wordnet_data_dir=wordnet_dir, lexname_type=None, wordnet_33=True):
        self.wordnet_data_dir = wordnet_data_dir
        self.lexname_type = lexname_type
        self.wordnet_33 = wordnet_33
        # Initializes the `_lemma_pos_offset_map` and `_pos_lemma_offset_map`
        # from wn.constants.
        self._load_lemma_pos_offset_map()
        # Initializes the `_synset_offset_cache`
        # from wn.constants.
        self._load_all_synsets()
        # Initialize all lemma's count.
        self._load_all_lemma_counts()

        self._synset_offset_cache = _synset_offset_cache
        self._lemma_pos_offset_map = _lemma_pos_offset_map

        self._lang_to_offsets_to_lemma = _lang_to_offsets_to_lemma
        self._lang_to_lemmas_to_offsets = _lang_to_lemmas_to_offsets

        self._lemmakey_to_count = _lemmakey_to_count

    def _load_lemma_pos_offset_map(self):
        for pos_tag in _FILEMAP.values():
            filename = os.path.join(self.wordnet_data_dir, 'index.{}'.format(pos_tag))
            with io.open(filename, encoding='utf8') as fin:
                for line in fin:
                    if line.startswith(' '):
                        continue
                    try:
                        lemma, pos, synset_offsets = parse_index_line(line)
                    except: # When there's inconsistencies.
                        if self.wordnet_33:
                            lemma, pos, synset_offsets = parse_index_line(fix_inconsistent_line(line))
                        else:
                            raise WordNetError('Error parsing:\n{}\nfrom {}'.format(line, filename))
                    # Cache the map.
                    _lemma_pos_offset_map[lemma][pos] = synset_offsets
                    if pos == 'a':
                        _lemma_pos_offset_map[lemma]['s'] = synset_offsets

    def _load_all_synsets(self):
        for pos_tag in _FILEMAP.values():
            filename = os.path.join(self.wordnet_data_dir, 'data.{}'.format(pos_tag))
            with io.open(filename, encoding='utf8') as fin:
                for line in fin:
                    # Skip documentation and empty lines.
                    if line.startswith(' ') or not line.strip():
                        continue
                    try:
                        synset, lemmas = parse_wordnet_line(line, lexname_type=self.lexname_type)
                        _synset_offset_cache[synset._pos][synset._offset] = synset
                    except:
                        err_msg = "Error parsing this line from {}:\n".format('data.{}'.format(pos_tag))
                        raise WordNetError(err_msg + line)

    def _load_all_lemma_counts(self):
        filename = os.path.join(self.wordnet_data_dir, 'cntlist.rev')
        with open(filename) as fin:
            for line in fin:
                lemma_key, _, count = line.strip().split()
                _lemmakey_to_count[lemma_key] = int(count)

    def synset_from_pos_and_offset(self, pos, offset):
        assert pos in POS_LIST, WordNetError('Part-of-Speech should be one of this: {}'.format(POS_LIST))
        offset = int(offset)
        try:
            return _synset_offset_cache[pos][offset]
        except:
            if pos == 's' and offset in _synset_offset_cache['a']:
                return _synset_offset_cache['a'][offset]
            if pos == 'a' and offset in _synset_offset_cache['s']:
                return _synset_offset_cache['s'][offset]
            raise WordNetError('Part-of-Speech and Offset combination not found in WordNet: {} + {}'.format(pos, offset))

    def synset(self, lemma_pos_index):
        # Parse the lemma_pos_index string.
        pos, offset = parse_lemma_pos_index(lemma_pos_index)
        # load synset information from the appropriate file
        synset = self.synset_from_pos_and_offset(pos, offset)
        # Return the synset object.
        return synset

    def synsets(self, lemma, pos=None, lang='eng', check_exceptions=True):
        """
        Load all synsets with a given lemma and part of speech tag.
        If no pos is specified, all synsets for all parts of speech
        will be loaded.
        If lang is specified, all the synsets associated with the lemma name
        of that language will be returned.
        """
        lemma = lemma.lower()
        pos_tags = POS_LIST if pos == None else [pos]
        if lang == 'eng':
            list_of_synsets = []
            for p in pos_tags:
                form = morphy(lemma, p, check_exceptions)
                for offset in _lemma_pos_offset_map[form].get(p, []):
                    if offset in _synset_offset_cache[p]:
                        list_of_synsets.append(_synset_offset_cache[p][offset])
                    else:
                        if pos == 's' and offset in _synset_offset_cache['a']:
                            list_of_synsets.append(_synset_offset_cache['a'][offset])
                        elif pos == 'a' and offset in _synset_offset_cache['s']:
                            list_of_synsets.append(_synset_offset_cache['s'][offset])

            return list_of_synsets
        else:
            # Tries to cache the OMW for the first time if not used before.
            self._load_lang_data(lang)
            # Iterate through the _lang_to_lemmas_to_offsets to get the offsets.
            list_of_offsets = []
            for p in pos_tags:
                if p == 's': # Skips the 's' tag.
                    continue
                if lemma in _lang_to_lemmas_to_offsets[lang][p]:
                    for offset in _lang_to_lemmas_to_offsets[lang][p][lemma]:
                        list_of_offsets.append((p, offset))
            return [self.synset_from_pos_and_offset(p, offset)
                    for p, offset in set(list_of_offsets)]

    def synset_from_sense_key(self, sense_key):
        lemma, pos, lex_id = parse_sense_key(sense_key)
        synset_id = '.'.join([lemma, pos, lex_id])
        return self.synset(synset_id)

    def all_synsets(self, pos=None):
        """Iterate over all synsets with a given part of speech tag.
        If no pos is specified, all synsets for all parts of speech
        will be loaded.
        """
        pos_tags = POS_LIST if pos is None else [pos]

        for _pos in pos_tags:
            for offset, ss in _synset_offset_cache[_pos].items():
                yield ss

    def all_lemma_names(self, pos=None, lang='eng'):
        if lang == 'eng':
            for lemma_name in _lemma_pos_offset_map:
                if pos in _lemma_pos_offset_map[lemma_name] or pos == None:
                    yield lemma_name
        else:
            # Tries to cache the OMW for the first time if not used before.
            self._load_lang_data(lang)
            for lemma_name in _lang_to_lemmas_to_offsets[lang][pos]:
                yield lemma_name

    def words(self, lang='lang'):
        """return lemmas of the given language as list of words"""
        return self.all_lemma_names(lang=lang)

    def lemma(self, name, lang='eng'):
        '''Return lemma object that matches the name'''
        # cannot simply split on first '.',
        # e.g.: '.45_caliber.a.01..45_caliber'
        separator = SENSENUM_RE.search(name).end()
        synset_name, lemma_name = name[: separator - 1], name[separator:]

        synset = self.synset(synset_name)
        for lemma in synset.lemmas(lang):
            if lemma._name == lemma_name:
                return lemma
        raise WordNetError('no lemma %r in %r' % (lemma_name, synset_name))

    def _compute_max_depth_once(self, pos, simulate_root):
        """
        Compute the max depth for the given part of speech.  This is
        used by the lch similarity metric.

        This function should never be used!!!
        It should be computed once, then put into wn.constants.
        """
        depth = 0
        for ss in self.all_synsets(pos):
            try:
                depth = max(depth, ss.max_depth())
            except RuntimeError:
                _msg = '{} throws error when searching for max_depth'.format(ss)
                raise WordNetError(_msg)
        if simulate_root:
            depth += 1
        return depth

    def get_version(self):
        filename = self.wordnet_data_dir+'/data.adj'
        with io.open(filename, encoding='utf8') as fin:
            for line in fin:
                match = re.search(r'WordNet (\d+\.\d+) Copyright', line)
                if match:
                    self._version = match.group(1)
                    return self._version
        raise WordNetError("Cannot find version number in {}".format(filename))

    def version(self):
        if hasattr(self, '_version'):
            return self._version
        return self.get_version()

    def _compute_max_depth(self, pos, simulate_root):
        """
        Compute the max depth for the given part of speech.  This is
        used by the lch similarity metric.
        """
        pos = 'a' if pos == 's' else pos
        # Try to fetch wordnet's max_depth from constants.
        version = self.version()
        if version in WN_MAX_DEPTH or hasattr(self, '_max_depth'):
            self._max_depth = WN_MAX_DEPTH
            return self._max_depth[version][simulate_root][pos]

        # Compute the _wn_max_depth for this wordnet version for the first time.
        self._max_depth = {version: {True: {}, False: {}}}
        for _pos in POS_LIST:
            if _pos == 's': # Skips the satellite adjective.
                continue
            depth = self._max_depth[version][False][_pos] = 0
            for ss in self.all_synsets(_pos):
                depth = max(depth, ss.max_depth())
            self._max_depth[version][True][_pos] = depth + 1
            self._max_depth[version][False][_pos] = depth
        return self._max_depth[version][simulate_root][pos]
