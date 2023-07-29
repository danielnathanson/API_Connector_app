from odoo import api, fields, models
import base64
import json


class ExportPostmanCollection(models.TransientModel):
    _name = 'export.postman.collection'
    _description = 'This is a wizard to export as a Postman collection'

    postman_collection = fields.Binary()

    def get_export_data_text(self, export_ids):
        item = []
        for con in self.env['api.connector'].browse(export_ids):
            request = {
                "auth": con.get_export_auth(),
                "method": con.request_type,
                "header":con.get_export_header(),
                "url": con.get_export_url(),
            }
            item_single = {
                "name": con.name,
                "request": request
            }
            item.append(item_single)
        return json.dumps({
            "info": {
            "name": "Exported Odoo API connectors",
            "version": "v2.0.0",
            "description": "This group of API connectors has been exported from Odoo",
            "schema": "https://schema.getpostman.com/json/collection/v2.0.0/"
            },
            "item": item
        })

    def download_postman_collection(self):
        selected_ids = self.env.context.get('active_ids', [])
        self.postman_collection = base64.b64encode(bytes(self.get_export_data_text(selected_ids), encoding='utf8'))
        return {
            'name': 'FEC',
            'type': 'ir.actions.act_url',
            'url': f'/web/content/?model=export.postman.collection&id={self.id}&field=postman_collection&filename=odoo_postman_collection.json&download=true',
            'target': 'self',
        }
