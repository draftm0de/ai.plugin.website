"""Preview `inspect`: the visible page is judged separately from the process. Real local HTTP servers on free ports
(a foreign server stands in for a dev server someone else started); nothing is started, signalled or adopted."""
import http.server
import threading
import unittest

from tests.support import preview_helpers as helpers  # noqa: F401
from tests.support.preview_process import ControlBase, run
import control

PAGE = ('<!doctype html><html><head><title>t</title><link rel="canonical" href="{canon}"/>'
        '<meta property="og:site_name" content="{name}"/></head><body><h1>{body}</h1></body></html>')
SITE_TS = "export const SITE = 'https://site.test';\nexport const SITE_NAME: string = \"Demo-Fu\\u00dfball\";\n"


class Serve:
    def __init__(self, port, body, canon="https://site.test/", name="Demo-Fußball", status=200):
        html = PAGE.format(canon=canon, name=name, body=body).encode()

        class H(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(status); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers(); self.wfile.write(html)

            def log_message(self, *a):
                pass
        self.httpd = http.server.HTTPServer(("127.0.0.1", port), H)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown(); self.httpd.server_close()


class InspectTests(ControlBase):
    def site(self):
        root = self.project()
        lib = root / "sites" / "site.test" / "src" / "lib"
        lib.mkdir(parents=True)
        (lib / "site.ts").write_text(SITE_TS)
        return root

    def serve(self, **kw):
        s = Serve(self.port, **kw)
        self.addCleanup(s.close)
        self._last = s
        return s

    def httpd_close(self):
        self._last.close()

    def test_foreign_server_blocks_start_but_the_page_can_still_be_inspected(self):
        root = self.site()
        self.serve(body="Welcome new players")
        code, start = run(root, "start", "site.test", "--timeout", "3")
        self.assertEqual((code, start["state"]), (1, "port-conflict"))                    # our own start is refused ...
        code, out = run(root, "inspect", "site.test", "--expect", "Welcome new players")
        self.assertEqual((code, out["state"]), (0, "page-confirmed"), out)                # ... the visible check is not
        self.assertEqual(out["process"], "not-managed-by-this-skill")                     # process and page are separate facts
        code, status = run(root, "status", "site.test")
        self.assertEqual(status["state"], "not-running")                                  # status is not reported as blocked
        self.assertTrue(status["foreign_candidate"])

    def test_manifest_and_port_are_not_changed_by_inspect(self):
        root = self.site()
        before = (root / ".project/specs/zyris-website.json").read_text()
        self.serve(body="x")
        run(root, "inspect", "site.test", "--expect", "x")
        self.assertEqual((root / ".project/specs/zyris-website.json").read_text(), before)

    def test_other_site_on_the_port_is_not_evidence(self):
        root = self.site()
        self.serve(body="Welcome", canon="https://other.example/", name="Other")
        code, out = run(root, "inspect", "site.test", "--expect", "Welcome")
        self.assertEqual((code, out["state"]), (1, "page-other-site"))

    def test_same_name_but_other_canonical_host_is_not_evidence(self):
        root = self.site()
        self.serve(body="Welcome", canon="https://other.example/")
        self.assertEqual(run(root, "inspect", "site.test", "--expect", "Welcome")[1]["state"], "page-other-site")

    def test_stale_page_is_not_evidence(self):
        root = self.site()
        self.serve(body="Old greeting")
        code, out = run(root, "inspect", "site.test", "--expect", "New greeting")
        self.assertEqual((code, out["state"]), (1, "page-stale"))

    def test_one_missing_expectation_among_several_is_stale(self):
        root = self.site()
        self.serve(body="Hello there")
        self.assertEqual(run(root, "inspect", "site.test", "--expect", "Hello", "--expect", "Missing")[1]["state"], "page-stale")

    def test_without_expected_content_only_identity_is_confirmed(self):
        root = self.site()
        self.serve(body="Hello")
        code, out = run(root, "inspect", "site.test")
        self.assertEqual((code, out["state"]), (1, "page-identity-only"))

    def test_unreadable_site_identity_is_not_evidence(self):
        root = self.project()                                  # no src/lib/site.ts
        self.serve(body="Hello")
        self.assertEqual(run(root, "inspect", "site.test", "--expect", "Hello")[1]["state"], "page-identity-unknown")

    def test_nothing_listening_and_server_errors_are_not_reachable(self):
        root = self.site()
        self.assertEqual(run(root, "inspect", "site.test", "--expect", "x")[1]["state"], "page-not-reachable")
        self.serve(body="x", status=500)
        self.assertEqual(run(root, "inspect", "site.test", "--expect", "x")[1]["state"], "page-not-reachable")

    def test_expected_text_may_be_html_escaped_or_inside_markup(self):
        root = self.site()
        self.serve(body="Fu&szlig;ball <em>f&uuml;r alle</em>")
        self.assertEqual(run(root, "inspect", "site.test", "--expect", "Fußball").__getitem__(1)["state"], "page-confirmed")
    def test_prefix_host_is_not_the_site(self):
        root = self.site()
        for canon in ("https://site.test.other.example/", "https://site.testing/", "https://evil.example/https://site.test/",
                      "http://site.test/", "https://user@site.test/", "https://site.test:8443/", "https://sub.site.test/"):
            self.serve(body="Welcome", canon=canon)
            out = run(root, "inspect", "site.test", "--expect", "Welcome")[1]
            self.assertEqual(out["state"], "page-other-site", canon)
            self.httpd_close()

    def test_same_site_url_forms_are_confirmed(self):
        for canon in ("https://site.test", "https://site.test/", "https://SITE.test/about.html", "https://site.test:443/x"):
            self.assertTrue(control.same_site_url(canon, "https://site.test"), canon)
        self.assertFalse(control.same_site_url("https://site.test/", "https://site.test/club"))
        self.assertTrue(control.same_site_url("https://site.test/club/a", "https://site.test/club"))
        self.assertFalse(control.same_site_url("https://site.test/clubhouse", "https://site.test/club"))
        self.assertFalse(control.same_site_url("javascript:alert(1)", "https://site.test"))

    def test_script_style_comment_and_metadata_are_not_visible_text(self):
        root = self.site()
        for body in ('Old greeting<script>const x="New greeting"</script>',
                     'Old greeting<style>.a::after{content:"New greeting"}</style>',
                     'Old greeting<!-- New greeting -->',
                     'Old greeting<template><p>New greeting</p></template>',
                     'Old greeting<noscript>New greeting</noscript>',
                     'Old greeting<p hidden>New <b>greeting</b></p>'):
            self.serve(body=body)
            out = run(root, "inspect", "site.test", "--expect", "New greeting")[1]
            self.assertEqual(out["state"], "page-stale", body)
            self.httpd_close()

    def test_title_and_meta_content_are_not_visible_text(self):
        doc = '<html><head><title>New greeting</title><meta name="description" content="New greeting"></head><body>Old</body></html>'
        self.assertNotIn("New greeting", control.visible_text(doc))

    def test_text_across_inline_elements_and_entities_is_matched(self):
        self.assertIn("New greeting for you", control.visible_text("<p>New <b>greet</b>ing\n for&nbsp;you</p>".replace("&nbsp;", " ")))
        self.assertIn("Fußball für alle", control.visible_text("<p>Fu&szlig;ball <em>f&uuml;r</em>\n alle</p>"))
        self.assertNotIn("Newgreeting", control.visible_text("<h1>New</h1><p>greeting</p>"))     # block elements separate words
        self.assertIn("New", control.visible_text("<p>New<br>greeting</p>"))

    def test_empty_expectation_is_no_evidence(self):
        root = self.site()
        self.serve(body="Welcome")
        for args in (["--expect", ""], ["--expect", "   "], ["--expect", "Welcome", "--expect", ""]):
            code, out = run(root, "inspect", "site.test", *args)
            self.assertEqual((code, out["state"]), (1, "page-identity-only"), args)

    def test_confirmed_is_a_precheck_only(self):
        root = self.site()
        self.serve(body="Welcome")
        out = run(root, "inspect", "site.test", "--expect", "Welcome")[1]
        self.assertEqual(out["state"], "page-confirmed")
        self.assertIs(out["visibility_checked"], False)

    def test_application_switch_reuses_the_existing_page_without_a_second_server(self):
        """Another application started the preview (foreign listener on the manifest port). The controller refuses to
        start, points to inspect, nothing else is started, the next port stays free, the foreign server keeps running."""
        root = self.site()
        manifest_before = (root / ".project/specs/zyris-website.json").read_text()
        self.serve(body="Brand new greeting")
        code, start = run(root, "start", "site.test", "--timeout", "3")
        self.assertEqual((code, start["state"]), (1, "port-conflict"))
        self.assertEqual(start["next_step"], "inspect")
        self.assertIn("do not start a second server", start["message"])
        self.assertNotIn("Stop that process", start["message"])
        code, out = run(root, "inspect", "site.test", "--expect", "Brand new greeting")
        self.assertEqual((code, out["state"]), (0, "page-confirmed"))
        self.assertTrue(out["url"].endswith(f":{self.port}/"))                      # the existing URL, no other port
        self.assertFalse(control.port_bound(self.port + 1))                         # no second server, no port move
        self.assertTrue(control.port_bound(self.port))                              # the foreign server still runs
        self.assertFalse(control.record_file(root, "site.test").exists())           # nothing adopted
        self.assertEqual((root / ".project/specs/zyris-website.json").read_text(), manifest_before)

    def test_old_page_of_the_other_application_is_not_accepted(self):
        root = self.site()
        self.serve(body="Old greeting")
        self.assertEqual(run(root, "start", "site.test", "--timeout", "3")[1]["state"], "port-conflict")
        code, out = run(root, "inspect", "site.test", "--expect", "Brand new greeting")
        self.assertEqual((code, out["state"]), (1, "page-stale"))
        self.assertFalse(control.port_bound(self.port + 1))

    def test_identity_parser_reads_unicode_escapes(self):
        root = self.site()
        self.assertEqual(control.site_identity(root / "sites" / "site.test"), ("https://site.test", "Demo-Fußball"))


if __name__ == "__main__":
    unittest.main()
