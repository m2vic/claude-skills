#!/usr/bin/env python3
"""Check SoC architecture dependency rules in any language. Standard library only.

Usage: python3 check_boundaries.py [root]    (default root: src)
Exit:  0 clean, 1 violations found, 2 nothing to check or bad config

Optional .soc-arch.json in the working directory or root. All keys are optional:
{
  "domain": ["domain"],
  "application": ["application", "usecases"],
  "adapters": ["adapters", "infrastructure"],
  "bootstrap": ["bootstrap"],
  "shared": ["shared"],
  "forbid": ["my_vendor_sdk"],   // added to the built-in list for inner layers
  "allow": ["http"],             // removed from the built-in list
  "exclude": ["vendor", "generated"]
}
(JSON has no comments; the notes above are documentation only.)

This is a line-based import scan, not a compiler. It sees imports written as
ordinary statements, so dynamic imports and path aliases that hide the layer
name can slip past it. Prefer build-level enforcement where the language has it.
"""
import json
import re
import sys
from pathlib import Path

DEFAULTS = {
    "domain": ["domain"],
    "application": ["application", "usecases", "use_cases"],
    "adapters": ["adapters", "infrastructure"],
    "bootstrap": ["bootstrap"],
    "shared": ["shared"],
    "forbid": [],
    "allow": [],
    "exclude": [],
}

# Libraries that mean I/O or a framework. Inner layers must not import these.
INFRA = """
sqlite3 sqlalchemy psycopg psycopg2 asyncpg pymongo redis django flask fastapi starlette
requests httpx aiohttp urllib http smtplib socket boto3 stripe celery
hmac pika kombu aio_pika kafka confluent_kafka
express fastify koa pg mysql mysql2 mongoose typeorm sequelize prisma @prisma/client axios
amqplib kafkajs bullmq @aws-sdk/client-sqs node-fetch nodemailer fs node:fs node:http node:https ioredis next @nestjs/common
crypto/hmac github.com/segmentio/kafka-go github.com/rabbitmq/amqp091-go net/http net/smtp database/sql gorm.io/gorm github.com/jackc/pgx github.com/gin-gonic/gin
org.apache.kafka com.rabbitmq java.sql javax.persistence jakarta.persistence org.springframework org.hibernate java.net.http
Confluent.Kafka MassTransit RabbitMQ.Client System.Data System.Net.Http Microsoft.EntityFrameworkCore Microsoft.AspNetCore Dapper
sqlx diesel reqwest axum actix_web tokio_postgres hyper
Illuminate Doctrine Symfony GuzzleHttp
active_record activerecord net/http rails sinatra sidekiq bunny
Ecto Phoenix HTTPoison Broadway
Foundation.URLSession Alamofire Vapor Fluent
""".split()

EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".go", ".java", ".kt", ".scala",
    ".cs", ".rs", ".php", ".rb", ".ex", ".exs", ".swift", ".c", ".cc", ".cpp", ".h", ".hpp",
}
SKIP_DIRS = {"node_modules", "vendor", "target", "build", "dist", "__pycache__", ".git",
             "venv", ".venv", "tests", "test", "spec", "__tests__"}
TEST_FILE = re.compile(r"(^test_|_test\.|\.test\.|\.spec\.|_spec\.|Tests?\.[a-z]+$)")
QUEUE_MECHANICS = re.compile(r"\.(ack|nack|dead_?letter)\(|\b(def|func|fn|function)\s+(ack|nack|dead_?letter)\b", re.I)
SQL = re.compile(r"\b(SELECT\s.+\sFROM|INSERT\s+INTO|DELETE\s+FROM|UPDATE\s+\w+\s+SET)\b")

JS = [re.compile(r"""\bfrom\s+['"]([^'"]+)['"]"""),
      re.compile(r"""^\s*import\s+['"]([^'"]+)['"]"""),
      re.compile(r"""\b(?:require|import)\(\s*['"]([^'"]+)['"]\s*\)""")]
