#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# connect_OET-RV_words_via_OET-LV.py
#
# Script to connect OET-RV words with OET-LV words that have word numbers.
#
# Copyright (C) 2023 Robert Hunt
# Author: Robert Hunt <Freely.Given.org@gmail.com>
# License: See gpl-3.0.txt
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Every word in the OET-LV has a word number tag suffixed to it,
    which connects it back to / aligns it with the Greek word it is translated from.

This script attempts to deduce how some of those same word are translated in the OET-RV
    and automatically connect them with the same word number tag.

It does have the potential to make wrong connections that will need to be manually fixed
        when the rest of the OET-RV words are aligned,
    but hopefully this script is relatively conservative
        so that the number of wrong alignments is not huge.
"""
from gettext import gettext as _
from tracemalloc import start
from typing import List, Tuple, Optional
from pathlib import Path
# from datetime import datetime
import logging
import re

if __name__ == '__main__':
    import sys
    sys.path.insert( 0, '../../BibleOrgSys/' )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import vPrint, fnPrint, dPrint
from BibleOrgSys.Bible import Bible
from BibleOrgSys.Internals.InternalBibleInternals import getLeadingInt
from BibleOrgSys.Reference.BibleBooksCodes import BOOKLIST_OT39, BOOKLIST_NT27, BOOKLIST_66
from BibleOrgSys.Reference.BibleOrganisationalSystems import BibleOrganisationalSystem
from BibleOrgSys.Formats.ESFMBible import ESFMBible


LAST_MODIFIED_DATE = '2023-04-03' # by RJH
SHORT_PROGRAM_NAME = "connect_OET-RV_words_via_OET-LV"
PROGRAM_NAME = "Convert OET-RV words to OET-LV word numbers"
PROGRAM_VERSION = '0.17'
PROGRAM_NAME_VERSION = '{} v{}'.format( SHORT_PROGRAM_NAME, PROGRAM_VERSION )

DEBUGGING_THIS_MODULE = False


project_folderpath = Path(__file__).parent.parent # Find folders relative to this module
FG_folderpath = project_folderpath.parent # Path to find parallel Freely-Given.org repos
# OET_LV_OT_USFM_InputFolderPath = project_folderpath.joinpath( 'intermediateTexts/auto_edited_OT_USFM/' )
OET_LV_NT_ESFM_InputFolderPath = project_folderpath.joinpath( 'intermediateTexts/auto_edited_VLT_ESFM/' )
OET_RV_ESFM_FolderPath = project_folderpath.joinpath( 'translatedTexts/ReadersVersion/' )
# assert OET_LV_OT_USFM_InputFolderPath.is_dir()
assert OET_LV_NT_ESFM_InputFolderPath.is_dir()
assert OET_RV_ESFM_FolderPath.is_dir()

# EN_SPACE = ' '
EM_SPACE = ' '
NARROW_NON_BREAK_SPACE = ' '
BACKSLASH = '\\'


class State:
    """
    A place to store some of the global stuff that needs to be passed around.
    """
    simpleNouns = ( # These are nouns that are likely to match one-to-one from the OET-LV to the OET-RV
                    #   i.e., there's really no other word for them.
        # NOTE: Some of these nouns can also be verbs -- we may need to remove those???
        # 'son' causes problems
        'ambassadors','ambassador', 'ancestors','ancestor', 'angels','angel', 'anger', 'ankles','ankle',
            'assemblies','assembly',
            'authorities','authority', 'axes','axe',
        'beginnings','beginning', 'belts','belt',
            'birth', 'blood', 'boats','boat', 'bodies','body', 'boys','boy', 'bread', 'branches','branch', 'brothers','brother',
            'bulls','bull', 'burials','burial',
        'camels','camel', 'chairs','chair', 'chariots','chariot', 'chests','chest', 'children','child',
            'cities','city', 'coats','coat', 'commands','command', 'compassion', 'councils','council', 'countries','country',
            'craftsmen','craftsman', 'crowds','crowd',
        'danger', 'darkness', 'daughters','daughter', 'days','day',
            'death', 'deceivers','deceiver',
            'donkeys','donkey', 'doors','door', 'doves','dove', 'dreams','dream', 'dyes','dye',
        'ears','ear', 'eyes','eye', 'exorcists','exorcist',
        'faces','face', 'faith', 'farmers','farmer', 'fathers','father',
            'fevers','fever',
            'fields','field', 'figs','fig', 'fingers','finger', 'fires','fire', 'fish', 'foot','feet',
            'followers','follower',
            'friends','friend', 'fruits','fruit',
        'generations','generation', 'gifts','gift', 'girls','girl', 'goats','goat', 'gods','god', 'gold',
            'grace', 'grains','grain', 'grapes','grape', 'greed',
        'handkerchiefs','handkerchief', 'hands','hand', 'happiness', 'hearts','heart', 'heavens','heaven', 'homes','home', 'honey', 'horses','horse', 'hours','hour', 'houses','house', 'husbands','husband',
        'idols','idol', 'ink',
        'joy', 'judgements','judgement',
        'kings','king', 'kingdoms','kingdom', 'kisses','kiss',
        'languages','language', 'leaders','leader', 'leather', 'letters','letter', 'life', 'lights','light', 'lions','lion', 'lips','lip', 'loaf','loaves', 'locusts','locust',
        'man','men', 'markets','market', 'masters','master',
            'mercy', 'messages','message', 'meetings','meeting', 'moon', 'mothers','mother', 'mouths','mouth',
        'names','name', 'nations','nation', 'nets','net', 'news', 'noises','noise',
        'officers','officer', 'officials','official',
        'peace', 'pens','pen', 'people','person', 'places','place', 'powers','power', 'prayers','prayer', 'priests','priest', 'prisons','prison', 'promises','promise'
        'rivers','river', 'roads','road', 'robes','robe', 'rocks','rock', 'ropes','rope', 'rulers','ruler',
        'sandals','sandal', 'sea',
            'scrolls','scroll',
            'servants','servant', 'services','service', 'shame', 'sheep', 'shepherds','shepherd', 'ships','ship',
            'signs','sign', 'silver', 'silversmiths','silversmith', 'sinners','sinner', 'sins','sin', 'sisters','sister', 'sky', 'slaves','slave',
            'soldiers','soldier', 'sons', 'souls','soul', 'spirits','spirit',
            'stars','star', 'stones','stone', 'streets','street', 'sun', 'swords','sword',
        'tables','table', 'teachers','teacher', 'testimonies','testimony',
            'theatres','theatre', 'things','thing', 'thrones','throne',
            'times','time', 'tombs','tomb', 'tongues','tongue', 'towns','town', 'trees','tree', 'truth',
        'vines','vine', 'visions','vision',
        'waists','waist', 'waters','water', 'ways','way',
            'weeks','week', 'wilderness', 'widows','widow', 'wife','wives', 'woman','women', 'words','word', 'workers','worker',
        'years','year',
        )
    assert len(set(simpleNouns)) == len(simpleNouns) # Check for accidental duplicates
    verbalNouns = ('confession', 'confidence',
                   'deception', 'dedication', 'discussion', 'distribution',
                   'fellowship', 'forgiveness', 'fulfilment',
                   'immersion', 'repentance')
    assert len(set(verbalNouns)) == len(verbalNouns) # Check for accidental duplicates
    # Verbs often don't work because we use the tenses differently between OET-RV and OET-LV/Greek
    simpleVerbs = ('accepted','accepting','accepts','accept',
                        'answered','answering','answers','answer',
                        'arrested','arresting','arrests','arrest',
                        'asked','asking','asks','ask', 'assembled','assembling','assembles','assemble',
                        'attracted','attracting','attracts','attract', 'attacked','attacking','attacks','attack',
                   'become','became','becomes','becoming', 'believed','believing','believes','believe',
                        'brought','bringing','brings','bring',
                        'burnt','burning','burns','burn', 'buried','burying','buries','bury',
                   'came','coming','comes','come', 'caught','catching','catches','catch',
                        'chose','choosing','chooses','choose',
                        'confessed','confessing','confesses','confess',
                        'cried','crying','cries','cry',
                   'deceived','deceiving','deceives','deceive', 'defended','defending','defends','defend', 'departed','departing','departs','depart',
                        'died','dying','dies','die', 'discussed','discussing','discusses','discuss', 'disowned','disowning','disowns','disown', 'distributed','distributing','distributes','distribute',
                        'drunk','drinking','drinks','drink',
                    'ate','eating','eats','eat', 'embraced','embracing','embraces','embrace',
                        'encouraged','encouraging','encourages','encourage', 'ended','ending','ends','end',
                        'existed','existing','exists','exist', 'extended','extending','extends','extend',
                    'feared','fearing','fears','fear',
                        'filled','filling','fills','fill',
                        'followed','following','follows','follow', 'forbidding','forbids','forbid', 'forgave','forgiven','forgiving','forgives','forgive',
                   'gathered','gathering','gathers','gather', 'gave','giving','gives','give', 'went','going','goes','go', 'greeted','greeting','greets','greet',
                   'harvested','harvesting','harvests','harvest', 'hated','hating','hates','hate',
                        'healed','healing','heals','heal', 'helped','helping','helps','help', 'heard','hearing','hears','hear',
                        'honoured','honouring','honours','honour',
                   'imitated','imitating','imitates','imitate', 'immersed','immersing','immerses','immerse',
                   'judged','judging','judges','judge',
                   'kept','keeping','keeps','keep', 'killed','killing','kills','kill', 'knew','known','knowing','knows','know',
                   'learnt','learning','learns','learn',
                        'listened','listening','listens','listen', 'lived','living','lives','live', 'looked','looking','looks','look', 'loved','loving','loves','love',
                   'magnified','magnifying','magnifies','magnify',
                   'obeyed','obeying','obeys','obey',
                   'passed','passing','passes','pass', 'persuaded','persuading','persuades','persuade',
                        'practiced','practicing','practices','practice', 'praised','praising','praises','praise', 'promised','promising','promises','promise',
                        'purified','purifying','purifies','purify',
                   'raged','raging','rages','rage', 'raised','raising','raises','raise',
                        'received','receiving','receives','receive', 'recognised','recognising','recognises','recognise', 'recovered','recovering','recovers','recover',
                            'released','releasing','releases','release',
                            'remained','remaining','remains','remain', 'reminded','reminding','reminds','remind', 'removed','removing','removes','remove',
                            'reported','reporting','reports','report',
                            'requested','requesting','requests','request',
                            'respected','respecting','respects','respect', 'restrained','restraining','restrains','restrain',
                        'ran','running','runs','run',
                   'sailed','sailing','sails','sail', 'said','saying','says','say', 'saved','saving','saves','save',
                        'seated','seating','seats','seat', 'seduced','seducing','seduces','seduce', 'saw','seeing','seen','sees','see', 'sent','sending','sends','send', 'served','serving','serves','serve',
                        'shook','shaken','shaking','shakes','shake', 'shared','sharing','shares','share', 'shone','shining','shines','shine',
                        'sat','sitting','sits','sit',
                        'spoke','spoken','speaking','speaks','speak',
                        'stayed','staying','stays','stay',
                        'summoned','summoning','summons','summon', 'supported','supporting','supports','support',
                   'took','taking','takes','take', 'talked','talking','talks','talk',
                        'testified','testifying','testifies','testify',
                        'thought','thinking','thinks','think', 'threw','throwing','throws','throw',
                        'touched','touching','touches','touch',
                        'travelled','travelling','travels','travel', 'turned','turning','turns','turn',
                   'united','uniting','unites','unite', 'untied','untying','unties','untie'
                   'walked','walking','walks','walk', 'wanted','wanting','wants','want', 'warned','warning','warns','warn', 'watched','watching','watches','watch',
                        'withdrew','withdrawing','withdraws','withdraw', 'withered','withering','withers','wither',
                        'wrote','written','writing','writes','write',
                   'yelled','yelling','yells','yell',
                   )
    assert len(set(simpleVerbs)) == len(simpleVerbs), [x for x in simpleVerbs if simpleVerbs.count(x)>1 ] # Check for accidental duplicates
    simpleAdverbs = ('quickly', 'immediately', 'loudly', 'suddenly',)
    assert len(set(simpleAdverbs)) == len(simpleAdverbs) # Check for accidental duplicates
    simpleAdjectives = ('alive', 'angry', 'bad', 'big', 'bitter',
                        'clean', 'cold',
                        'dangerous', 'dead', 'disobedient', 'entire', 'evil',
                        'female', 'foolish', 'foreign', 'friendly', 'godly', 'good', 'happy',
                        'impossible',
                        'large', 'little', 'local', 'loud', 'male', 'naked',
                        'obedient', 'opposite', 'possible', 'sad', 'same', 'sick', 'small', 'sudden', 'sweet',
                        'whole', 'wounded')
    assert len(set(simpleAdjectives)) == len(simpleAdjectives) # Check for accidental duplicates
    # Don't use 'one' below because it has other meanings
    simpleNumbers = ('two','three','four','five','six','seven','eight','nine',
                     'ten','eleven','twelve','thirteen','fourteen','fifteen','sixteen','seventeen','eighteen','nineteen',
                     'twenty','thirty','forty','fifty','sixty','seventy','eighty','ninety',
                     'none')
    assert len(set(simpleNumbers)) == len(simpleNumbers) # Check for accidental duplicates
    pronouns = ('he','she','it', 'him','her','its', 'you','we','they', 'your','our','their',
                'himself','herself','itself', 'yourself','yourselves', 'ourselves', 'themselves',
                'everyone')
    assert len(set(pronouns)) == len(pronouns) # Check for accidental duplicates
    # We don't expect connectors to work very well
    connectors = ('and', 'but')
    assert len(set(connectors)) == len(connectors) # Check for accidental duplicates
    simpleWords = simpleNouns + verbalNouns + simpleVerbs + simpleAdverbs+ simpleAdjectives  + simpleNumbers + pronouns + connectors
    # assert len(set(simpleWords)) == len(simpleWords) # Check for accidental duplicates -- but may be overlaps, e.g., love is a verb and a noun
# end of State class

state = State()


def main():
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # global genericBookList
    # genericBibleOrganisationalSystem = BibleOrganisationalSystem( 'GENERIC-KJV-ENG' )
    # genericBookList = genericBibleOrganisationalSystem.getBookList()

    # Load the OET-RV
    rv = ESFMBible( OET_RV_ESFM_FolderPath, givenAbbreviation='OET-RV' )
    rv.loadAuxilliaryFiles = True
    rv.loadBooks() # So we can iterate through them all later
    rv.lookForAuxilliaryFilenames()
    dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{rv=}")

    # Load the OET-LV
    lv = ESFMBible( OET_LV_NT_ESFM_InputFolderPath, givenAbbreviation='OET-LV' )
    lv.loadAuxilliaryFiles = True
    lv.loadBooks() # So we can iterate through them all later
    lv.lookForAuxilliaryFilenames()
    dPrint( 'verbose', DEBUGGING_THIS_MODULE, f"{lv=}")

    # Connect linked words in the OET-LV to the OET-RV
    connect_OET_RV( rv, lv )
# end of connect_OET-RV_words_via_OET-LV.main


def connect_OET_RV( rv, lv ):
    """
    Firstly, load the OET-LV wordtable.
        Loads into state.tableHeaderList and state.wordTable.

    Then connect linked words in the OET-LV to the OET-RV.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"connect_OET_RV( {rv}, {lv} )" )

    # Go through books chapters and verses
    totalSimpleListedAdds = totalProperNounAdds = totalFirstPartMatchedAdds = 0
    for BBB,bookObject in lv.books.items():
        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Processing connect words for OET {BBB}…" )

        bookSimpleListedAdds = bookProperNounAdds = booksFirstPartMatchedAdds = 0
        wordFileName = bookObject.ESFMWordTableFilename
        if wordFileName:
            assert wordFileName.endswith( '.tsv' )
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Found ESFMBible filename '{wordFileName}' for {lv.abbreviation} {BBB}" )
            if lv.ESFMWordTables[wordFileName]:
                vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Found ESFMBible loaded '{wordFileName}' word link lines: {len(lv.ESFMWordTables[wordFileName]):,}" )
            else:
                vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  No word links loaded yet for '{wordFileName}'" )
            if lv.ESFMWordTables[wordFileName] is None:
                with open( OET_LV_NT_ESFM_InputFolderPath.joinpath(wordFileName), 'rt', encoding='UTF-8' ) as wordFile:
                    lv.ESFMWordTables[wordFileName] = wordFile.read().split( '\n' )
                vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  connect_OET_RV loaded {len(lv.ESFMWordTables[wordFileName]):,} total rows from {wordFileName}" )
                dPrint( 'Info', DEBUGGING_THIS_MODULE, f"  connect_OET_RV loaded column names were: ({len(lv.ESFMWordTables[wordFileName][0])}) {lv.ESFMWordTables[wordFileName][0]}" )
        state.wordTable = [row.split('\t') for row in lv.ESFMWordTables[wordFileName]]
        state.tableHeaderList = state.wordTable[0]

        rvESFMFilename = f'OET-RV_{BBB}.ESFM'
        rvESFMFilepath = OET_RV_ESFM_FolderPath.joinpath( rvESFMFilename )
        with open( rvESFMFilepath, 'rt', encoding='UTF-8' ) as esfmFile:
            state.rvESFMText = esfmFile.read() # We keep the original (for later comparison)
            state.rvESFMLines = state.rvESFMText.split( '\n' )

        numChapters = lv.getNumChapters( BBB )
        if numChapters >= 1:
            for c in range( 1, numChapters+1 ):
                vPrint( 'Info', DEBUGGING_THIS_MODULE, f"      Connecting words for {BBB} {c}…" )
                numVerses = lv.getNumVerses( BBB, c )
                if numVerses is None: # something unusual
                    logging.critical( f"connect_OET_RV: no verses found for OET-LV {BBB} {c}" )
                    continue
                for v in range( 1, numVerses+1 ):
                    try:
                        rvVerseEntryList, _rvCcontextList = rv.getContextVerseData( (BBB, str(c), str(v)) )
                        lvVerseEntryList, _lvCcontextList = lv.getContextVerseData( (BBB, str(c), str(v)) )
                    except KeyError:
                        logging.critical( f"Seems we have no {BBB} {c}:{v} -- versification issue?" )
                        continue
                    # dPrint( 'Info', DEBUGGING_THIS_MODULE, f"RV entries: ({len(rvVerseEntryList)}) {rvVerseEntryList}")
                    # dPrint( 'Info', DEBUGGING_THIS_MODULE, f"LV entries: ({len(lvVerseEntryList)}) {lvVerseEntryList}")
                    numSimpleListedAdds, numProperNounAdds, numFirstPartMatchedAdds = connect_OET_RV_Verse( BBB, c, v, rvVerseEntryList, lvVerseEntryList ) # updates state.rvESFMLines
                    bookSimpleListedAdds += numSimpleListedAdds
                    bookProperNounAdds += numProperNounAdds
                    booksFirstPartMatchedAdds += numFirstPartMatchedAdds
        else:
            dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"connect_OET_RV {BBB} has {numChapters} chapters!!!" )
            assert BBB in ('INT','FRT',)

        newESFMtext = '\n'.join( state.rvESFMLines )
        if newESFMtext != state.rvESFMText:
            dPrint( 'Info', DEBUGGING_THIS_MODULE, f"{BBB} ESFM text has changed {len(state.rvESFMText):,} -> {len(newESFMtext):,}" )
            illegalWordLinkRegex1 = re.compile( '[0-9]¦' ) # Has digits BEFORE the broken pipe
            assert not illegalWordLinkRegex1.search( newESFMtext), f"illegalWordLinkRegex1 failed before saving {BBB}" # Don't want double-ups of wordlink numbers
            illegalWordLinkRegex2 = re.compile( '¦[1-9][0-9]{0,5}[a-z]' ) # Has letters AFTER the wordlink number
            assert not illegalWordLinkRegex2.search( newESFMtext), f"illegalWordLinkRegex2 failed before saving {BBB}" # Don't want double-ups of wordlink numbers
            with open( rvESFMFilepath, 'wt', encoding='UTF-8' ) as esfmFile:
                esfmFile.write( newESFMtext )
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  Did {bookSimpleListedAdds:,} simple listed adds and {bookProperNounAdds:,} proper noun adds for {BBB}." )
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"    Saved OET-RV {BBB} {len(newESFMtext):,} bytes to {rvESFMFilepath}" )
        else:
            # assert bookSimpleListedAdds == bookProperNounAdds == 0
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    No changes made to OET-RV {BBB}." )
        totalSimpleListedAdds += bookSimpleListedAdds
        totalProperNounAdds += bookProperNounAdds
        totalFirstPartMatchedAdds += booksFirstPartMatchedAdds

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  Did total of {totalSimpleListedAdds:,} simple listed adds, {totalProperNounAdds:,} proper noun adds, and {totalFirstPartMatchedAdds:,} first part adds." )
# end of connect_OET-RV_words_via_OET-LV.connect_OET_RV


