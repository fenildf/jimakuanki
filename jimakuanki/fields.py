# -*- mode: python ; coding: utf-8 -*-
#
# Copyright © 2013 Roland Sieker <ospalh@gmail.com>
#
# License: GNU AGPL, version 3 or later;
# http://www.gnu.org/copyleft/agpl.html


"""
List of standard fields.
"""

# I really wanted to put this in one of the other files but didn’t
# manage to. Somehow i got import errors.

import gettext
import os

gettext.bindtextdomain('jimakuanki', os.path.join('.', 'translations'))
gettext.textdomain('jimakuanki')
_ = gettext.gettext



standard_fields = {
    'start': _(u'Start'), 'end': _(u'End'), 'expr': _(u'Expression'),
    'mean': _(u'Meaning'), 'read': _(u'Reading'), 'img': _(u'Image'),
    'vid': _(u'Video'), 'aud': _(u'Audio')}
"""
A few standard fields.

The programm expects a few standard fields. Define the names
here. Override the content to taste. Later these strings are used to
set up the model.
"""
