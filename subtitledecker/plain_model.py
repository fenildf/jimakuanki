# -*- coding: utf-8 -*-
#
# Copyright 2012 ©: Roland Sieker <ospalh@gmail.com>

# Provenance: Based on anki.stdmodels.addBasicModel
# by Damien Elmes <anki@ichi2.net>
#
# License: GNU AGPL, version 3 or later;
# http://www.gnu.org/licenses/agpl.html

from anki.lang import _

def add_plain_model(col):
    mm = col.models
    m = mm.new(_('Subtitle deck'))
    fm = mm.newField(_('Timestamp'))
    mm.addField(m, fm)
    fm = mm.newField(_('Text'))
    mm.addField(m, fm)
    fm = mm.newField(_('Native'))
    mm.addField(m, fm)
    fm = mm.newField(_('Image'))
    mm.addField(m, fm)
    fm = mm.newField(_('Video'))
    mm.addField(m, fm)
    fm = mm.newField(_('Audio'))
    mm.addField(m, fm)
    fm = mm.newField(_('Literal'))
    mm.addField(m, fm)
    fm = mm.newField(_('Notes'))
    mm.addField(m, fm)
    t = mm.newTemplate(_('Watch'))
    t['qfmt'] = '<div>{{' + _('Image') + '}}</div>\n{{'+_('Video')+'}}\n' \
        + '<div class=small>{{' + _('Timestamp') + '}}</div>'
    t['afmt'] = '{{' + _('Image') + '}}\n{{' + _('Audio')+ '}}\n' + \
        '<div>{{'+_('Text')+'}}</div>' + \
        '<div class="native">{{'+_('Native')+'}}</div>' + \
        '<div class="small">{{'+_('Timestamp')+'}}</div>'
    mm.addTemplate(m, t)
    mm.add(m)
    return m
