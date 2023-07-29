odoo.define('import_export_buttons.buttons', function (require) {
"use strict";
var ListController = require('web.ListController');
var ListView = require('web.ListView');
var viewRegistry = require('web.view_registry');
var TreeButton = ListController.extend({
   buttons_template: 'import_export_buttons.buttons',
   events: _.extend({}, ListController.prototype.events, {
        'click .open_import_wizard_action': '_OpenImportWizard',
        'click .open_export_wizard_action': '_OpenExportWizard'
   }),

   _OpenImportWizard: function () {
    this.do_action({
       type: 'ir.actions.act_window',
       res_model: 'import.postman.collection',
       name :'Import Postman Collection',
       view_mode: 'form',
       view_type: 'form',
       views: [[false, 'form']],
       target: 'new',
       res_id: false,
        });
    },

    _OpenExportWizard: function () {
        this.do_action({
           type: 'ir.actions.act_window',
           res_model: 'export.postman.collection',
           name :'Export As Postman Collection',
           view_mode: 'form',
           view_type: 'form',
           views: [[false, 'form']],
           target: 'new',
           res_id: false,
           context: {'active_ids': this.getSelectedIds()}
       });
   },
});

var ConnectorListView = ListView.extend({
    config: _.extend({}, ListView.prototype.config, {
        Controller: TreeButton
    }),
 });
viewRegistry.add('import_export_buttons', ConnectorListView);
});
