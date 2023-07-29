from odoo import api, fields, models

class AddToURL(models.Model):
    _name = 'add.to.url'
    _description = 'Add parameters to URL'

    api_connector_id = fields.Many2one(
        comodel_name='api.connector',
        string="Parent API")
    key = fields.Char("Key")
    api_trigger_id = fields.Many2one(related='api_connector_id.api_trigger_id')
    trigger_model_id = fields.Many2one(related='api_trigger_id.model_id')
    static_value = fields.Char("Static Value")
    dynamic_value = fields.Many2one('ir.model.fields', string='Dynamic Value', ondelete='cascade')
    take_from_event_record = fields.Boolean(string="Take From Event Record")
