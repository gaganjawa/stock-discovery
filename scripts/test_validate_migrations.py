"""Guard against silently losing database integration coverage."""
from pathlib import Path
import tempfile
import unittest

from validate_migrations import verify_integration_report


class IntegrationReportTests(unittest.TestCase):
    def check_report(self, xml):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / 'integration.xml'
            report.write_text(xml)
            verify_integration_report(report)

    def test_executed_tests_are_accepted(self):
        self.check_report('<testsuites><testsuite><testcase name="database"/></testsuite></testsuites>')

    def test_skipped_tests_are_rejected(self):
        with self.assertRaisesRegex(AssertionError, 'Database integration tests skipped'):
            self.check_report('<testsuites><testsuite><testcase name="database"><skipped/></testcase></testsuite></testsuites>')

    def test_empty_report_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, 'No database integration tests executed'):
            self.check_report('<testsuites><testsuite/></testsuites>')
