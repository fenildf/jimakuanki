# -*- mode: python ; coding: utf-8 -*-
#
# Copyright © 2012–2013 Roland Sieker <ospalh@gmail.com>
#
# Provenance: Parts of the code were written by Damien Elmes, as
# * anki.storage.Collection()
# * aqt.profiles
#
# License: GNU AGPL, version 3 or later;
# http://www.gnu.org/copyleft/agpl.html

"""
Turn a video and sets of subtitles into an Anki2 deck.
"""

import bisect
import os
import pysubs  # N.B.: This has to be the py27compat branch.
import random
import shutil
import tempfile

from libanki.collection import _Collection
from libanki.db import DB
from libanki.exporting import AnkiPackageExporter
from libanki.notes import Note
from libanki.storage import _createDB
from libanki.lang import _

from . import models

# How many ms will we shift to make the time unique
fudge_timing_max_ms = 500

standard_fields = {
    'start': _(u'Start'), 'end': _(u'End'), 'exp': _(u'Expression'),
    'mean': _(u'Meaning'), 'read': _(u'Reading'), 'img': _(u'Image'),
    'vid': _(u'Video'), 'aud': _(u'Audio')}
"""
A few standard fields.

The programm expects a few standard fields. Define the names
here. Override the content to taste. Later these strings are used to
set up the model.
"""

# Set up how leading and trailing field names are generated. For
# example, the 2nd leadig Expression field gets the field name
# leading_format.format(field=standard_fields['exp'],
# num=lead_trail_num_dict[2]), which be default evaluates to _(u'Leading
# Expression 2').
leading_format = _(u'Leading {field}{num}')
trailing_format = _(u'Trailing {field}{num}')
lead_trail_num_dict = {1: u'', 2: _(u' 2'), 3: _(u' 3'), 4: _(u' 4')}


