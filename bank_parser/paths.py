# Copyright 2024-2026 Koushik Mondal (github.com/raptar231)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Conventions for where statements live.

The tool works on a ``data`` root directory (``/data`` inside the Docker
image, ``./data`` on a normal machine). Under it live the ``input``,
``output`` and ``unlocked`` directories, all created automatically when
missing.
"""

import os
from pathlib import Path

DATA_DIR_ENV = "BANK_PARSER_DATA_DIR"

DEFAULT_SUBDIRS = ("input", "output", "unlocked")


def _resolve_data_root(env_value: str | None, has_docker_dir: bool) -> Path:
    if env_value:
        return Path(env_value)
    if has_docker_dir:
        return Path("/data")
    return Path("data")


def data_root() -> Path:
    """Return the root data directory for this run.

    Priority is: the ``BANK_PARSER_DATA_DIR`` environment variable (set to
    ``/data`` in the Docker image), then ``/data`` when it already exists,
    then ``./data`` next to the current working directory.
    """
    return _resolve_data_root(os.environ.get(DATA_DIR_ENV), Path("/data").exists())


def data_dirs() -> dict[str, Path]:
    """Return the standard sub-directories under :func:`data_root`.

    The ``input``, ``output`` and ``unlocked`` directories are created if
    missing.
    """
    root = data_root()
    dirs = {name: root / name for name in DEFAULT_SUBDIRS}
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return dirs
