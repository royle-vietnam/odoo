# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import contextlib
import io

from odoo import api, fields, models, tools, _

NEW_LANG_KEY = '__new__'

class BaseLanguageExport(models.TransientModel):
    _name = "base.language.export"
    _description = 'Language Export'

    @api.model
    def _get_languages(self):
        langs = self.env['res.lang'].get_installed()
        return [(NEW_LANG_KEY, _('New Language (Empty translation template)'))] + \
               langs
   
    name = fields.Char('File Name', readonly=True)
    lang = fields.Selection(_get_languages, string='Language', required=True, default=NEW_LANG_KEY)
    format = fields.Selection([('csv','CSV File'), ('po','PO File'), ('tgz', 'TGZ Archive')],
                              string='File Format', required=True, default='po')
    modules = fields.Many2many('ir.module.module', 'rel_modules_langexport', 'wiz_id', 'module_id',
                               string='Apps To Export', domain=[('state','=','installed')])
    data = fields.Binary('File', readonly=True, attachment=False)
    state = fields.Selection([('choose', 'choose'), ('get', 'get')], # choose language or get the file
                             default='choose')

    def act_getfile(self):
        this = self[0]
        lang = this.lang if this.lang != NEW_LANG_KEY else False
        mods = sorted(this.mapped('modules.name')) or ['all']

        import glob, os
        from odoo.tools import file_open, TranslationFileReader, TranslationFileWriter
        v16_i18n_files = (
            glob.glob('/home/royle/Viindoo/source_code/odoo-16.0/addons' + '/*/*/vi.po')
            + glob.glob('/home/royle/Viindoo/source_code/odoo-16.0/addons' + '/*/*/vi_VN.po')
            + glob.glob('/home/royle/Viindoo/source_code/odoo-16.0/odoo/addons' + '/*/*/vi.po')
            + glob.glob('/home/royle/Viindoo/source_code/odoo-16.0/odoo/addons' + '/*/*/vi_VN.po')
        )
        for v16_i18n_file in v16_i18n_files:
            with open(v16_i18n_file, mode='rb') as v16_fileobj:
                v16_fileformat = os.path.splitext(v16_i18n_file)[-1][1:].lower()
                v16_fileobj.seek(0)
                v16_reader = TranslationFileReader(v16_fileobj, fileformat=v16_fileformat)

                v15_i18n_file = v16_i18n_file.replace('16.0', '15.0')
                if not os.path.exists(v15_i18n_file):
                    print('File not exists: %s: %s' % (v16_i18n_file, v15_i18n_file))
                    continue
                with open(v15_i18n_file, mode='rb') as v15_fileobj:
                    v15_fileformat = os.path.splitext(v15_i18n_file)[-1][1:].lower()
                    v15_fileobj.seek(0)
                    v15_reader = TranslationFileReader(v15_fileobj, fileformat=v15_fileformat)
                    for v16_po in v16_reader.pofile:
                        if v16_po.obsolete:
                            continue
                        for v15_po in v15_reader.pofile:
                            if v15_po.msgid == v16_po.msgid and v15_po.msgstr != v16_po.msgstr:
                                v16_po.msgstr = v15_po.msgstr

                with contextlib.closing(io.BytesIO()) as buf:
                    buf.write(str(v16_reader.pofile).encode())
                    with open(v16_i18n_file, mode='wb') as fileobj:
                        fileobj.write(buf.getvalue())

        with contextlib.closing(io.BytesIO()) as buf:
            tools.trans_export(lang, mods, buf, this.format, self._cr)
            out = base64.encodebytes(buf.getvalue())

        filename = 'new'
        if lang:
            filename = tools.get_iso_codes(lang)
        elif len(mods) == 1:
            filename = mods[0]
        extension = this.format
        if not lang and extension == 'po':
            extension = 'pot'
        name = "%s.%s" % (filename, extension)
        this.write({'state': 'get', 'data': out, 'name': name})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'base.language.export',
            'view_mode': 'form',
            'res_id': this.id,
            'views': [(False, 'form')],
            'target': 'new',
        }
