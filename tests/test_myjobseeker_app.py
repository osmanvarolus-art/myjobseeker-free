"""MyJobSeeker app: the monthly free tier, the rule checks, the fit check, the model guard and the local web API."""
import datetime as dt
import http.client
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
import myjobseeker as app  # noqa: E402

POSTING = """Buyer, operations team
- Experience with supplier follow-up and delivery planning
- Strong Excel and reporting skills
- Fluent English; Spanish is a plus
- Knowledge of SAP S/4HANA is required
"""


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.env = mock.patch.dict(os.environ, {"MYJOBSEEKER_HOME": self.tmp})
        self.env.start()
        self.profile = app.example_profile()
        app.write_json(app.home() / "profile.json", self.profile)

    def tearDown(self):
        self.env.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def job(self, title="Buyer", company="Acme"):
        return app.add_job(title, company, POSTING)


class FreeTier(Base):
    def test_three_pairs_a_month_and_the_fourth_is_refused(self):
        day = dt.date(2026, 3, 10)
        for _ in range(3):
            app.write_documents(self.job()["id"], use_model=False, today=day)
        self.assertEqual(app.usage(day)["left"], 0)
        with self.assertRaises(app.QuotaError) as caught:
            app.write_documents(self.job()["id"], use_model=False, today=day)
        self.assertIn("2026-04-01", str(caught.exception))

    def test_the_count_starts_again_next_month(self):
        for _ in range(3):
            app.write_documents(self.job()["id"], use_model=False, today=dt.date(2026, 3, 31))
        app.write_documents(self.job()["id"], use_model=False, today=dt.date(2026, 4, 1))
        self.assertEqual(app.usage(dt.date(2026, 4, 1))["used"], 1)

    def test_every_generation_uses_one_also_for_the_same_job(self):
        day = dt.date(2026, 5, 2)
        job = self.job()
        for _ in range(3):
            app.write_documents(job["id"], use_model=False, today=day)
        self.assertEqual(app.usage(day)["used"], 3)
        with self.assertRaises(app.QuotaError):  # a fourth generation for the same job
            app.write_documents(job["id"], use_model=False, today=day)
        self.assertEqual(len(app.load_job(job["id"])["versions"]), 3)

    def test_the_fourth_generation_for_a_different_job_is_refused(self):
        day = dt.date(2026, 5, 3)
        job = self.job()
        for _ in range(3):
            app.write_documents(job["id"], use_model=False, today=day)
        with self.assertRaises(app.QuotaError) as caught:
            app.write_documents(self.job("Planner", "Other Co")["id"], use_model=False, today=day)
        self.assertIn("Editing and downloading existing drafts are unlimited", str(caught.exception))

    def test_edits_are_free(self):
        day = dt.date.today()
        job = self.job()
        doc = app.write_documents(job["id"], use_model=False, today=day)
        app.save_edit(job["id"], doc)
        self.assertEqual(app.usage(day)["used"], 1)

    def test_a_failure_uses_nothing(self):
        day = dt.date(2026, 6, 1)
        (app.home() / "profile.json").unlink()
        with self.assertRaises(ValueError):
            app.write_documents(self.job()["id"], use_model=False, today=day)
        self.assertEqual(app.usage(day)["used"], 0)

    def test_a_model_that_does_not_answer_falls_back_and_counts_once(self):
        app.write_json(app.home() / "settings.json", {"model": {"kind": "local", "url": "http://127.0.0.1:9", "name": "x"}})
        day = dt.date(2026, 7, 1)
        doc = app.write_documents(self.job()["id"], today=day)
        self.assertEqual(doc["written_by"], "your profile (no model)")
        self.assertTrue(doc["notes"])
        self.assertEqual(app.usage(day)["used"], 1)


class Rules(Base):
    def doc(self, **letter):
        d = app.draft_without_model(self.profile, {"title": "Buyer", "company": "Acme", "posting": POSTING})
        d["letter"].update(letter)
        return d

    def test_an_invented_number_is_refused(self):
        d = self.doc(paragraphs=["I cut costs by 37 percent."])
        self.assertTrue(any("37" in p for p in app.gate(self.profile, app.load_rules(), d)))

    def test_numbers_from_the_profile_pass(self):
        d = self.doc(paragraphs=["I plan deliveries for 40 suppliers."])
        self.assertFalse([p for p in app.gate(self.profile, app.load_rules(), d) if "number" in p])

    def test_a_banned_phrase_and_a_missing_must_mention_are_reported(self):
        rules = dict(app.load_rules(), must_mention=["available from June"])
        d = self.doc(paragraphs=["I am writing to apply for this role."])
        problems = app.gate(self.profile, rules, d)
        self.assertTrue(any("I am writing to apply" in p for p in problems))
        self.assertTrue(any("available from June" in p for p in problems))

    def test_an_employer_not_in_the_profile_is_refused(self):
        d = self.doc()
        d["experience"].append({"role": "Director", "company": "Invented Corp", "bullets": []})
        self.assertTrue(any("Invented Corp" in p for p in app.gate(self.profile, app.load_rules(), d)))

    def test_the_draft_without_a_model_uses_only_profile_facts(self):
        d = self.doc()
        problems = app.gate(self.profile, app.load_rules(), d, {"title": "Buyer", "company": "Acme"})
        self.assertFalse([p for p in problems if "number" in p or "employer" in p], problems)


