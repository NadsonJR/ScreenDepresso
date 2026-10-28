"""Expose failed test details as GitHub annotations, preserving the runner exit code."""
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


def escaped(value):
    return value.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')


def report(path, platform='Windows'):
    path = Path(path)
    if not path.exists():
        print('::error::Test report was not created.')
        return
    for case in ET.parse(path).iter('testcase'):
        for result in list(case):
            if result.tag in ('failure', 'error'):
                detail = f"{case.get('classname', '')}.{case.get('name', '')}\n{result.text or result.get('message', '')}"
                print('::error title='+platform+' test failure::'+escaped(detail[:12000]))


if __name__ == '__main__':
    report(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else 'Windows')
