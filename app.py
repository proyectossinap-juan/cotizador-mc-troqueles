import streamlit as st
import tempfile, os, json
from datetime import datetime
import pandas as pd

from motor_pdf import analizar_pdf, calcular_materiales
from motor_dxf import analizar_dxf
from precios import (
    TIPOS_CUCHILLA, TIPOS_GRAFA, TIPOS_PERFORADORA,
    CLIENTES, calcular_cotizacion, PRECIO_MADERA_M2,
    PRECIO_ENCAUCHE_CM, REGLA_ENCAUCHE
)

# ─── CONFIG ────────────────────────────────────────────────
st.set_page_config(
    page_title="MC Troqueles — Cotizador",
    page_icon="✂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── ESTILOS ────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow:wght@400;500;600&family=Barlow+Condensed:wght@600;700;800&display=swap');

:root {
    --azul-acero:   #1C2B3A;
    --azul-medio:   #2E4A6B;
    --azul-claro:   #4A7BAE;
    --gris-grafito: #3D4654;
    --gris-medio:   #6B7685;
    --gris-claro:   #EDF0F4;
    --gris-borde:   #D1D9E0;
    --blanco:       #FFFFFF;
    --texto:        #1C2B3A;
    --acento:       #4A7BAE;
}

html, body, [class*="css"] {
    font-family: 'Barlow', sans-serif;
    background-color: var(--gris-claro);
    color: var(--texto);
}
.stApp { background-color: var(--gris-claro); }

/* ── HEADER ─────────────────────────────────── */
.mc-header {
    background: var(--azul-acero);
    padding: 1.2rem 2rem;
    border-radius: 10px;
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-shadow: 0 3px 12px rgba(28,43,58,0.25);
}
.mc-header-left { display: flex; align-items: center; gap: 1rem; }
.mc-logo-icon {
    width: 42px; height: 42px;
    background: var(--azul-claro);
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.4rem;
}
.mc-header-left h1 {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1.7rem;
    color: var(--blanco);
    margin: 0;
    font-weight: 800;
    letter-spacing: 2px;
    text-transform: uppercase;
}
.mc-header-left p {
    color: rgba(255,255,255,0.55);
    margin: 0;
    font-size: 0.78rem;
    font-weight: 400;
    letter-spacing: 0.5px;
}
.mc-header-right {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 4px;
}
.mc-badge {
    background: rgba(74,123,174,0.25);
    border: 1px solid var(--azul-claro);
    color: #8DB8D8;
    border-radius: 4px;
    padding: 0.25rem 0.75rem;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
}

/* ── CARDS ──────────────────────────────────── */
.mc-card {
    background: var(--blanco);
    border: 1px solid var(--gris-borde);
    border-radius: 8px;
    padding: 1.4rem;
    margin-bottom: 1rem;
    box-shadow: 0 1px 4px rgba(28,43,58,0.07);
}
.mc-card-title {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 0.8rem;
    color: var(--azul-claro);
    letter-spacing: 2px;
    text-transform: uppercase;
    font-weight: 700;
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid var(--gris-claro);
}

/* ── MÉTRICAS ───────────────────────────────── */
.metric-row {
    display: flex;
    gap: 0.6rem;
    margin-bottom: 1rem;
    flex-wrap: wrap;
}
.metric-item {
    flex: 1;
    min-width: 100px;
    background: var(--blanco);
    border-radius: 8px;
    padding: 0.85rem 1rem;
    border-left: 3px solid var(--azul-claro);
    box-shadow: 0 1px 3px rgba(28,43,58,0.08);
}
.metric-item .m-label {
    font-size: 0.65rem;
    color: var(--gris-medio);
    text-transform: uppercase;
    letter-spacing: 1.2px;
    font-weight: 600;
}
.metric-item .m-value {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1.6rem;
    color: var(--azul-acero);
    font-weight: 700;
    line-height: 1.2;
}
.metric-item .m-unit { font-size: 0.68rem; color: var(--gris-medio); }

/* ── TABLA DETALLE ──────────────────────────── */
.detalle-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.6rem 0.5rem;
    border-bottom: 1px solid var(--gris-claro);
    border-radius: 4px;
    transition: background 0.15s;
}
.detalle-row:hover { background: var(--gris-claro); }
.detalle-row:last-child { border-bottom: none; }
.detalle-nombre { color: var(--texto); font-size: 0.88rem; font-weight: 500; }
.detalle-cant { color: var(--gris-medio); font-size: 0.75rem; margin-top: 1px; }
.detalle-valor { font-weight: 700; color: var(--azul-medio); font-size: 0.92rem; font-family: 'Barlow Condensed', sans-serif; letter-spacing: 0.5px; }

