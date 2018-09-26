#!/usr/bin/env python

"""
Usage: git show HEAD:[filename] | python compare-branch-index.py [branch] [filename]

Compare two branch index files, the old one on stdin, and the new one as a
second argument filename.

Ideal for use by `refresh-data.sh` to include output in commit messages
summarising changes to branch indexes (i.e. `legislative/index.json` or
`executive/index.json`).
"""

import json
import sys
import textwrap

branch_type = sys.argv[1]
if branch_type == 'legislative':
    branch_item_name = 'legislature'
    branch_item_name_plural = 'legislatures'
    branch_id_name = 'house_item_id'
    branch_attribute_names = ('comment', 'area_id', 'seat_count', 'position_item_id')
    subitem_label = 'term'
    subitem_key = 'terms'
    subitem_id_name = 'term_item_id'
elif branch_type == 'executive':
    branch_item_name = 'executive'
    branch_item_name_plural = 'executives'
    branch_id_name = 'executive_item_id'
    branch_attribute_names = ('comment', 'area_id')
    subitem_label = 'position'
    subitem_key = 'positions'
    subitem_id_name = 'position_item_id'
else:
    raise AssertionError

old_data = json.load(sys.stdin)
with open(sys.argv[2]) as f:
   new_data = json.load(f)

def compare_by_id(old, new, id_name):
    old = {entry[id_name]: entry for entry in old if id_name in entry}
    new = {entry[id_name]: entry for entry in new if id_name in entry}
    removed = set(old) - set(new)
    added = set(new) - set(old)
    return old, new, added, removed

old, new, added, removed = compare_by_id(old_data, new_data, branch_id_name)

if removed:
    print("Removed {}:".format(branch_item_name_plural if len(removed) > 1 else branch_item_name))
    for id in sorted(removed):
        print("  {0:12} {1}".format(id, old[id]['comment']))

if added:
    print("Added {}:".format(branch_item_name_plural if len(removed) > 1 else branch_item_name))
    for id in sorted(added):
        print("  {0:12} {1}".format(id, new[id]['comment']))

for id in sorted(set(old) & set(new)):
    changes = []
    for name in branch_attribute_names:
        if old[id].get(name) != new[id].get(name):
            changes.append('{} changed from {!r} to {!r}'.format(name, old[id].get(name), new[id].get(name)))

    old_subitems, new_subitems, added_subitems, removed_subitems = \
        compare_by_id(old[id][subitem_key], new[id][subitem_key], subitem_id_name)

    for subitem_id in removed_subitems:
        changes.append("{} removed:           {:12} {}".format(subitem_label, subitem_id,
                                                               old_subitems[subitem_id]['comment']))
    for subitem_id in added_subitems:
        changes.append("{} added:             {:12} {}".format(subitem_label, subitem_id,
                                                               new_subitems[subitem_id]['comment']))
    for subitem_id in sorted(set(old_subitems) & set(new_subitems)):
        if old_subitems[subitem_id].get('comment') != new_subitems[subitem_id].get('comment'):
            changes.append("{0} comment changed:   {1:12} {2!r} to {3!r}".format(
                subitem_label, subitem_id,
                old_subitems[subitem_id]['comment'],
                new_subitems[subitem_id]['comment']))

    if changes:
        print("Changes for {} - {!r}".format(id, new[id]['comment']))
        print(textwrap.indent('\n'.join(changes), '  '))