PATTERNS = {
    ".py": [re.compile(r"^\s*from\s+(\S+)\s+import\b"), re.compile(r"^\s*import\s+([\w.]+)")],
    ".java": [re.compile(r"^\s*import\s+(?:static\s+)?([\w.]+)")],
    ".cs": [re.compile(r"^\s*(?:global\s+)?using\s+(?:static\s+)?([\w.]+)\s*;")],
    ".rs": [re.compile(r"^\s*(?:pub\s+)?use\s+([\w:]+)"), re.compile(r"^\s*(?:pub\s+)?mod\s+(\w+)\s*;")],
    ".php": [re.compile(r"^\s*use\s+([\w\\]+)"),
             re.compile(r"""^\s*(?:require|include)(?:_once)?\s*\(?\s*['"]([^'"]+)['"]""")],
    ".rb": [re.compile(r"""^\s*require(?:_relative)?\s+['"]([^'"]+)['"]""")],
    ".ex": [re.compile(r"^\s*(?:alias|import|use|require)\s+([\w.]+)")],
    ".swift": [re.compile(r"^\s*import\s+([\w.]+)")],
    ".c": [re.compile(r'^\s*#include\s+"([^"]+)"')],
}
for ext in (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"):
    PATTERNS[ext] = JS
PATTERNS[".kt"] = PATTERNS[".scala"] = PATTERNS[".java"]
PATTERNS[".exs"] = PATTERNS[".ex"]
for ext in (".cc", ".cpp", ".h", ".hpp"):
    PATTERNS[ext] = PATTERNS[".c"]

GO_BLOCK = re.compile(r"^\s*import\s*\(")
GO_SINGLE = re.compile(r'^\s*import\s+(?:[\w.]+\s+)?"([^"]+)"')
GO_ITEM = re.compile(r'^\s*(?:[\w.]+\s+)?"([^"]+)"')


def segments(path):
    return [s.lower() for s in re.split(r"[/\\.:]+", path) if s]


def imports_of(path):
    text = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    found = []
    in_go_block = False
    for number, line in enumerate(text, 1):
        if path.suffix == ".go":
            if in_go_block:
                if line.strip().startswith(")"):
                    in_go_block = False
                else:
                    match = GO_ITEM.match(line)
                    if match:
                        found.append((number, match.group(1)))
            elif GO_BLOCK.match(line):
                in_go_block = True
            else:
                match = GO_SINGLE.match(line)
                if match:
                    found.append((number, match.group(1)))
            continue
        for pattern in PATTERNS.get(path.suffix, []):
            match = pattern.search(line)
            if match:
                found.append((number, match.group(1)))
                break
    return found


def load_config(root):
    config = {key: list(value) for key, value in DEFAULTS.items()}
    for folder in (root, Path.cwd()):
        file = folder / ".soc-arch.json"
        if file.exists():
            try:
                config.update(json.loads(file.read_text()))
            except (json.JSONDecodeError, OSError) as error:
                print(f"bad config {file}: {error}")
                sys.exit(2)
            break
    return config


def layer_lookup(config):
    lookup = {}
    for layer in ("domain", "application", "adapters", "bootstrap"):
        for name in config[layer]:
            lookup[name.lower()] = layer
    return lookup


def locate(parts, lookup):
    """Return (layer, capability) from the innermost layer folder in parts."""
    for index in range(len(parts) - 1, -1, -1):
        layer = lookup.get(parts[index])
        if layer:
            return layer, parts[index - 1] if index else ""
    return None, ""


def is_infra(target, denied):
    lowered = target.lower()
    for name in denied:
        name = name.lower()
        if lowered == name or any(lowered.startswith(name + sep) for sep in "./\\:"):
            return name
    return None


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "src").resolve()
    if not root.is_dir():
        print(f"not a directory: {root}")
        return 2
    config = load_config(root)
    lookup = layer_lookup(config)
    shared = {name.lower() for name in config["shared"]}
    denied = [n for n in INFRA + config["forbid"] if n not in config["allow"]]
    skip = SKIP_DIRS | set(config["exclude"])

    files = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in EXTENSIONS or TEST_FILE.search(path.name):
            continue
        relative = path.relative_to(root)
        if skip & set(relative.parts):
            continue
        folders = [part.lower() for part in relative.parts[:-1]]
        layer, capability = locate(folders, lookup)
        if not layer and set(folders) & shared:
            layer = "domain"  # shared code outside shared/adapters follows domain rules
        files.append((path, relative, layer, capability))

    capabilities = {cap for _, _, layer, cap in files if layer and layer != "bootstrap" and cap}
    capabilities -= shared
    checked = sum(1 for _, _, layer, _ in files if layer)
    if not checked:
        print(f"no layer folders found under {root}; nothing was checked")
        return 2

    violations = []
    for path, relative, layer, capability in files:
        for number, target in imports_of(path):
            target_parts = segments(target)
            target_layer, target_cap = locate(target_parts, lookup)
            where = f"{relative}:{number}"
            if target_layer == "bootstrap" and layer and layer != "bootstrap":
                violations.append(f"{where} nothing may import bootstrap: {target}")
            if layer in ("domain", "application"):
                if target_layer in ("adapters", "bootstrap"):
                    violations.append(f"{where} {layer} must not import {target_layer}: {target}")
                if layer == "domain" and target_layer == "application":
                    violations.append(f"{where} domain must not import application: {target}")
                library = is_infra(target, denied)
                if library:
                    violations.append(f"{where} {layer} must not use infrastructure library {library}; add a port")
            if layer and layer != "bootstrap":
                others = (set(target_parts) & capabilities) - {capability}
                if others and capability not in shared:
                    other = sorted(others)[0]
                    allowed = layer == "adapters" and target_layer == "application"
                    if not allowed:
                        violations.append(
                            f"{where} capability {capability} reaches into {other}: {target}; "
                            f"use an outbound port whose adapter calls {other}'s application layer")
        if layer in ("domain", "application"):
            source = path.read_text(encoding="utf-8", errors="ignore").splitlines()
            for number, line in enumerate(source, 1):
                if SQL.search(line):
                    violations.append(f"{relative}:{number} {layer} contains SQL; move it to an outbound adapter")
                if QUEUE_MECHANICS.search(line):
                    violations.append(f"{relative}:{number} {layer} handles queue mechanics; move ack, nack and dead-letter to the inbound consumer adapter")

    for violation in violations:
        print(violation)
    print(f"checked {checked} files in layer folders: {len(violations)} violation(s)")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
