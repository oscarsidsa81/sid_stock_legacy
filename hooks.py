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
            write_val = _convert_value_for_field(Model, src, dst, sv)
            if write_val is None:
                continue
            # si ya está igual, skip
            if _field_values_equal(r, dst, write_val):
                continue
            vals_list.append((r.id, write_val))
        if vals_list:
            # write uno a uno: más seguro con tipos M2M / M2O / selection
            for rid, sv in vals_list:
                Model.browse(rid).write({dst: sv})
            total += len(vals_list)
        offset += batch
    return total


def _field_values_equal(record, field_name, write_val):
    fld = record._fields[field_name]
    current = record[field_name]
    if fld.type == "many2many":
        target_ids = set(write_val[0][2]) if write_val else set()
        return set(current.ids) == target_ids
    if fld.type == "one2many":
        # one2many no se copia en este módulo
        return False
    if fld.type == "many2one":
        return (current.id or False) == (write_val or False)
    return current == write_val


def _convert_value_for_field(Model, src, dst, source_val):
    src_fld = Model._fields[src]
    dst_fld = Model._fields[dst]

    # tipos simples
    if dst_fld.type not in ("many2one", "many2many", "one2many"):
        return source_val

    # no copiamos one2many para evitar writes complejos/inesperados
    if dst_fld.type == "one2many":
        return None

    # many2one
    if dst_fld.type == "many2one":
        if not source_val:
            return False
        if src_fld.type != "many2one":
            return None
        if src_fld.comodel_name == dst_fld.comodel_name:
            return source_val.id
        # fallback: mapear por nombre
        mapped = _map_by_name(Model.env, source_val, dst_fld.comodel_name)
        return mapped.id if mapped else None

    # many2many
    if dst_fld.type == "many2many":
        if src_fld.type != "many2many":
            return None
        if src_fld.comodel_name == dst_fld.comodel_name:
            return [(6, 0, source_val.ids)]
        mapped_ids = _map_many2many_by_name(Model.env, source_val, dst_fld.comodel_name)
        return [(6, 0, mapped_ids)] if mapped_ids else None

    return None


def _map_by_name(env, source_record, target_model):
    name = source_record.display_name or source_record.name
    if not name:
        return env[target_model]
    return env[target_model].search([("name", "=", name)], limit=1)


def _map_many2many_by_name(env, source_records, target_model):
    names = [n for n in source_records.mapped("display_name") if n]
    if not names:
        return []
    targets = env[target_model].search([("name", "in", names)])
    by_name = {t.name: t.id for t in targets if t.name}
    return [by_name[n] for n in names if n in by_name]


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
