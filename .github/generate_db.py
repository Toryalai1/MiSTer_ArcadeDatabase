#!/usr/bin/env python3
# Copyright (c) 2021 José Manuel Barroso Galindo <theypsilon@gmail.com>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
import subprocess
from pathlib import Path
import configparser
from inspect import currentframe, getframeinfo
import itertools
import os
import io
import hashlib
import distutils.util
import datetime
import difflib
import shutil
import time
import json
import xml.etree.cElementTree as ET
import urllib.request

def main():

    print('START!')

    rotations = dict()
    for line in urllib.request.urlopen('https://raw.githubusercontent.com/theypsilon/_arcade-organizer/master/rotations/mame-rotations.txt'):
        parts = line.decode('utf-8').split(',')
        if len(parts) == 2:
            rot = translate_mame_rotation(parts[1].strip('\n').lower())
            if rot is not None:
                rotations[parts[0]] = rot

    mad_finder = MadFinder('mad')
    mad_reader = MadReader()

    for mad in mad_finder.find_all_mads():
        print(str(mad))
        mad_reader.read_mad(mad)
    
    data = mad_reader.data()
    repeated = mad_reader.repeated()
    errors = mad_reader.errors()

    for setname in rotations:
        if setname not in data:
            data[setname] = dict()

        if 'rotation' not in data[setname]:
            data[setname]['rotation'] = rotations[setname]

    create_orphan_branch('db')
    json_filename = 'mad_db.json'
    zip_filename = json_filename + '.zip'
    save_data_to_compressed_json(data, json_filename, zip_filename)

    md5_filename = zip_filename + '.md5'
    with open(md5_filename, 'w') as md5_file:
        md5_file.write(hash(zip_filename))

    run_succesfully('git add %s' % md5_filename)

    if len(repeated) > 0:
        with open('repeated.txt', 'w') as repeated_file:
            for repeats_key in sorted(repeated):
                repeated_file.write('%s: ' % repeats_key)
                repeated_file.write(', '.join(repeated[repeats_key]))
                repeated_file.write('\n')

        run_succesfully('git add repeated.txt')

    if len(errors) > 0:
        with open('errors.txt', 'w') as errors_file:
            for key in sorted(errors):
                errors_file.write('%s: ' % key)
                errors_file.write(', '.join(errors[key]))
                errors_file.write('\n')

        run_succesfully('git add errors.txt')

    force_push_file(zip_filename, 'db')

    print('Done.')

def translate_mame_rotation(rot):
    if rot == 'rot0':
        return 0
    elif  rot == 'rot90':
        return 90
    elif  rot == 'rot180':
        return 180
    elif  rot == 'rot270':
        return 270
    else:
        return None

def translate_mad_rotation(rot):
    if rot == 'horizontal':
        return 0
    elif  rot == 'vertical (cw)':
        return 90
    elif  rot == 'horizontal (180)':
        return 180
    elif  rot == 'vertical (ccw)':
        return 270
    else:
        return None

class MadFinder:
    def __init__(self, dir):
        self._dir = dir

    def find_all_mads(self):
        return sorted(self._scan(self._dir), key=lambda mad: mad.name.lower())

    def _scan(self, directory):
        for entry in os.scandir(directory):
            if entry.is_dir(follow_symlinks=False):
                yield from self._scan(entry.path)
            elif entry.name.lower().endswith(".mad"):
                yield Path(entry.path)

def read_mad_fields(mad_path, tags):
    fields = { i : '' for i in tags }

    try:
        context = ET.iterparse(str(mad_path), events=("start",))
        for event, elem in context:
            elem_tag = elem.tag.lower()
            if elem_tag in tags:
                tags.remove(elem_tag)
                elem_value = elem.text
                if isinstance(elem_value, str):
                    fields[elem_tag] = elem_value
                if len(tags) == 0:
                    break
    except Exception as e:
        print("Line %s || %s (%s)" % (lineno(), e, mad_path))

    return fields

