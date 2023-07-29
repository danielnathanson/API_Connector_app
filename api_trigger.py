from odoo import api, fields, models
from collections import defaultdict


class BaseAutomation(models.Model):
    _inherit = 'base.automation'
    _name = 'base.automation.api.trigger'

    api_connector_id = fields.Many2one(
        comodel_name='api.connector',
        string="API Connector", ondelete='cascade')
    on_change_field_ids = fields.Many2many(
        "ir.model.fields",
        relation="base_automation_api_trigger_onchange_fields_rel",
        compute='_compute_on_change_field_ids',
        readonly=False, store=True,
        string="On Change Fields Trigger",
        help="Fields that trigger the onchange.",
    )

    action_server_id = fields.Many2one(ondelete='cascade')

    def _register_hook(self):
        def make_create():
            """ Instanciate a create method that processes action rules. """

            @api.model_create_multi
            def create(self, vals_list, **kw):
                # retrieve the action rules to possibly execute
                actions = self.env['base.automation.api.trigger']._get_actions(self,
                                                                               ['on_create', 'on_create_or_write'])
                if not actions:
                    return create.origin(self, vals_list, **kw)
                # call original method
                records = create.origin(self.with_env(actions.env), vals_list, **kw)
                # check postconditions, and execute actions on the records that satisfy them
                for action in actions.with_context(old_values=None):
                    action._process(action._filter_post(records))
                return records.with_env(self.env)

            return create

        def make_write():
            """ Instanciate a write method that processes action rules. """

            def write(self, vals, **kw):
                # retrieve the action rules to possibly execute
                actions = self.env['base.automation.api.trigger']._get_actions(self, ['on_write', 'on_create_or_write'])
                if not (actions and self):
                    return write.origin(self, vals, **kw)
                records = self.with_env(actions.env).filtered('id')
                # check preconditions on records
                pre = {action: action._filter_pre(records) for action in actions}
                # read old values before the update
                old_values = {
                    old_vals.pop('id'): old_vals
                    for old_vals in (records.read(list(vals)) if vals else [])
                }
                # call original method
                write.origin(self.with_env(actions.env), vals, **kw)
                # check postconditions, and execute actions on the records that satisfy them
                for action in actions.with_context(old_values=old_values):
                    records, domain_post = action._filter_post_export_domain(pre[action])
                    action._process(records, domain_post=domain_post)
                return True

            return write

        def make_compute_field_value():
            """ Instanciate a compute_field_value method that processes action rules. """

            #
            # Note: This is to catch updates made by field recomputations.
            #
            def _compute_field_value(self, field):
                # determine fields that may trigger an action
                stored_fields = [f for f in self.pool.field_computed[field] if f.store]
                if not any(stored_fields):
                    return _compute_field_value.origin(self, field)
                # retrieve the action rules to possibly execute
                actions = self.env['base.automation.api.trigger']._get_actions(self, ['on_write', 'on_create_or_write'])
                records = self.filtered('id').with_env(actions.env)
                if not (actions and records):
                    _compute_field_value.origin(self, field)
                    return True
                # check preconditions on records
                pre = {action: action._filter_pre(records) for action in actions}
                # read old values before the update
                old_values = {
                    old_vals.pop('id'): old_vals
                    for old_vals in (records.read([f.name for f in stored_fields]))
                }
                # call original method
                _compute_field_value.origin(self, field)
                # check postconditions, and execute actions on the records that satisfy them
                for action in actions.with_context(old_values=old_values):
                    records, domain_post = action._filter_post_export_domain(pre[action])
                    action._process(records, domain_post=domain_post)
                return True

            return _compute_field_value

        def make_unlink():
            """ Instanciate an unlink method that processes action rules. """

            def unlink(self, **kwargs):
                # retrieve the action rules to possibly execute
                actions = self.env['base.automation.api.trigger']._get_actions(self, ['on_unlink'])
                records = self.with_env(actions.env)
                # check conditions, and execute actions on the records that satisfy them
                for action in actions:
                    action._process(action._filter_post(records))
                # call original method
                return unlink.origin(self, **kwargs)

            return unlink

        def make_onchange(action_rule_id):
            """ Instanciate an onchange method for the given action rule. """

            def base_automation_onchange(self):
                action_rule = self.env['base.automation.api.trigger'].browse(action_rule_id)
                result = {}
                server_action = action_rule.sudo().action_server_id.with_context(
                    active_model=self._name,
                    active_id=self._origin.id,
                    active_ids=self._origin.ids,
                    onchange_self=self,
                )
                try:
                    res = server_action.run()
                except Exception as e:
                    action_rule._add_postmortem_action(e)
                    raise e

                if res:
                    if 'value' in res:
                        res['value'].pop('id', None)
                        self.update({key: val for key, val in res['value'].items() if key in self._fields})
                    if 'domain' in res:
                        result.setdefault('domain', {}).update(res['domain'])
                    if 'warning' in res:
                        result['warning'] = res['warning']
                return result

            return base_automation_onchange

        patched_models = defaultdict(set)

        def patch(model, name, method):
            """ Patch method `name` on `model`, unless it has been patched already. """
            if model not in patched_models[name]:
                patched_models[name].add(model)
                ModelClass = type(model)
                origin = getattr(ModelClass, name)
                method.origin = origin
                wrapped = api.propagate(origin, method)
                wrapped.origin = origin
                setattr(ModelClass, name, wrapped)

        # retrieve all actions, and patch their corresponding model
        for action_rule in self.with_context({}).search([]):
            Model = self.env.get(action_rule.model_name)

            # Do not crash if the model of the base_action_rule was uninstalled
            if Model is None:
                _logger.warning("Action rule with ID %d depends on model %s" %
                                (action_rule.id,
                                 action_rule.model_name))
                continue

            if action_rule.trigger == 'on_create':
                patch(Model, 'create', make_create())

            elif action_rule.trigger == 'on_create_or_write':
                patch(Model, 'create', make_create())
                patch(Model, 'write', make_write())
                patch(Model, '_compute_field_value', make_compute_field_value())

            elif action_rule.trigger == 'on_write':
                patch(Model, 'write', make_write())
                patch(Model, '_compute_field_value', make_compute_field_value())

            elif action_rule.trigger == 'on_unlink':
                patch(Model, 'unlink', make_unlink())

            elif action_rule.trigger == 'on_change':
                # register an onchange method for the action_rule
                method = make_onchange(action_rule.id)
                for field in action_rule.on_change_field_ids:
                    Model._onchange_methods[field.name].append(method)
