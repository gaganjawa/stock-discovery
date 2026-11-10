"""Guard against silently losing database integration coverage."""
from contextlib import redirect_stdout
from io import StringIO
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import validate_migrations
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

    def test_timing_summary_reports_completed_phases_and_total(self):
        output = StringIO()
        with redirect_stdout(output):
            validate_migrations.print_timing_summary({
                'Initial database migrations': 1.25,
                'PostgreSQL integration tests': 2.5,
                'Total execution': 3.75,
            })
        self.assertEqual(
            output.getvalue(),
            'Timing summary:\n'
            '  Initial database migrations: 1.25s\n'
            '  PostgreSQL integration tests: 2.50s\n'
            '  Total execution: 3.75s\n',
        )

    def test_validation_failure_reports_completed_timings_and_reraises(self):
        output = StringIO()
        failure = RuntimeError('integration command failed')
        with (
            patch.dict(os.environ, {'STK_TEST_DATABASE_URL': 'postgresql://localhost/stk013_test'}),
            patch.object(validate_migrations.psycopg.conninfo, 'conninfo_to_dict', return_value={'dbname': 'stk013_test'}),
            patch.object(validate_migrations, 'Config'),
            patch.object(validate_migrations.command, 'upgrade'),
            patch.object(validate_migrations.subprocess, 'run', side_effect=failure),
            patch.object(validate_migrations, 'perf_counter', side_effect=[10.0, 11.0, 13.0, 14.0, 15.0]),
            redirect_stdout(output),
        ):
            with self.assertRaisesRegex(RuntimeError, 'integration command failed') as raised:
                validate_migrations.main()
        self.assertIs(raised.exception, failure)
        self.assertIn('  Initial database migrations: 2.00s\n', output.getvalue())
        self.assertIn('  Total execution: 5.00s\n', output.getvalue())
        self.assertNotIn('PostgreSQL integration tests:', output.getvalue())
