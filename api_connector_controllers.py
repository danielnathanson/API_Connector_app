import requests

from odoo import http

class APIConnector(http.Controller):
    @http.route('/oauthcallback', auth='public', website=False, sitemap=False)
    def oauth_callback(self, **kwargs):
        try:
            code = kwargs.get('code')
            api_connector_id = kwargs.get('id')
            api_connector=http.request.env['api.connector'].search([("id","=",api_connector_id)])
            data = {
                'client_id': api_connector.oauth_client_id,
                'client_secret': api_connector.oauth_client_secret,
                'code': code,
                'redirect_uri': api_connector.oauth_redirect_uri,
                'grant_type': 'authorization_code'
            }
            headers = {'Accept': 'application/json'}
            response = requests.post(api_connector.oauth_access_token_url, data=data, headers=headers)
            response_json = response.json()
            access_token = response_json['access_token']
            api_connector.bearer_token = access_token
            return "Your token has been generated. Please close this tab"
        except Exception as e:
            return "Error while generating the Oauth 2 token\n"+str(e)