class JimakuAnki(object):
    """
    Representation of an Anki deck containing subtitles.

    This is a representation of an Anki2 spaced repetition system
    flashcard collection. The collection can be automatically filled
    with a deck of flashcards of video clips and subtitles.

    Workflow:
    * Create JimakuAnki object
    * Add a video file
    * Add subtitles, either as extra files or pointing to subtitles
      from the video files.
    * Set up other parameters such as languages, deck and output file names.
    *
    """

    def __init__(self):
        self.default_sub_encoding = 'utf-8'
        self.col_path = u''
        self.col_name = u'collection'
        self.model = None
        self.out_file = ''
        self.deck_id = None
        self.subtitle_files = []
        self.index_subtitles_index = 0
        self.master_subtitles = None
        self.other_subtitles = []
        self.leading_lines = 2
        self.trailing_lines = 2
        # Should we add local translations of leading and trailing
        # lines as well?
        self.lead_trail_translated = True
        self.video = None
        self.model_name = None
        self.use_video = True
        self.normalize = True
        self.normalize_video = True
        self.japanese = False
        self.chinese = False
        self.use_reading = False
        self.automatic_reading = False
        self.language_names = [u'Expression', u'Meaning']
        self.language_codes = [u'ja', u'en']
        self.field_list = [u'Start', u'End', u'Expression', u'Meaning',
                           u'Reading', u'Image', u'Video', u'Audio']
        # Frame rate, that infamous number that is not quite 30.
        self.fps = pysubs.misc.Time.NAMED_FPS['ntsc']
        # We fudge the timing data a bit when there is a second
        # subtitle starting at the same time. Keep track of that.
        self.start_times_seen = []
        # Keep track of the longest title. With this searching of
        # matching titles becoms quicker.
        self.longest_title = pysubs.misc.Time()
        self.start_dir = os.getcwd()
        self.col = self.get_collection()
        self.dm = self.col.decks

    def add_simple_model(self):
        self.model = models.simple_model(
            self.col, self.model_name, self.language_name,
            self.native_language_name)
        self.col.models.setCurrent(self.model)
        self.model['did'] = self.deck_id

    def add_dynamic_model(self):
        self.model = models.dynamic_model(self)
        self.col.models.setCurrent(self.model)
        self.model['did'] = self.deck_id

    def fix_path(self, path):
        if not os.path.isabs(path):
            return os.path.abspath(os.path.join(self.start_dir, path))
        return path

    def _start_times(self, start_time):
        """Yield a number of fudged start times."""
        count = 0
        st_ms = int(start_time)
        while (count <= fudge_timing_max_ms):
            yield start_time + pysubs.misc.Time(ms=count), st_ms + count
            count += 1

    def _start_time_stamp(self, line):
        """Return a value to use as the start time string."""
        for (st, st_ms) in self._start_times(line.start):
            if not st_ms in self.start_times_seen:
                self.start_times_seen.append(st_ms)
                return st.to_str('ass')
        else:
            # Don't shift too far (not more than 500ms). Instead
            # add a random number and hope for the best.
            return st.to_str('ass') + str(random.random()).lstrip('0.')

    def get_collection(self):
        """
        Create a new collection

        """
        # As we will add a ton of media to our collection, we have to
        # use a real directory to create the db so we can have another
        # directory to put these media files.
        self.col_path = tempfile.mkdtemp()
        db = DB(os.path.join(self.col_path, self.col_name + ".anki2"))
        _createDB(db)
        db.execute("pragma temp_store = memory")
        db.execute("pragma synchronous = off")
        # add db to col and do any remaining upgrades
        col = _Collection(db, server=False)
        col.save()
        col.lock()
        return col

    def _get_subtitles_from_single_file(self, fn):
        sta = self.fix_path(fn)
        # The nested try is from the pysubs examples,
        # https://github.com/tigr42/pysubs/blob/
        # master/examples/chapter_gen.py
        try:
            return pysubs.load(sta)
        except pysubs.exceptions.EncodingDetectionError:
            try:
                return pysubs.load(sta, self.default_sub_encoding)
            except UnicodeDecodeError:
                with open(sta) as fp:
                    subs = pysubs.SSAFile()
                    subs.from_str(unicode(
                            fp.read(), encoding=self.default_sub_encoding,
                            errors="replace"))
                return subs

    def _get_subtitles_from_files(self):
        for i, stf in enumerate(self.subtitle_files):
            if i == self.index_subtitles_index:
                # No try. Crash-and-burn if we can't load the key subtitles.
                for i_line in sorted(self._get_subtitles_from_single_file(
                        stf)):
                    line_dict = {}
                    # We always have start end end.
                    line_dict['start'] = self._start_time_stamp(i_line.start)
                    line_dict['end'] = i_line.end
                    line_dict['length'] = line_dict['end'] - line_dict['start']
                    if i_line.text:
                        line_dict['expr'] = i_line.plaintext
                        self.master_subtitles.append(line_dict)
                        if line_dict['length'] > self.longest_title:
                            self.longest_title = line_dict['length']
            else:
                try:
                    # We sort the subtitles (by start time.)  (Here
                    # and above.) Typically they are sorted, but i
                    # guess it is not guaranteed. Sorting turns the
                    # 'SSAFile' object into a list, but i guess the
                    # important difference is that you can just save
                    # SSAFiles again, which we don't want to
                    # do. Knowing it is sorted makes it easier to
                    # match the subtitles later.
                    sorted_st = sorted(
                        self._get_subtitles_from_single_file(stf))
                    # Drop empty lines now
                    sorted_st = [stl for stl in sorted_st if stl.text]
                    self.other_subtitles.append(sorted_st)
                except:
                    # We can deal with dropping this subtitles.
                    print(u"Can't load subtitles from file {0}.".format(stf))
                    pass

    def _matching_subtitle_dict(self, start_time, end_time):
        u"""
        Return the subtitle dict that best matches the star and end time

        Return that subtitle with start closest to start_time and end
        closest to end_time, if it overlaps that time span
        enough. Otherwise raise an RuntimeError.
        """
        # First a quick step. Get indices of those too late (NN >
        # end_time) or too early (NN < start_time -
        # longest_title). (We are comparing subtitle lines to times,
        # which is OK. The start time is taken.)
        pass

    def _get_subtitle_dict(self, start_time, end_time):
        u"""
        Return a subtitle dict for the given start and end time.

        This tries to get the line from master_subtitles that best
        matches the start and end time, and returns that. When there
        is no line that matches, we create a new dict and insert it
        into the master_subtitles and return it.
        """
        try:
            return self._matching_subtitle_dict(start_time, end_time)
        except RuntimeError:
            # No matching line: create a new one
            line_dict = {}
            line_dict['start'] = self._start_time_stamp(start_time)
            line_dict['end'] = end_time
            # With empty expression.
            line_dict['expr'] = u''
            line_dict['length'] = line_dict['end'] - line_dict['start']
            if line_dict['length'] > self.longest_title:
                self.longest_title = line_dict['length']
            # The bisect makes the finding where we should insert
            # faster (O(log(n))). The actual insert can’t be that fast
            # (O(n)). To be honest, i use it mostly for the coding
            # conveniance.
            # Only it doesn't work.
            bisect.insort(master_subtitles, line_dict)
            return line_dict


    def _add_line_to_subtiles(self, st_line, st_name):
        line_to_add_to = self._get_subtitle_line(
            st_line.start, st_line.end)
        pass

    def _match_titles(self):
        """
        Match the times of the subtiles

        This goes through the collection and matches other subtitles
        to the master subtitles, adding them to self.master_subtitles
        as ...
        """
        # Go through the _other_ subtitles first.
        for st in self.other_subtitles:
            for ol in st:
                st_name = "Fixme, get name"
                self._add_line_to_subtiles(ol, st_name)
                # We should
                pass

    def _fill_note(self, note, data):
        for itms in data:
            try:
                note[k] = v
            except KeyError:
                pass

    def _fill_deck(self):
        for dct in self.master_subtitles:
            note = Note(self.col, model=self.model)
            self._fill_note(note, dct)
            self.col.addNote(note)

    def process(self):
        """
        Do the main processing of the subtitles.
        """
        self._get_subtitles_from_files()
        self._match_titles()
        self._fill_deck()

    def export(self):
        ape = AnkiPackageExporter(self.col)
        ape.did = self.deck_id
        ape.includeSched = False
        ape.includeMedia = True
        ape.exportInto(self.out_file)

    def cleanup(self):
        self.col.close()
        shutil.rmtree(self.col_path)
        self.col = None
        self.model = None
