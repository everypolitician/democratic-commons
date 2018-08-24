#!/bin/env python3

import csv
import json
import os
import shutil
import tempfile

import fiona
import requests

wikidata_ids = set()

# We'll use this to recreate the original line-endings in CSV files. Can't
# easily get it on the second (write) pass as we need it before the CSV reader
# has read any data from the file
newlines = {}

if os.path.isdir(os.path.join('boundaries', 'build')):
    boundaries_dir = os.path.join('boundaries', 'build')
else:
    boundaries_dir = 'boundaries'

boundaries_index_fn = os.path.join(boundaries_dir, 'index.json')
with open(boundaries_index_fn) as f:
    boundaries_index = json.load(f)
directories = {entry['directory'] for entry in boundaries_index}

# Gather Wikidata IDs from CSV files
for directory in directories:
    csv_fn = os.path.join(boundaries_dir, directory, directory + '.csv')
    with open(csv_fn, newline='') as f:
        reader = csv.DictReader(f)
        # Some CSVs might not yet have been reconciled into Wikidata.
        if 'WIKIDATA' not in reader.fieldnames:
            continue
        wikidata_ids |= {row['WIKIDATA'] for row in reader}
        newlines[csv_fn] = f.newlines

# And from associated positions in the boundary index
for entry in boundaries_index:
    for association in entry.get('associations', ()):
        wikidata_ids.add(association['position_item_id'])

# Query for any replacement IDs
query = """
SELECT ?old ?new WHERE {
  VALUES ?old { %s }
  ?old owl:sameAs ?new
}
""" % ' '.join('wd:' + wikidata_id for wikidata_id in wikidata_ids)

response = requests.post('https://query.wikidata.org/sparql', query, headers={
    'Accept': 'application/sparql-results+json',
    'Content-Type': 'application/sparql-query',
})

response.raise_for_status()

data = response.json()
bindings = data['results']['bindings']

# Map old IDs to new IDs. `id_mapping.get(old, old)` therefore returns a new ID
# if it exists, and the old ID as a default otherwise.
id_mapping = {b['old']['value'].rsplit('/', 1)[1]: b['new']['value'].rsplit('/', 1)[1]
              for b in bindings}

# Rewrite Wikidata IDs in CSV files
for directory in directories:
    csv_fn = os.path.join(boundaries_dir, directory, directory + '.csv')
    shp_fn = os.path.join(boundaries_dir, directory, directory + '.shp')
    changed = False  # To keep track of substantive changes, to not rewrite
                     # unexpected quoting unnecessarily.

    with open(csv_fn, newline='') as old_f:
        reader = csv.DictReader(open(csv_fn))
        if 'WIKIDATA' not in reader.fieldnames:
            continue
        with tempfile.NamedTemporaryFile('w', delete=False) as new_f:
            writer = csv.DictWriter(new_f, reader.fieldnames, lineterminator=newlines[csv_fn])
            writer.writeheader()
            for row in reader:
                if row['WIKIDATA'] in id_mapping:
                    row['WIKIDATA'] = id_mapping[row['WIKIDATA']]
                    changed = True
                writer.writerow(row)
    if changed:
        shutil.move(new_f.name, csv_fn)
    else:
        os.unlink(new_f.name)
        continue  # No need to attempt to rewrite shapefile if nothing changed in the CSV

    if not os.path.isfile(shp_fn):
        continue  # Sometimes we have CSVs without shapefiles

    print("Rewriting shapefile: " + shp_fn)
    with fiona.open(shp_fn, 'r') as old_shp:
        meta = old_shp.meta
        with fiona.open(os.path.join(boundaries_dir, directory, 'new.' + directory + '.shp'),
                        'w', encoding='utf-8', **meta) as new_shp:
            for feature in old_shp:
                if 'WIKIDATA' in feature['properties']:
                    feature['properties']['WIKIDATA'] = id_mapping.get(feature['properties']['WIKIDATA'],
                                                                       feature['properties']['WIKIDATA'])
                new_shp.write(feature)
        # Move the new shapefile files into place
        for fn in os.listdir(os.path.join(boundaries_dir, directory)):
            if fn.startswith('new.'):
                os.rename(os.path.join(boundaries_dir, directory, fn),
                          os.path.join(boundaries_dir, directory, fn[4:]))


# Rewrite associated position IDs in boundary index, but don't rewrite the file
# unless we have substantive changes to make.
boundaries_index_changed = False
for entry in boundaries_index:
    for association in entry.get('associations', ()):
        if association['position_item_id'] in id_mapping:
            association['position_item_id'] = id_mapping[association['position_item_id']]
            boundaries_index_changed = True

if boundaries_index_changed:
    with open(boundaries_index_fn, 'w') as f:
        json.dump(boundaries_index, f, indent=2, ensure_ascii=False)
        f.write('\n')

