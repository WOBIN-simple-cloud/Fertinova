# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError
from odoo.tools.translate import _

import logging
_logger = logging.getLogger(__name__)     


class WobinLogisticaTrips(models.Model):
    _name        = 'wobin.logistica.trips'
    _description = 'Logistics Trips'
    _inherit     = ['mail.thread', 'mail.activity.mixin']        


    @api.model
    def create(self, vals):  
        """This method intends to create a sequence for a given trip and a new analytic tag"""
        #Change of sequence (if it isn't stored is shown "New" else e.g VJ000005)  
        if vals.get('name', 'New') == 'New':
            sequence = self.env['ir.sequence'].next_by_code(
                'self.trip') or 'New'

            vals['name'] = sequence
            vals['trip_number_tag'] = sequence

            values = {
                    'name': sequence,
                    'analytic_tag_type': 'trip'
                }
            self.env['account.analytic.tag'].create(values)  
                      
        result = super(WobinLogisticaTrips, self).create(vals)
        return result


    # General Data / - / - / - / - / - / - / - / - / - /
    name              = fields.Char(string="Trip", readonly=True, required=True, copy=False, default='New')
    trip_number_tag   = fields.Char(string='Trip Number (Analytic Tag)', track_visibility='always')
    contracts_id      = fields.Many2one('wobin.logistica.contracts', string='Contracts', track_visibility='always', ondelete='set null')
    sucursal_id       = fields.Many2one('stock.warehouse', string='Branch Office', track_visibility='always')
    client_id         = fields.Many2one('res.partner', string='Client', track_visibility='always')
    vehicle_id        = fields.Char(string='Vehicle', track_visibility='always')     
    analytic_accnt_id = fields.Many2one('account.analytic.account', string='Analytic Account', track_visibility='always')
    operator_id       = fields.Many2one('hr.employee',string='Operator', track_visibility='always')
    route             = fields.Char(string='Route', track_visibility='always')
    advance_ids       = fields.Many2many('purchase.order',string='Related Expenses', track_visibility='always', compute='_set_purchase_orders')
   
    # Upload data / - / - / - / - / - / - / - / - / - / - /
    start_date        = fields.Date(string='Start Date', track_visibility='always')
    upload_date       = fields.Date(string='Upload Date', track_visibility='always')
    estimated_qty     = fields.Float(string='Estimated Quantity (kg)', digits=dp.get_precision('Product Unit of Measure'), track_visibility='always')
    real_upload_qty   = fields.Float(string='Real Upload Quantity (kg)', digits=dp.get_precision('Product Unit of Measure'), track_visibility='always')
    attachment_upload = fields.Many2many('ir.attachment', relation='first_upl_att_relation', string='Upload Attachments', track_visibility='always')
    upload_location   = fields.Char(string='Upload Location', track_visibility='always')
   
    # Download Data / - / - / - / - / - / - / - / - / - / - /
    download_date      = fields.Date(string='Download Date', track_visibility='always')
    real_download_qty  = fields.Float(string='Real Download Quantity (kg)', digits=dp.get_precision('Product Unit of Measure'), track_visibility='always')
    attachment_downld  = fields.Many2many('ir.attachment', relation='second_dwn_att_relation', string='Download Attachments', track_visibility='always')
    qty_to_bill        = fields.Float(string='Quantiy to bill $', digits=dp.get_precision('Product Unit of Measure'), track_visibility='always', compute='_set_qty_to_bill') 
    conformity         = fields.Binary(string='Conformity and Settlement', track_visibility='always')
    checked            = fields.Boolean(string=" ")
    discharge_location = fields.Char(string='Discharge Location', track_visibility='always')
    sales_order_id     = fields.Many2one('sale.order', string='Sales Order Generated', track_visibility='always', compute='_set_sale_order', ondelete='set null')    
    state              = fields.Selection(selection=[('assigned', 'Assigned'),
                                                     ('route', 'En route'),
                                                     ('discharged', 'Discharged')], 
                                                    string='State', required=True, readonly=True, copy=False, tracking=True, default='assigned', compute="set_status", track_visibility='always')
    state_aux          = fields.Selection(selection=[('assigned', 'Assigned'),
                                                     ('route', 'En route'),
                                                     ('discharged', 'Discharged')], 
                                                    string='State', required=True, readonly=True, copy=False, tracking=True, default='assigned', store=True)                                                    

    # Analysis Fields / - / - / - / - / - / - / - / - / - / - /
    trip_taxes        = fields.Many2many('account.tax', string='Taxes', compute="_set_trip_taxes", track_visibility='always')
    income_provisions = fields.Float(string='Income Provisions', digits=dp.get_precision('Product Unit of Measure'), compute='_set_income_prov', track_visibility='always')                                                    
    billed_income     = fields.Float(string='Billed Income', digits=dp.get_precision('Product Unit of Measure'), track_visibility='always', compute='_set_billed_income')                                      
    expenses          = fields.Float(string='Expenses', digits=dp.get_precision('Product Unit of Measure'), track_visibility='always', compute='_set_expenses')                                      
    profitability     = fields.Float(string='Profitability', digits=dp.get_precision('Product Unit of Measure'), track_visibility='always', compute='_set_profitability') 
    advance_payment   = fields.Float(string='Advance Payment', digits=dp.get_precision('Product Unit of Measure'), track_visibility='always', compute='_set_advance_payment') 
    advance_sum_amnt = fields.Float(string='Advances', digits=(15,2), compute='set_advances')
    settlement        = fields.Float(string='Settlement', digits=dp.get_precision('Product Unit of Measure'), track_visibility='always', compute='_set_settlement')     
    invoice_status    =  fields.Selection([('draft','Draft'),
                                           ('open', 'Open'),
                                           ('in_payment', 'In Payment'),
                                           ('paid', 'Paid'),
                                           ('cancel', 'Cancelled'),
                                          ], string='Status', index=True, readonly=True, default='draft', copy=False, compute='_set_inv_status', track_visibility='always')                                         
    
   
        
    @api.one
    def set_status(self):
        '''Set up state in base a which fields are filled up'''
        if self.contracts_id and self.sucursal_id and self.client_id and self.vehicle_id and self.analytic_accnt_id and self.operator_id and self.route and self.start_date and self.upload_date and self.estimated_qty and self.real_upload_qty and self.upload_location and self.download_date and self.real_download_qty and self.checked and self.discharge_location:
            self.state = 'discharged'  
            self.write({'state_aux': self.state})        
        elif self.contracts_id and self.sucursal_id and self.client_id and self.vehicle_id and self.analytic_accnt_id and self.operator_id and self.route and self.start_date and self.upload_date and self.estimated_qty and self.real_upload_qty and self.upload_location:
            self.state = 'route'
            self.write({'state_aux': self.state})  
        else:
            self.state = 'assigned'
            self.write({'state_aux': self.state})  
        


    @api.one
    @api.depends('name')    
    def _set_sale_order(self):
        self.sales_order_id = self.env['sale.order'].search([('trips_id', '=', self.id)]).id



    @api.onchange('contracts_id')
    def _onchange_contract(self):
        '''Authomatic assignation for fields in Trips from contracts_id's input'''
        self.client_id      = self.env['wobin.logistica.contracts'].search([('id', '=', self.contracts_id.id)]).client_id.id    
        
        origin          = self.env['wobin.logistica.contracts'].search([('id', '=', self.contracts_id.id)]).origin_id.id    
        destination     = self.env['wobin.logistica.contracts'].search([('id', '=', self.contracts_id.id)]).destination_id.id
        origin_obj      = self.env['wobin.logistica.routes'].browse(origin)    
        destination_obj = self.env['wobin.logistica.routes'].browse(destination)
        if origin and destination:
            self.route = origin_obj.name + ', ' + destination_obj.name
        else:
            self.route = ""



    @api.one
    @api.depends('name')
    def _set_purchase_orders(self):            
        #ID of trip tag:
        trip_tag_id = self.env['account.analytic.tag'].search([('name', '=', self.trip_number_tag)], limit=1).id
        
        #Process valid in case of having an ID of Trip Tag:
        if trip_tag_id:
            #IDs corresponding to Purchase Lines with the present Trip Tag ID: 
            po_lnes_ids = self.env['purchase.order.line'].search([('analytic_tag_ids','=', trip_tag_id)]).ids

            pur_ord_set = set()  #Set in order to avoid duplicate values

            for line in po_lnes_ids:
                #Iterate Purchase Lines and get their Header Purchase Order ID
                #and add them into a set (averting duplicate ones):
                pur_ord_lin_obj = self.env['purchase.order.line'].browse(line)
                pur_ord_set.add(pur_ord_lin_obj.order_id.id)

            #Conversion from set to list in order to permit injection of multiple values:
            pur_ords_lst = list(pur_ord_set)
            
            #Now many2many field Advance_ids has various values:
            self.advance_ids = [(6, 0, pur_ords_lst)]
                 


    @api.one
    def _set_trip_taxes(self):
        self.trip_taxes = self.env['account.invoice.line'].search([('trips_id', '=', self.id)], limit=1).invoice_line_tax_ids.ids



    @api.one
    def _set_income_prov(self):
        inv_init = None; inv_next = None
        inv_lines_gotten = self.env['account.invoice.line'].search([('trips_id', '=', self.id)])
        
        if inv_lines_gotten:
            _logger.info('\n\n\n ANTES DE FOR CICLO inv_init %s  Y   inv_NEXT %s\n\n\n', inv_init, inv_next)
            for line in inv_lines_gotten:
                inv_init = line.invoice_id.id
                _logger.info('\n\n\n DENTRO DE FOR CICLO inv_init %s  Y   inv_NEXT %s\n\n\n', inv_init, inv_next)
                inv_state = self.env['account.invoice'].search([('id', '=', inv_init)]).state
        
                if inv_init != inv_next and inv_state != 'cancel':
                    self.income_provisions = self.income_provisions + line.price_subtotal
                    _logger.info('\n\n\n self.income_provisions %s\n\n\n', self.income_provisions)
            
            inv_next = line.invoice_id.id        
        #self.income_provisions = self.env['account.invoice.line'].search([('trips_id', '=', self.id)], limit=1).price_subtotal



    @api.one
    def _set_qty_to_bill(self):
        #Get Tariff from Contract data belonging to this Trip:
        tariff = self.env['wobin.logistica.contracts'].search([('id', '=', self.contracts_id.id)]).tariff
        self.qty_to_bill = self.real_upload_qty * tariff



    @api.one
    def _set_inv_status(self):
        invoice_id = self.env['account.invoice.line'].search([('trips_id', '=', self.id)], limit=1).invoice_id.id
        self.invoice_status = self.env['account.invoice'].search([('id', '=', invoice_id)]).state



    @api.one
    @api.depends('name')
    def _set_billed_income(self):
        inv_init = None; inv_next = None
        inv_lines_gotten = self.env['account.invoice.line'].search([('trips_id', '=', self.id)])
        
        if inv_lines_gotten:
            _logger.info('\n\n\n ANTES DE FOR CICLO {inv_init} %s  Y   [inv_NEXT] %s\n\n\n', inv_init, inv_next)
            for line in inv_lines_gotten:
                inv_init = line.invoice_id.id
                _logger.info('\n\n\n DENTRO DE FOR CICLO inv_init %s  Y   inv_NEXT %s\n\n\n', inv_init, inv_next)
                inv_state = self.env['account.invoice'].search([('id', '=', inv_init)]).state
        
                if inv_init != inv_next and inv_state != 'cancel':
                    self.billed_income = self.billed_income + line.price_subtotal
                    _logger.info('\n\n\n self.billed_income %s\n\n\n', self.billed_income)
            
            inv_next = line.invoice_id.id                   
        #self.billed_income = self.env['account.invoice.line'].search([('trips_id', '=', self.id)], limit=1).price_unit



    @api.one
    @api.depends('name')
    def _set_expenses(self):
        billed_amount_po = 0.0

        if self.advance_ids:
            for pur_ord in self.advance_ids.ids:
                amount = self.env['purchase.order'].search([('id', '=', pur_ord)]).amount_total
                billed_amount_po += amount

        self.expenses = billed_amount_po            




    @api.one
    @api.depends('name')
    def _set_profitability(self):
        self.profitability = self.billed_income - self.expenses



    @api.one
    @api.depends('name')
    def _set_advance_payment(self):
        pass



    @api.one
    @api.depends('name')
    def _set_settlement(self):
        self.settlement = (self.income_provisions + self.expenses) - self.advance_payment
   


    @api.one
    @api.depends('name')
    def set_advances(self):
        list_advances = self.env['wobin.advances'].search([('operator_id', '=', self.operator_id.id),
                                                           ('trip_id', '=', self.id)]).ids

        if list_advances:
            sum_amount = sum(line.amount for line in self.advance_ids)
            self.advance_sum_amnt = sum_amount





