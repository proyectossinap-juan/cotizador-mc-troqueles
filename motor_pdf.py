import fitz
import math
import re

PT_TO_CM = 1 / 28.3465

def dist(p1, p2):
    return math.sqrt((p2.x - p1.x)**2 + (p2.y - p1.y)**2)

def bezier_len(p0, p1, p2, p3, steps=100):
    length = 0
    prev = p0
    for i in range(1, steps + 1):
        t = i / steps
        mt = 1 - t
        x = mt**3*p0.x + 3*mt**2*t*p1.x + 3*mt*t**2*p2.x + t**3*p3.x
        y = mt**3*p0.y + 3*mt**2*t*p1.y + 3*mt*t**2*p2.y + t**3*p3.y
        curr = fitz.Point(x, y)
        length += dist(prev, curr)
        prev = curr
    return length

def color_categoria(r, g, b):
    """Clasifica un color RGB en categoría visual."""
    if r < 0.15 and g < 0.15 and b < 0.15:
        return "negro"
    if r > 0.65 and g < 0.35 and b < 0.35:
        return "rojo"
    if b > 0.45 and r < 0.45 and g < 0.55:
        return "azul"
    if g > 0.45 and b > 0.35 and r < 0.25:
        return "cyan"
    if r > 0.55 and g > 0.35 and b > 0.55:
        return "rosado"
    # Colores adicionales para archivos .ai
    if r > 0.7 and g > 0.7 and b < 0.3:
        return "amarillo"   # grafa en .ai
    if g > 0.45 and r < 0.35 and b < 0.35:
        return "verde"      # pretroquelado en .ai
    if r > 0.65 and g > 0.3 and b < 0.2:
        return "naranja"
    return f"otro ({r:.2f},{g:.2f},{b:.2f})"

def medir_path(p):
    recta = curva = 0
    for item in p.get('items', []):
        t = item[0]
        if t == 'l':
            recta += dist(item[1], item[2]) * PT_TO_CM
        elif t == 'c':
            curva += bezier_len(item[1], item[2], item[3], item[4]) * PT_TO_CM
        elif t == 're':
            rect = item[1]
            w = (rect.x1 - rect.x0) * PT_TO_CM
            h = (rect.y1 - rect.y0) * PT_TO_CM
            recta += 2 * (w + h)
    return recta, curva

def extraer_madera_texto(texto):
    """Busca dimensiones de madera en el texto del PDF."""
    patrones = [
        r'MADERA\s+(\d+[\.,]\d+)\s*[Xx]\s*(\d+[\.,]\d+)\s*CMS?',
        r'TAMA[ÑN]O\s+MADERA\s+(\d+)\s*[Xx]\s*(\d+)\s*MM',
        r'MADERA\s+(\d+)\s*[Xx]\s*(\d+)',
    ]
    for patron in patrones:
        m = re.search(patron, texto, re.IGNORECASE)
        if m:
            v1 = float(m.group(1).replace(',', '.'))
            v2 = float(m.group(2).replace(',', '.'))
            # Si están en mm, convertir a cm
            if 'MM' in patron:
                v1 /= 10
                v2 /= 10
            return v1, v2
    return None, None

def extraer_specs_texto(texto):
    """Extrae especificaciones técnicas del texto."""
    specs = {}
    # Cliente (primera línea generalmente)
    lineas = [l.strip() for l in texto.split('\n') if l.strip()]
    specs['texto_completo'] = texto

    # Máquina
    m = re.search(r'MAQUINA\s+(\w+)', texto, re.IGNORECASE)
    if m: specs['maquina'] = m.group(1)

    # Material
    m = re.search(r'MATERIAL\s+([^\n]+)', texto, re.IGNORECASE)
    if m: specs['material'] = m.group(1).strip()

    # Cuchilla pts
    m = re.search(r'CUCHILLA\s+([\d\.]+)', texto, re.IGNORECASE)
    if m: specs['cuchilla_pts'] = float(m.group(1))

    # Grafadora pts
    m = re.search(r'GRAFA[DOR]*\s+([\d\.]+)', texto, re.IGNORECASE)
    if m: specs['grafa_pts'] = float(m.group(1))

    # Perforadora paso
    m = re.search(r'PERFORADORA\s+(\d+)\s*[Xx]\s*(\d+)', texto, re.IGNORECASE)
    if m: specs['perf_paso'] = f"{m.group(1)}x{m.group(2)}"

    # Pinza
    m = re.search(r'PINZA\s+([\d\.]+)', texto, re.IGNORECASE)
    if m: specs['pinza'] = float(m.group(1))

    # Servicios adicionales
    servicios = []
    if re.search(r'ENCAUCHE', texto, re.IGNORECASE): servicios.append('Encauche técnico')
    if re.search(r'DESPIQUE', texto, re.IGNORECASE): servicios.append('Despique dinámico')
    if re.search(r'PERTINAX', texto, re.IGNORECASE): servicios.append('Pertinax')
    if re.search(r'DESCARTONE', texto, re.IGNORECASE): servicios.append('Descartone')
    if re.search(r'ARRASTRE', texto, re.IGNORECASE): servicios.append('Puntos de arrastre')
    if re.search(r'ESPEJO', texto, re.IGNORECASE): servicios.append('Derecho de impresión / Espejo')
    specs['servicios'] = servicios

    return specs

