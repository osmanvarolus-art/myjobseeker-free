# MyJobSeeker

**Build your profile once. For each job ad, see which requirements your profile covers, draft a tailored CV and
cover letter, review flagged claims, and export both as PDFs.**

A small app that runs on your own computer. No account, no sign-up.

Sample output for a fictional candidate and a fictional ad:
[CV (PDF)](docs/samples/sample_cv.pdf) · [cover letter (PDF)](docs/samples/sample_cover_letter.pdf)

<p align="center">
  <img src="assets/readme/app.png" alt="The job screen: each requirement marked Supported, Partial or No evidence with the profile line that supports it, the drafted letter and CV, and PDF links." width="100%">
</p>

## Free tier

Generate up to three CV and cover letter pairs per calendar month. Editing and downloading existing drafts are
unlimited.

- Every successful generation counts, also a new version for a job you already drafted. A failed attempt does not.
- Fit checks, rule checks, edits and PDF downloads are unlimited.
- The count is kept on your computer and starts again on the 1st.

**Premium is not currently available.**

## Start

You need Python 3.10 or newer. Download this repository (green **Code** button → **Download ZIP**) or clone it, then
in its folder run `./start.sh` (Windows: double-click `start.bat`). Your browser opens at `http://127.0.0.1:8377`:

1. **Profile**: your jobs, what you did in each, education, skills, languages. *Fill with the example person* shows a
   good profile; replace it with your own facts.
2. **Rules**: phrases you never want, things every letter must say, length limits. Sensible defaults are set.
3. **Model** (optional): a model server on your computer (Ollama, LM Studio, llama.cpp) or a command you already use
   (for example `claude -p`). Without one, the app drafts from your own profile text.
4. **Jobs**: paste a job ad, read the fit check, click **Generate CV + cover letter**, edit, download the PDFs.

## How the fit check decides

Each requirement is compared with one line of your profile at a time, and the app quotes that line:

- **Supported**: the line itself covers most of the requirement, and if years are asked, the line's role covers them.
- **Partial**: some of it is there; the app says what is missing ("asks for 3 years; the profile shows about 1").
- **No evidence in profile**: nothing speaks to it.

Keywords scattered over unrelated lines never add up, and a job title alone cannot carry a requirement. Drafts only
claim Supported requirements. The tests include trap profiles with overlapping keywords but different
qualifications; on that set the app never says Supported when the profile does not support it.

## What the rule checks catch

Numbers and employers that are not in your profile, your banned phrases, missing must-mention items, letter and
sentence length. A model that breaks a rule is asked to repair it once; anything left is shown in red. The checks do
not prove every sentence is true, so read each draft before you send it.

## Privacy and cost

Your profile and drafts are stored locally in `~/.myjobseeker` (outside this repository; change it with
`MYJOBSEEKER_HOME`). The app uploads nothing and answers only on `127.0.0.1`. A local model costs nothing.

> If you connect a cloud-backed command-line tool, it may send profile and job-ad text to its provider and use your
> account's quota or incur charges.

PDFs are made with Chrome, Chromium, Brave or Edge if one is installed; otherwise use the preview page and your
browser's **Print → Save as PDF**.

## License

MIT, see [LICENSE](LICENSE). Anyone may use, change, share or sell copies with the notice kept, including changing
the monthly counter: the three-per-month count is how this client behaves out of the box, not a license restriction.
Any future paid feature would run as a separate service.

What ships in this repository, and where each file comes from: [docs/SHIPS_WITH.md](docs/SHIPS_WITH.md).
Run the tests with `python3 -m unittest discover -s tests`. Inspired by
[ai-job-search](https://github.com/ai-job-search-dev/ai-job-search).
