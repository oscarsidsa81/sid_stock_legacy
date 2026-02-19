# -*- coding: utf-8 -*-
{
    "name": "SID Stock Legacy",
    "summary": "Migración de datos x_* (Studio) hacia sid_* (campos base) en modelos de stock.",
    "version": "15.0.1.0.1",
    "category": "Inventory/Inventory",
    "author": "SIDSA",
    "license": "LGPL-3",
    "depends": [
        "sid_stock_base",
        "sid_product_base",
    ],
    "data": [],
    "post_init_hook": "post_init_copy_stock_legacy_to_base",
    "installable": True,
    "application": False,
    "auto_install": False,
}
