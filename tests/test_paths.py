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

from pathlib import Path

from bank_parser.paths import _resolve_data_root, data_dirs


def test_resolve_uses_env_override():
    assert _resolve_data_root("/custom", True) == Path("/custom")
    assert _resolve_data_root("/custom", False) == Path("/custom")


def test_resolve_uses_docker_dir_when_present():
    assert _resolve_data_root(None, True) == Path("/data")


def test_resolve_defaults_to_local_data():
    assert _resolve_data_root(None, False) == Path("data")


def test_data_dirs_creates_subdirs(tmp_path, monkeypatch):
    monkeypatch.setenv("BANK_PARSER_DATA_DIR", str(tmp_path))
    dirs = data_dirs()
    assert dirs == {
        "input": tmp_path / "input",
        "output": tmp_path / "output",
        "unlocked": tmp_path / "unlocked",
    }
    for path in dirs.values():
        assert path.is_dir()