def analizar_pagina(page):
    """Analiza una página y retorna grupos de paths por color/dash."""
    paths = page.get_drawings()
    texto = page.get_text()

    # Agrupar paths por color + dash
    grupos = {}
    madera_rect = None

    for p in paths:
        c = p.get('color')
        dash = p.get('dashes', [])
        items = p.get('items', [])
        if not c:
            continue

        r, g, b = c
        cat = color_categoria(r, g, b)
        dash_str = 'punteado' if (dash and str(dash) != '[] 0') else 'solido'
        key = f"{cat}_{dash_str}"

        # Detectar rectángulo de madera (rect rojo o de cualquier color)
        for item in items:
            if item[0] == 're':
                rect = item[1]
                w = (rect.x1 - rect.x0) * PT_TO_CM
                h = (rect.y1 - rect.y0) * PT_TO_CM
                if w > 10 and h > 10:  # mínimo 10cm para ser madera
                    madera_rect = (round(w, 2), round(h, 2))

        # Medir
        recta, curva = medir_path(p)
        total = recta + curva
        if total < 0.001:
            continue

        if key not in grupos:
            grupos[key] = {
                'color_rgb': (round(r, 3), round(g, 3), round(b, 3)),
                'categoria': cat,
                'dash': dash_str,
                'recta_cm': 0,
                'curva_cm': 0,
                'total_cm': 0,
                'n_paths': 0,
                'paths_cortos': 0,   # ≤ 0.5cm (posible perforadora)
            }
        grupos[key]['recta_cm'] += recta
        grupos[key]['curva_cm'] += curva
        grupos[key]['total_cm'] += total
        grupos[key]['n_paths'] += 1
        if total <= 0.5:
            grupos[key]['paths_cortos'] += 1

    # Madera desde texto si no viene en rect
    mw, mh = extraer_madera_texto(texto)

    specs = extraer_specs_texto(texto)
    bb = calcular_bounding_box(page, margin=3)

    return {
        'grupos': grupos,
        'madera_rect': madera_rect,
        'madera_texto': (mw, mh) if mw else None,
        'bounding_box': bb,
        'specs': specs,
        'texto': texto,
    }

def calcular_bounding_box(page, margin=3):
    paths = page.get_drawings()
    rects = []
    for p in paths:
        c = p.get('color')
        if not c: continue
        r, g, b = c
        cat = color_categoria(r, g, b)
        if cat in ['cyan', 'rosado']: continue  # ignorar marcas
        rect = p.get('rect')
        if rect:
            rects.append(rect)
    if not rects:
        return None
    min_x = min(r.x0 for r in rects) * PT_TO_CM
    min_y = min(r.y0 for r in rects) * PT_TO_CM
    max_x = max(r.x1 for r in rects) * PT_TO_CM
    max_y = max(r.y1 for r in rects) * PT_TO_CM
    ancho = round((max_x - min_x) + 2 * margin, 2)
    alto  = round((max_y - min_y) + 2 * margin, 2)
    return (ancho, alto)

def analizar_pdf(pdf_path):
    """Analiza todas las páginas de un PDF de troquel."""
    doc = fitz.open(pdf_path)
    paginas = []
    for i, page in enumerate(doc):
        resultado = analizar_pagina(page)
        resultado['pagina'] = i + 1
        resultado['tam_pagina'] = (
            round(page.rect.width * PT_TO_CM, 2),
            round(page.rect.height * PT_TO_CM, 2)
        )
        paginas.append(resultado)
    doc.close()
    return paginas

def calcular_materiales(asignaciones, madera_cm):
    """
    Calcula totales de materiales a partir de asignaciones del usuario.
    asignaciones: dict {grupo_key: 'cuchilla'|'grafa'|'perforadora'|'ignorar'}
    madera_cm: (ancho, alto) en cm
    """
    cuchilla_recta = cuchilla_curva = 0
    grafa_recta = grafa_curva = 0
    perf_total = 0

    for key, tipo in asignaciones.items():
        # key tiene formato "grupo_key::recta::curva::paths_cortos"
        partes = key.split('::')
        recta = float(partes[1])
        curva = float(partes[2])
        paths_cortos = int(partes[3])
        total = recta + curva

        if tipo == 'cuchilla':
            # Separar perforadora de cuchilla por paths cortos
            prop_cortos = paths_cortos / max(1, int(partes[4])) if len(partes) > 4 else 0
            cuchilla_recta += recta
            cuchilla_curva += curva
        elif tipo == 'grafa':
            grafa_recta += recta
            grafa_curva += curva
        elif tipo == 'perforadora':
            perf_total += total

    cuchilla_total = cuchilla_recta + cuchilla_curva
    grafa_total = grafa_recta + grafa_curva

    madera_w, madera_h = madera_cm
    madera_area_m2 = (madera_w * madera_h) / 10000

    puentes = int(cuchilla_recta / 7.5)
    encauche_cm = cuchilla_total * 1.5

    return {
        'cuchilla_total': round(cuchilla_total, 2),
        'cuchilla_recta': round(cuchilla_recta, 2),
        'cuchilla_curva': round(cuchilla_curva, 2),
        'grafa_total': round(grafa_total, 2),
        'perf_total': round(perf_total, 2),
        'madera_w': madera_w,
        'madera_h': madera_h,
        'madera_area_m2': round(madera_area_m2, 4),
        'puentes': puentes,
        'encauche_cm': round(encauche_cm, 2),
    }
