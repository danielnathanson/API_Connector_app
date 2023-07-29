from urllib.parse import urlencode
from odoo import api, fields, models
from odoo.exceptions import UserError
import requests
import json
import base64
import validators


class ApiConnector(models.Model):
    _name = 'api.connector'
    _description = 'API Connector'
    header_line = fields.One2many(
        comodel_name='api.header',
        inverse_name='api_connector_id',
        string="Header Line",
        ondelete="cascade", auto_join=True)

    parameter_line = fields.One2many(
        comodel_name='api.parameter',
        inverse_name='api_connector_id',
        string="Parameter Line",
        ondelete="cascade", auto_join=True)

    add_to_url_line = fields.One2many(
        comodel_name='add.to.url',
        inverse_name='api_connector_id',
        string="Parameter Line",
        ondelete="cascade", auto_join=True)

    api_trigger_id = fields.Many2one(
        comodel_name='base.automation.api.trigger',
        string="API trigger",
        ondelete="cascade")

    name = fields.Char(required=True)
    url = fields.Char('URL', required=True)
    request_method = fields.Selection([("REST", "REST"), ("GRAPHQL", "GRAPH QL")], string='Request Method', default = "REST")
    request_type = fields.Selection(
        [('GET', 'GET'), ('PUT', 'PUT'), ('POST', 'POST'), ('PATCH', 'PATCH'), ('DELETE', 'DELETE')],
        string='Request Type', default="GET")
    request_body = fields.Text('Request Body')
    response = fields.Text('Response', readonly=True)
    authorization = fields.Selection(
        [('No Auth', 'No Auth'), ('Bearer', 'Bearer'), ('Basic Auth', 'Basic Auth'), ('O Auth 2', 'O Auth 2')],
        string='Authorization', default="No Auth")
    bearer_token = fields.Char('Bearer Token')
    basic_auth_user_name = fields.Char('User Name')
    basic_auth_password = fields.Char('Password')
    oauth_authorization_url = fields.Char('Authorization URL')
    oauth_client_id = fields.Char('Client Id')
    oauth_client_secret = fields.Char('Client Secret')
    oauth_redirect_uri = fields.Char('Redirect URL')
    oauth_access_token_url = fields.Char('Access Token URL')
    request_func = {'GET': requests.get, 'PUT': requests.put, 'POST': requests.post, 'PATCH': requests.patch,
                    'DELETE': requests.delete}
    response_handler_update_key = fields.Char()
    response_handler_update_value = fields.Char()
    response_event_record = fields.Reference(
        selection='_get_polymorphic_model',
        string='Polymorphic Field',
    )

    @api.model
    def _get_polymorphic_model(self):
        models = self.env['ir.model'].search([])
        return [(model.model, model.name) for model in models]

    @api.depends('url')
    def send_request(self, event_record=None):
        PARAMS = {}
        HEADERS = {}
        if event_record is not None:
            self.response_event_record = event_record
        headers_dict = self._get_request_headers(event_record)
        parameters_dict = self._get_request_parameters(event_record)
        url_to_call = self._add_to_url(event_record)
        HEADERS.update(headers_dict)
        PARAMS.update(parameters_dict)
        payload = ""
        if self.authorization == 'Bearer':
            HEADERS['Authorization'] = 'Bearer ' + self.bearer_token
        elif self.authorization == 'Basic Auth':
            HEADERS['Authorization'] = 'Basic ' + base64.b64encode(
                bytes(self.basic_auth_user_name + ':' + self.basic_auth_password, 'utf-8')).decode('utf-8')
        elif self.authorization == 'O Auth 2':
            HEADERS['Authorization'] = 'Bearer ' + self.bearer_token
        if self.request_method == "REST":
            r = self.request_func[self.request_type](url_to_call, params=PARAMS, headers=HEADERS, data=payload)
        else:
            r = self.request_func[self.request_type](url_to_call, json={"query": self.request_body})
        if r.status_code == 200:
            try:
                self.response = json.dumps(ApiConnector._flatten_dict(r.json()), indent=4)
            except Exception as e:
                raise UserError("Invalid Response to the given request. Please check the request. \nExpecting "
                                      "the response in JSON\n\nCurrent Response\n" + str(r.content))
        else:
            raise UserError("Invalid Request Response Code\n" + str(r.status_code))

    def _get_request_headers(self, event_record):
        headers_dict = {}
        for request in self:
            request_headers = self.env["api.header"].search([("api_connector_id", "=", request.id)])
            for header in request_headers:
                if event_record is not None and header.take_from_event_record:
                    headers_dict[header.key] = getattr(event_record, header.dynamic_value.name)
                else:
                    headers_dict[header.key] = header.static_value
        return headers_dict

    def _get_request_parameters(self, event_record):
        parameters_dict = {}
        for request in self:
            request_parameters = self.env["api.parameter"].search([("api_connector_id", "=", request.id)])
            for parameter in request_parameters:
                if event_record is not None and parameter.take_from_event_record:
                    parameters_dict[parameter.key] = getattr(event_record, parameter.dynamic_value.name)
                else:
                    parameters_dict[parameter.key] = parameter.static_value
        return parameters_dict

    def _add_to_url(self, event_record):
        url_to_call = self.url
        for request in self:
            add_to_urls = self.env["add.to.url"].search([("api_connector_id", "=", request.id)])
            for url in add_to_urls:
                if event_record is not None and url.take_from_event_record:
                    url_to_call = f'{url_to_call}{"/"}{getattr(event_record, url.dynamic_value.name)}'
                else:
                    url_to_call = f'{url_to_call}{"/"}{url.static_value}'
        return url_to_call

    DEFAULT_PYTHON_CODE = """# Available variables:
    #  - env: Odoo Environment on which the action is triggered
    #  - model: Odoo Model of the record on which the action is triggered; is a void recordset
    #  - record: record on which the action is triggered; may be void
    #  - records: recordset of all records on which the action is triggered in multi-mode; may be void
    #  - time, datetime, dateutil, timezone: useful Python libraries
    #  - float_compare: Odoo function to compare floats based on specific precisions
    #  - log: log(message, level='info'): logging function to record debug information in ir.logging table
    #  - UserError: Warning Exception to use with raise
    #  - Command: x2Many commands namespace
    # To return an action, assign: action = {...}\n\n\n\n"""
    state = fields.Selection([
        ('code', 'Execute Python Code'),
        ('object_create', 'Create a new Record'),
        ('object_write', 'Update the Record')], string='Action To Do',
        default='object_write', required=True, copy=True)
    code = fields.Text(string='Python Code', groups='base.group_system',
                       default=DEFAULT_PYTHON_CODE,
                       help="Write Python code that the action will execute. Some variables are "
                            "available for use; help about python expression is given in the help tab.")

    target_model_id = fields.Many2one(
        'ir.model', string='Target Model', readonly=False, store=True,
        help="Model for record creation / update. Set this field only to specify a different model than the base model.")
    target_model_name = fields.Char(related='target_model_id.model', string='Target Model Name', readonly=True)
    link_field_id = fields.Many2one(
        'ir.model.fields', string='Link Field', readonly=False, store=True,
        help="Provide the field used to link the newly created record on the record used by the server action.")
    fields_lines = fields.One2many(comodel_name='response.key.value', inverse_name='response_key_id', string='Value '
                                                                                                             'Mapping',
                                   copy=True)

    def _fetch_key_value_pair_response(self):
        actual_values = {}
        response_object = json.loads(self.response)
        for request in self:
            response_keys_values = self.env["response.key.value"].search([("response_key_id", "=", request.id)])
            for response_key_value in response_keys_values:
                if not response_key_value.take_from:
                    actual_values[response_key_value.key.name] = response_key_value.static_value
                else:
                    try:
                        actual_values[response_key_value.key.name] = response_object[response_key_value.dynamic_value]
                    except KeyError:
                        raise UserError("Key not found in Response Object " + response_key_value.dynamic_value)
        return actual_values

    def open_oauth_user_authentication_url(self):
        oauth_url = self._get_oauth_authorization_url()
        return {
            "type": "ir.actions.act_url",
            "url": oauth_url,
            "target": "parent",
        }

    def _get_oauth_authorization_url(self):
        self.oauth_redirect_uri = "http://localhost:8069/oauthcallback?id=" + str(self.id)
        oauth_params = {
            'response_type': 'code',
            'client_id': self.oauth_client_id,
            'redirect_uri': self.oauth_redirect_uri,
            'id': self.id
        }
        authorization_url = self.oauth_authorization_url + '?' + urlencode(oauth_params)
        return authorization_url

    @api.depends('response')
    def trigger_response(self):
        converted_key_value = self._fetch_key_value_pair_response()
        if self.state == 'object_create':
            self.env[self.target_model_name].create(
                converted_key_value
            )
        elif self.state == 'object_write':
            set_string = ""
            model_name = str(self.target_model_name)
            model_name = model_name.replace(".", "_")
            for key in converted_key_value:
                set_string = f"{set_string}{key} = '{converted_key_value[key]}', "
            query_string = 'UPDATE ' + model_name + ' SET ' + set_string[:-2] + ' WHERE id = ' + str(
                self.response_event_record.id)
            self.env.cr.execute(query_string)

    @api.model_create_multi
    def create(self, vals_list):
        api_connectors = super().create(vals_list)
        for api_connector in api_connectors:
            api_connector.api_trigger_id.action_server_id.is_connector_action = True
            api_connector.api_trigger_id.action_server_id.action_api_connector_id = api_connector
        return api_connectors

    def write(self, vals):
        res = super().write(vals)
        self.api_trigger_id.action_server_id.is_connector_action = True
        self.api_trigger_id.action_server_id.action_api_connector_id = self
        return res

    @staticmethod
    def _flatten_dict(d):
        ans = {}
        for k, v in d.items():
            if type(v) is not list:
                ans[k] = v
            else:
                for d in v:
                    ans |= ApiConnector._flatten_dict(d)
        return ans

    def get_export_url(self):
        url = self._add_to_url(None)
        params = self._get_request_parameters(None)
        if not params:
            return url
        url += '/?'
        for key, value in params.items():
            url += f"{key}={value}&"
        return url[:len(url) - 1]

    def get_export_header(self):
        header = []
        for key, value in self._get_request_headers(None).items():
            header.append({
                "key": key,
                "value": value,
                "type": "text"
            }, )
        return header

    def get_export_auth(self):
        auth = {}
        postman_auth = {'No Auth': "noauth", 'Bearer': 'bearer', 'Basic Auth': 'basic', 'O Auth 2': 'oauth2'}
        auth["type"] = postman_auth[self.authorization]
        match auth["type"]:
            case "oauth2":
                auth["oauth2"] = {
                    "clientSecret": self.oauth_client_secret,
                    "clientId": self.oauth_client_id,
                    "accessTokenUrl": self.oauth_access_token_url,
                    "grant_type": "client_credentials",
                    "addTokenTo": "header"
                }
            case "bearer":
                auth["bearer"] = {"token": self.bearer_token}
            case "basic":
                auth["basic"] = {"username": self.basic_auth_user_name, "password": self.basic_auth_password}
            case _:
                pass
        return auth

    @api.constrains('url')
    def _check_url(self):
        for record in self:
            if not validators.url(record.url):
                raise UserError("The url is malformed")
