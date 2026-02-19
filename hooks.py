# -*- coding: utf-8 -*-

from odoo import api, SUPERUSER_ID


def _writable_field(Model, field_name):
    """Return True if field exists and can be written safely."""
    fld = Model._fields.get(field_name)
    if not fld:
        return False
    # related/computed fields are not safely writable (and often readonly)
    if getattr(fld, "related", None):
        return False
    if getattr(fld, "compute", None):
        return False
    if getattr(fld, "readonly", False):
        return False
    return True


def _copy_field_values(Model, src, dst, batch=2000):
    if src not in Model._fields:
        return 0
    if dst not in Model._fields:
        return 0
    if not _writable_field(Model, dst):
        # no copiamos a campos no-escribibles
        return 0

    total = 0
    domain = [(src, "!=", False)]
    # iteración por lotes para no cargar demasiados records
    offset = 0
    while True:
        recs = Model.search(domain, offset=offset, limit=batch, order="id")
        if not recs:
            break
        vals_list = []
        for r in recs:
            sv = r[src]
            if not sv:
                continue
            # si ya está igual, skip
            if r[dst] == sv:
                continue
            vals_list.append((r.id, sv))
        if vals_list:
            # write uno a uno: más seguro con tipos M2M / M2O / selection
            for rid, sv in vals_list:
                Model.browse(rid).write({dst: sv})
            total += len(vals_list)
        offset += batch
    return total


def post_init_copy_stock_legacy_to_base(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Mapeo explícito (solo campos realmente detectados en tu dump)
    mapping = {
        "stock.picking": [
            ("x_asignado", "sid_asignado"),
            ("x_completado", "sid_completado"),
            ("x_enviar", "sid_enviar"),
            ("x_modifica", "sid_modifica"),
            ("x_motivo", "sid_motivo"),
            ("x_pagina_final", "sid_pagina_final"),
            # x_cliente suele ser related/readonly en Studio; si en base existe como writable lo copiará.
            ("x_cliente", "sid_cliente"),
            # x_studio_pedido_cliente (char) -> si existe equivalente base
            ("x_studio_pedido_cliente", "sid_pedido_cliente"),
        ],
        "stock.move": [
            ("x_ayudante", "sid_ayudante"),
            ("x_prioridad_linea", "sid_prioridad_linea"),
            ("x_coladas", "sid_coladas"),
            ("x_color", "sid_color"),
            ("x_item", "sid_item"),
            ("x_tags_activities", "sid_tags_activities"),
            # x_asignado en move es related a picking_id.x_asignado; si en base existe writable, se copiará
            ("x_asignado", "sid_asignado"),
        ],
        "stock.move.line": [
            ("x_item", "sid_item"),
            # Los siguientes eran related en Studio; solo copiará si en base son campos propios escribibles
            ("x_studio_compra", "sid_compra"),
            ("x_studio_related_field_WRoVn", "sid_proveedor"),
        ],
        "stock.picking.type": [
            ("x_note", "sid_note"),
        ],
        "stock.picking.batch": [
            ("x_direccion", "sid_direccion"),
            ("x_studio_many2many_field_6Qdqh", "sid_partners"),
            ("x_studio_notas_de_inspeccin", "sid_notas_inspeccion"),
        ],
        # stock.quant.x_pasillo es related a product; no copiamos aquí.
    }

    for model_name, pairs in mapping.items():
        Model = env[model_name].sudo()
        for src, dst in pairs:
            _copy_field_values(Model, src, dst)
