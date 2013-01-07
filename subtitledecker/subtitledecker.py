# -*- mode: python ; coding: utf-8 -*-
#
# Copyright © 2012 Roland Sieker <ospalh@gmail.com>
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
import pysubs
import random
import shutil
import tempfile


from libanki.collection import _Collection
from libanki.db import DB
from libanki.exporting import AnkiPackageExporter
from libanki.notes import Note
from libanki.storage import _createDB
from libanki.lang import _

from .model import add_simple_model

# How many times will we try to
fudge_timing_max_frames = 10


class SubtitleDecker(object):
    """
    Representation of an Anki deck containing subtitles.

    This is a representation of an Anki2 spaced repetition system
    flashcard collection. The collection can be automatically filled
    with a deck of flashcards of video clips and subtitles.

    Workflow:
    * Create SubtitleDecker object
    * Add a video file
    * Add subtitles, either as extra files or pointing to subtitles
      from the video files.
    * Set up other parameters such as languages, deck and output file names.
    *
    """
    def __init__(self):
        self.default_sub_encoding = 'utf-8'
        self.col_path = ''
        self.col_name = 'collection'
        self.model = None
        self.out_file = ''
        self.deck_id = None
        self.subtitle_files = []
        self.subtitles = []
        self.time_sub_index = 0
        self.video = None
        self.model_name = None
        self.language_name = 'Text'
        self.native_language_name = 'Text (native)'
        # Frame rate, that infamous number that is not quite 30.
        self.fps = pysubs.misc.Time.NAMED_FPS['ntsc']
        # We fudge the timing data a bit when there is a second
        # subtitle starting on the same frame. Keep track of that.
        self.start_frames_seen = []
        self.start_dir = os.getcwd()
        self.col = self.get_collection()
        self.dm = self.col.decks

    def add_model(self):
        self.model = add_simple_model(
            self.col, self.model_name, self.language_name,
            self.native_language_name)
        self.col.models.setCurrent(self.model)
        self.model['did'] = self.deck_id

    def fix_path(self, path):
        if not os.path.isabs(path):
            return os.path.abspath(os.path.join(self.start_dir, path))
        return path

    def _add_frames(self, time, frames):
        """Add n frame length to a pysubs time."""
        return pysubs.misc.Time(
            fps=self.fps, frame=time.to_frame(fps=self.fps) + frames)

    def _start_times(self, start_time):
        """Yield a number of fudged start times."""
        count = 0
        while (count <= fudge_timing_max_frames):
            yield self._add_frames(start_time, count)
            count += 1

    def _start_time_stamp(self, line):
        """Return a value to use as the start time string."""
        for st in self._start_times(line.start):
            fr = st.to_frame(fps=self.fps)
            if not fr in self.start_frames_seen:
                self.start_frames_seen.append(fr)
                return st.to_str('ass')
        else:
            # Don't shift too far (not more than 10 frames). Instead
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

    def _get_subtitles_from_files(self):
        for sta in self.subtitle_files:
            sta = self.fix_path(sta)
            # The nested try is from the pysubs examples,
            # https://github.com/tigr42/pysubs/blob/\
            # master/examples/chapter_gen.py
            try:
                subs = pysubs.load(sta)
            except pysubs.exceptions.EncodingDetectionError:
                try:
                    subs = pysubs.load(sta, self.default_sub_encoding)
                except UnicodeDecodeError:
                    with open(sta, encoding=self.default_sub_encoding,
                              errors="replace") as fp:
                        subs = pysubs.SSAFile()
                        subs.from_str(fp.read())
            self.subtitles.append(subs)

    def process(self):
        self._get_subtitles_from_files()
        if not self.subtitles:
            print('No subtitles loaded')
            return
        time_sub = self.subtitles[self.time_sub_index]
        # Need to avoid code duplication.
        for sl in time_sub:
            note = Note(self.col, model=self.model)
            note['Start'] = self._start_time_stamp(sl)
            note['End'] = sl.end.to_str('ass')
            note[self.language_name] = sl.plaintext
            self.col.addNote(note)

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
