<details><summary>Unified session</summary>

<details><summary>Session overview</summary>

```text
Records: 13 (agent=13)

Agent source: agent
Model: claude-sonnet-5.5
Initialization:
  Engine: copilot
  Session ID: dd4d4337-ffcb-48be-8cfc-2d1b618df2e0
  Working Directory: /home/runner/work/airflow-agentic-triage-sandbox/airflow-agentic-triage-sandbox

Statistics:
  Turns: 1
  Duration: 4s
  Errors:
    {
  "errorType": "query",
  "message": "400 The requested model is not supported.",
  "statusCode": 400,
  "providerCallId": "E444:67129:6C7446:728EB7:6AE3750F",
  "serviceRequestId": "e59cefc7-e6d3-4703-a7b6-fb850e780984",
  "originatingMessageId": "5b89bd9b-a539-4b88-a368-dfb4c91d5a04"
}
```

</details>

### Conversation

```text
No agent conversation recorded.
```

<details><summary>Full timeline</summary>

```text
Chronological trace (user prompts omitted; untimed observations follow):

[1] agent/agent session.start model=claude-sonnet-5.5 sessionId=dd4d4337-ffcb-48be-8cfc-2d1b618df2e0 reasoningEffort=medium cwd=/home/runner/work/airflow-agentic-triage-sandbox/airflow-agentic-triage-sandbox [untimed]
  sessionId=dd4d4337-ffcb-48be-8cfc-2d1b618df2e0

[2] agent/agent session.init sourceEngine=copilot model=claude-sonnet-5.5 sessionId=dd4d4337-ffcb-48be-8cfc-2d1b618df2e0 reasoningEffort=medium cwd=/home/runner/work/airflow-agentic-triage-sandbox/airflow-agentic-triage-sandbox [untimed]
  sessionId=dd4d4337-ffcb-48be-8cfc-2d1b618df2e0

[3] agent/agent session.info message=Integration ID overridden via environment variable: agentic-workflows [untimed]

[5] agent/agent system.message [system instructions omitted] [untimed]

[6] agent/agent assistant.turn_start turnId=0 interactionId=8e9c326a-4f14-48e3-8594-6ef65de75491 [untimed]

[7] agent/agent assistant.turn_end turnId=0 [untimed]

[8] agent/agent session.error errorType=query statusCode=400 message=400 The requested model is not supported. [untimed]

[9] agent/agent session.result  [untimed]
  sessionId=dd4d4337-ffcb-48be-8cfc-2d1b618df2e0

[10] agent/agent session.shutdown shutdownType=routine premiumRequests=0 totalApiDurationMs=0 totalNanoAiu=0 [untimed]

[11] agent/agent session.result durationMs=4259 [untimed]
  sessionId=dd4d4337-ffcb-48be-8cfc-2d1b618df2e0

[12] agent/agent session.result numTurns=1 [untimed]
  sessionId=dd4d4337-ffcb-48be-8cfc-2d1b618df2e0

[13] agent/agent agent.execution categories=["model_not_supported_error"] errorCodes=[400] errorTypes=["query"] [untimed]
```

</details>



</details>