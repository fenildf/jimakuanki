# -*- coding: utf-8 -*-
#
# Copyright 2012 ©: Roland Sieker <ospalh@gmail.com>

# Provenance: Based on anki.stdmodels.addBasicModel
# by Damien Elmes <anki@ichi2.net>
#
# License: GNU AGPL, version 3 or later;
# http://www.gnu.org/licenses/agpl.html

from anki.lang import _


def add_model(col, args):
    mm = col.models
    if args.deck:
        model_name = _('Subtitles ({0})').format(args.deck)
    else:
        model_name = _('Subtitles')
    m = mm.new(model_name)
    fm = mm.newField(_('Timestamp'))
    mm.addField(m, fm)
    if args.language_name:
        text_name = args.language_name
    elif args.language:
        text_name = _('Text ({0})').format(args.language)
    else:
        text_name = _('Text')
    fm = mm.newField(text_name)
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
    t['qfmt'] = '<div>{{' + _('Image') + '}}</div>\n{{' + _('Video') + '}}\n' \
        + '<div class=small>{{' + _('Timestamp') + '}}</div>'
    t['afmt'] = '{{' + _('Image') + '}}\n{{' + _('Audio') + '}}\n' + \
        '<div>{{' + _('Text') + '}}</div>' + \
        '<div class="native">{{' + _('Native') + '}}</div>' + \
        '<div class="small">{{' + _('Timestamp') + '}}</div>'
    mm.addTemplate(m, t)
    mm.add(m)
    return m
