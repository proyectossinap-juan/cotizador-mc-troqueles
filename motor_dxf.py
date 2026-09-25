"""
Motor de lectura de archivos DXF para MC Troqueles.

Características clave:
- Descompone bloques (INSERT) automáticamente → mide 1 troquel base
- Detecta repeticiones (matrices) e informa al usuario
- Clasifica por COLOR ACI (independiente del motor PDF)
- Convierte unidades automáticamente a cm
- NO hereda reglas de color del motor PDF
"""

import ezdxf
import math

UNIDADES_A_CM = {
    0: 1.0, 1: 2.54, 2: 30.48, 4: 0.1,
    5: 1.0, 6: 100.0, 13: 0.1, 14: 10.0,
}
UNIDADES_NOMBRE = {
    0: 'sin definir (asumido cm)', 1: 'pulgadas', 2: 'pies',
    4: 'milímetros', 5: 'centímetros', 6: 'metros',
}

ACI_INFO = {
    1:  {'nombre': 'rojo',      'rgb': (0.85, 0.1,  0.1)},
    2:  {'nombre': 'amarillo',  'rgb': (0.9,  0.85, 0.0)},
    3:  {'nombre': 'verde',     'rgb': (0.1,  0.75, 0.1)},
    4:  {'nombre': 'cyan',      'rgb': (0.1,  0.8,  0.8)},
    5:  {'nombre': 'azul',      'rgb': (0.1,  0.2,  0.85)},
    6:  {'nombre': 'magenta',   'rgb': (0.75, 0.1,  0.75)},
    7:  {'nombre': 'negro',     'rgb': (0.25, 0.25, 0.25)},
    8:  {'nombre': 'gris_osc',  'rgb': (0.4,  0.4,  0.4)},
    9:  {'nombre': 'gris_cla',  'rgb': (0.65, 0.65, 0.65)},
    10: {'nombre': 'naranja',   'rgb': (0.9,  0.45, 0.1)},
    30: {'nombre': 'naranja2',  'rgb': (0.85, 0.55, 0.1)},
    97: {'nombre': 'azul_osc',  'rgb': (0.1,  0.15, 0.6)},
    98: {'nombre': 'azul_med',  'rgb': (0.2,  0.3,  0.7)},
}

def aci_info(c):
    if c in ACI_INFO: return ACI_INFO[c]
    if 10 <= c <= 19:   return {'nombre': f'rojo_v{c}',     'rgb': (0.85, 0.2, 0.2)}
    if 20 <= c <= 29:   return {'nombre': f'naranja_v{c}',  'rgb': (0.85, 0.5, 0.1)}
    if 50 <= c <= 69:   return {'nombre': f'amarillo_v{c}', 'rgb': (0.85, 0.8, 0.1)}
    if 80 <= c <= 99:   return {'nombre': f'verde_v{c}',    'rgb': (0.1,  0.7, 0.3)}
    if 130 <= c <= 149: return {'nombre': f'cyan_v{c}',     'rgb': (0.1,  0.7, 0.8)}
    if 150 <= c <= 169: return {'nombre': f'azul_v{c}',     'rgb': (0.1,  0.3, 0.8)}
    if 190 <= c <= 209: return {'nombre': f'magenta_v{c}',  'rgb': (0.7,  0.1, 0.7)}
    if 250 <= c <= 255: return {'nombre': f'gris_{c}',      'rgb': (0.6,  0.6, 0.6)}
    return {'nombre': f'color_{c}', 'rgb': (0.5, 0.5, 0.5)}

CAPAS_IGNORAR = {
    'annotation','defpoints','borde','border','ref',
    'fibra','text','texto','dimension','cotas','hatch','frame','marco'
}

def debe_ignorar_capa(nombre):
    return any(x in nombre.lower() for x in CAPAS_IGNORAR)

def sugerir_por_aci(color_aci, nombre_color, total_cm):
    if total_cm < 2: return 'ignorar'
    n = nombre_color.lower()
    if 'rojo'    in n: return 'cuchilla'
    if 'negro'   in n: return 'cuchilla'
    if 'azul'    in n: return 'cuchilla'
    if 'amarill' in n: return 'grafa'
    if 'verde'   in n: return 'grafa'
    if 'magenta' in n: return 'perforadora'
    if 'naranja' in n: return 'ignorar'
    if 'cyan'    in n: return 'ignorar'
    return '— sin asignar —'

