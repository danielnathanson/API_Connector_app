from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class ResponseKeyValue(models.Model):
    _name = 'response.key.value'
    _description = 'Response Key Value'
    response_key_id=fields.Many2one('api.connector', string='Related Server Action', ondelete='cascade')
    key = fields.Many2one('ir.model.fields', string='Field', required=True, ondelete='cascade')
    take_from = fields.Boolean(string='Take From Response')
    static_value = fields.Char("Static Value")
    dynamic_value = fields.Char("Dynamic Value")

    @api.onchange('key')
    def _onchange_key(self):
        if self.key.ttype in ('one2many', 'many2one', 'many2many'):
            raise ValidationError(f"You can only change Char, Float, and Integer fields. The following field(s) are invalid:\n\n {self.key.name}")
        if not self.key or not self.key.store:
            raise ValidationError(f"You cannot change the following field(s), as they are not stored in the database:\n\n {self.key.name}")