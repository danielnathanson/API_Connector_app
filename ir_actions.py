from odoo import api, fields, models

class IrActionsServer(models.Model):
    _inherit = 'ir.actions.server'

    action_api_connector_id = fields.Many2one(
            comodel_name='api.connector',
            string="API Connector", ondelete='cascade')

    is_connector_action = fields.Boolean()

    def _get_runner(self):
        if self.is_connector_action:
            return type(self)._run_action_api_call, False
        return super()._get_runner()

    def _run_action_api_call(self, eval_context):
        event_record = self.env[self.model_id.model].browse(self._context.get('active_id'))
        self.action_api_connector_id.send_request(event_record)
        self.action_api_connector_id.trigger_response()
