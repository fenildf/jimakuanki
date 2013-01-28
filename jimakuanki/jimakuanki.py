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
        self.index_subtitles = None
        self.other_subtitles = []
        self.matched_subtitles = []
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
        self.use_reading = True
        self.automatic_reading = False
        self.language_name = u'Expression'
        self.native_language_name = u'Meaning'
        # Frame rate, that infamous number that is not quite 30.
        self.fps = pysubs.misc.Time.NAMED_FPS['ntsc']
        # We fudge the timing data a bit when there is a second
        # subtitle starting on the same frame. Keep track of that.
        self.start_times_seen = []
        self.start_dir = os.getcwd()
        self.col = self.get_collection()
        self.dm = self.col.decks

    def add_simple_model(self):
        self.model = models.add_simple_model(
            self.col, self.model_name, self.language_name,
            self.native_language_name)
        self.col.models.setCurrent(self.model)
        self.model['did'] = self.deck_id

    def add_dynamic_model(self):
        self.model = models.add_dynamic_model(self)
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
            # add a random number and number and hope for the best.
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
                with open(sta, encoding=self.default_sub_encoding,
                          errors="replace") as fp:
                    subs = pysubs.SSAFile()
                    subs.from_str(fp.read())
                return subs

    def _get_subtitles_from_files(self):
        for i, stf in enumerate(self.subtitle_files):
            if i == self.index_subtitles_index:
                # No try. Crash-and-burn when we can't load the key subtitles.
                self.index_subtitles = \
                    self._get_subtitles_from_single_file(stf)
            else:
                try:
                    self.other_subtitles.append(
                        self._get_subtitles_from_single_file(stf))
                except:
                    # We can deal with dropping this subtitles.
                    print(u"Can't load subtitles from file {0}.".format(stf))
                    pass

    def _match_titles(self):
        """
        Match the times of the subtiles

        This goes through the collection and matches other subtitles
        to the index subtitles, adding them to self.matched_subtitles
        as a list of tuples.
        """
        for sl in self.index_subtitles:
            line_dict = {
                'start': self._start_time_stamp(sl),
                'end': sl.end.to_str('ass'),
                self.language_name: sl.plaintext}
            for st in self.other_subtitles:
                pass
            self.matched_subtitles.append(line_dict)

    def _fill_note(self, note, data):
        for k, v in data.items():
            try:
                note[k] = v
            except KeyError:
                pass

    def _fill_deck(self):
        for dct in self.matched_subtitles:
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