def resolver_color(ent, doc):
    c = getattr(ent.dxf, 'color', 256)
    if c in (0, 256):
        try: c = doc.layers.get(ent.dxf.layer).dxf.color
        except: c = 7
    return c

TIPOS_MEDIBLES = {'LINE','ARC','CIRCLE','LWPOLYLINE','SPLINE','ELLIPSE'}

def medir_line(e, f):
    p1,p2 = e.dxf.start, e.dxf.end
    return math.sqrt((p2.x-p1.x)**2+(p2.y-p1.y)**2)*f, 0.0

def medir_arc(e, f):
    r = e.dxf.radius*f
    a1 = math.radians(e.dxf.start_angle)
    a2 = math.radians(e.dxf.end_angle)
    if a2 <= a1: a2 += 2*math.pi
    return 0.0, r*(a2-a1)

def medir_circle(e, f):
    return 0.0, 2*math.pi*e.dxf.radius*f

def medir_lwpolyline(e, f):
    pts = list(e.get_points())
    recta = curva = 0.0
    for i in range(len(pts)-1):
        dx=(pts[i+1][0]-pts[i][0])*f; dy=(pts[i+1][1]-pts[i][1])*f
        bulge = pts[i][4] if len(pts[i])>4 else 0
        if bulge != 0:
            d = math.sqrt(dx**2+dy**2)
            theta = 4*math.atan(abs(bulge))
            r = d/(2*math.sin(theta/2)) if math.sin(theta/2)!=0 else 0
            curva += r*theta if r>0 else math.sqrt(dx**2+dy**2)
        else:
            recta += math.sqrt(dx**2+dy**2)
    if e.is_closed and len(pts)>1:
        dx=(pts[0][0]-pts[-1][0])*f; dy=(pts[0][1]-pts[-1][1])*f
        recta += math.sqrt(dx**2+dy**2)
    return recta, curva

def medir_spline(e, f):
    try:
        pts = list(e.flattening(0.05))
        return 0.0, sum(math.sqrt((pts[i+1].x-pts[i].x)**2+(pts[i+1].y-pts[i].y)**2)*f for i in range(len(pts)-1))
    except: return 0.0, 0.0

def medir_ellipse(e, f):
    try:
        pts = list(e.flattening(0.05))
        return 0.0, sum(math.sqrt((pts[i+1].x-pts[i].x)**2+(pts[i+1].y-pts[i].y)**2)*f for i in range(len(pts)-1))
    except: return 0.0, 0.0

def medir_entidad(e, f):
    t = e.dxftype()
    try:
        if t=='LINE':       return medir_line(e,f)
        if t=='ARC':        return medir_arc(e,f)
        if t=='CIRCLE':     return medir_circle(e,f)
        if t=='LWPOLYLINE': return medir_lwpolyline(e,f)
        if t=='SPLINE':     return medir_spline(e,f)
        if t=='ELLIPSE':    return medir_ellipse(e,f)
    except: pass
    return 0.0, 0.0

def procesar_coleccion(entidades, doc, factor):
    grupos = {}
    for ent in entidades:
        if ent.dxftype() not in TIPOS_MEDIBLES: continue
        if debe_ignorar_capa(ent.dxf.layer): continue
        color_aci = resolver_color(ent, doc)
        info = aci_info(color_aci)
        key = f"ACI_{color_aci}"
        recta, curva = medir_entidad(ent, factor)
        if recta+curva < 0.001: continue
        if key not in grupos:
            grupos[key] = {
                'color_aci': color_aci, 'color_nombre': info['nombre'],
                'color_rgb': info['rgb'], 'recta_cm': 0.0, 'curva_cm': 0.0,
                'total_cm': 0.0, 'n_entidades': 0, 'tipos_ent': set(), 'capas': set(),
            }
        grupos[key]['recta_cm']    += recta
        grupos[key]['curva_cm']    += curva
        grupos[key]['total_cm']    += recta+curva
        grupos[key]['n_entidades'] += 1
        grupos[key]['tipos_ent'].add(ent.dxftype())
        grupos[key]['capas'].add(ent.dxf.layer)
    return grupos

