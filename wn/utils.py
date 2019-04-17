


class WordNetError(Exception):
    """An exception class for wordnet-related errors."""

class WordNetObject(object):
    """A common base class for lemmas and synsets."""

    def hypernyms(self):
        return self._related('@')

    def _hypernyms(self):
        return self._related('@')

    def instance_hypernyms(self):
        return self._related('@i')

    def _instance_hypernyms(self):
        return self._related('@i')

    def hyponyms(self):
        return self._related('~')

    def instance_hyponyms(self):
        return self._related('~i')

    def member_holonyms(self):
        return self._related('#m')

    def substance_holonyms(self):
        return self._related('#s')

    def part_holonyms(self):
        return self._related('#p')

    def member_meronyms(self):
        return self._related('%m')

    def substance_meronyms(self):
        return self._related('%s')

    def part_meronyms(self):
        return self._related('%p')

    def topic_domains(self):
        return self._related(';c')

    def in_topic_domains(self):
        return self._related('-c')

    def region_domains(self):
        return self._related(';r')

    def in_region_domains(self):
        return self._related('-r')

    def usage_domains(self):
        return self._related(';u')

    def in_usage_domains(self):
        return self._related('-u')

    def attributes(self):
        return self._related('=')

    def entailments(self):
        return self._related('*')

    def causes(self):
        return self._related('>')

    def also_sees(self):
        return self._related('^')

    def verb_groups(self):
        return self._related('$')

    def similar_tos(self):
        return self._related('&')

    def __hash__(self):
        return hash(self._name)

    def __eq__(self, other):
        return self._name == other._name

    def __ne__(self, other):
        return self._name != other._name

    def __lt__(self, other):
        return self._name < other._name