class Fit(Base):
    def test_requirements_get_supported_partial_or_no_evidence_with_the_exact_profile_line(self):
        rows = {r["requirement"]: r for r in app.fit(self.profile, POSTING)["requirements"]}
        excel = rows["Strong Excel and reporting skills"]
        self.assertEqual(excel["status"], "supported")
        self.assertIn("Excel", excel["evidence"][0]["text"])  # an experience line or the skills list, quoted exactly
        planning = rows["Experience with supplier follow-up and delivery planning"]
        self.assertEqual(planning["status"], "supported")
        self.assertIn("Example Logistics", planning["evidence"][0]["where"])
        sap = rows["Knowledge of SAP S/4HANA is required"]
        self.assertEqual(sap["status"], "none")
        self.assertEqual(sap["evidence"], [])


REQ = "Three years managing procurement contracts"


def person(*experience, skills=(), summary=""):
    return {"name": "Test Person", "summary": summary, "skills": list(skills),
            "experience": [{"role": r, "company": c, "dates": d, "bullets": list(b)} for r, c, d, b in experience]}


class Evidence(unittest.TestCase):
    """Fictional profiles with overlapping keywords but different qualifications (none of them real)."""
    TODAY = dt.date(2026, 6, 1)

    def status(self, profile, requirement=REQ):
        return app.judge(requirement, app.evidence_units(profile, self.TODAY))

    def test_the_task_and_the_years_in_one_role_is_supported(self):
        p = person(("Procurement Officer", "Example Council", "2019 - 2024", ["Managed procurement contracts for public tenders."]))
        r = self.status(p)
        self.assertEqual(r["status"], "supported")
        self.assertEqual(r["evidence"][0]["text"], "Managed procurement contracts for public tenders.")
        self.assertIn("2019 - 2024", r["evidence"][0]["where"])

    def test_the_task_but_too_few_years_is_partial(self):
        p = person(("Buyer", "Example Shop", "2025 - present", ["Managed procurement contracts with 12 suppliers."]))
        r = self.status(p)
        self.assertEqual(r["status"], "partial")
        self.assertIn("about 1", r["reason"])

    def test_keywords_scattered_over_unrelated_lines_are_not_supported(self):
        p = person(("HR Assistant", "Sample Agency", "2015 - 2025", ["Reviewed employment contracts.", "Managed the office calendar."]),
                   skills=["Procurement"])
        self.assertNotEqual(self.status(p)["status"], "supported")

    def test_a_skill_with_no_dates_cannot_prove_years(self):
        p = person(("Clerk", "Sample Office", "2020 - 2026", ["Filed letters."]), skills=["Managing procurement contracts"])
        r = self.status(p)
        self.assertEqual(r["status"], "partial")
        self.assertIn("no dates", r["reason"])

    def test_nothing_related_is_no_evidence(self):
        p = person(("Chef", "Sample Bistro", "2010 - 2026", ["Cooked lunch for 80 guests."]))
        r = self.status(p)
        self.assertEqual(r["status"], "none")
        self.assertEqual(r["reason"], "No evidence in profile")

    def test_launch_metric_no_false_supported_on_the_trap_set(self):
        """How often the app says 'you meet this' when the profile does not support it: must be zero here."""
        traps = [
            (person(("Contract Cleaner", "Sample Services", "2012 - 2026", ["Managed cleaning rotas."])), REQ),
            (person(("Teacher", "Sample School", "2010 - 2026", ["Taught procurement law basics to adults."])), REQ),
            (person(("Analyst", "Sample Bank", "2024 - present", ["Managed procurement contracts reporting."])), REQ),
            (person(("Driver", "Sample Transport", "2015 - 2026", ["Delivered parcels."]), skills=["Excel"]),
             "Five years of SAP S/4HANA configuration"),
            (person(("Receptionist", "Sample Hotel", "2018 - 2026", ["Answered phone calls in English."])),
             "Fluent German and Dutch"),
        ]
        false_supported = [req for p, req in traps if self.status(p, req)["status"] == "supported"]
        self.assertEqual(false_supported, [])

    def test_drafts_only_claim_supported_requirements(self):
        p = person(("Buyer", "Example Shop", "2025 - present", ["Managed procurement contracts with 12 suppliers."]), skills=["Excel"])
        d = app.draft_without_model(p, {"title": "Buyer", "company": "Acme", "posting": "- " + REQ + "\n- Strong Excel skills"})
        letter = " ".join(d["letter"]["paragraphs"])
        self.assertNotIn("three years managing", letter.lower())

    def test_the_model_prompt_carries_the_evidence_labels(self):
        p = person(("Buyer", "Example Shop", "2025 - present", ["Managed procurement contracts."]))
        text = app.evidence_text(p, {"posting": "- " + REQ + "\n- Knowledge of SAP is required"})
        self.assertIn("[PARTIAL] Three years managing procurement contracts", text)
        self.assertIn("[NO EVIDENCE] Knowledge of SAP is required", text)


