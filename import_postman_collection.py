import base64
import json
import re
import traceback
from json import JSONDecodeError
from odoo.exceptions import UserError
from odoo import api, fields, models


class ImportPostmanCollection(models.Model):
    _name = 'import.postman.collection'
    _description = 'Import Postman Collection'

    json_file_for_import = fields.Binary(string='File for upload')
    json_data = fields.Text(string="JSON Data", compute='_compute_from_json_file')

    @api.depends('json_file_for_import')
    def _compute_from_json_file(self):
        if self._is_Base64(self.json_file_for_import) is not False:
            string_variable = str(self.json_file_for_import)[1:]
            try:
                postman_collection_json = json.loads(base64.b64decode(string_variable))
                for individual_request in postman_collection_json["item"]:
                    converted_api_connector_record = self._convert_request_to_api_record(individual_request)
                    self.env["api.connector"].create(converted_api_connector_record)
                    individual_request_id = self.env["api.connector"].search([("name", "=", individual_request["name"])]).id
                    self._create_request_header(individual_request["request"]["header"], individual_request_id)
                    self._create_request_parameter(individual_request["request"], individual_request_id)
                self.json_data = json.dumps(postman_collection_json, indent=4, sort_keys=True)
            except JSONDecodeError:
                raise UserError("Invalid POSTMAN Collection. Malformed JSON!!")
            except ValueError:
                raise UserError("A postman API with same name already exists")
        else:
            self.json_data = False

    def _is_Base64(self, sb):
        try:
            if isinstance(sb, str):
                # If there's any unicode here, an exception will be thrown and the function will return false
                sb_bytes = bytes(sb, 'ascii')
            elif isinstance(sb, bytes):
                sb_bytes = sb
            else:
                raise ValueError("Argument must be string or bytes")
            return base64.b64encode(base64.b64decode(sb_bytes)) == sb_bytes
        except Exception:
            return False

    def _convert_request_to_api_record(self, individual_request):
        api_connector_record = {}
        api_connector_record["name"] = individual_request["name"]
        api_connector_record["request_method"] = "REST"
        if isinstance(individual_request["request"]["url"], dict):
            url_body = individual_request["request"]["url"]
            result = re.search("[^?]*", url_body['raw'])
            api_connector_record["url"] = result.group()
        else:
            api_connector_record["url"] = individual_request["request"]["url"]
        api_connector_record["request_type"] = individual_request["request"]["method"]
        auth_dict = self._add_auth_fields_to_record(individual_request["request"]["auth"])
        api_connector_record.update(auth_dict)

        return api_connector_record

    def _add_auth_fields_to_record(self, auth_body):
        auth_record = {}
        if auth_body["type"] == "basic":
            auth_record["authorization"] = 'Basic Auth'
            auth_record["basic_auth_user_name"] = auth_body['basic']["username"]
            auth_record["basic_auth_password"] = auth_body['basic']["password"]

        elif auth_body["type"] == "oauth2":
            auth_record["authorization"] = 'O Auth 2'
            auth_record["oauth_authorization_url"] = auth_body['oauth2']["accessTokenUrl"]
            auth_record["oauth_client_id"] = auth_body['oauth2']["clientId"]
            auth_record["oauth_client_secret"] = auth_body['oauth2']["clientSecret"]
            auth_record["oauth_access_token_url"] = auth_body['oauth2']["accessTokenUrl"]

        elif auth_body["type"] == "bearer":
            auth_record["authorization"] = 'Bearer'
            auth_record["bearer_token"] = auth_body['bearer']["token"]
        else:
            auth_record["authorization"] = 'No Auth'
        return auth_record

    def _create_request_header(self, header_array, api_connector_id):
        header_dict = {}
        for header in header_array:
            header_dict["key"] = header["key"]
            header_dict["static_value"] = header["value"]
            header_dict["api_connector_id"] = api_connector_id
            self.env["api.header"].create(header_dict)

    def _create_request_parameter(self, request, api_connector_id):
        parameter_dict = {}
        if isinstance(request["url"], dict):
            for parameters in request["url"]["query"]:
                parameter_dict["key"] = parameters["key"]
                parameter_dict["static_value"] = parameters["value"]
                parameter_dict["api_connector_id"] = api_connector_id
                self.env["api.parameter"].create(parameter_dict)
