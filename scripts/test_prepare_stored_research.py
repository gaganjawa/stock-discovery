import unittest
import tempfile
from pathlib import Path
from prepare_stored_research import prepare,write_prepared
from stock_discovery_analysis.real_views import ViewConfig
from stock_discovery_analysis.real_access import SourceConfig
from stock_discovery_analysis.schedule_fixtures import fixture_config
from stock_discovery_analysis.daily_insight import LISTING
from stock_discovery_contracts.v2 import digest

class PrepareStoredTests(unittest.TestCase):
    def test_isolated_derivative_preserves_calendar_and_originals(self):
        view=ViewConfig(sources=SourceConfig(grant_file='/test/grants',retention_days=30),listing_ids=(LISTING,'NSE:OTHER'))
        schedule=fixture_config().model_copy(update={'mode':'live_paper'})
        before=(view.model_dump(),schedule.model_dump())
        new,plan=prepare(view,schedule,code_version='test',starts_on='2026-10-16')
        self.assertEqual(before,(view.model_dump(),schedule.model_dump()))
        self.assertEqual(new.listing_ids,(LISTING,));self.assertEqual(new.sources,view.sources)
        self.assertEqual(plan.calendar,schedule.calendar)
        self.assertEqual(plan.input_hash,digest(new.model_dump(mode='json')))
        self.assertEqual(new.pilot_scope_id,plan.scope_id)
        self.assertEqual(new.descriptive_freshness_policy,'one_trailing_session_v1')

    def test_synthetic_calendar_mode_cannot_be_used(self):
        view=ViewConfig(sources=SourceConfig(grant_file='/test',retention_days=30),listing_ids=(LISTING,))
        with self.assertRaises(ValueError):prepare(view,fixture_config(),code_version='test',starts_on='2026-10-16')

    def test_repeated_preparation_preserves_first_valid_files(self):
        view=ViewConfig(sources=SourceConfig(grant_file='/test',retention_days=30),listing_ids=(LISTING,))
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'deployment'
            write_prepared(out,view,fixture_config())
            before={p.name:p.read_bytes() for p in out.iterdir()}
            with self.assertRaises(FileExistsError):write_prepared(out,view,fixture_config())
            self.assertEqual(before,{p.name:p.read_bytes() for p in out.iterdir()})
            self.assertEqual(out.stat().st_mode&0o777,0o700)
            self.assertTrue(all(p.stat().st_mode&0o777==0o600 for p in out.iterdir()))