def calcular_bbox(entidades, factor, margin=3.0):
    xs, ys = [], []
    for e in entidades:
        try:
            t = e.dxftype()
            if t == 'LINE':
                xs += [e.dxf.start.x*factor, e.dxf.end.x*factor]
                ys += [e.dxf.start.y*factor, e.dxf.end.y*factor]
            elif t in ('ARC','CIRCLE'):
                cx,cy,r = e.dxf.center.x*factor, e.dxf.center.y*factor, e.dxf.radius*factor
                xs += [cx-r,cx+r]; ys += [cy-r,cy+r]
            elif t == 'LWPOLYLINE':
                for pt in e.get_points():
                    xs.append(pt[0]*factor); ys.append(pt[1]*factor)
        except: pass
    if not xs: return None
    return (round((max(xs)-min(xs))+2*margin,2), round((max(ys)-min(ys))+2*margin,2))

def analizar_dxf(dxf_path):
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()

    unidad_code = doc.header.get('$INSUNITS', 0)
    factor = UNIDADES_A_CM.get(unidad_code, 1.0)

    # Detectar bloques repetidos
    inserts_count = {}
    for e in msp:
        if e.dxftype() == 'INSERT':
            inserts_count[e.dxf.name] = inserts_count.get(e.dxf.name, 0) + 1

    bloque_principal = None
    n_repeticiones = 1
    info_bloques = {}

    if inserts_count:
        bloque_principal = max(inserts_count, key=lambda k: inserts_count[k])
        n_repeticiones = inserts_count[bloque_principal]
        info_bloques = {
            'nombre': bloque_principal,
            'repeticiones': n_repeticiones,
            'mensaje': f"Troquel en placa {n_repeticiones}× — midiendo 1 unidad base"
        }

    # Medir bloque base
    if bloque_principal:
        entidades = list(doc.blocks[bloque_principal])
        grupos = procesar_coleccion(entidades, doc, factor)
        bbox = calcular_bbox(entidades, factor)
    else:
        entidades = list(msp)
        grupos = procesar_coleccion(entidades, doc, factor)
        bbox = calcular_bbox(entidades, factor)

    # Agregar sugerencias y limpiar sets
    for key, g in grupos.items():
        g['sugerencia_dxf'] = sugerir_por_aci(g['color_aci'], g['color_nombre'], g['total_cm'])
        g['tipos_ent'] = list(g['tipos_ent'])
        g['capas']     = list(g['capas'])
        g['recta_cm']  = round(g['recta_cm'], 2)
        g['curva_cm']  = round(g['curva_cm'], 2)
        g['total_cm']  = round(g['total_cm'], 2)

    specs = {
        'unidades_codigo':   unidad_code,
        'unidades_nombre':   UNIDADES_NOMBRE.get(unidad_code, f'código {unidad_code}'),
        'factor_cm':         factor,
        'n_repeticiones':    n_repeticiones,
        'bloque_principal':  bloque_principal or 'entidades directas',
        'capas_disponibles': [l.dxf.name for l in doc.layers],
        'servicios':         [],
    }

    return {
        'tipo_archivo': 'dxf',
        'pagina':       1,
        'grupos_dxf':   grupos,
        'grupos':       _a_formato_app(grupos),
        'madera_rect':  None,
        'madera_texto': None,
        'bounding_box': bbox,
        'specs':        specs,
        'texto':        '',
        'info_bloques': info_bloques,
    }

def _a_formato_app(grupos_dxf):
    out = {}
    for key, g in grupos_dxf.items():
        out[key] = {
            'color_rgb':      g['color_rgb'],
            'categoria':      g['color_nombre'],
            'dash':           'solido',
            'recta_cm':       g['recta_cm'],
            'curva_cm':       g['curva_cm'],
            'total_cm':       g['total_cm'],
            'n_paths':        g['n_entidades'],
            'paths_cortos':   0,
            'capa':           g['capas'][0] if g['capas'] else '',
            'color_aci':      g['color_aci'],
            'sugerencia_dxf': g['sugerencia_dxf'],
            'tipos_ent':      g['tipos_ent'],
            'es_dxf':         True,
        }
    return out