/* ── TOTAL BOX ──────────────────────────────── */
.total-box {
    background: linear-gradient(145deg, var(--azul-acero) 0%, var(--azul-medio) 100%);
    border-radius: 10px;
    padding: 1.8rem;
    text-align: center;
    margin-top: 1.5rem;
    box-shadow: 0 6px 20px rgba(28,43,58,0.3);
    border: 1px solid rgba(74,123,174,0.2);
}
.total-box .label {
    color: rgba(255,255,255,0.6);
    font-size: 0.68rem;
    letter-spacing: 2px;
    text-transform: uppercase;
    font-weight: 600;
}
.total-box .valor {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 2.8rem;
    color: white;
    font-weight: 800;
    letter-spacing: 1px;
    line-height: 1.1;
}
.total-box .subtotal-line {
    color: rgba(255,255,255,0.65);
    font-size: 0.85rem;
    font-family: 'Barlow Condensed', sans-serif;
    font-weight: 600;
    letter-spacing: 0.5px;
}

/* ── SIDEBAR ────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: var(--blanco);
    border-right: 1px solid var(--gris-borde);
}
section[data-testid="stSidebar"] .stMarkdown h2 {
    font-family: 'Barlow Condensed', sans-serif;
    color: var(--azul-acero);
    letter-spacing: 1.5px;
    font-size: 0.8rem;
    text-transform: uppercase;
    font-weight: 800;
}

/* ── BOTONES ────────────────────────────────── */
.stButton > button {
    background: var(--azul-acero) !important;
    color: white !important;
    border: none !important;
    border-radius: 6px !important;
    font-family: 'Barlow Condensed', sans-serif !important;
    font-weight: 700 !important;
    letter-spacing: 1.5px !important;
    font-size: 0.95rem !important;
    padding: 0.55rem 2rem !important;
    text-transform: uppercase !important;
    transition: all 0.2s !important;
    box-shadow: 0 2px 8px rgba(28,43,58,0.2) !important;
}
.stButton > button:hover {
    background: var(--azul-medio) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 14px rgba(28,43,58,0.3) !important;
}

/* ── STEPS BADGE ────────────────────────────── */
.step-badge {
    background: var(--azul-acero);
    color: white;
    border-radius: 50%;
    width: 24px;
    height: 24px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.75rem;
    margin-right: 8px;
    font-family: 'Barlow Condensed', sans-serif;
}

/* ── AVISO ──────────────────────────────────── */
.aviso {
    background: #EDF2F7;
    border: 1px solid var(--gris-borde);
    border-left: 3px solid var(--azul-claro);
    border-radius: 6px;
    padding: 0.8rem 1rem;
    margin: 0.5rem 0;
    font-size: 0.82rem;
    color: var(--gris-grafito);
}

