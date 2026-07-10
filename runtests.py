#!/usr/bin/env python
"""Test calistirici.

Kullanim:
    python runtests.py
"""

import os
import sys

import django
from django.test.utils import get_runner
from django.conf import settings


def run():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")
    django.setup()
    test_runner = get_runner(settings)(verbosity=2)
    failures = test_runner.run_tests(["tests"])
    sys.exit(bool(failures))


if __name__ == "__main__":
    run()
