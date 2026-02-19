from odoo import fields, models

class StockPicking(models.Model):
    _inherit = "stock.picking"

    x_asignado = fields.Many2one("res.users", string="Asignado (legacy)")
    x_completado = fields.Boolean(string="Completado (legacy)")
    x_enviar = fields.Boolean(string="Enviar (legacy)")
    x_modifica = fields.Text(string="Modifica (legacy)")
    x_motivo = fields.Text(string="Motivo (legacy)")
    x_pagina_final = fields.Boolean(string="Página final (legacy)")
