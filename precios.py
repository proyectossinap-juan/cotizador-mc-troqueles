"""
Tabla de precios MC Troqueles 2026
Vigente desde 01 de marzo de 2026 (+12% sobre 2025)
"""

TIPOS_CUCHILLA = {
    "Cuchilla 2 pts - filo biselado (plegadiza)": 616,
    "Cuchilla 3 pts - cartón corrugado":          649,
    "Cuchilla compensación":                       504,
    "Cuchilla Supra Z":                            980,
    "Cuchilla Bohler CFDB (PRE)":                 940,
    "Cuchilla Bohler CF (TRO)":                   896,
    "Cuchilla flexografía":                        980,
}

TIPOS_GRAFA = {
    "Grafadora 2 pts 23.3 - plegadiza":   538,
    "Grafadora 3 pts 23.00 - corrugado":  571,
    "Grafadora 4 pts":                    823,
}

TIPOS_PERFORADORA = {
    "Perforadora / Corte-hendido 2 pts":  695,
}

PRECIO_MADERA_M2    = 100_000   # COP por m²
PRECIO_ENCAUCHE_CM  = 90        # COP por cm lineal (encauche = 1.5x cuchilla)
REGLA_ENCAUCHE      = 1.5       # multiplicador sobre cm de cuchilla

CAUCHOS = {
    "Cito Verde 35 Shore (70.3cm)":     {"precio_metro": 425_198, "ancho_cm": 70.3},
    "Profilgumi 5mm (70cm)":            {"precio_metro": 6_525,   "ancho_cm": 70.0},
    "Profilgumi 8mm (70cm)":            {"precio_metro": 6_525,   "ancho_cm": 70.0},
    "Polytop Azul Vulkoran (66.4cm)":   {"precio_metro": 4_946,   "ancho_cm": 66.4},
    "Verde 20 Shore Chino (37.6cm)":    {"precio_metro": 4_568,   "ancho_cm": 37.6},
    "EPDM Cito Negro 11x11 (69.5cm)":  {"precio_metro": 5_510,   "ancho_cm": 69.5},
    "EPDM Cito Negro 8x8 (69.5cm)":    {"precio_metro": 4_568,   "ancho_cm": 69.5},
    "Caucho Negro para Bolsas":         {"precio_metro": 10_212,  "ancho_cm": 100.0},
}

OTROS_INSUMOS = {
    "Nicks":                            1_100,
    "Barras en madera":                 12_000,
    "Rutear hembra":                    150,
    "Sacabocados con expulsor (1-15mm)": 2_500,
    "Cremallera (el par)":              1_900,
    "Corte-hendido Bohler":             38_570,
    "Stripping Rule 6mm":               2_946,
    "Stripping Rule 10mm":              3_068,
    "Stripping Rule 15mm":              3_476,
    "Stripping Rule 30mm":              4_211,
    "Stripping Rule 50mm":              5_337,
}

