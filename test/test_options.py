"""
Tests for mongoalchemy.options

"""
from nose.tools import *

from mongoalchemy import options
from mongoalchemy.document import Document
from mongoalchemy.fields import Field


DEFAULTS = None

def setup():
    # Let's always start with the same defaults, yea?
    global DEFAULTS
    if not DEFAULTS:
        DEFAULTS = options.CONFIG.copy()
    else:
        options.CONFIG = DEFAULTS.copy()


def test_options_update():
    options.configure(namespace='foobar')
    assert options.CONFIG['namespace'] == 'foobar'


def test_document_options_transparency():
    class D(Document):
        pass
    # Change an option
    options.configure(required=not options.CONFIG['required'])
    # And make sure it shows up
    assert D.config_required == options.CONFIG['required']
    assert D().config_required == options.CONFIG['required']


def test_field_options_transparency():
    class F(Field):
        pass
    # Change an option
    options.configure(required=not options.CONFIG['required'])
    # And make sure it shows up
    assert F.required == options.CONFIG['required']
    assert F().required == options.CONFIG['required']

