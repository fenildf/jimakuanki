# -*- coding: utf-8 -*-
#
# Copyright 2012 ©: Roland Sieker <ospalh@gmail.com>

# Provenance: Based on anki.stdmodels.addBasicModel
# by Damien Elmes <anki@ichi2.net>
#
# License: GNU AGPL, version 3 or later;
# http://www.gnu.org/licenses/agpl.html


"""
Create a simple static model for the subtitle deck.
"""
from libanki.lang import _

remove_arial = True
extra_styling = '''
.small {font-size: 9px;}
'''


def add_simple_model(col, name, language_name, native_language_name):
    mm = col.models
    m = mm.new(name or _('Subtitles'))

    start_name = _('Start')
    end_name = _('End')
    fm = mm.newField(start_name)
    mm.addField(m, fm)
    fm = mm.newField(end_name)
    mm.addField(m, fm)
    fm = mm.newField(language_name)
    mm.addField(m, fm)
    reading_name = _(u'Reading')
    fm = mm.newField(reading_name)
    mm.addField(m, fm)
    fm = mm.newField(native_language_name or _(u'Meaning'))
    mm.addField(m, fm)
    image_name = _(u'Image')
    fm = mm.newField(image_name)
    mm.addField(m, fm)
    video_name = _(u'Video')
    fm = mm.newField(video_name)
    mm.addField(m, fm)
    audio_name = _(u'Audio')
    fm = mm.newField(audio_name)
    mm.addField(m, fm)
    fm = mm.newField(_(u'Literal'))
    mm.addField(m, fm)
    fm = mm.newField(_(u'Notes'))
    mm.addField(m, fm)
    t = mm.newTemplate(_(u'Watch'))
    # NB.: those things are five pairs of braces: double braces are
    # escapes for single braces, so four of the five give double
    # braces, what we want in the output. The last pair is used by
    # str.format().
    # The character between start and end is an n-dash.
    t['qfmt'] = u'''\
{{{{{image}}}}}
{{{{{video}}}}}
<div class="small">{{{{{st}}}}}–{{{{{end}}}}}</div>
'''.format(image=image_name, video=video_name, st=start_name, end=end_name)

    t['afmt'] = u'''\
{{{{{image}}}}}
{{{{{audio}}}}}
<div>{{{{{text}}}}}</div>
<div>{{{{furigana:{read}}}}}</div>
<div>{{{{{native}}}}}</div>
<div class="small">{{{{{st}}}}}–{{{{{end}}}}}</div>
'''.format(image=image_name, audio=audio_name, text=language_name,
           read=reading_name, native=native_language_name, st=start_name,
           end=end_name)
    # Arial is ugly.
    if remove_arial:
        m['css'] = m['css'].replace(
            'font-family: arial;', '/* font-family: arial; */')
    m['css'] += extra_styling
    mm.addTemplate(m, t)
    mm.add(m)
    return m
