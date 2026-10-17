# Companion projects

[GitHub Repo Health Analyzer](https://github.com/ammar31mawassi/repo-health-analyzer) reviews public repository presentation and visible quality signals. It is optional; tailoring works without it. Clone/install it separately, then run `python manage.py github-health USER --analyzer PATH`. Our adapter executes the companion's actual TypeScript scoring function. It needs Node 18+ and the companion's dependencies. Scores can be affected by rate limits, truncated trees, missing README access and activity sampling. Errors produce `score: null`, never a fake zero. Low scores suggest specific improvements; they never authorize modifying GitHub.

[AI Job Tracker](https://github.com/ammar31mawassi/ai-job-tracker) is an optional place to track applications and outcomes. It is a separate project, not bundled or required. Some of its features may require external providers; Evidence CV's automated generation does not inherit those requirements.

Keep companion checkout code, reports and credentials outside this repository's tracked files. Do not copy private career records into a companion's issues or examples. Third-party repositories keep their own licenses; they are linked, not vendored here.