/* ── MISC ───────────────────────────────────── */
hr { border-color: var(--gris-borde) !important; }
.stCaption { color: var(--gris-medio) !important; }
.streamlit-expanderHeader {
    background: var(--gris-claro) !important;
    color: var(--azul-acero) !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    font-family: 'Barlow', sans-serif !important;
}
</style>
""", unsafe_allow_html=True)

# ─── SESSION STATE ──────────────────────────────────────────
if 'paginas' not in st.session_state:
    st.session_state.paginas = None
if 'pagina_activa' not in st.session_state:
    st.session_state.pagina_activa = 0
if 'asignaciones' not in st.session_state:
    st.session_state.asignaciones = {}
if 'materiales_calc' not in st.session_state:
    st.session_state.materiales_calc = None
if 'cotizacion' not in st.session_state:
    st.session_state.cotizacion = None
if 'tipo_archivo' not in st.session_state:
    st.session_state.tipo_archivo = 'pdf'

# ─── CONVERSIÓN DXF → FORMATO APP ───────────────────────────
def convertir_dxf_a_formato_app(resultado_dxf):
    # El motor_dxf actualizado ya entrega grupos en formato compatible
    # Solo necesitamos pasar el resultado directamente
    return {
        "tipo_archivo": "dxf",
        "pagina":       1,
        "grupos":       resultado_dxf.get("grupos", {}),
        "madera_rect":  resultado_dxf.get("madera_rect"),
        "madera_texto": resultado_dxf.get("madera_texto"),
        "bounding_box": resultado_dxf.get("bounding_box"),
        "specs":        resultado_dxf.get("specs", {}),
        "texto":        "",
        "info_bloques": resultado_dxf.get("info_bloques", {}),
    }

# ─── HEADER ────────────────────────────────────────────────
st.markdown("""
<div class="mc-header">
    <div class="mc-header-left">
        <div class="mc-logo-icon">⬡</div>
        <div>
            <h1>MC TROQUELES</h1>
            <p>Sistema de Cotización · Medellín, Colombia</p>
        </div>
    </div>
    <div class="mc-header-right">
        <span class="mc-badge">Tarifas 2026</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── SIDEBAR ────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## DATOS DEL TRABAJO")
    st.markdown("---")

    cliente_nombres = list(CLIENTES.keys()) + ["Nuevo cliente..."]
    cliente_sel = st.selectbox("Cliente", cliente_nombres)
    if cliente_sel == "Nuevo cliente...":
        cliente_nombre = st.text_input("Nombre del cliente")
    else:
        cliente_nombre = cliente_sel

    st.markdown("---")
    st.markdown("## TIPO DE MATERIALES")

    tipo_cuchilla = st.selectbox("Tipo de cuchilla", list(TIPOS_CUCHILLA.keys()))
    precio_cuchilla = TIPOS_CUCHILLA[tipo_cuchilla]
    st.caption(f"💰 ${precio_cuchilla:,} / cm")

    tipo_grafa = st.selectbox("Tipo de grafa/hendido", list(TIPOS_GRAFA.keys()))
    precio_grafa = TIPOS_GRAFA[tipo_grafa]
    st.caption(f"💰 ${precio_grafa:,} / cm")

    tipo_perforadora = st.selectbox("Tipo de perforadora", list(TIPOS_PERFORADORA.keys()))
    precio_perf = TIPOS_PERFORADORA[tipo_perforadora]
    st.caption(f"💰 ${precio_perf:,} / cm")

    st.markdown("---")
    st.markdown("## AJUSTES")
    recargo = st.slider("Recargo por dificultad (%)", 0, 50, 0, step=5)
    if recargo > 0:
        st.caption(f"⚠️ Se aplicará +{recargo}% sobre materiales")

    st.markdown("---")
    st.markdown("## SERVICIOS ADICIONALES")
    srv_despique = st.checkbox("Despique dinámico")
    val_despique = st.number_input("Valor despique ($)", 0, 5_000_000, 0, 10_000) if srv_despique else 0

    srv_pertinax = st.checkbox("Pertinax")
    val_pertinax = st.number_input("Valor pertinax ($)", 0, 5_000_000, 0, 10_000) if srv_pertinax else 0

    srv_arrastre = st.checkbox("Puntos de arrastre")
    val_arrastre = st.number_input("Valor arrastre ($)", 0, 1_000_000, 0, 5_000) if srv_arrastre else 0

    srv_descartone = st.checkbox("Descartone")
    val_descartone = st.number_input("Valor descartone ($)", 0, 2_000_000, 0, 10_000) if srv_descartone else 0

    srv_otro = st.checkbox("Otro servicio")
    if srv_otro:
        nombre_otro = st.text_input("Descripción")
        val_otro = st.number_input("Valor ($)", 0, 10_000_000, 0, 10_000)
    else:
        nombre_otro = ""
        val_otro = 0