def connect_OET_RV_Verse( BBB:str, c:int,v:int, rvEntryList, lvEntryList ) -> Tuple[int,int,int]:
    """
    Some undocumented documentation of the GlossCaps column from state.wordTable:
        ●    U – lexical entry capitalized
        ●    W – proper noun
        ●    G – reference to deity
        ●    P – paragraph boundary
        ●    S – start of sentence
        ●    D – quoted dialog
        ●    V – vocative title
        ●    B – Biblical quotation
        ●    R – other quotation
        ●    T – translated words
        ●    N – nomina sacra (our addition)

        ●    h – partial word capitalized
        ●    n – named but not proper name
        ●    b – incorporated Biblical quotation
        ●    c – continuation of quotation
        ●    e – emphasized words (scare quotes)
    The lowercase letters mark other significant places where the words are not normally capitalized.
    """
    # fnPrint( DEBUGGING_THIS_MODULE, f"connect_OET_RV( {BBB} {c}:{v} {len(rvEntryList)}, {len(lvEntryList)} )" )

    rvText = ''
    for rvEntry in rvEntryList:
        rvMarker, rvRest = rvEntry.getMarker(), rvEntry.getCleanText()
        # print( f"OET-RV {BBB} {c}:{v} {rvMarker}='{rvRest}'")
        if rvMarker in ('v~','p~'):
            rvText = f"{rvText}{' ' if rvText else ''}{rvRest}"
    lvText = ''
    for lvEntry in lvEntryList:
        lvMarker,lvRest = lvEntry.getMarker(), lvEntry.getCleanText()
        if lvMarker in ('v~','p~'):
            lvText = f"{lvText}{' ' if lvText else ''}{lvRest.replace('+','')}"
    if not rvText or not lvText: return 0, 0, 0
    rvAdjText = rvText.replace('≈','').replace('…','') \
                .replace('.','').replace(',','').replace(':','').replace(';','').replace('?','').replace('!','').replace('—',' ') \
                .replace( '(', '').replace( ')', '' ) \
                .replace( '“', '' ).replace( '”', '' ).replace( '', '' ).replace( '’', '') \
                .replace('  ',' ').strip()
    lvAdjText = lvText.replace('XX/_',' ').replace('_',' ').replace('Bēyt ','Bēyt_') \
                .replace('XX/(>',' ') \
                .replace('0/','0 ').replace('1/','1 ').replace('2/','2 ').replace('3/','3 ').replace('4/','4 ').replace('5/','5 ').replace('6/','6 ').replace('7/','7 ').replace('8/','8 ').replace('9/','9 ') \
                .replace('.','').replace(',','').replace(':','').replace(';','').replace('?','').replace('!','') \
                .replace( '(', '').replace( ')', '' ) \
                .replace('   ',' ').replace('  ',' ').strip()
    if lvAdjText.startswith( '/' ): lvAdjText = lvAdjText[1:]
    # print( f"({len(rvAdjText)}) {rvAdjText=}")
    # print( f"({len(lvAdjText)}) {lvAdjText=}")
    if not rvAdjText or not lvAdjText: return 0, 0, 0

    lvWords = lvAdjText.split( ' ' )
    rvWords = rvAdjText.split( ' ' )
    # print( f"({len(rvWords)}) {rvWords=}")
    # print( f"({len(lvWords)}) {lvWords=}")
    assert lvWords
    # if 0: # Mostly works but a couple of exceptions
    #     badIx = None
    #     for ix,lvWord in enumerate( lvWords ):
    #         if lvWord == 'Galilaia': continue # These two bad lines are from 2 Ti NOT Galilaia TODO
    #         if lvWord == 'NOT': badIx = ix
    #         else:
    #             assert lvWord, f"{lvText=} {lvAdjText=}"
    #             assert lvWord.count( '¦' ) == 1, f"{BBB} {c}:{v} {lvWord=}" # Check that we haven't been retagging already tagged RV words
    #     if badIx is not None: lvWords.pop( badIx )

    assert rvWords
    for rvWord in rvWords:
        assert rvWord, f"{rvText=} {rvAdjText=}"
        assert rvWord.count( '¦' ) <= 1 # Check that we haven't been retagging already tagged RV words
    numSimpleListedAdds = matchOurListedSimpleWords( BBB, c,v, rvWords, lvWords )

    # Now get the uppercase words
    rvUpperWords = [rvWord for rvWord in rvWords if rvWord[0].isupper()]
    lvUpperWords = [lvWord for lvWord in lvWords if lvWord[0].isupper()]
    # print( f"'{rvText=}' '{lvText=}'" )

    if lvText[0].isupper(): # Try to determine why the first word was capitalised
        # print( f"{lvUpperWords=} from {lvText=}")
        firstLVUpperWord, firstLVUpperNumber = lvUpperWords[0].split( '¦' )
        rowForFirstLVUpperWord = state.wordTable[int(firstLVUpperNumber)]
        assert state.tableHeaderList.index( 'GlossCaps' ) == 3
        firstLVUpperWordCapsFlags = rowForFirstLVUpperWord[3]
        # print( f"{firstLVUpperWordCapsFlags=} from {rowForFirstLVUpperWord=}" )
        if 'G' not in firstLVUpperWordCapsFlags and 'W' not in firstLVUpperWordCapsFlags and firstLVUpperWord!='I':
            # print( f"Removing first LV Uppercase word: '{lvUpperWords[0]}' with '{firstLVUpperWordCapsFlags}'")
            lvUpperWords.pop(0) # Throw away the first word because it might just be capitalised for being at the beginning of the sentence.
    # if rvText[0].isupper():
    #   rvUpperWords.pop(0) # Throw away the first word because it might just be capitalised for being at the beginning of the sentence.
    # print( f"({len(rvUpperWords)}) {rvUpperWords=}")
    # print( f"({len(lvUpperWords)}) {lvUpperWords=}")
    numProperNounAdds = matchProperNouns( BBB, c,v, rvUpperWords, lvUpperWords ) if rvUpperWords and lvUpperWords else 0

    numFirstPartMatchedWords = matchWordsFirstParts( BBB, c,v, rvWords, lvWords )

    return numSimpleListedAdds, numProperNounAdds, numFirstPartMatchedWords
