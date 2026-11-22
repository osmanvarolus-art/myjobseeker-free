# MyJobSeeker

**Build your profile once. For each job ad, see which requirements your profile covers, draft a tailored CV and
cover letter, review flagged claims, and export both as PDFs.**

MyJobSeeker is a small app that runs on your own computer. There is no account and no sign-up.

**Sample output** for a fictional candidate and a fictional "Junior Buyer" ad:
[sample CV (PDF)](docs/samples/sample_cv.pdf) · [sample cover letter (PDF)](docs/samples/sample_cover_letter.pdf)

<p align="center">
  <img src="assets/readme/app.png" alt="The job screen: fit check with covered and missing requirements, the drafted cover letter and CV, the rule check result, and PDF links." width="100%">
</p>

## Free tier

Generate up to three CV and cover letter pairs per calendar month. Editing and downloading existing drafts are
unlimited.

| | |
|---|---|
| New CV + cover letter generations | **3 per calendar month**, for any job, including a new version for a job you already drafted. The count starts again on the 1st. |
| A failed attempt | free: it does not use a generation |
| Editing drafts, downloading PDFs again | free, unlimited |
| Fit checks and rule checks | free, unlimited |

The count is kept on your computer, in your data folder. There is no server.

**Premium is not currently available.**

## Start in two minutes

You need **Python 3.10 or newer**. Nothing else to install.

Download this repository (green **Code** button → **Download ZIP**, then unzip), or clone it with git. Then, in its
folder:

```bash
./start.sh            # Windows: double-click start.bat
```

Your browser opens at `http://127.0.0.1:8377`. The app walks you through four steps:

1. **Profile.** Your jobs, what you did in each, education, skills and languages. Click *Fill with the example
   person* to see what a good profile looks like, then replace it with your own facts.
2. **Rules.** Phrases you never want to see ("I am writing to apply", "passionate"), things every letter must say
   (your availability, your work permit), letter length and sentence length. Sensible rules are already set.
3. **Model** (optional). Connect a language model on your computer for more tailored writing. Without one, the app
   still writes a clean first version from your own profile text.
4. **Jobs.** Paste a job ad. You get a fit score with every requirement marked ✓ (your profile covers it) or ✗ (a
   gap). Click **Generate CV + cover letter**, edit anything you like, and download the PDFs.

## What the checks catch, and what they do not

Every draft goes through your rules before you see it. The checks are plain code, not a model's opinion:

- **Numbers that are not in your profile** are flagged ("cut costs by 37%" when your profile never says 37).
- **Employers that are not in your profile** are flagged on the CV.
- **Your banned phrases** and **your must-mention items** are checked on every version.
- **Letter length and sentence length** follow your limits.

When a model breaks a rule, the app lists the problems and asks it to repair them once. Anything still wrong is shown
in red next to your draft.

The checks do not prove that every sentence is true. A model can still overstate a skill in words the checks cannot
see. Read each draft before you send it: you are the final check.

## Connect a model (optional)

The app connects only to a model server on your own computer (it refuses internet addresses) or to a command you
choose. A local model costs nothing.

**Ollama (free, local):**

```bash
ollama pull qwen3:8b
```

In the app: *Model* → *A local model server* → address `http://127.0.0.1:11434`, model `qwen3:8b` → *Test the model*.
LM Studio and llama.cpp work the same way (any OpenAI-compatible server on localhost).

**A command-line tool you already use** (Claude Code, Codex CLI, Gemini CLI): *Model* → *A command I already use* →
for example `claude -p`. The prompt goes to the command's input and the answer is read from its output.

> Your profile and drafts are stored locally. If you connect a cloud-backed command-line tool, it may send profile and
> job-ad text to its provider and use your account's quota or incur charges.

## PDFs

If Chrome, Chromium, Brave or Edge is installed, *CV as PDF* and *Letter as PDF* download ready files. If not, open
*Preview CV* or *Preview letter* and use your browser's **Print → Save as PDF**. Both are A4 and print-ready.

## Your data

Your profile and drafts are stored locally, in one folder outside this repository: `~/.myjobseeker` (change it with
`MYJOBSEEKER_HOME`). The app itself uploads nothing and has no telemetry. A cloud-backed model command, if you
connect one, is the exception described above.

```
~/.myjobseeker/
  profile.json    your facts
  rules.json      your writing rules
  settings.json   your model choice
  usage.json      this month's generations
  jobs/           one file per job, with every version you generated or edited
```

Because it is outside the repository, you can fork or update the code without committing your personal data. Back up
that folder to keep your work; delete it to start over.

## Settings

| Variable | What it does | Default |
|---|---|---|
| `MYJOBSEEKER_HOME` | your data folder | `~/.myjobseeker` |
| `MYJOBSEEKER_PORT` | the local port | `8377` |
| `MYJOBSEEKER_BROWSER` | the browser used for PDFs | first one found |

The app answers only on `127.0.0.1`. Other computers on your network cannot open it.

## For power users: the Claude Code workflow

This repository is built on [ai-job-search](https://github.com/ai-job-search-dev/ai-job-search) by Mads Lorentzen.
Its full Claude Code workflow (`/setup`, `/scrape`, `/rank`, `/apply`, `/interview`, `/outcome`, LaTeX templates, job
portal search tools) is still here. Read [docs/CLAUDE_CODE_WORKFLOW.md](docs/CLAUDE_CODE_WORKFLOW.md) to use it. The
monthly limit above applies to the MyJobSeeker app.

## Development

```bash
python3 -m pytest tests/test_myjobseeker_app.py      # the app
python3 -m pytest tests                              # everything
```

The app is one Python file (`app/myjobseeker.py`, standard library only) plus a static page in `app/static/`.

## License and credits

- Code: MIT, see [LICENSE](LICENSE). Original framework © Mads Lorentzen and the
  [ai-job-search](https://github.com/ai-job-search-dev/ai-job-search) contributors.
- Images and samples: see [docs/ASSETS.md](docs/ASSETS.md) for where each image, font and sample file comes from and
  its license.
