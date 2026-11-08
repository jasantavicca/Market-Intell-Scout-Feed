import copy
import datetime as dt
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scout'))
import runner as r

CLOCK = dt.datetime(2026, 11, 8, 10, 30, tzinfo=r.ET)
ITEM = {'id': 'scout-20261108-1030-example', 'observed_at': CLOCK.isoformat(),
        'title': 'Example fixture', 'summary': 'A material event happened. Its impact remains uncertain.',
        'tickers': ['TEST'], 'sectors': ['Energy'], 'evidence_grade': 'single-source',
        'observations': [{'label': 'Risk', 'value': 'Uncertain impact'}],
        'key_finding': 'An example', 'sources': [{'title': 'Dated source', 'url': 'https://example.com/'}],
        'status': 'new', 'supersedes': None}
FEED = {'feed_version': 'scout-feed-v1', 'generated_at': '2026-11-08T09:30:00-05:00',
        'as_of_et': '9:30 AM EST', 'items': []}
def result(items):
    return {'coverage': {k: 'Checked dated public sources for this sector.' for k in
            ('semiconductors_ai', 'software_networking', 'power_grid', 'healthcare',
             'international', 'oil_shipping', 'macro_markets')}, 'items': items}

class RunnerTests(unittest.TestCase):
    def test_detroit_schedule_dst_weekends_boundaries(self):
        for month, offset in [(7, -4), (11, -5)]:
            for hour in range(9, 17):
                clock = CLOCK.replace(month=month, hour=hour)
                self.assertEqual(r.slot_at(clock).hour, hour)
                self.assertEqual(clock.utcoffset().total_seconds(), offset * 3600)
        self.assertIsNone(r.slot_at(CLOCK.replace(hour=9, minute=29)))
        self.assertEqual(r.slot_at(CLOCK.replace(hour=17, minute=29)).hour, 16)
        self.assertIsNone(r.slot_at(CLOCK.replace(hour=17, minute=30)))

    def test_no_change_preserves_timestamp_and_input(self):
        current = copy.deepcopy(FEED)
        self.assertIsNone(r.compose(current, result([]), CLOCK))
        self.assertEqual(current, FEED)

    def test_empty_or_partial_research_is_failure(self):
        for bad in ({}, {'items': []}, {'coverage': {}, 'items': []}):
            with self.assertRaises(ValueError):
                r.compose(FEED, bad, CLOCK)

    def test_new_findings_keep_previous_items_and_max_five(self):
        current = copy.deepcopy(FEED)
        current['items'] = [dict(ITEM, id='scout-20261108-0930-old-' + str(i)) for i in range(5)]
        item = dict(ITEM, title='New material announcement')
        updated = r.compose(current, result([item]), CLOCK, False)
        self.assertEqual(len(updated['items']), 5)
        self.assertEqual(updated['items'][0], item)
        self.assertEqual(updated['items'][1], current['items'][0])

    def test_duplicate_ignores_new_id_and_clock(self):
        current = dict(FEED, items=[ITEM])
        self.assertIsNone(r.compose(current, result([dict(ITEM, id='scout-20261108-1031-new-id')]), CLOCK, False))

    def test_corrections_reference_prior_id(self):
        with self.assertRaises(ValueError):
            r.compose(FEED, result([dict(ITEM, status='invalidated')]), CLOCK, False)
        current = dict(FEED, items=[ITEM])
        corrected = dict(ITEM, id='scout-20261108-1030-correction', status='invalidated',
                         supersedes=ITEM['id'], summary='Correction. The earlier claim was wrong.')
        self.assertEqual(r.compose(current, result([corrected]), CLOCK, False)['items'][0], corrected)

    def test_broken_source_rejects_whole_write(self):
        with patch.object(r, 'working_source', return_value=False), self.assertRaises(ValueError):
            r.compose(FEED, result([ITEM]), CLOCK)

    def test_rejects_bad_schema_stale_or_naive_times(self):
        for bad in [dict(ITEM, extra='x'), dict(ITEM, evidence_grade='guess'),
                    dict(ITEM, observed_at='2026-11-08T10:30:00'),
                    dict(ITEM, observed_at='2026-11-07T10:30:00-05:00')]:
            with self.assertRaises(ValueError):
                r.compose(FEED, result([bad]), CLOCK, False)

    def test_success_atomic_commit_and_readback(self):
        gh = object.__new__(r.GitHub)
        calls = []
        def call(path, payload=None, method=None):
            calls.append((path, payload, method))
            return {'sha': 'commit' if path == '/git/commits' else 'tree'}
        gh.call = call
        gh.read = lambda path: FEED if path == r.FEED else {'outcome': 'published'}
        self.assertEqual(gh.publish('old', {r.FEED: FEED, r.STATE: {'outcome': 'published'}}), 'commit')
        self.assertEqual(calls[-1][1], {'sha': 'commit', 'force': False})
        self.assertEqual(len(calls[0][1]['tree']), 2)

    def test_readback_failure_never_reports_success(self):
        gh = object.__new__(r.GitHub)
        gh.call = lambda *a, **kw: {'sha': 'new'}
        gh.read = lambda path: {}
        with self.assertRaises(RuntimeError):
            gh.publish('old', {r.FEED: FEED})

    def test_prevents_other_repositories_and_paths(self):
        with patch.dict(r.os.environ, {'GITHUB_REPOSITORY': 'other/repo'}), self.assertRaises(RuntimeError):
            r.GitHub()
        with self.assertRaises(RuntimeError):
            object.__new__(r.GitHub).publish('head', {'index.html': {}})

if __name__ == '__main__':
    unittest.main()
