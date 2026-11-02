# Quality chatbot

The assistant appears after the TU/BME reports. It combines locally retrieved DPCP excerpts with the same computed facts used by the visible dashboard. It uses the existing Qwen/DashScope configuration and does not modify source data or scoring policies.

## Configuration

Keep `DASHSCOPE_API_KEY` (or `QWEN_API_KEY`) in Streamlit Secrets. The bottom assistant defaults to `qwen3.7-flash`; an optional `QWEN_CHAT_MODEL` overrides this model. The shared `QWEN_MODEL` remains independent for existing AI reports. Assistant requests explicitly disable thinking and retain JSON output. Model changes invalidate the current conversation, and the configured model appears in the assistant header. Add `QUALITY_KNOWLEDGE_KEY` at the TOML root to decrypt `assets/quality-knowledge.bin`. Never commit the key, the plaintext corpus, provider responses, or original source documents. The production corpus contains 18 documents; archived documents and spreadsheet formula cells were excluded. Document versions remain source versions, not a claim of current approval.

The bundle uses authenticated encryption with [Fernet](https://cryptography.io/en/latest/fernet/). Plaintext can optionally be loaded from a local `QUALITY_KNOWLEDGE_INDEX` path for development; it is excluded from Git.

## Refreshing documents

1. Run `tools/build_quality_knowledge.py` with one or more `--source` directories containing prepared `.txt` extracts and a private `--output` directory.
2. Run `tools/pack_quality_knowledge.py --input <private-index.jsonl> --output assets/quality-knowledge.bin --key-file <private-key-file>`.
3. Keep the key file private and configure the same key in Streamlit Secrets. Replace the encrypted bundle and verify the document count and citations.

## Data boundaries

- Chat uses current community, supplier, product and date filters; a selected cluster CC also scopes the linked quality analysis.
- Global KPI/report scope remains distinct from the selected CC. Changing the scope or corpus clears conversation history.
- Missing IQC CC mappings remain unavailable. Missing data is never treated as zero. An omitted retrieved row is not a missing source record.
- Undated N0 customer snapshots are not calendar trends. Risk scores are review priorities. Recorded inspections do not establish effective CAP closure.
- Source identifiers and numerical values are checked before displaying answers, with one bounded repair attempt. This check does not replace a quality lead's review of interpretation and recommendations.

## Validation

Install `requirements.txt`, then run:

```sh
python -m unittest discover -s tests -p test_quality_chatbot.py -v
```

The tests run locally without model calls. Operational acceptance additionally needs a configured Qwen account, the encrypted corpus key, actual TU/BME data, and browser verification of conversation, citations, clearing and filter changes.
