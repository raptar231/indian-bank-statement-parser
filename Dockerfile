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

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install --no-cache-dir .

# Data directory convention: statements live under /data. The tool looks in
# /data/input for PDFs, writes parsed files to /data/output and unlocks to
# /data/unlocked. Mount a volume here to share files with the host:
#   docker run -v "$PWD:/data" -p 8000:8000 <image> --serve
ENV BANK_PARSER_DATA_DIR=/data
RUN mkdir -p /data/input /data/output /data/unlocked

WORKDIR /data
EXPOSE 8000

ENTRYPOINT ["parse-bank-statements"]