# end of connect_OET-RV_words_via_OET-LV.connect_OET_RV_Verse


CNTR_ROLE_NAME_DICT = {'N':'noun', 'S':'substantive adjective', 'A':'adjective', 'E':'determiner/case-marker', 'R':'pronoun',
                  'V':'verb', 'I':'interjection', 'P':'preposition', 'D':'adverb', 'C':'conjunction', 'T':'particle'}
CNTR_MOOD_NAME_DICT = {'I':'indicative', 'M':'imperative', 'S':'subjunctive',
            'O':'optative', 'N':'infinitive', 'P':'participle', 'e':'e'}
CNTR_TENSE_NAME_DICT = {'P':'present', 'I':'imperfect', 'F':'future', 'A':'aorist', 'E':'perfect', 'L':'pluperfect', 'U':'U', 'e':'e'}
CNTR_VOICE_NAME_DICT = {'A':'active', 'M':'middle', 'P':'passive', 'p':'p', 'm':'m', 'a':'a'}
CNTR_PERSON_NAME_DICT = {'1':'1st', '2':'2nd', '3':'3rd', 'g':'g'}
CNTR_CASE_NAME_DICT = {'N':'nominative', 'G':'genitive', 'D':'dative', 'A':'accusative', 'V':'vocative', 'g':'g', 'n':'n', 'a':'a', 'd':'d', 'v':'v', 'U':'U'}
CNTR_GENDER_NAME_DICT = {'M':'masculine', 'F':'feminine', 'N':'neuter', 'm':'m', 'f':'f', 'n':'n'}
CNTR_NUMBER_NAME_DICT = {'S':'singular', 'P':'plural', 's':'s', 'p':'p'}
def matchProperNouns( BBB:str, c:int,v:int, rvCapitalisedWordList:List[str], lvCapitalisedWordList:List[str] ) -> int:
    """
    Given a list of capitalised words from OET-RV and OET-LV,
        see if we can match any proper nouns
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"matchProperNouns( {BBB} {c}:{v} {rvCapitalisedWordList}, {lvCapitalisedWordList} )" )
    assert rvCapitalisedWordList and lvCapitalisedWordList

    # But we don't want any rvWords that are already tagged
    numAdded = 0
    numRemovedRV = 0 # Extra work because we're deleting from same list that we're iterating through (a copy of)
    for rvN,rvCapitalisedWord in enumerate( rvCapitalisedWordList[:] ):
        # print( f"{BBB} {c}:{v} {rvN} {rvCapitalisedWord=} from {rvCapitalisedWordList}")
        if '¦' in rvCapitalisedWord:
            _rvCapitalisedWord, rvWordNumber = rvCapitalisedWord.split('¦')
            dPrint( 'Info', DEBUGGING_THIS_MODULE, f"  matchProperNouns( {BBB} {c}:{v} ) removing already tagged '{rvCapitalisedWord}' from RV list…")
            rvCapitalisedWordList.pop( rvN - numRemovedRV )
            numRemovedRV += 1
            numRemovedLV = 0 # Extra work because we're deleting from same list that we're iterating through (a copy of)
            for lvN,lvCapitalisedWord in enumerate( lvCapitalisedWordList[:] ):
                if lvCapitalisedWord.endswith( f'¦{rvWordNumber}' ):
                    dPrint( 'Info', DEBUGGING_THIS_MODULE, f"  matchProperNouns( {BBB} {c}:{v} ) removing already tagged '{lvCapitalisedWord}' from LV list…")
                    lvCapitalisedWordList.pop( lvN - numRemovedLV )
                    numRemovedLV += 1
    if not rvCapitalisedWordList or not lvCapitalisedWordList:
        return numAdded # nothing left to do here

    if len(rvCapitalisedWordList)==1 and len(lvCapitalisedWordList)==1: # easy case!
        assert rvCapitalisedWordList[0].replace("'",'').isalpha(), f"{rvCapitalisedWordList=}" # It might contain an apostrophe
        capitalisedNoun,wordNumber,wordRow = getLVWordRow( lvCapitalisedWordList[0] )
        wordRole = wordRow[state.tableHeaderList.index('Role')]
        dPrint( 'Info', DEBUGGING_THIS_MODULE, f"'{capitalisedNoun}' {wordRole}" )
        if wordRole == 'N': # let's assume it's a proper noun
            result = addNumberToRVWord( BBB, c,v, rvCapitalisedWordList[0], wordNumber )
            if result:
                numAdded += 1
    elif len(rvCapitalisedWordList) == len(lvCapitalisedWordList):
        dPrint( 'Info', DEBUGGING_THIS_MODULE, f"Lists are equal size ({len(rvCapitalisedWordList)})" )
        return numAdded
        for capitalisedNounPair in lvCapitalisedWordList:
            capitalisedNoun,wordNumber,wordRow = getLVWordRow( capitalisedNounPair )
            dPrint( 'Info', f"'{capitalisedNoun}' {wordRow}" )
            halt
    else:
        dPrint( 'Info', DEBUGGING_THIS_MODULE, f"Lists are different sizes {len(rvCapitalisedWordList)=} and {len(lvCapitalisedWordList)=}" )
        # for capitalisedNounPair in lvCapitalisedWordList:
        #     capitalisedNoun,wordNumber,wordRow = getLVWordRow( capitalisedNounPair )
        #     dPrint( 'Info', DEBUGGING_THIS_MODULE, f"'{capitalisedNoun}' {wordRow}" )
        #     halt
    return numAdded
# end of connect_OET-RV_words_via_OET-LV.matchProperNouns


def matchOurListedSimpleWords( BBB:str, c:int,v:int, rvWordList:List[str], lvWordList:List[str] ) -> int:
    """
    If the simple word (e.g., nouns) only occur once in the RV verse and once in the LV verse,
        we assume that we can match them, i.e., copy the wordlink numbers from the LV into the RV.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"matchOurListedSimpleWords( {BBB} {c}:{v} {rvWordList}, {lvWordList} )" )
    assert rvWordList and lvWordList

    numAdded = 0
    for simpleNoun in state.simpleWords:
        # print( f"{simpleNoun}" )
        lvIndexList = []
        for lvN,lvWord in enumerate( lvWordList ):
            # assert lvWord.isalpha(), f"'{lvWord}'" # Might contain an apostrophe
            if f'{simpleNoun}¦' in lvWord:
                lvIndexList.append( lvN )
        if not lvIndexList: continue
        # print( f"{BBB} {c}:{v} {simpleNoun=} {lvIndexList=}" )
        rvIndexList = []
        for rvN,rvWord in enumerate( rvWordList ):
            # assert rvWord.isalpha(), f"'{rvWord}'" # Might contain an apostrophe
            if rvWord == simpleNoun:
                rvIndexList.append( rvN )
        if not rvIndexList: continue

        if len(rvIndexList) != 1 or len(lvIndexList) != 1: # then I don't think we can guarantee matching the right words
            return numAdded
        assert len(rvIndexList) == len(lvIndexList), f"{BBB} {c}:{v} {simpleNoun=} {rvIndexList=} {lvIndexList=}"

        lvNumbers = []
        for lvN in lvIndexList:
            lvNoun,lvWordNumber,lvWordRow = getLVWordRow( lvWordList[lvN] )
            lvNumbers.append( lvWordNumber )
        assert len(lvNumbers) == 1 # NOT TRUE: If there's two 'camels' in the verse, we expect both to have the same word number
        for rvN in rvIndexList:
            rvNoun = rvWordList[rvN]
            dPrint( 'Info', DEBUGGING_THIS_MODULE, f"matchOurListedSimpleWords() is adding a number to RV '{rvNoun}' at {BBB} {c}:{v} {rvN=}")
            result = addNumberToRVWord( BBB, c,v, rvNoun, lvWordNumber )
            if result:
                numAdded += 1

    return numAdded