# ─── PASO 1: CARGAR PDF ────────────────────────────────────
st.markdown('<span class="step-badge">1</span> **CARGAR ARCHIVO DEL TROQUEL**', unsafe_allow_html=True)

col_up1, col_up2 = st.columns([3,1])
with col_up1:
    uploaded = st.file_uploader(
        "Sube el archivo del troquel (PDF, AI o DXF)",
        type=['pdf', 'ai', 'dxf'],
        label_visibility="collapsed"
    )
with col_up2:
    st.markdown("""
    <div style="background:#1a1a1a;border:1px solid #333;border-radius:8px;padding:0.8rem;margin-top:0.3rem;font-size:0.8rem;color:#888">
        ✅ <b style="color:#ccc">PDF</b> vectorial<br>
        ✅ <b style="color:#ccc">AI</b> Adobe Illustrator<br>
        ✅ <b style="color:#ccc">DXF</b> AutoCAD / CorelDraw
    </div>
    """, unsafe_allow_html=True)

if uploaded:
    extension = uploaded.name.split('.')[-1].lower()
    suffix = f'.{extension}'

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded.read())
        tmp_path = tmp.name

    with st.spinner(f"Leyendo el troquel ({extension.upper()})..."):
        try:
            if extension in ('pdf', 'ai'):
                paginas = analizar_pdf(tmp_path)
                st.session_state.tipo_archivo = 'pdf'
            elif extension == 'dxf':
                resultado_dxf = analizar_dxf(tmp_path)
                # Convertir formato DXF al formato estándar de la app
                paginas = [convertir_dxf_a_formato_app(resultado_dxf)]
                st.session_state.tipo_archivo = 'dxf'

            st.session_state.paginas = paginas
            st.session_state.asignaciones = {}
            st.success(f"✅ {uploaded.name} leído — {len(paginas)} troquel(es) encontrado(s)")
            # Mostrar info de bloques para DXF
            if extension == 'dxf' and paginas[0].get('info_bloques'):
                ib = paginas[0]['info_bloques']
                if ib.get('repeticiones', 1) > 1:
                    st.info(f"📐 {ib['mensaje']} — cotizando 1 unidad")
        except Exception as e:
            st.error(f"❌ Error leyendo el archivo: {str(e)}")

    os.unlink(tmp_path)

