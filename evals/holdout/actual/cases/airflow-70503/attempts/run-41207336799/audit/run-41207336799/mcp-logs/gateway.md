<details>
<summary>MCP Gateway</summary>

- ✓ **startup** MCPG Gateway version: v0.5.0
- ✓ **startup** Starting MCPG with config: stdin, listen: 0.0.0.0:8080, log-dir: /tmp/gh-aw/mcp-logs/
- ✓ **startup** WASM compilation cache directory: /tmp/gh-aw/wazero-cache
- ✓ **startup** Environment validation passed
- ✓ **startup** Loaded 1 MCP server(s): [safeoutputs]
- ✓ **startup** Guards sink server ID logging enrichment disabled (no sink server IDs configured)
- ✓ **startup** OpenTelemetry tracing disabled (no OTLP endpoint configured)
- ✓ **backend**
  ```
  Successfully connected to MCP backend server, command=docker
  ```
- 🔍 rpc **safeoutputs**→`tools/list`
- 🔍 rpc **safeoutputs**←`resp` `{"jsonrpc":"2.0","id":1,"result":{"ttlMs":0,"cacheScope":"","tools":[{"description":"WRITE-ONCE: do NOT probe this tool with empty or placeholder arguments. If not ready to post a real comment, call noop. Adds a comment to an existing GitHub issue, pull request, or discussion; use create_issue, create_discussion, or create_pull_request for new items. IMPORTANT CONSTRAINTS: Input is limited to 524288 characters, 10 mentions, and configured max-links URL occurrences (default: 50). Oversized agent content is a...`
- ✓ **startup** Starting MCPG in ROUTED mode on 0.0.0.0:8080
- ✓ **startup** Routes: /mcp/<server> where <server> is one of: [safeoutputs]
- ✓ **startup** TLS not configured — listening on http://0.0.0.0:8080 (set --tls-cert/--tls-key to enable)
- ✓ **backend**
  ```
  Successfully connected to MCP backend server, command=docker
  ```
- 🔍 rpc **safeoutputs**→`tools/call` `add_comment`
  
  ```json
  {"params":{"arguments":{"body":"No further action is required at this time.\n\u003c!-- airflow-triage-skill:v1 --\u003e","integrity":"high"},"name":"add_comment"}}
  ```
- 🔍 rpc **safeoutputs**→`tools/call` `add_labels`
  
  ```json
  {"params":{"arguments":{"integrity":"high","labels":[]},"name":"add_labels"}}
  ```
- 🔍 rpc **safeoutputs**←`resp` `{"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":"{\"result\":\"error\",\"error\":\"add_comment cannot resolve an issue, pull request, or discussion target from the \\\"workflow_dispatch\\\" event payload. The add-comment handler uses target: triggering which only applies when an issue, pull request, or discussion triggered the workflow. To report results from this workflow, use create_discussion or create_issue instead. If you need to comment on a specific item, configure safe-outputs.add...`
- 🔍 rpc **safeoutputs**←`resp`
  
  ```json
  {"id":1,"result":{"content":[{"text":"{\"result\":\"error\",\"error\":\"add_labels requires an issue or pull request context but the workflow is running on a \\\"workflow_dispatch\\\" event. The add-labels handler auto-targets the issue or pull request that triggered this workflow. To label a specific item, supply item_number explicitly.\"}","type":"text"}],"isError":true}}
  ```
- 🔍 rpc **safeoutputs**→`tools/call` `noop`
  
  ```json
  {"params":{"arguments":{"integrity":"high","message":"Triage audit complete: workflow_dispatch event does not support safe-output writes. No labels or comments were applied."},"name":"noop"}}
  ```
- 🔍 rpc **safeoutputs**←`resp`
  
  ```json
  {"id":1,"result":{"content":[{"text":"{\"result\":\"success\"}","type":"text"}]}}
  ```

</details>