class MadReader:
    def __init__(self):
        self._data = dict()
        self._repeated = dict()
        self._errors = dict()

    def read_mad(self, mad):
        self._mad = mad
        self._entry_fields = read_mad_fields(mad, [
            'setname',
            'name',
            'alternative',
            'rotation',
            'flip',
            'resolution',
            'cocktail',
            'region',
            'year',
            'category',
            'manufacturer',
            'homebrew',
            'bootleg',
            'enhancements',
            'translations',
            'hacks',
            'best_of',
            'platform',
            'series',
            'num_buttons',
            'players',
            'num_monitors',
            'move_inputs',
            'special_controls',
        ])

        self._entry_data = {'file': mad.stem + '.mra'}
        self.set_str_if_not_empty('name')
        self.set_bool_if_not_empty('alternative')
        self.set_bool_if_not_empty('flip')
        self.set_str_if_not_empty('resolution')
        self.set_str_if_not_empty('cocktail')
        self.set_str_if_not_empty('region')
        self.set_int_if_not_empty('year')
        self.set_str_list_if_not_empty('category')
        self.set_str_list_if_not_empty('manufacturer')
        self.set_bool_if_not_empty('homebrew')
        self.set_bool_if_not_empty('bootleg')
        self.set_bool_if_not_empty('enhancements')
        self.set_bool_if_not_empty('translations')
        self.set_bool_if_not_empty('hacks')
        self.set_str_list_if_not_empty('best_of')
        self.set_str_list_if_not_empty('platform')
        self.set_str_list_if_not_empty('series')
        self.set_int_if_not_empty('num_buttons')
        self.set_str_if_not_empty('players')
        self.set_int_if_not_empty('num_monitors')
        self.set_str_list_if_not_empty('move_inputs')
        self.set_str_list_if_not_empty('special_controls')

        if self._entry_fields['rotation'] != '':
            rot = translate_mad_rotation(self._entry_fields['rotation'].strip().lower())
            if rot is not None:
                self._entry_data['rotation'] = rot

        if self._entry_fields['setname'] in self._repeated:
            self._repeated[self._entry_fields['setname']].append(str(mad))
            print('REPEATED! %s' % mad)
            return

        self._repeated[self._entry_fields['setname']] = [str(mad)]
        self._data[self._entry_fields['setname']] = self._entry_data

    def get_field(self, key):
        field = self._entry_fields[key].strip('"\' ')
        if field != '':
            return field

        return None

    def set_str_list_if_not_empty(self, key):
        field = self.get_field(key)
        if field is not None:
            self._entry_data[key] = [s.strip('"\' ') for s in field.split(',')]

    def set_int_list_if_not_empty(self, key):
        field = self.get_field(key)
        if field is not None:
            try:
                self._entry_data[key] = [int(s.strip('"\' ')) for s in field.split(',')]
            except:
                self.add_error('field %s could not be parsed as int list' % key)

    def set_str_if_not_empty(self, key):
        field = self.get_field(key)
        if field is not None:
            self._entry_data[key] = field

    def set_bool_if_not_empty(self, key):
        field = self.get_field(key)
        if field is not None:
            self._entry_data[key] = field.lower() == "yes" or field.lower() == "true" or field.lower() == "y" or field.lower() == "t"

    def set_int_if_not_empty(self, key):
        field = self.get_field(key)
        if field is not None:
            try:
                self._entry_data[key] = int(field)
            except:
                self.add_error('field %s could not be parsed as int' % key)

    def add_error(self, message):
        print('ERROR! %s' % message)
        if self._mad not in self._errors:
            self._errors[self._mad] = []
            
        self._errors[self._mad].append(message)

    def data(self):
        return self._data

    def repeated(self):
        return {key: self._repeated[key] for key in self._repeated if len(self._repeated[key]) > 1}

    def errors(self):
        return self._errors

def create_orphan_branch(branch):
    run_succesfully('git checkout -qf --orphan %s' % branch)
    run_succesfully('git rm -rf .')

def force_push_file(file_name, branch):
    run_succesfully('git add %s' % file_name)
    run_succesfully('git commit -m "BOT: Releasing new MAD database." > /dev/null 2>&1 || true')
    run_succesfully('git fetch origin %s > /dev/null 2>&1 || true' % branch)
    if not run_conditional('git diff --exit-code %s origin/%s' % (branch, branch)):
        print("There are changes to push.")
        print()

        run_succesfully('git push --force origin %s' % branch)
        print()
        print("New %s ready to be used." % file_name)
    else:
        print("Nothing to be updated.")

def save_data_to_compressed_json(db, json_name, zip_name):

    with open(json_name, 'w') as f:
        json.dump(db, f, sort_keys=True)

    run_succesfully('touch -a -m -t 202108231405 %s' % json_name)
    run_succesfully('zip -rq -D -X -9 -A --compression-method deflate %s %s' % (zip_name, json_name))

def hash(file):
    with open(file, "rb") as f:
        file_hash = hashlib.md5()
        chunk = f.read(8192)
        while chunk:
            file_hash.update(chunk)
            chunk = f.read(8192)
        return file_hash.hexdigest()

def run_conditional(command):
    result = subprocess.run(command, shell=True, stderr=subprocess.DEVNULL, stdout=subprocess.PIPE)

    stdout = result.stdout.decode()
    if stdout.strip():
        print(stdout)
        
    return result.returncode == 0

def run_succesfully(command):
    result = subprocess.run(command, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)

    stdout = result.stdout.decode()
    stderr = result.stderr.decode()
    if stdout.strip():
        print(stdout)
    
    if stderr.strip():
        print(stderr)

    if result.returncode != 0:
        raise Exception("subprocess.run Return Code was '%d'" % result.returncode)

if __name__ == '__main__':
    main()