# ─── PASO 2: CLASIFICAR LÍNEAS ──────────────────────────────
if st.session_state.paginas:
    paginas = st.session_state.paginas
    st.markdown("---")
    st.markdown('<span class="step-badge">2</span> **CLASIFICAR LÍNEAS DEL TROQUEL**', unsafe_allow_html=True)
    st.caption("Asigna qué representa cada grupo de líneas detectado")

    # Tabs si hay varias páginas
    if len(paginas) > 1:
        tabs = st.tabs([f"Troquel {p['pagina']}" for p in paginas])
    else:
        tabs = [st.container()]

    COLOR_MAP = {
        'negro':    '#444',
        'rojo':     '#E53E3E',
        'azul':     '#1E5FAD',
        'cyan':     '#2FB5B5',
        'rosado':   '#D48FAD',
        'amarillo': '#F6C90E',
        'verde':    '#2ECC71',
        'naranja':  '#E67E22',
    }

    for idx, (tab, pagina) in enumerate(zip(tabs, paginas)):
        with tab:
            specs = pagina['specs']
            col_info, col_grupos = st.columns([1, 2])

            with col_info:
                st.markdown('<div class="mc-card">', unsafe_allow_html=True)
                st.markdown('<div class="mc-card-title">ESPECIFICACIONES</div>', unsafe_allow_html=True)
                if specs.get('maquina'):
                    st.markdown(f"🏭 **Máquina:** {specs['maquina']}")
                if specs.get('material'):
                    st.markdown(f"📦 **Material:** {specs['material']}")
                if specs.get('cuchilla_pts'):
                    st.markdown(f"✂️ **Cuchilla:** {specs['cuchilla_pts']} pts")
                if specs.get('grafa_pts'):
                    st.markdown(f"📏 **Grafadora:** {specs['grafa_pts']} pts")
                if specs.get('perf_paso'):
                    st.markdown(f"⭕ **Perforadora:** paso {specs['perf_paso']}")
                if specs.get('servicios'):
                    st.markdown(f"🔧 **Servicios:** {', '.join(specs['servicios'])}")

                # Madera
                mw = mh = None
                if pagina['madera_texto']:
                    mw, mh = pagina['madera_texto']
                    st.markdown(f"🪵 **Madera (archivo):** {mw} × {mh} cm")
                elif pagina['madera_rect']:
                    mw, mh = pagina['madera_rect']
                    st.markdown(f"🪵 **Madera (rectángulo):** {mw} × {mh} cm")
                elif pagina['bounding_box']:
                    mw, mh = pagina['bounding_box']
                    st.markdown(f"🪵 **Madera (calculada +3cm):** {mw} × {mh} cm")

                if mw and mh:
                    area_m2 = (mw * mh) / 10000
                    st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;Área: {area_m2:.4f} m²")

                # Guardar madera en session
                if mw and mh:
                    st.session_state[f'madera_{idx}'] = (mw, mh)

                st.markdown("</div>", unsafe_allow_html=True)

                # Override manual de madera
                with st.expander("✏️ Ajustar dimensiones de madera"):
                    mw_override = st.number_input("Ancho (cm)", 0.0, 300.0,
                        float(mw) if mw else 0.0, 0.5, key=f"mw_{idx}")
                    mh_override = st.number_input("Alto (cm)", 0.0, 300.0,
                        float(mh) if mh else 0.0, 0.5, key=f"mh_{idx}")
                    if mw_override > 0 and mh_override > 0:
                        st.session_state[f'madera_{idx}'] = (mw_override, mh_override)

            with col_grupos:
                st.markdown('<div class="mc-card">', unsafe_allow_html=True)
                st.markdown('<div class="mc-card-title">GRUPOS DE LÍNEAS DETECTADOS</div>', unsafe_allow_html=True)

                grupos = pagina['grupos']
                OPCIONES = ['— sin asignar —', 'cuchilla', 'grafa', 'perforadora', 'ignorar']

                # Sugerencia automática por color
                def sugerir(cat, dash, paths_cortos, n_paths, total):
                    # Colores estándar PDF/AI
                    if cat in ('cyan', 'rosado'): return 'ignorar'   # marcos en .ai
                    if cat == 'verde':            return 'perforadora' # pretroquelado en .ai
                    if cat == 'amarillo':         return 'grafa'       # grafa en .ai
                    if cat == 'azul' and dash == 'solido': return 'cuchilla'
                    if cat == 'rojo' and dash == 'punteado': return 'grafa'
                    if cat == 'rojo' and dash == 'solido':  return 'cuchilla'  # cuchilla en .ai
                    if cat == 'negro' and dash == 'punteado': return 'perforadora'
                    if cat == 'negro' and dash == 'solido':
                        ratio = paths_cortos / max(1, n_paths)
                        if ratio > 0.7: return 'perforadora'
                        return 'cuchilla'
                    return '— sin asignar —'

                for key, grupo in grupos.items():
                    cat   = grupo['categoria']
                    dash  = grupo['dash']
                    total = grupo['total_cm']
                    recta = grupo['recta_cm']
                    curva = grupo['curva_cm']
                    n     = grupo['n_paths']
                    cortos= grupo['paths_cortos']

                    sugerencia = grupo.get('sugerencia_dxf') or sugerir(cat, dash, cortos, n, total)
                    storage_key = f"asig_{idx}_{key}"
                    data_key = f"{key}::{recta:.2f}::{curva:.2f}::{cortos}::{n}"

                    col_badge, col_info2, col_sel = st.columns([0.08, 0.5, 0.42])

                    rgb = grupo['color_rgb']
                    css_color = f"rgb({int(rgb[0]*255)},{int(rgb[1]*255)},{int(rgb[2]*255)})"

                    with col_badge:
                        st.markdown(f'<div style="width:18px;height:18px;border-radius:50%;background:{css_color};margin-top:8px;border:1px solid #555"></div>', unsafe_allow_html=True)

                    with col_info2:
                        dash_icon = "╌" if dash == 'punteado' else "—"
                        st.markdown(f"**{cat.upper()}** {dash_icon} `{total:.1f} cm` *(recta: {recta:.1f} | curva: {curva:.1f})*")
                        st.caption(f"{n} paths · {cortos} segmentos cortos (≤0.5cm)")

                    with col_sel:
                        idx_default = OPCIONES.index(sugerencia) if sugerencia in OPCIONES else 0
                        asig = st.selectbox("", OPCIONES, index=idx_default, key=storage_key, label_visibility="collapsed")
                        if asig != '— sin asignar —':
                            st.session_state.asignaciones[data_key] = asig

                st.markdown("</div>", unsafe_allow_html=True)

