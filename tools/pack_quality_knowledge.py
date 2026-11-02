"""Create an authenticated encrypted corpus; the key stays outside public sources."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path

from cryptography.fernet import Fernet


def pack(source, output, key_file):
    source, output, key_file = map(Path, (source, output, key_file))
    content = source.read_bytes()
    # Refuse malformed JSONL before producing a deployment bundle.
    rows = [json.loads(line) for line in content.decode('utf-8').splitlines() if line.strip()]
    assert rows and all(row.get('content') and row.get('source') for row in rows)
    if key_file.exists():
        key = key_file.read_text().strip().encode()
    else:
        key = Fernet.generate_key()
        key_file.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(key_file), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as handle:
            handle.write(key)
    cipher = Fernet(key).encrypt(gzip.compress(content))
    assert gzip.decompress(Fernet(key).decrypt(cipher)) == content
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(cipher)
    return {'documents': len({row['source'] for row in rows}), 'chunks': len(rows),
            'encrypted_bytes': len(cipher), 'sha256': hashlib.sha256(cipher).hexdigest()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--key-file', required=True)
    args = parser.parse_args()
    print(json.dumps(pack(args.input, args.output, args.key_file)))