# Lista de clientes MC Troqueles — actualizada desde Clientes.xlsx
CLIENTES = {
    "INTERCALCO IMPRESORES S.A.S.":          "grande",
    "MARCA ZETA SAS":                         "pequeño",
    "DORICOLOR - INDULIT S.A.S.":            "grande",
    "ESPECIAL IMPRESORES SAS":               "pequeño",
    "INTERCOLOR SAS":                         "grande",
    "FOTOMONTAJES SAS":                       "pequeño",
    "SERVIBARRAS SAS":                        "pequeño",
    "IMPRESOS EL DIA SAS":                   "pequeño",
    "MULTIMPRESOS SAS":                       "pequeño",
    "LITOGRAFIKAZ S.A.S.":                   "pequeño",
    "EDITORIAL LA PATRIA S.A.":              "grande",
    "COMPAÑIA DE EMPAQUES SA":               "grande",
    "GRAFICAS DIAMANTE SAS":                  "pequeño",
    "AVERY DENINSON":                         "grande",
    "LITOGRAFIA FRANCISCO JARAMILLO V SAS":  "pequeño",
    "TIPALMA S.A.S.":                        "grande",
    "PILOTO S.A.S":                           "pequeño",
    "LITOGRAFIA NUEVA ERA ARTEIMPRES SAS":   "pequeño",
    "LITOGRAFIA GONAVA SAS":                  "pequeño",
    "TRAMAS LITOGRAFIA SAS":                  "pequeño",
    "LITOGRAFIA SECREA SAS":                  "pequeño",
    "PROPLANET SAS":                          "pequeño",
    "ARTROCOL LINEAL SAS":                    "pequeño",
    "SEEDPACK S.A.S.":                        "grande",
    "VALVER COLOMBIA SAS":                    "pequeño",
    "PIXIE HOUSE DESING SAS":                "pequeño",
    "SISTEMAS LITOGRÁFICOS SAS":             "pequeño",
    "INVERSIONES DCRUZ S.A.S.":              "pequeño",
    "MAQUILAS CHEPE S.A.S.":                 "pequeño",
    "MARQUIDEAS CO S.A.S.":                   "pequeño",
}

def calcular_cotizacion(materiales, tipo_cuchilla, tipo_grafa, tipo_perforadora,
                         recargo_pct=0, servicios_adicionales=None):
    """
    Calcula el valor total de la cotización.
    materiales: dict del motor_pdf.calcular_materiales()
    recargo_pct: porcentaje de recargo por dificultad (0-50)
    servicios_adicionales: list of (descripcion, valor)
    """
    if servicios_adicionales is None:
        servicios_adicionales = []

    precio_cuchilla    = TIPOS_CUCHILLA.get(tipo_cuchilla, 616)
    precio_grafa      = TIPOS_GRAFA.get(tipo_grafa, 538)
    precio_perforadora = TIPOS_PERFORADORA.get(tipo_perforadora, 695)

    val_cuchilla    = materiales['cuchilla_total'] * precio_cuchilla
    val_grafa      = materiales['grafa_total']   * precio_grafa
    val_perforadora = materiales['perf_total']     * precio_perforadora
    val_madera      = materiales['madera_area_m2'] * PRECIO_MADERA_M2
    val_encauche    = materiales['encauche_cm']    * PRECIO_ENCAUCHE_CM

    subtotal_materiales = val_cuchilla + val_grafa + val_perforadora + val_madera + val_encauche

    val_recargo = subtotal_materiales * (recargo_pct / 100)

    val_servicios = sum(v for _, v in servicios_adicionales)

    total = subtotal_materiales + val_recargo + val_servicios

    return {
        'detalle': {
            'Cuchilla':    {'cantidad': materiales['cuchilla_total'], 'unidad': 'cm', 'precio_unit': precio_cuchilla, 'valor': val_cuchilla},
            'Grafa':      {'cantidad': materiales['grafa_total'],   'unidad': 'cm', 'precio_unit': precio_grafa,   'valor': val_grafa},
            'Perforadora': {'cantidad': materiales['perf_total'],     'unidad': 'cm', 'precio_unit': precio_perforadora, 'valor': val_perforadora},
            'Madera':      {'cantidad': materiales['madera_area_m2'], 'unidad': 'm²', 'precio_unit': PRECIO_MADERA_M2,   'valor': val_madera},
            'Encauche':    {'cantidad': materiales['encauche_cm'],    'unidad': 'cm', 'precio_unit': PRECIO_ENCAUCHE_CM,  'valor': val_encauche},
        },
        'subtotal_materiales': subtotal_materiales,
        'recargo_pct': recargo_pct,
        'val_recargo': val_recargo,
        'servicios_adicionales': servicios_adicionales,
        'val_servicios': val_servicios,
        'total': total,
        'puentes': materiales['puentes'],
        'madera_dim': f"{materiales['madera_w']} × {materiales['madera_h']} cm",
    }