# ─── PASO 3: CALCULAR Y COTIZAR ────────────────────────────
if st.session_state.paginas and st.session_state.asignaciones:
    st.markdown("---")
    st.markdown('<span class="step-badge">3</span> **CALCULAR COTIZACIÓN**', unsafe_allow_html=True)

    if st.button("⚡ GENERAR COTIZACIÓN", use_container_width=True):
        # Consolidar materiales de todas las páginas
        # Por ahora tomamos página 0 (se puede extender a multipage)
        pagina_idx = st.session_state.pagina_activa
        madera = st.session_state.get(f'madera_{pagina_idx}', (0, 0))

        if madera[0] == 0:
            st.error("⚠️ Define las dimensiones de madera antes de continuar.")
        else:
            mats = calcular_materiales(st.session_state.asignaciones, madera)

            servicios = []
            if srv_despique and val_despique > 0: servicios.append(("Despique dinámico", val_despique))
            if srv_pertinax and val_pertinax > 0: servicios.append(("Pertinax", val_pertinax))
            if srv_arrastre and val_arrastre > 0: servicios.append(("Puntos de arrastre", val_arrastre))
            if srv_descartone and val_descartone > 0: servicios.append(("Descartone", val_descartone))
            if srv_otro and val_otro > 0: servicios.append((nombre_otro, val_otro))

            cotizacion = calcular_cotizacion(
                mats, tipo_cuchilla, tipo_grafa, tipo_perforadora,
                recargo_pct=recargo,
                servicios_adicionales=servicios
            )
            st.session_state.materiales_calc = mats
            st.session_state.cotizacion = cotizacion
            st.session_state.cliente_nombre = cliente_nombre

