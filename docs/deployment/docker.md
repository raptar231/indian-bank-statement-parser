```bash
# Pull image
docker pull ghcr.io/raptar231/indian-bank-statement-parser:latest

# Parse directory
docker run --rm \
  -v $(pwd)/statements:/input \
  -v $(pwd)/parsed:/output \
  ghcr.io/raptar231/indian-bank-statement-parser:latest \
  --input-dir /input --output-dir /output --bank hdfc

# Parse single file
docker run --rm \
  -v $(pwd)/statement.pdf:/input/statement.pdf \
  -v $(pwd)/parsed:/output \
  ghcr.io/raptar231/indian-bank-statement-parser:latest \
  --input-file /input/statement.pdf --output-file /output/parsed.csv --bank icici

# GSTR-2A reconciliation
docker run --rm \
  -v $(pwd)/statements:/input \
  -v $(pwd)/gstr2a:/output \
  ghcr.io/raptar231/indian-bank-statement-parser:latest \
  --input-dir /input --output-dir /output --bank sbi \
  --reconcile-gstr2a --gstin 29ABCDE1234F1Z5
```

## Image Tags

| Tag | Description |
|-----|-------------|
| `latest` | Latest stable release |
| `v0.1.0` | Specific version |
| `0.1` | Major.minor |
| `sha-abc123` | Commit SHA |

## Build Locally

```bash
# Build
docker build -t indian-bank-statement-parser .

# Run local build
docker run --rm \
  -v $(pwd)/statements:/input \
  -v $(pwd)/parsed:/output \
  indian-bank-statement-parser \
  --input-dir /input --output-dir /output --bank hdfc
```

## Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# System dependencies for PDF processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Install package
RUN pip install --no-cache-dir -e .

ENTRYPOINT ["parse-bank-statements"]
```

## Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  parser:
    image: ghcr.io/raptar231/indian-bank-statement-parser:latest
    volumes:
      - ./statements:/input
      - ./parsed:/output
    command: --input-dir /input --output-dir /output --bank hdfc --format csv
```

Run: `docker compose up`

## Kubernetes

```yaml
# k8s-job.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: bank-statement-parser
spec:
  template:
    spec:
      containers:
      - name: parser
        image: ghcr.io/raptar231/indian-bank-statement-parser:latest
        command: ["parse-bank-statements"]
        args:
          - "--input-dir"
          - "/input"
          - "--output-dir"
          - "/output"
          - "--bank"
          - "hdfc"
        volumeMounts:
        - name: statements
          mountPath: /input
        - name: parsed
          mountPath: /output
      volumes:
      - name: statements
        persistentVolumeClaim:
          claimName: statements-pvc
      - name: parsed
        persistentVolumeClaim:
          claimName: parsed-pvc
      restartPolicy: OnFailure
```

## Air-gapped / Offline

```bash
# Save image
docker save ghcr.io/raptar231/indian-bank-statement-parser:latest | gzip > parser.tar.gz

# Transfer to air-gapped machine
# Load image
docker load < parser.tar.gz

# Run (no internet needed)
docker run --rm -v /data/statements:/input -v /data/parsed:/output \
  ghcr.io/raptar231/indian-bank-statement-parser:latest \
  --input-dir /input --output-dir /output --bank hdfc
```

## Environment Variables

No required environment variables. All config via CLI flags.

Optional:
```bash
# Custom Python path
export PYTHONPATH=/app

# Debug
export PYTHONUNBUFFERED=1
```

## Multi-platform Build

```bash
# Build for multiple architectures
docker buildx build --platform linux/amd64,linux/arm64 \
  -t ghcr.io/raptar231/indian-bank-statement-parser:latest \
  --push .
```

## Security

- Runs as non-root user (UID 1000)
- Read-only root filesystem (optional)
- No secrets in image
- Minimal base image (python:3.11-slim)

## Resource Limits

```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "100m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `poppler-utils` not found | Use provided Dockerfile or install in base image |
| Permission denied on volumes | Run with `--user $(id -u):$(id -g)` |
| Out of memory | Increase memory limit, process fewer files |
| PDF not parsed | Try different bank code, check PDF format |

## See Also

- [GitHub Actions](../deployment/github_actions.md)
- [PyPI Release](../deployment/pypi_release.md)