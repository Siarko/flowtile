# Source - https://stackoverflow.com/a/29725346
# Posted by Martijn Pieters, modified by community. See post 'Timeline' for change history
# Retrieved 2026-08-23, License - CC BY-SA 3.0

import fnmatch
import glob
import os.path
from itertools import product


# Cross-Python dictionary views on the keys
if hasattr(dict, 'viewkeys'):
    # Python 2
    def _viewkeys(d):
        return d.viewkeys()
else:
    # Python 3
    def _viewkeys(d):
        return d.keys()


def _in_trie(trie, path):
    """Determine if path is completely in trie"""
    current = trie
    for elem in path:
        try:
            current = current[elem]
        except KeyError:
            return False
    return None in current


def find_matching_paths(paths, pattern) -> list[str]:
    """Produce a list of paths that match the pattern.

    * paths is a list of strings representing filesystem paths
    * pattern is a glob pattern as supported by the fnmatch module

    """
    if os.altsep:  # normalise
        pattern = pattern.replace(os.altsep, os.sep)
    pattern = pattern.split(os.sep)

    # build a trie out of path elements; efficiently search on prefixes
    path_trie = {}
    for path in paths:
        if os.altsep:  # normalise
            path = path.replace(os.altsep, os.sep)
        _, path = os.path.splitdrive(path)
        elems = path.split(os.sep)
        current = path_trie
        for elem in elems:
            current = current.setdefault(elem, {})
        current.setdefault(None, None)  # sentinel

    matching = []

    current_level = [path_trie]
    for subpattern in pattern:
        if not glob.has_magic(subpattern):
            # plain element, element must be in the trie or there are
            # 0 matches
            if not any(subpattern in d for d in current_level):
                return []
            matching.append([subpattern])
            current_level = [d[subpattern] for d in current_level if subpattern in d]
        else:
            # match all next levels in the trie that match the pattern
            names = {k for d in current_level for k in d}
            if len(names.difference({None})) == 0:
                return []
            matched_names = fnmatch.filter(names, subpattern)
            if not matched_names:
                # nothing found
                return []
            matching.append(matched_names)
            current_level = [d[n] for d in current_level for n in _viewkeys(d) & set(matched_names)]

    return [os.sep.join(p) for p in product(*matching)
            if _in_trie(path_trie, p)]
