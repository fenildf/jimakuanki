#!/usr/bin/env python
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

import random


from anki.collection import _Collection
from anki.storage import _createDB
import os
import tempfile
import shutil
from anki.db import DB
from anki.consts import SCHEMA_VERSION
from anki.notes import Note
from anki.decks import DeckManager

from plain_japanese_model import add_plain_japanese_model


class SubtitleDecker(object):
    """
    Representation of an Anki deck containing subtitles.


    """
    def __init__(self, args):
        self.args = args
        self.col_path = ''
        self.col_name = 'collection'
        self.model = None
        self.col = self.get_collection()
        self.dm = self.col.decks
        self.deck_id = self.dm.id("Video deck")
        self.dm.select(self.deck_id)
        self.col.models.setCurrent(self.model)

    def get_collection(self):
    #def Collection(path, lock=True, server=False, sync=True):
        """
        Create a new collection in memory.

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
        self.model = add_plain_japanese_model(col)
        # add in reverse order so basic is default
        # addClozeModel(col)
        # addForwardOptionalReverse(col)
        # addForwardReverse(col)
        # addBasicModel(col)
        col.save()
        col.lock()
        return col

    def process(self):
        note = Note(self.col, model=self.model)
        note['Timestamp'] = "007"
        self.col.addNote(note)
        pass


    def rm_temp_collection(self):
        self.col.close()
        print 'should delete {}'.format(self.col_path)
        #shutil.rmtree(self.col_path)
