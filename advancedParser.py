#!/usr/bin/env python
# -*- coding: utf-8 -*-

import AdvancedHTMLParser
import urllib
import sexmachine.detector
from textblob import TextBlob
from DateFormatter import DateFormatter

import sys, re
from textblob.exceptions import NotTranslated

reload(sys)
sys.setdefaultencoding('utf8')
'''
This service creates .scs file using wiki-url
'''


class PersonGeneratorService:

    SAVE_PATH = "/home/overlord/ostis/kb/Persons/"

    def __init__(self, wiki_url):
        self.EN_HTML = AdvancedHTMLParser.AdvancedHTMLParser()
        self.EN_HTML.parseStr(urllib.urlopen(wiki_url).read())
        try:
            self.RU_HTML = AdvancedHTMLParser.AdvancedHTMLParser()
            ru_href_container = self.EN_HTML.getElementsByClassName('interwiki-ru')[0]
            ru_url = 'https:' + ru_href_container.getChildren()[0].getAttribute('href')
            self.RU_HTML.parseStr(urllib.urlopen(ru_url).read())
            self.ru_infobox = self.RU_HTML.getElementsByClassName('infobox')[0]
        except IndexError:
            self.RU_HTML = None
            self.ru_infobox = None
        # ============================================================================
        self.en_infobox = self.EN_HTML.getElementsByClassName('infobox')[0]
        self.system_name = None
        self.full_name = {'en': None, 'ru': None}
        self.first_name = {'en': None, 'ru': None}
        self.last_name = {'en': None, 'ru': None}
        self.patronimic_name = {'en': None, 'ru': None}
        self.gender = None
        self.image_path = None
        self.image_name = None
        self.birth_date = None
        self.death_date = None
        self.alma_mater = []
        self.occupation = []

    def get_full_name(self, en_html, ru_html):
        self.full_name['en'] = en_html.getElementById('firstHeading').innerHTML
        split_en_full_name = self.full_name['en'].split(' ')
        self.system_name = '_'.join(split_en_full_name)
        self.first_name['en'] = split_en_full_name[0]
        self.last_name['en'] = ' '.join(split_en_full_name[1:])

        try:
            self.full_name['ru'] = ru_html.getElementById('firstHeading').innerHTML
            split_ru_full_name = self.full_name['ru'].split(',')
            self.last_name['ru'] = split_ru_full_name[0]
            split_ru_full_name = split_ru_full_name[1].split(' ')
            if split_ru_full_name[-1].endswith('ович') or split_ru_full_name[-1].endswith('евич')\
                or split_ru_full_name[-1].endswith('овна') or split_ru_full_name[-1].endswith('евна'):
                self.patronimic_name['ru'] = ' '.join(split_ru_full_name[-1])
                self.first_name['ru'] = ' '.join(split_ru_full_name[-2:])
            else:
                self.first_name['ru'] = ' '.join(split_ru_full_name[-1:])
            self.full_name['ru'] = ''.join(x for x in self.full_name['ru'] if x not in ',')
        except AttributeError:
            pass

    def get_image(self, infobox):
        image = infobox.getElementsByClassName('image')[0]
        for image_url_container in image.getChildren():
            image_url = image_url_container.getAttribute('src')
            image_extension = image_url.split('.')[-1]
            self.image_name = self.system_name + '.' + image_extension
            self.image_path = self.SAVE_PATH + 'content/' + self.system_name + '.' + image_extension
            urllib.urlretrieve('https:' + image_url, self.image_path)

    def get_gender(self):
        self.gender = sexmachine.detector.Detector().get_gender(self.first_name['en'])

    def get_birth_date(self, infobox):
        for _property in infobox.getChildren():
            if _property.getChildren()[0].innerHTML.startswith('Born'):
                self.birth_date = _property.getElementsByClassName('bday')[0].innerHTML
                self.birth_date = '_'.join(self.birth_date.split('-'))
                break

    def get_death_date(self, infobox):
        for _property in infobox.getChildren():
            if _property.getChildren()[0].innerHTML.startswith('Died'):
                self.death_date = _property.getElementsByClassName('dday')[0].innerHTML
                self.death_date = '_'.join(self.death_date.split('-'))
                break

    def get_alma_mater(self, infobox):

        def get_inside(arg):
            for i in arg.getChildren():
                value = re.sub(r'\([^)]*\)', '', i.innerHTML)
                if len(i.getChildren()) > 0 and len(value) > 0:
                    get_inside(i)
                elif len(value) > 0:
                    self.alma_mater.append(value)

        for _property in infobox.getChildren():
            try:
                _property.getElementsByAttr('title', 'Alma mater')[0]
                for alma_mater in _property.getChildren()[1].getChildren():
                    if len(alma_mater.getChildren()) > 0 and len(re.sub(r'\([^)]*\)', '', alma_mater.innerHTML)) > 0:
                        get_inside(alma_mater)
                    else:
                        value = re.sub(r'\([^)]*\)', '', alma_mater.innerHTML)
                        if len(value) > 0:
                            self.alma_mater.append(value)
            except IndexError:
                th = _property.getChildren()[0]
                if th.innerHTML == 'Alma mater' or th.innerHTML == 'Alma&#160;mater':
                    td = _property.getChildren()[1]
                    for i in td:
                        self.alma_mater.append(i.innerHTML)

    def get_occupation(self, infobox):
        for _property in infobox.getChildren():
            if _property.getChildren()[0].innerHTML == 'Profession':
                for occupation in _property.getChildren()[1].getChildren():
                    if len(occupation.innerHTML) > 0:
                        self.occupation.append(occupation.innerHTML.lower())
                if len(_property.getChildren()[1].getChildren()) == 0:
                    self.occupation = _property.getChildren()[1].innerHTML.lower().split(', ')
            elif _property.getChildren()[0].innerHTML == 'Occupation':
                for occupation in _property.getChildren()[1].getChildren():
                    if len(occupation.innerHTML) > 0:
                        self.occupation.append(occupation.innerHTML.lower())
                if len(_property.getChildren()[1].getChildren()) == 0:
                    self.occupation = _property.getChildren()[1].innerHTML.lower().split(', ')
                    
    def generate_scs_file(self):
        scs_file = open(self.SAVE_PATH + self.system_name + '.scs', 'w')
        self.write_name(scs_file)
        self.write_gender(scs_file)
        if self.image_name is not None:
            self.write_person_image(scs_file)
        if self.birth_date is not None:
            self.write_birth_date(scs_file)
        if self.death_date is not None:
            self.write_death_date(scs_file)
        if len(self.alma_mater) > 0:
            self.write_alma_mater(scs_file)
        if len(self.occupation) > 0:
            self.write_occupation(scs_file)
        self.write_main_statement(scs_file)

    def write_name(self, scs_file):
        # full name
        scs_file.write(self.system_name + ' => nrel_main_idtf:' + '\n')
        scs_file.write('   [' + self.full_name['en'] + '](* <- lang_en;; *);;' + '\n')
        if self.full_name['ru'] is not None:
            scs_file.write(self.system_name + ' => nrel_main_idtf:' + '\n')
            scs_file.write('   [' + self.full_name['ru'] + '](* <- lang_ru;; *);;' + '\n')
        # first name
        scs_file.write(self.system_name + ' => nrel_first_name:' + '\n')
        scs_file.write('    name_' + self.first_name['en'] + '(*' + '\n')
        scs_file.write(2*'    ' + ' => nrel_main_idtf: [' + self.first_name['en'] + '](* <- lang_en;; *);;' + '\n')
        if self.first_name['ru'] is not None:
            scs_file.write(2*'    ' + ' => nrel_main_idtf: [' + self.first_name['ru'] + '](* <- lang_ru;; *);;' + '\n')
        scs_file.write(2*'    ' + '*);;' + '\n')
        # last name
        scs_file.write(self.system_name + ' => nrel_surname:' + '\n')
        scs_file.write('    surname_' + self.last_name['en'] + '(*' + '\n')
        scs_file.write(2*'    ' + ' => nrel_main_idtf: [' + self.last_name['en'] + '](* <- lang_en;; *);;' + '\n')
        if self.last_name['ru'] is not None:
            scs_file.write(2*'    ' + ' => nrel_main_idtf: [' + self.last_name['ru'] + '](* <- lang_ru;; *);;' + '\n')
        scs_file.write(2*'    ' + '*);;' + '\n')

    def write_person_image(self, scs_file):
        scs_file.write(self.system_name + ' <- rrel_key_sc_element:' + '\n')
        scs_file.write('    ' + self.system_name + '_Image (*' + '\n')
        scs_file.write('    ' + '=> nrel_main_idtf:' + '\n')
        scs_file.write('    ' + ' [Image of ' + self.full_name['en'] + '](* <- lang_en;; *);;' + '\n')
        if self.full_name['ru'] is not None:
            scs_file.write('    ' + '=> nrel_main_idtf:' + '\n')
            scs_file.write('    ' + ' [' + self.full_name['ru'] + ' - Изображение](* <- lang_ru;; *);;' + '\n')
        scs_file.write('    ' + '<-sc_illustration;;' + '\n')
        scs_file.write('    ' + '<= nrel_sc_text_translation: ...' + '\n')
        scs_file.write(2*'    ' + '(*' + '\n')
        scs_file.write(2*'    ' + '->rrel_example:' + '"file://content/' + self.image_name + '"(* <-image;; *);;' + '\n')
        scs_file.write(2*'    ' + '*);;' + '\n')
        scs_file.write('*);;' + '\n')

    def write_gender(self, scs_file):
        scs_file.write(self.system_name + ' <- concept_' + self.gender + ';;' + '\n')

    def write_birth_date(self, scs_file):
        date_formatter = DateFormatter()
        split_date = self.birth_date.split('_')
        day = split_date[2]
        en_month = date_formatter.get_str_month(split_date[1], 'en')
        ru_month = date_formatter.get_str_month(split_date[1], 'ru')
        year = split_date[0]
        scs_file.write(self.system_name + ' => nrel_date_of_birth: ' + self.birth_date + '\n')
        scs_file.write('    (*' + '\n')
        scs_file.write('    => nrel_main_idtf:' + '\n')
        scs_file.write('    [' + en_month + ' ' + day + ', ' + year + '](* <- lang_en;; *);' + '\n')
        scs_file.write('    [' + day + ' ' + ru_month + ', ' + year + '](* <- lang_ru;; *);;' + '\n')
        scs_file.write('    *);;' + '\n')

    def write_death_date(self, scs_file):
        date_formatter = DateFormatter()
        split_date = self.death_date.split('_')
        day = split_date[2]
        en_month = date_formatter.get_str_month(split_date[1], 'en')
        ru_month = date_formatter.get_str_month(split_date[1], 'ru')
        year = split_date[0]
        scs_file.write(self.system_name + ' => nrel_date_of_death: ' + self.death_date + '\n')
        scs_file.write('    (*' + '\n')
        scs_file.write('    => nrel_main_idtf:' + '\n')
        scs_file.write('    [' + en_month + ' ' + day + ', ' + year + '](* <- lang_en;; *);' + '\n')
        scs_file.write('    [' + day + ' ' + ru_month + ', ' + year + '](* <- lang_ru;; *);;' + '\n')
        scs_file.write('    *);;' + '\n')

    def write_alma_mater(self, scs_file):
        for i in self.alma_mater:
            print i, type(i)
            blob = TextBlob(i)
            try:
                ru_i = str(blob.translate('en', 'ru'))
                '_'.join(i.split(' '))
                scs_file.write(self.system_name + ' <= nrel_student: ' + '\n')
                scs_file.write('    ' + '_'.join(i.split(' ')) + '\n')
                scs_file.write(2*'    ' + '(*' + '\n')
                scs_file.write(2*'    ' + '=> nrel_main_idtf:' + '\n')
                scs_file.write(3*'    ' + '[' + i + '](* <- lang_en;; *);' + '\n')
                scs_file.write(3*'    ' + '[' + ru_i + '](* <- lang_ru;; *);;' + '\n')
                scs_file.write(2*'    ' + '*);;')
                scs_file.write('\n')
            except NotTranslated:
                pass

    def write_occupation(self, scs_file):
        scs_file.write(self.system_name + ' <- ' + '\n')
        for i in self.occupation:
            blob = TextBlob(i)
            try:
                ru_i = str(blob.translate('en', 'ru')).lower()
                scs_file.write('    ' + '_'.join(i.split(' ')).lower() + '\n')
                scs_file.write(2*'    ' + '(*' + '\n')
                scs_file.write(2*'    ' + '=> nrel_main_idtf:' + '\n')
                scs_file.write(3*'    ' + '[' + i.lower() + '](* <- lang_en;; *);' + '\n')
                scs_file.write(3*'    ' + '[' + ru_i + '](* <- lang_ru;; *);;' + '\n')
                scs_file.write(2*'    ' + '*);')
                if self.occupation.index(i) == len(self.occupation) - 1:
                    scs_file.write(';')
                scs_file.write('\n')
            except NotTranslated:
                pass

    def write_main_statement(self, scs_file):
        a = self.RU_HTML.getElementById('mw-content-text')

        for child in a.getChildren():
            def get_rid_of_parentheses(text, first_symbol, last_symbol):
                split_text = text.split(last_symbol, 1)
                subtext = split_text[0].rsplit(first_symbol, 1)
                return subtext[0]+split_text[1]

            if child.getTagName() == 'p':
                text = child.innerHTML
                while True:
                    try:
                        text = get_rid_of_parentheses(text, '(', ')')
                    except IndexError:
                        break
                while True:
                    try:
                        text = get_rid_of_parentheses(text, '<', '>')
                    except IndexError:
                        break
                while True:
                    try:
                        text = get_rid_of_parentheses(text, '[', ']')
                    except IndexError:
                        break
                text = text.replace('́', '')
                text = text.replace('&#160;', '')

                print text

                scs_file.write(self.system_name + ' <- rrel_key_sc_element:' + '\n')
                scs_file.write('    ' + self.system_name + '_Main_Information (*' + '\n')
                scs_file.write('    ' + '=> nrel_main_idtf:' + '\n')
                scs_file.write('    ' + ' [' + self.full_name['en'] + ' - Main Information](* <- lang_en;; *);;' + '\n')
                if self.full_name['ru'] is not None:
                    scs_file.write('    ' + '=> nrel_main_idtf:' + '\n')
                    scs_file.write('    ' + ' [' + self.full_name['ru'] + ' - Основная информация](* <- lang_ru;; *);;' + '\n')
                scs_file.write('    ' + '<-sc_statement;;' + '\n')
                scs_file.write('    ' + '<= nrel_sc_text_translation: ...' + '\n')
                scs_file.write(2*'    ' + '(*' + '\n')
                scs_file.write(2*'    ' + '->rrel_example: [' + text + '](* <-lang_ru;; *);;' + '\n')
                scs_file.write(2*'    ' + '*);;' + '\n')
                scs_file.write('*);;' + '\n')
                break

person = PersonGeneratorService("https://en.wikipedia.org/wiki/Stephen_Hawking")
person.get_full_name(person.EN_HTML, person.RU_HTML)
person.get_image(person.en_infobox)
person.get_gender()
person.get_birth_date(person.en_infobox)
person.get_death_date(person.en_infobox)
person.get_alma_mater(person.en_infobox)
person.get_occupation(person.en_infobox)
person.generate_scs_file()

#re.sub(r'\([^)]*\)', '', i.innerHTML)