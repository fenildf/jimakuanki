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
import shutil
import tempfile
# NB. pysubs, not pysub
import pysubs

from anki.collection import _Collection
from anki.db import DB
from anki.exporting import AnkiPackageExporter
from anki.notes import Note
from anki.storage import _createDB
from anki.lang import _

from .model import add_simple_model


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
        self.video = None
        self.model_name = None
        self.language_name = None
        self.native_language_name = None
        self.start_dir = os.getcwd()
        self.col = self.get_collection()
        self.dm = self.col.decks


    def set_from_args(self, args):
        dirs, base = os.path.split(args.output)
        if not dirs:
            dirs = self.start_dir
        self.out_file = os.path.abspath(os.path.join(dirs, base))
        print('Will write to "{}"'.format(self.out_file))
        self.deck_name = args.deck
        self.deck_id = self.dm.id(args.deck)
        self.model_name = 'Subtitles ({})'.format(self.deck_name)
        self.language_name = args.language_name
        self.native_language_name = args.native_language_name
        self.subtitle_files = args.subtitles
        self._get_subtitles_from_files()


    def add_model(self):
        self.model = add_simple_model(self.col, self.model_name, self.language_name,
                               self.native_language_name)
        self.col.models.setCurrent(self.model)
        self.model['did'] = self.deck_id


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
        print('Subtitle files: {}'.format(self.subtitle_files))
        print (len(self.subtitle_files))
        for sta in self.subtitle_files:
            print ('get from {}'.format(sta))
            try:
                subs = pysubs.load(sta)
            except pysubs.exceptions.EncodingDetectionError:
                subs = pysubs.load(sta, self.default_sub_encoding)
            self.subtitles.append(subs)



    def process(self):
        if not self.subtitles:
            print ('No subtitles loaded')
            return
        time_sub = self.subtitles[0]
        print('Write {} lines'.format(len(time_sub)))
        # Need to avoid code duplication.
        for sl in time_sub:
            note = Note(self.col, model=self.model)
            note['Start'] = str(sl.start)
            note['End'] = str(sl.end)
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
