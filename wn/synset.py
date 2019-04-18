
import math
from itertools import chain
from collections import defaultdict

import wn.path
from wn.constants import *
from wn.morphy import morphy
from wn.utils import WordNetObject, WordNetError
from wn.utils import breadth_first

class Synset(WordNetObject):
    def __init__(self, offset, pos, name, lexname_index, lexname,
                 definition, examples=None, pointers=None,
                 lemmas=None, wordnet_line=None):

        self._offset = offset
        self._pos = pos
        self._name = name
        self._lexname = lexname  # lexicographer name.

        self._definition = definition
        self._examples = examples if examples else []

        self._pointers = pointers if pointers else defaultdict(set)
        self._lemmas = lemmas

        self._wordnet_line = wordnet_line

    def __repr__(self):
        return "%s('%s')" % (type(self).__name__, self._name)

    def offset(self):
        return self._offset

    def pos(self):
        return self._pos

    def name(self):
        return self._name

    def definition(self):
        return self._definition

    def examples(self):
        return self._examples

    def lexname(self):
        return self._lexname

    def _needs_root(self): # Assumes Wordnet >=V3.0.
        if self._pos == NOUN:
            return False
        elif self._pos == VERB:
            return True

    def lemmas(self, lang='eng'):
        '''Return all the lemma objects associated with the synset'''
        if lang == 'eng':
            return self._lemmas

    def lemma_names(self, lang='eng'):
        if lang == 'eng':
            return [l._name for l in self._lemmas]

    def _related(self, relation_symbol, sort=True):
        if relation_symbol not in self._pointers:
            return []
        related_synsets = []
        for pos, offset in self._pointers[relation_symbol]:
            if pos in ['s', 'a']:
                try:
                    related_synset = _synset_offset_cache['a'][offset]
                except:
                    try:
                        related_synset = _synset_offset_cache['s'][offset]
                    except:
                        raise WordNetError('Part-of-Speech and Offset combination not found in WordNet: {} + {}'.format(pos, offset))
            else:
                related_synset = _synset_offset_cache[pos][offset]
            related_synsets.append(related_synset)

        return sorted(related_synsets) if sort else related_synsets

    def _hypernym_paths(self):
        """
        Get the path(s) from this synset to the root, where each path is a
        list of the synset nodes traversed on the way to the root.
        :return: A list of lists, where each list gives the node sequence
        connecting the initial ``Synset`` node and a root node.
        """
        paths = []
        hypernyms = self.hypernyms() + self.instance_hypernyms()
        if len(hypernyms) == 0:
            paths  = [[self]]
        for hypernym in hypernyms:
            for ancestor_list in hypernym._hypernym_paths():
                ancestor_list.append(self)
                paths.append(ancestor_list)
        return paths

    def _init_hypernym_paths(self):
        """
        Note: This can only be done after the whole wordnet is read, so
        this will be called on the fly when user tries to access:
        (i) _hyperpaths, (ii) _min_depth, (iii) _max_depth or (iv) _root_hypernyms
        """
        self._hyperpaths = self._hypernym_paths()
        # Compute the path related statistics.
        if self._hyperpaths:
            self._min_depth = min(len(path) for path in self._hyperpaths) - 1
            self._max_depth = max(len(path) for path in self._hyperpaths) - 1
        else:
            self._min_depth = self._max_depth = 0
        # Compute the store the root hypernyms.
        self._root_hypernyms = list(set([path[0] for path in self._hyperpaths]))
        # Initialize the hypernyms_set for `common_hypernyms()`
        self._hypernyms_set = set(chain(*self._hyperpaths))
        self._hypernyms_set.remove(self)

    def hypernym_paths(self):
        if not hasattr(self, '_hyperpaths'):
            self._init_hypernym_paths()
        return self._hyperpaths

    def min_depth(self):
        if not hasattr(self, '_min_depth'):
            self._init_hypernym_paths()
        return self._min_depth

    def max_depth(self):
        if not hasattr(self, '_max_depth'):
            self._init_hypernym_paths()
        return self._max_depth

    def root_hypernyms(self):
        if not hasattr(self, '_root_hypernyms'):
            self._init_hypernym_paths()
        return self._root_hypernyms

    def hypernyms_set(self):
        if not hasattr(self, '_hypernyms_set'):
            self._init_hypernym_paths()
        return self._hypernyms_set

    def closure(self, rel, depth=-1):
        """Return the transitive closure of source under the rel
        relationship, breadth-first
            >>> from nltk.corpus import wordnet as wn
            >>> dog = wn.synset('dog.n.01')
            >>> hyp = lambda s:s.hypernyms()
            >>> list(dog.closure(hyp))
            [Synset('canine.n.02'), Synset('domestic_animal.n.01'),
            Synset('carnivore.n.01'), Synset('animal.n.01'),
            Synset('placental.n.01'), Synset('organism.n.01'),
            Synset('mammal.n.01'), Synset('living_thing.n.01'),
            Synset('vertebrate.n.01'), Synset('whole.n.02'),
            Synset('chordate.n.01'), Synset('object.n.01'),
            Synset('physical_entity.n.01'), Synset('entity.n.01')]
        """
        synset_offsets = []
        for synset in breadth_first(self, rel, depth):
            if synset._offset != self._offset:
                if synset._offset not in synset_offsets:
                    synset_offsets.append(synset._offset)
                    yield synset

    def tree(self, rel, depth=-1, cut_mark=None):
        """
        >>> from nltk.corpus import wordnet as wn
        >>> dog = wn.synset('dog.n.01')
        >>> hyp = lambda s:s.hypernyms()
        >>> from pprint import pprint
        >>> pprint(dog.tree(hyp))
        [Synset('dog.n.01'),
         [Synset('canine.n.02'),
          [Synset('carnivore.n.01'),
           [Synset('placental.n.01'),
            [Synset('mammal.n.01'),
             [Synset('vertebrate.n.01'),
              [Synset('chordate.n.01'),
               [Synset('animal.n.01'),
                [Synset('organism.n.01'),
                 [Synset('living_thing.n.01'),
                  [Synset('whole.n.02'),
                   [Synset('object.n.01'),
                    [Synset('physical_entity.n.01'),
                     [Synset('entity.n.01')]]]]]]]]]]]]],
         [Synset('domestic_animal.n.01'),
          [Synset('animal.n.01'),
           [Synset('organism.n.01'),
            [Synset('living_thing.n.01'),
             [Synset('whole.n.02'),
              [Synset('object.n.01'),
               [Synset('physical_entity.n.01'), [Synset('entity.n.01')]]]]]]]]]
        """
        tree = [self]
        if depth != 0:
            tree += [x.tree(rel, depth - 1, cut_mark) for x in rel(self)]
        elif cut_mark:
            tree += [cut_mark]
        return tree

    def shortest_path_distance(self, other, simulate_root=False):
        """
        Returns the distance of the shortest path linking the two synsets (if
        one exists). For each synset, all the ancestor nodes and their
        distances are recorded and compared. The ancestor node common to both
        synsets that can be reached with the minimum number of traversals is
        used. If no ancestor nodes are common, None is returned. If a node is
        compared with itself 0 is returned.
        :type other: Synset
        :param other: The Synset to which the shortest path will be found.
        :return: The number of edges in the shortest path connecting the two
        nodes, or None if no path exists.
        """
        if self == other:
            return 0
        # Find the shortest hypernym path to *ROOT*
        dist_dict1 = wn.path.find_shortest_hypernym_paths(self, simulate_root)
        dist_dict2 = wn.path.find_shortest_hypernym_paths(other, simulate_root)
        # For each ancestor synset common to both subject synsets, find the
        # connecting path length. Return the shortest of these.
        inf = float('inf')
        path_distance = inf
        for synset, d1 in dist_dict1.items():
            d2 = dist_dict2.get(synset, inf)
            path_distance = min(path_distance, d1 + d2)
        return None if math.isinf(path_distance) else path_distance

    def hypernym_distances(self, distance=0, simulate_root=False):
        """
        Get the path(s) from this synset to the root, counting the distance
        of each node from the initial node on the way. A set of
        (synset, distance) tuples is returned.
        :type distance: int
        :param distance: the distance (number of edges) from this hypernym to
        the original hypernym ``Synset`` on which this method was called.
        :return: A set of ``(Synset, int)`` tuples where each ``Synset`` is
        a hypernym of the first ``Synset``.
        """
        distances = set([(self, distance)])
        for hypernym in self._hypernyms() + self._instance_hypernyms():
            distances |= hypernym.hypernym_distances(distance + 1, simulate_root=False)
        if simulate_root:
            fake_synset = Synset(None)
            fake_synset._name = '*ROOT*'
            fake_synset_distance = max(distances, key=itemgetter(1))[1]
            distances.add((fake_synset, fake_synset_distance + 1))
        return distances