# end of connect_OET-RV_words_via_OET-LV.matchOurListedSimpleWords


def matchWordsFirstParts( BBB:str, c:int,v:int, rvWordList:List[str], lvWordList:List[str] ) -> int:
    """
    If the longish word only occurs once in the LV word list
        and a similar starting word only occurs on in the RV word list
            we assume that we can match them, i.e., copy the wordlink numbers from the LV into the RV.

    This handles tense changes, e.g., LV despising and RV despised.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"matchWordsFirstParts( {BBB} {c}:{v} {rvWordList}, {lvWordList} )" )
    assert rvWordList and lvWordList

    # Firstly make a matching list of LV words without the word numbers
    simpleLVWordList = []
    for lvWordStr in lvWordList:
        try: lvWord, lvNumber = lvWordStr.split( '¦' )
        except ValueError:
            logging.critical( f"matchWordsFirstParts failed on {lvWordStr=}" )
            lvWord = lvWordStr # One or two little mess-ups
        simpleLVWordList.append( lvWord )

    numAdded = 0
    for lvIx,lvWord in enumerate( simpleLVWordList ):
        if len(lvWord) < 5: continue # We only process longer words
        if simpleLVWordList.count( lvWord ) != 1: continue # We can't distinguish between two usages in one verse
        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"{lvWord=} {lvNumber=}" )

        lvWordStart = lvWord[:5] # Get the first 5 letters
        dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  Looking for RV '{lvWordStart}' from LV '{lvWord}'" )
        rvIndexes = []
        for rvIx,rvWord in enumerate( rvWordList ):
            if rvWord.startswith( lvWordStart ):
                dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  Found RV '{rvWord}' in {BBB} {c}:{v}")
                rvIndexes.append( rvIx )

        if len(rvIndexes) == 1: # Only one RV word starts with those same letters
            rvWord = rvWordList[rvIndexes[0]]
            if '¦' not in rvWord:
                lvWord,lvWordNumber,lvWordRow = getLVWordRow( lvWordList[lvIx] )
                dPrint( 'Info', DEBUGGING_THIS_MODULE, f"matchWordsFirstParts() is adding a number to RV '{rvWord}' from '{lvWord}' at {BBB} {c}:{v} {rvIx=}")
                result = addNumberToRVWord( BBB, c,v, rvWord, lvWordNumber )
                if result:
                    numAdded += 1
                else:
                    logging.warning( f"Got addNumberToRVWord( {BBB} {c}:{v} '{rvWord}' {lvWordNumber} ) result = {result}" )
                    # why_did_we_fail

    return numAdded
# end of connect_OET-RV_words_via_OET-LV.matchWordsFirstParts


def getLVWordRow( wordWithNumber:str ) -> Tuple[str,int,List[str]]:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"getLVWordRow( {wordWithNumber} )" )

    # print( f"{wordWithNumber=}" )
    word,wordNumber = wordWithNumber.split( '¦' )
    # assert word.isalpha(), f"Non-alpha '{word}'" # not true, e.g., from 'Yaʸsous/(Yəhōshūˊa)¦21754'
    try: wordNumber = int( wordNumber )
    except ValueError:
        logging.critical( f"getLVWordRow() got non-number '{wordNumber}' from '{wordWithNumber}'" )
        wordNumber = getLeadingInt( wordNumber )
    assert wordNumber < len( state.wordTable )
    wordRow = state.wordTable[wordNumber]
    dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"'{word}' {wordRow}" )
    return word,wordNumber,wordRow
# end of connect_OET-RV_words_via_OET-LV.getLVWordRow


def addNumberToRVWord( BBB:str, c:int,v:int, word:str, wordNumber:int ) -> bool:
    """
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"addNumberToRVWord( {BBB} {c}:{v} '{word}' {wordNumber} )" )

    C = V = None
    found = False
    for n,line in enumerate( state.rvESFMLines[:] ): # iterate through a copy
        try: marker, rest = line.split( ' ', 1 )
        except ValueError: marker, rest = line, '' # Only a marker
        dPrint( 'Info', DEBUGGING_THIS_MODULE, f"addNumberToRVWord A searching {BBB} {C}:{V} {marker}='{rest}'" )
        if marker == '\\c':
            C = int(rest)
            if C > c: return False # Gone too far
        elif marker == '\\v':
            dPrint( 'Info', DEBUGGING_THIS_MODULE, f"addNumberToRVWord B searching {BBB} {C}:{V} {marker}='{rest}'")
            Vstr, rest = rest.split( ' ', 1 )
            try: V = int(Vstr)
            except ValueError: # might be a range like 21-22
                V = int(Vstr.split('-',1)[0])
            found = C==c and V==v
        if found:
            wholeWordRegexStr = f'\\b{word}\\b'
            allWordMatches = [match for match in re.finditer( wholeWordRegexStr, line )]
            if len(allWordMatches) == 1:
                match = allWordMatches[0]
                dPrint( 'Info', DEBUGGING_THIS_MODULE, type(allWordMatches), type(match), match )
                assert match.group(0) == word
                dPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Found {word=} {line=}" )
                try:
                    if line[match.end()] != '¦': # next character after word
                        state.rvESFMLines[n] = f'{line[:match.start()]}{word}¦{wordNumber}{line[match.end():]}'
                        # print( f"{word=} {line=}" )
                        dPrint( 'Info', DEBUGGING_THIS_MODULE, f"  addNumberToRVWord() added ¦{wordNumber} to '{word}' in OET-RV {BBB} {c}:{v}" )
                        return True
                    else:
                        logging.warning( f"Tried to append second number to {BBB} {C}:{V} {marker} '{line[match.start():match.end()]}' -> '{word}¦{wordNumber}'" )
                        # already_numbered
                        return False
                except IndexError:
                    assert line.endswith( word )
                    state.rvESFMLines[n] = f'{line}¦{wordNumber}'
                    dPrint( 'Info', DEBUGGING_THIS_MODULE, f"  addNumberToRVWord() added ¦{wordNumber} to final '{word}' in OET-RV {BBB} {c}:{v}" )
                    return True
            else:
                dPrint( 'Info', DEBUGGING_THIS_MODULE, f"  addNumberToRVWord {BBB} {c}:{v} '{word}' found {len(allWordMatches)=}" )

            # for _safetyCount in range( 4 ):
            #     match = re.search( wholeWordRegexStr, rest )
            #     if not match: break
            #     print( match )
            #     assert match.group(0) == word
            #     if rest[match.end()] != '': # next character after word
            #         rest = f'{rest[:match.start()]}{word}¦{wordNumber}{rest[:match.end():]}'
            #         print( f"{word=} {rest=}" ); halt
            # else: not_enough_loops

            # if f' {word} ' in rest: # that's quite a restrictive match
            #     dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"addNumberToRVWord() found {BBB} {C}:{V} {marker}" )
            #     # assert word in rest, f"No {word=} in {rest=}"
            #     if rest.count( word ) > 1:
            #         return False
            #     assert rest.count( word ) == 1, f"'{word}' {rest.count(word)} '{rest}'"
            #     if f' {word}¦' not in rest: # already
            #         state.rvESFMLines[n] = line.replace( word, f'{word}¦{wordNumber}' )
            #         dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  addNumberToRVWord() added ¦{wordNumber} to '{word}' in OET-RV {BBB} {c}:{v}" )
            #         return True
            #     else:
            #         logging.critical( f"addNumberToRVWord() found {BBB} {C}:{V} {marker} found ' {word}¦' already in {rest=}")
            #         oops
# end of connect_OET-RV_words_via_OET-LV.addNumberToRVWord


if __name__ == '__main__':
    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( PROGRAM_NAME, PROGRAM_VERSION )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=False )

    main()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of connect_OET-RV_words_via_OET-LV.py