class ModelGuard(Base):
    def test_a_model_outside_this_computer_is_refused(self):
        with self.assertRaises(RuntimeError):
            app.ask_model({"model": {"kind": "local", "url": "https://api.example.com"}}, "hi")

    def test_a_command_model_reads_the_prompt(self):
        settings = {"model": {"kind": "command", "command": f'"{sys.executable}" -c "import sys; print(sys.stdin.read().upper())"'}}
        self.assertIn("HELLO", app.ask_model(settings, "hello"))

    def test_a_model_answer_is_checked_and_repaired(self):
        good = {"headline": "Buyer", "summary": "Operations coordinator.", "skills": ["Excel"],
                "experience": [{"role": "Operations Coordinator", "company": "Example Logistics", "dates": "2021 - present", "bullets": ["Plan deliveries."]}],
                "letter": {"greeting": "Dear Hiring Manager,", "paragraphs": ["I plan deliveries for 40 suppliers. " * 12], "closing": "Kind regards,\nJordan Example"}}
        bad = json.loads(json.dumps(good))
        bad["letter"]["paragraphs"] = ["I saved 99 percent. " * 30]
        answers = iter([json.dumps(bad), json.dumps(good)])
        app.write_json(app.home() / "settings.json", {"model": {"kind": "command", "command": "x"}})
        prompts = []
        with mock.patch.object(app, "ask_model", side_effect=lambda s, p, **k: prompts.append(p) or next(answers)):
            doc = app.write_documents(self.job()["id"])
        self.assertEqual(doc["written_by"], "your model")
        self.assertIn("99", prompts[1])  # the second prompt names the broken rule
        self.assertFalse([p for p in doc["problems"] if "number" in p])


class WebApi(Base):
    def setUp(self):
        super().setUp()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.port = self.server.server_address[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        super().tearDown()

    def call(self, method, path, body=None, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        h = {"Host": f"127.0.0.1:{self.port}"}
        if body is not None:
            h["Content-Type"] = "application/json"
        h.update(headers or {})
        c.request(method, path, json.dumps(body) if body is not None else None, h)
        r = c.getresponse()
        data = r.read()
        c.close()
        return r.status, data

    def test_page_and_state(self):
        self.assertEqual(self.call("GET", "/")[0], 200)
        status, data = self.call("GET", "/api/state")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(data)["usage"]["limit"], 3)

    def test_add_write_view_and_quota_over_http(self):
        ids = []
        for i in range(4):
            status, data = self.call("POST", "/api/jobs", {"title": f"Buyer {i}", "company": "Acme", "posting": POSTING})
            self.assertEqual(status, 200)
            ids.append(json.loads(data)["id"])
        for job_id in ids[:3]:
            self.assertEqual(self.call("POST", f"/api/jobs/{job_id}/write", {"use_model": False})[0], 200)
        self.assertEqual(self.call("POST", f"/api/jobs/{ids[3]}/write", {"use_model": False})[0], 429)
        status, page = self.call("GET", f"/view/{ids[0]}/cv")
        self.assertEqual(status, 200)
        self.assertIn(b"Jordan Example", page)
        self.assertEqual(self.call("POST", f"/api/jobs/{ids[0]}/write", {"use_model": False})[0], 429)  # same job, 4th generation
        self.assertEqual(self.call("GET", f"/view/{ids[1]}/letter")[0], 200)  # existing drafts still open after the limit
        doc = json.loads(self.call("GET", f"/api/jobs/{ids[2]}")[1])["versions"][-1]
        self.assertEqual(self.call("POST", f"/api/jobs/{ids[2]}/edit", {"doc": doc})[0], 200)  # and can still be edited

    def test_a_foreign_host_and_a_cross_site_post_are_refused(self):
        self.assertEqual(self.call("GET", "/api/state", headers={"Host": "evil.example"})[0], 403)
        self.assertEqual(self.call("POST", "/api/profile", {"profile": {"name": "x"}}, {"Origin": "https://evil.example"})[0], 403)

    def test_a_remote_model_cannot_be_saved(self):
        status, _ = self.call("POST", "/api/settings", {"model": {"kind": "local", "url": "https://api.example.com/v1"}})
        self.assertEqual(status, 400)

    def test_a_bad_job_id_is_404(self):
        self.assertEqual(self.call("GET", "/api/jobs/..%2Fprofile")[0], 404)


class DataStaysOutOfTheRepo(unittest.TestCase):
    def test_default_data_folder_is_outside_the_repository(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MYJOBSEEKER_HOME", None)
            with mock.patch.object(Path, "mkdir"):
                root = app.home()
        self.assertNotIn(str(Path(app.__file__).resolve().parents[1]), str(root))


if __name__ == "__main__":
    unittest.main()
