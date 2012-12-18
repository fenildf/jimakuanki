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

from .model import add_model


class SubtitleDecker(object):
    """
    Representation of an Anki deck containing subtitles.


    """
    def __init__(self, args):
        self.default_sub_encoding = 'utf-8'
        self.args = args
        self.out_file = os.path.abspath(self.args.output)
        self.col_path = ''
        self.col_name = 'collection'
        self.model = None
        self.subs = []
        self.get_subtitles_from_files()
        self.col = self.get_collection()
        self.dm = self.col.decks
        self.deck_id = self.dm.id(self.args.deck)
        self.model['did'] = self.deck_id
        self.col.models.setCurrent(self.model)

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
        self.model = add_model(col, self.args)
        col.save()
        col.lock()
        return col

    def get_subtitles_from_files(self):
        print (len(self.args.subtitles))
        for sta in self.args.subtitles:
            print ('get from {}'.format(sta))
            try:
                subs = pysubs.load(sta)
            except pysubs.exceptions.EncodingDetectionError:
                subs = pysubs.load(sta, self.default_sub_encoding)
            self.subs.append(subs)


    def process(self):
        if not self.subs:
            print ('No subtitles loaded')
            return
        time_sub = self.subs[0]
        # Need to avoid code duplication.
        if self.args.language_name:
            text_name = self.args.language_name
        elif self.args.language:
            text_name = _('Text ({0})').format(self.args.language)
        else:
            text_name = _('Text')

        for sl in time_sub:
            note = Note(self.col, model=self.model)
            note['Timestamp'] = '{start}–{end}'.format(
                start=sl.start, end=sl.end)
            note[text_name] = sl.text
            self.col.addNote(note)


    def export(self):
        ape = AnkiPackageExporter(self.col)
        ape.did = self.deck_id
        ape.includeSched = False
        ape.includeMedia = True
        ape.exportInto(self.out_file)

    def rm_temp_collection(self):
        self.col.close()
        shutil.rmtree(self.col_path)