class AccountAnalyticTag(models.Model):
    _inherit = "account.analytic.tag"

    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    # Aggregation of a new selection field in Analytic Tags to manage types
    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::       
    analytic_tag_type = fields.Selection([('trip', 'Trip'),
                                          ('route', 'Route'),
                                          ('operator', 'Operator')],
                                         'Analytic Tag Type')




class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    # Aggregation of new relational fields
    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::  
    contracts_ids     = fields.Many2many('wobin.logistica.contracts', compute='_set_contract', string='Contracts Information')
    trips_related_ids = fields.Many2many('wobin.logistica.trips', compute='_set_trips', string='Related Trips')
    flag_cont_trip    = fields.Boolean(string='Flag for contract and trip', compute='_set_flag_ct', default=False, store=True)


    @api.one
    @api.depends('number')
    def _set_trips(self):
        #Get trips assigned from invoice lines:        
        trip_list = [ inv.trips_id.id for inv in self.invoice_line_ids ]
        if trip_list:
            self.trips_related_ids = [(6, 0, trip_list)]         


    @api.one
    @api.depends('number')
    def _set_contract(self): 
        contract_list = [ trip.id for trip in self.trips_related_ids ]
        if contract_list:
            self.contracts_ids = [(6, 0, contract_list)]  


    @api.one
    @api.depends('number')
    def _set_flag_ct(self):
        self.flag_cont_trip = False

        if self.contracts_ids:
            if self.contracts_ids.ids:
                self.flag_cont_trip = True
        




class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    # Aggregation of a new many2one field of Trips in Customer Invoices
    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::  
    trips_id = fields.Many2one('wobin.logistica.trips', string='Trip')    
    




class SaleOrder(models.Model):
    _inherit = "sale.order"

    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    # Aggregation of a new many2one field of Trips in Customer Invoices
    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::  
    trips_id = fields.Many2one('wobin.logistica.trips', string='Trip')     
    flag_trip = fields.Boolean(string='Flag to indicate this sale order has trip', compute='_set_flag_trip', store=True)
    

    @api.one
    @api.depends('trips_id')
    def _set_flag_trip(self):
        if self.trips_id:
            self.flag_trip = True            
        else:
            self.flag_trip = False