# ─── RESULTADO ─────────────────────────────────────────────
if st.session_state.cotizacion:
    cot = st.session_state.cotizacion
    mats = st.session_state.materiales_calc
    cliente_nombre = st.session_state.get('cliente_nombre', '')

    st.markdown("---")
    st.markdown('<span class="step-badge">4</span> **RESULTADO DE LA COTIZACIÓN**', unsafe_allow_html=True)

    # Métricas de materiales
    st.markdown(f"""
    <div class="metric-row">
        <div class="metric-item">
            <div class="m-label">Cuchilla</div>
            <div class="m-value">{mats['cuchilla_total']:.0f}</div>
            <div class="m-unit">cm lineales</div>
        </div>
        <div class="metric-item">
            <div class="m-label">Grafa</div>
            <div class="m-value">{mats['grafa_total']:.0f}</div>
            <div class="m-unit">cm lineales</div>
        </div>
        <div class="metric-item">
            <div class="m-label">Perforadora</div>
            <div class="m-value">{mats['perf_total']:.0f}</div>
            <div class="m-unit">cm lineales</div>
        </div>
        <div class="metric-item">
            <div class="m-label">Puentes</div>
            <div class="m-value">{mats['puentes']}</div>
            <div class="m-unit">unidades</div>
        </div>
        <div class="metric-item">
            <div class="m-label">Madera</div>
            <div class="m-value">{mats['madera_area_m2']:.3f}</div>
            <div class="m-unit">m² · {cot['madera_dim']}</div>
        </div>
        <div class="metric-item">
            <div class="m-label">Encauche</div>
            <div class="m-value">{mats['encauche_cm']:.0f}</div>
            <div class="m-unit">cm (1.5× cuchilla)</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Detalle de valores
    col_det, col_total = st.columns([3, 2])

    with col_det:
        st.markdown('<div class="mc-card">', unsafe_allow_html=True)
        st.markdown('<div class="mc-card-title">DESGLOSE DE MATERIALES</div>', unsafe_allow_html=True)

        for nombre, d in cot['detalle'].items():
            if d['valor'] > 0:
                st.markdown(f"""
                <div class="detalle-row">
                    <div>
                        <div class="detalle-nombre">{nombre}</div>
                        <div class="detalle-cant">{d['cantidad']:.2f} {d['unidad']} × ${d['precio_unit']:,}</div>
                    </div>
                    <div class="detalle-valor">${d['valor']:,.0f}</div>
                </div>
                """, unsafe_allow_html=True)

        if cot['servicios_adicionales']:
            st.markdown("<div style='margin-top:1rem;padding-top:1rem;border-top:1px solid #333'>", unsafe_allow_html=True)
            st.markdown('<div class="mc-card-title" style="font-size:1rem">SERVICIOS ADICIONALES</div>', unsafe_allow_html=True)
            for nombre, valor in cot['servicios_adicionales']:
                st.markdown(f"""
                <div class="detalle-row">
                    <div class="detalle-nombre">{nombre}</div>
                    <div class="detalle-valor">${valor:,.0f}</div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        if cot['recargo_pct'] > 0:
            st.markdown(f"""
            <div class="detalle-row">
                <div class="detalle-nombre">Recargo por dificultad ({cot['recargo_pct']}%)</div>
                <div class="detalle-valor">${cot['val_recargo']:,.0f}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    with col_total:
        st.markdown(f"""
        <div class="total-box">
            <div class="label">CLIENTE</div>
            <div style="color:white;font-size:1rem;margin:0.3rem 0 1rem 0">{cliente_nombre or '—'}</div>
            <div class="label">SUBTOTAL MATERIALES</div>
            <div style="color:rgba(255,255,255,0.7);font-size:1.4rem;font-family:'Bebas Neue',sans-serif">
                ${cot['subtotal_materiales']:,.0f}
            </div>
            <div style="margin-top:1rem;border-top:1px solid rgba(255,255,255,0.2);padding-top:1rem">
            <div class="label">TOTAL COTIZACIÓN</div>
            <div class="valor">${cot['total']:,.0f}</div>
            </div>
            <div style="color:rgba(255,255,255,0.5);font-size:0.75rem;margin-top:1rem">
                {datetime.now().strftime('%d/%m/%Y %H:%M')} · Tarifas 2026
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Notas
        st.markdown("""
        <div class="aviso" style="margin-top:1rem">
            ⚠️ Precio de madera sujeto a variación.<br>
            Troqueles con grado de dificultad pueden tener recargo adicional.
        </div>
        """, unsafe_allow_html=True)

    # Botón exportar (próxima versión)
    st.markdown("---")
    st.info("📄 **Exportar cotización a PDF/Word** — disponible en la próxima versión")
