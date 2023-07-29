from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError

class TestApiConnector(TransactionCase):

    def setUp(self):
        # super(TestApiConnector, self).setUp()
        self.api_connector = self.env['api.connector'].create({
            'name': 'Test API Connector',
            'url': 'https://www.boredapi.com/api/activity',
            'request_method': 'REST',
            'request_type': 'GET',
            'authorization': 'No Auth',
        })
    def test_send_request_success(self):
        # Test sending a successful request without authorization
        self.api_connector.send_request()
        self.assertTrue(self.api_connector.response)
    def test_add_to_url(self):
        # Test AddToURL functionality
        add_to_url = self.env['add.to.url'].create({
            'api_connector_id': self.api_connector.id,
            'key': 'test_key',
            'value': 'test_value',
        })
        url_to_call = self.api_connector._add_to_url(event_record=None)
        self.assertEqual(url_to_call, 'https://www.boredapi.com/api/activity/test_value')

    def test_api_header(self):
        # Test ApiHeader functionality
        api_header = self.env['api.header'].create({
            'api_connector_id': self.api_connector.id,
            'key': 'test_header_key',
            'value': 'test_header_value',
        })
        headers_dict = self.api_connector._get_request_headers(event_record=None)
        self.assertEqual(headers_dict.get('test_header_key'), 'test_header_value')

    def test_api_parameter(self):
        # Test ApiParameter functionality
        api_parameter = self.env['api.parameter'].create({
            'api_connector_id': self.api_connector.id,
            'key': 'test_param_key',
            'value': 'test_param_value',
        })
        params_dict = self.api_connector._get_request_parameters(event_record=None)
        self.assertEqual(params_dict.get('test_param_key'), 'test_param_value')
    def test_send_request_with_invalid_url(self):
        # Test sending a request with an invalid URL
        self.api_connector.url = 'invalid_url'
        with self.assertRaises(UserError):
            self.api_connector.send_request()
