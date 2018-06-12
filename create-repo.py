#!/usr/bin/env python3

import argparse
import json
import os
import re
import subprocess
import textwrap
from urllib.parse import urljoin

import requests

parser = argparse.ArgumentParser("Bootstrap a new Democratic Commons repository based on an identifier")
parser.add_argument('iso_3166_1_code',
                    help="An ISO 3166-1 code")
parser.add_argument('-d', '--directory',
                    help="Directory in which to create the repository. "
                         "Defaults to the lowercase of the ISO 3166-1 code")

args = parser.parse_args()

sparql_endpoint = 'https://query.wikidata.org/sparql'
github_api = 'https://api.github.com/'
org_name = 'everypolitician'

iso_3166_1_code = args.iso_3166_1_code
repo_dir = args.directory or iso_3166_1_code

if os.path.isdir(repo_dir):
    raise AssertionError('Country repository already exists locally: {}'.format(repo_dir))

try:
    github_access_token = os.environ['GITHUB_ACCESS_TOKEN']
except KeyError:
    raise AssertionError('No GITHUB_ACCESS_TOKEN found in environment; '
                         'set one up at https://github.com/settings/tokens and add it to your environment.')

query = '''\
SELECT * WHERE {{
  ?country wdt:P297 '{iso_3166_1_code}' ;
           wdt:P37/wdt:P424 ?language ;
           rdfs:label ?label .
  FILTER(LANG(?label) = 'en')
}}
'''.format(iso_3166_1_code=iso_3166_1_code.upper())

response = requests.post(sparql_endpoint, query,
                         headers={'Content-Type': 'application/sparql-query',
                                  'Accept': 'application/sparql-results+json'})
response.raise_for_status()

results = response.json()
bindings = results['results']['bindings']

languages = {binding['language']['value'] for binding in bindings}
languages = sorted(languages)
if 'en' not in languages:
    languages.append('en')

countries = sorted({binding['country']['value'] for binding in bindings})
if not countries:
    raise AssertionError('No country found for code {!r}'.format(iso_3166_1_code))
if len(countries) > 1:
    raise AssertionError('More than one country found: {}'.format(', '.join(countries)))

country_wikidata_id = countries[0].split('/')[-1]
label = bindings[0]['label']['value']

# Slugify the label for inclusion in the repository name:
# * lowercase the English (en) country label
# * drop apostrophes
# * replace runs of non-letters with hyphens
# * strip any leading or trailing hyphens
repo_name = 'proto-commons-' + re.sub('[^a-z]+', '-', label.lower().replace("'", '')).strip('-')
repo_url = 'git@github.com:{org_name}/{repo_name}.git'.format(org_name=org_name, repo_name=repo_name)

print("Country information:")
print("  Languages:      ", ' '.join(languages))
print("  Country ID:     ", country_wikidata_id)
print("  Country name:   ", label)
print("  Repository name:", repo_name)

os.mkdir(repo_dir)
subprocess.check_call(['git', 'init'], cwd=repo_dir)

files_for_initial_commit = ['config.json', 'Gemfile', 'Gemfile.lock']

with open(os.path.join(repo_dir, 'config.json'), 'w') as f:
    json.dump({
        'country_wikidata_id': country_wikidata_id,
        'languages': languages,
    }, f, indent=2)

data_directories = ['boundaries/build', 'executive', 'legislative']
for data_directory in data_directories:
    dirname = os.path.join(repo_dir, data_directory)
    os.makedirs(dirname)
    index_filename = os.path.join(dirname, 'index.json')
    with open(index_filename, 'w') as f:
        # This is how Ruby serializes an empty array
        f.write('[\n\n]')
    files_for_initial_commit.append(os.path.relpath(index_filename, repo_dir))

with open(os.path.join(repo_dir, 'Gemfile'), 'w') as f:
    f.write(textwrap.dedent("""
        # frozen_string_literal: true

        source 'https://rubygems.org'

        ruby '2.4.2'

        gem 'commons-builder', :git => 'git://github.com/everypolitician/commons-builder.git'
    """))

subprocess.check_call(['bundle', 'install'], cwd=repo_dir)

subprocess.check_call(['git', 'add', *files_for_initial_commit], cwd=repo_dir)
subprocess.check_call(['git', 'commit', '-m', 'Initial structure'], cwd=repo_dir)

subprocess.check_call(['../refresh-data.sh'], cwd=repo_dir)

# Now to create the repo on GitHub

print("Creating and initialising GitHub repository…")

github_headers = {
    'Authorization': 'Token ' + github_access_token,
    'Content-Type': 'application/json',
    'Accept': 'application/vnd.github.mercy-preview+json',
}

response = requests.post(
    urljoin(github_api, '/orgs/{org_name}/repos'.format(org_name=org_name)),
    json.dumps({
        'name': repo_name,
        'description': 'A basic Democratic Commons repository for ' + label,
    }),
    headers=github_headers,
)
response.raise_for_status()

response = requests.put(
    urljoin(github_api, '/repos/{org_name}/{repo_name}/topics'.format(org_name=org_name, repo_name=repo_name)),
    json.dumps({
        'names': [
            'commons-data',
            'country-code-{iso_3166_1_code}'.format(iso_3166_1_code=iso_3166_1_code),
        ],
    }),
    headers=github_headers,
)
response.raise_for_status()

# And push

print("Pushing to GitHub…")

subprocess.check_call(['git', 'remote', 'add', 'origin', repo_url], cwd=repo_dir)
subprocess.check_call(['git', 'push', '-u', 'origin', 'master'], cwd=repo_dir)

print("Done!", "https://github.com/{org_name}/{repo_name}".format(org_name=org_name, repo_name=repo_name))
