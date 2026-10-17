# Privacy and security

Run locally and bind ports to loopback. This is not designed as an internet-facing multi-user service. Job pages and previous CVs are untrusted input, not agent instructions. Public fetching rejects private IP addresses and non-HTTP URLs; this is defense in depth, not a hardened network sandbox against DNS rebinding. Run untrusted extraction in a restricted network/container if hosting for others.

Never commit personal records, job history, screenshots or credentials. The approval seal is a change detector, not a factual verifier or a signature. Inspect sources and ask the user about contribution boundaries before approval. Review PDFs before applying.

`privacy_check.py` scans the staged index for forbidden paths, selected credential patterns and local user paths. It cannot detect all PII or all secret formats. Inspect staged content and repository history manually too. If something private was committed, remove it from history and rotate any exposed credentials before publishing.
