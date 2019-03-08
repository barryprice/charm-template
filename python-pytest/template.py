#!/usr/bin/env python3

#    Copyright (C) 2014  Canonical Ltd.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
import os
import os.path as path
import time
import shutil
import subprocess
import tempfile

from Cheetah.Template import Template
from stat import ST_MODE

from charmtools.generators import (
    CharmTemplate,
)

log = logging.getLogger(__name__)


class ReactivePythonCharmTemplate(CharmTemplate):
    """Creates a reactive, layered python-based charm"""

    # _EXTRA_FILES is the list of names of files present in the git repo
    # we don't want transferred over to the charm template:
    _EXTRA_FILES = ["README.md", ".git", ".gitmodules"]

    _TEMPLATE_URL = "https://github.com/chris-sanders/template-python-pytest.git"

    def create_charm(self, config, output_dir):
        config['metadata']['package'] = config['metadata']['package'].lower()
        self._clone_template(config, output_dir)

        for root, dirs, files in os.walk(output_dir):
            for outfile in files:
                if self.skip_template(outfile):
                    continue

                self._template_file(config, path.join(root, outfile))

    def _template_file(self, config, outfile):
        if path.islink(outfile):
            return

        # Add configurations to simplify the templates
        config['libfile'] = 'lib_{}'.format(config['metadata']['package'].replace('-', '_')).lower()
        config['libclass'] = '{}Helper'.format(config['metadata']['package'].replace('-', '').capitalize())
        config['fixture'] = config['metadata']['package'].replace('-', '').lower()
        mode = os.stat(outfile)[ST_MODE]
        t = Template(file=outfile, searchList=(config))
        o = tempfile.NamedTemporaryFile(
            dir=path.dirname(outfile), delete=False)
        os.chmod(o.name, mode)
        o.write(str(t).encode())
        o.close()
        backupname = outfile + str(time.time())
        os.rename(outfile, backupname)
        os.rename(o.name, outfile)
        os.unlink(backupname)

    def _clone_template(self, config, output_dir):
        cmd = "git clone {} {}".format(
            self._TEMPLATE_URL, output_dir
        )

        try:
            subprocess.check_call(cmd.split())
        except OSError as e:
            raise Exception(
                "The below error has occurred whilst attempting to clone"
                "the charm template. Please make sure you have git"
                "installed on your system.\n" + str(e)
            )

        # iterate and remove all the unwanted files from the git repo:
        for item in [path.join(output_dir, i) for i in self._EXTRA_FILES]:
            if not path.exists(item):
                continue

            if path.isdir(item) and not path.islink(item):
                shutil.rmtree(item)
            else:
                os.remove(item)

        # rename handlers.py to <charm-name>.py
        new_name = '%s.py' % config['metadata']['package'].replace('-', '_')
        os.rename(os.path.join(output_dir, 'reactive', 'handlers.py'),
                  os.path.join(output_dir, 'reactive', new_name))

        # rename lib.py to <charm-name>.py
        new_name = '%s.py' % config['metadata']['package'].replace('-', '_')
        os.rename(os.path.join(output_dir, 'lib', 'lib.py'),
                  os.path.join(output_dir, 'lib', 'lib_' + new_name.lower()))

    def skip_template(self, filename):
        return (filename.startswith('.') or filename in ('Makefile', ) or
                filename.endswith('.pyc'))
