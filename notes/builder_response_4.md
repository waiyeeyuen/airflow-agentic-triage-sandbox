# Builder response 4: deterministic input and output guards

No model was run and no AI credits were spent in this repair round.

## Fix

- A pre-agent workflow step writes either the triggering issue event or the selected frozen case to
  `/tmp/gh-aw/agent/case.json` before inference.
- The model has no edit tool or GitHub-read tool. It is instructed never to create files, redirect
  shell output, use stdin, or continue after any denied command.
- The workflow exposes only the three required Python 3 script command families. gh-aw v1.0.1
  injects generic read-shell approvals in the Copilot harness; explicit engine `--deny-tool`
  arguments override every injected command and its shell safe-output shim. Native safe-output MCP
  tools remain available.
- AI threat detection is disabled. A fail-closed deterministic step checks the safe-output record:
  labels must pass the allowlist/combination validator, comments must equal a fixed template, links
  and mentions are rejected, unknown output types are rejected, and label/comment call counts are
  bounded. This is preferable to a capped AI detector because the output language is small and
  exact, while run 40993175316 spent 60.137 AIC in 34 detector requests without reaching a result.

## Credit-free airflow-69284 simulation

The exact workflow/skill commands were run locally against the frozen input, with a `python3`
alias to the installed Python 3.12 interpreter because Windows reserves `python3.exe` as a Store
alias. The GitHub-hosted Ubuntu check runs the literal `python3` commands.

| Command | Result | Elapsed |
| --- | --- | ---: |
| prepare fixed-path case JSON | success | 202.612 ms |
| search prior duplicate corpus | success; top candidate 69275, score 0.191747 | 228.114 ms |
| validate `kind:bug`, `area:providers`, `provider:openlineage` | success | 208.063 ms |
| render `none` comment | success; empty body | 213.897 ms |

The deterministic safe-output fixture also passed. The unit/contract suite passed 21/21, and all 18
historical plus three adversarial frozen cases passed integrity verification.

## Failed run recorded

Run 40993175316 failed because the old skill required the model to create an intermediate JSON
file, while the shell guard prohibited the attempted `echo` redirection and heredoc. The guard
worked as designed; the 10-minute timeout contained the resulting loop. The golden result records
failure, cause, denials, 0/1 score, and the timeout as a tested budget control.

## Cost forecast

Deterministic threat detection costs 0 AIC. The failed main-agent portion used 10.166 AIC despite
two blocked file-writing turns. Allowing for three successful script turns, the planning estimate is
12 AIC ($0.12) per case, with a hard ceiling of 25 AIC ($0.25) per case. A 21-case golden batch is
therefore expected to use about 252 AIC ($2.52), with a hard aggregate ceiling of 525 AIC ($5.25).
