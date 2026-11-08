"""One manual paid research pass; read-only GitHub access, no feed/heartbeat writes."""
import json
import os
from pathlib import Path
import runner


def main():
    os.environ['SCOUT_TEST'] = '1'
    gh = runner.GitHub()
    head = gh.head()
    current = gh.read(runner.FEED, head)
    clock = runner.now()
    result, evidence = runner.research(current, clock)
    updated = runner.compose(current, result, clock)
    # Public research content only; never credentials or API request headers.
    report = {
        'mode': 'test_only_no_publication',
        'source_commit': head,
        'validated': True,
        'would_publish_findings': updated is not None,
        'research': result,
        'evidence': evidence,
    }
    Path('scout-test-result.json').write_text(json.dumps(report, indent=2))
    if gh.read(runner.FEED) != current:
        raise RuntimeError('Feed changed concurrently; trial did not publish')
    print('Manual test passed. Feed and heartbeat were not written.')
    print('Candidate findings:', len(result['items']))


if __name__ == '__main__':
    main()
