#!/usr/bin/env python3

import json
import re
import requests
import subprocess
import sys

url = 'https://api.github.com/users/everypolitician/repos'

def get_country_code(topics):
    country_topics = [t for t in topics if t.startswith('country-code-')]
    n = len(country_topics)
    if n == 0:
        return None
    if n > 1:
        raise Exception('Multiple country codes found in: ' + topics)
    return re.sub(r'^country-code-', '', country_topics[0])

existing_countries = set(
    line.strip().split()[1].decode() for line in
    subprocess.check_output(['git','submodule', 'status']).splitlines()
)

while url:
    response = requests.get(
        url,
        headers={'Accept': 'application/vnd.github.mercy-preview+json'}
    )
    response.raise_for_status
    for data in response.json():
        # print(json.dumps(data, indent=4, sort_keys=True))
        repo_name = data['name']
        topics = data['topics']
        topic = 'commons-data' in topics
        country_code = get_country_code(topics)
        if topic:
            if country_code:
                msg = 'Add everypolitician/{0} as a submodule at {1}'
                print(msg.format(repo_name, country_code))
                if country_code not in existing_countries:
                    subprocess.check_call([
                        'git',
                        'submodule',
                        'add',
                        'git@github.com:everypolitician/{0}.git'.format(repo_name),
                        country_code,
                    ])
            else:
                print('Warning: not country-code- topic found for ' + repo_name)
    if 'next' not in response.links:
        break
    url = response.links['next']['url']
