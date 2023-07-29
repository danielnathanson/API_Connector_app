{
    "name": "API Connector",
    "website": "https://www.odoo.com",
    "author": "Odoo Inc.",
    "summary": "This app will be use to connect to a rest end point and fetch the desired request and response data",
    "description": "",
    "category": "Custom Development.",
    "depends": ["base_automation","website"],
    "data": [
        "views/postman_menuitems.xml",
        "views/postman_view.xml",
        "views/postman_view_button.xml",
        "views/postman_export_view.xml",
        "views/postman_import_export_buttons.xml",
        "security/api_connector_groups.xml",
        "security/ir.model.access.csv",
    ],
    'assets': {'web.assets_backend': ['api_connector/static/src/js/import_export_buttons.js',
                                      'api_connector/static/src/xml/import_export_buttons.xml',
                                      'api_connector/static/src/css/style.css'], },
    "website": "www.odoo.com",
    
    "application": True,
    
}
