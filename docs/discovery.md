# Local discovery and email digest

The n8n workflow `Local Job Discovery - Daily Matches Email` runs at **13:00 Asia/Jerusalem**, respecting daylight saving time. The PC and Docker must be running. `job-cv` queues a catch-up check after startup; before 13:00 or after a successful run on the same local date, it does nothing. A rejected or uncertain email is visible in local status; it is never reported as a confirmed delivery.

## Commands

```powershell
job-cv                       # Start services; check for a missed daily digest
job-cv -Discover -NoEmail     # Run discovery/ranking without email
job-cv -Discover              # Force a discovery run; send new matches
job-cv -DigestStatus          # Read the latest run/report
job-cv 'https://employer.example/job'  # Generate a CV for a selected job
```

Discovery is asynchronous and shares the worker's single queue with CV generation. The local model is not asked to run shell commands, search independently or send mail. Python owns source access, eligibility, scoring validation, delivery and persistent state.

## Setup for another candidate

1. Finish the reviewed profile/project bank and approval seal in `private/`.
2. Copy `examples/search.example.json` to ignored `private/search.json`. Set role/location preferences, source boards, recipient and sender. Keep `enabled=false` while testing.
3. Create ignored `private/employer-blacklist.json` with `{"companies":[]}` or entries shaped as `{name, aliases, reason, sources}`. This is a static private preference file. The workflow only compares employer names to aliases; it does not research companies, infer military ties or quarantine unknown companies. Short aliases use word boundaries to reduce false matches. Include alternate employer/parent names explicitly when desired. The list is not exhaustive or self-updating.
4. Add a random `DISCOVERY_TOKEN` to ignored `.env`. This protects the worker's digest endpoints and is supplied to the local n8n workflow through its environment. Do not paste it into tracked workflow JSON. n8n node environment access is enabled for this locally controlled workflow.
5. Configure a dedicated Gmail App Password with `./configure-gmail.ps1 -Email your-address@gmail.com`. Enable 2-step verification and create an App Password named Evidence CV at [Google Account](https://myaccount.google.com/apppasswords), then enter it only in the local hidden prompt. This sets `mail.mode=smtp` and saves ignored `private/mail-secrets/smtp.json`. Mount `./private/mail-secrets:/mail-secrets:ro` in an ignored `compose.local.yaml`. The runtime connects to Gmail over verified TLS on port 465. App Passwords are separate from your normal Google password. See [Google's help](https://support.google.com/mail/answer/7104828) for account support. Credentials are never sent to the model. No paid model keys are required.
6. Optional crawler: set worker build arg `INSTALL_CRAWL4AI: "1"` and environment `ENABLE_CRAWL4AI: "1"` in the local override. Browser requests keep public-network checks; login/captcha bypass is not implemented. See NOTICE for attribution.
7. Run `job-cv -Build`, then `job-cv -Discover -NoEmail`. Inspect the actual matches, exclusions, source failures and gaps with `job-cv -DigestStatus`.
8. Set `enabled=true` after review and run `job-cv -Discover` to test a real digest. Both the explicit recipient and scheduled sending must be authorized by the user. The importer publishes the discovery workflow when the local token is configured.

Dedicated Gmail OAuth is an alternative (`mail.mode=gmail`, `GMAIL_TOKEN_FILE=/mail-secrets/gmail-token.json`). Use an OAuth client created for this project and confirm the app name in Google's consent screen. Never silently borrow another project's client or mailbox. To set up or renew dedicated authorization on the host:

```powershell
python -m pip install google-auth-oauthlib
python authorize-gmail.py --client ./private/client_secret.json --token ./private/gmail-token.json
```

Use a Gmail Desktop OAuth client and complete Google's browser consent. The helper requests only `gmail.send`, listens on loopback, and saves the token locally. Point the read-only mail mount at that token directory. An OAuth project left in Google's external testing mode can have short-lived refresh authorization; see [Google's documentation](https://developers.google.com/identity/protocols/oauth2#expiration). No secret or authorization link belongs in Git. A rejected login/refresh is a failed run, never a successful email.

The schedule is defined in `n8n/job-discovery.json`. If changing the hour/timezone, update that workflow and `private/search.json` together, then rerun the importer. There is no remote scheduler and no execution while the PC is offline.

## Source and matching pipeline

Read-only adapters support Freehire search and employer boards on Greenhouse, Ashby and Lever. Each response is bounded; redirects and URLs must stay on public networks. Freehire is an external public job-data catalog, not local hosting. Candidate profile, project evidence and model inference remain local. Direct employer feeds are preferred over duplicate catalog copies.

SQLite records canonical jobs, first/last seen, description hashes, source failures/cooldowns, evidence evaluations, delivery reservations, digests and application outcomes. Unchanged evaluations are cached by posting content, approved evidence hashes, model and blacklist. Public employer-board delisting is tracked after successful complete reads; source errors do not mark all jobs closed.

Eligibility excludes senior titles, substantial required experience and locations not confirmed as Israel or eligible worldwide remote. Illinois `IL` is not treated as Israel. Degree-in-progress and requested industry years remain visible gaps; project work is never counted as professional tenure. Unknown company military involvement is not investigated or inferred. The static blacklist is the only employer exclusion policy.

Qwen maps source requirement IDs to approved bullet IDs. BM25 retrieves relevant evidence first. The digest shows source-backed strengths, gaps, posting links and local generation commands. Scores are relevance heuristics, not hiring probabilities. Finalists are re-fetched before delivery; changed titles, closed pages and stale requirement evidence are rejected/re-evaluated. A maximum number of candidates is evaluated each run; this is a bounded shortlist, not a claim of exhaustive market coverage.

No new matching jobs means no email by default. Already delivered unchanged jobs are suppressed. A delivery is reserved before the outbound request; timeouts, ambiguous server errors or a crash in that window cannot trigger automatic duplicate sends. Check uncertain deliveries manually before clearing a reservation. Rejected authorization does not reserve the jobs permanently. Mail content is saved locally for audit; credentials and authorization headers are not logged.

## Evidence and evaluation tools

`python refresh-evidence.py` exports the approved claim-ID bank and readable source/contribution/limit report into ignored private files. It does not approve new claims. Role-specific summaries and coursework in the sealed profile are fixed reviewed text, not unconstrained model writing.

`python evaluate.py` runs labeled eligibility cases. `python evaluate.py --models qwen3.5:4b deepseek-r1:8b` compares small structured-ID tasks through the same local model client. Install the model tags first. Reports stay under ignored `state/`. These tests measure narrow capabilities; they do not establish superior end-to-end CV quality or hiring performance.

The existing AI Job Tracker remains separate. Outcome records are supported locally via `discovery.record_outcome(job_key, status, note)`; applied/dismissed/rejected jobs leave future shortlists. No application is submitted by this workflow.
