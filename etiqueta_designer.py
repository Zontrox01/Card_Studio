import os
import json
from PIL import Image, ImageDraw, ImageFont
import qrcode
import sys

def _get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

# ── Constantes ────────────────────────────────────────────────────
DPI         = 300
BASE_DIR    = _get_base_dir()
DATOS_DIR   = os.path.join(BASE_DIR, "datos")
LAYOUTS_DIR = os.path.join(DATOS_DIR, "layouts")
CONFIG_FILE = os.path.join(DATOS_DIR, "etiquetas_config.txt")

os.makedirs(LAYOUTS_DIR, exist_ok=True)


# ── Conversiones ──────────────────────────────────────────────────
def mm_to_px(mm, dpi=DPI):
    return int(mm / 25.4 * dpi)

def px_to_mm(px, dpi=DPI):
    return px * 25.4 / dpi

def pt_to_px(pt, dpi=DPI):
    """Convierte puntos tipográficos a píxeles según DPI."""
    return max(1, int(pt / 72 * dpi))

def dpi_scale(value, dpi=DPI):
    """
    Escala un valor entero (grosor, etc.) definido a 96 DPI
    al DPI de renderizado actual.
    """
    return max(1, int(value * dpi / 96))

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

# ── Fuentes ───────────────────────────────────────────────────────
def cargar_fuente(size_px, fuente_nombre=None):
    """Carga fuente por nombre, Arial o fallback DejaVu."""
    candidatos = []
    if fuente_nombre:
        candidatos += [fuente_nombre, fuente_nombre + ".ttf"]
    candidatos += ["arialbd.ttf", "arial.ttf",
                   "DejaVuSans-Bold.ttf", "DejaVuSans.ttf"]
    for nombre in candidatos:
        try:
            return ImageFont.truetype(nombre, size_px)
        except Exception:
            pass
    return ImageFont.load_default()

# ── Config ────────────────────────────────────────────────────────
def config_default():
    return {
        "excel_path":    "",
        "ultimo_layout": "",
        "hoja": {
            "ancho_mm":    210.0,
            "alto_mm":     297.0,
            "orientacion": "vertical",
            "cols":        3,
            "rows":        4,
            "margen_mm":   5.0,
            "sangrado_mm": 2.0,
            "linea_corte_preview":    True,
            "linea_corte_impresion":  False,
            "color_linea_preview":    "#aaaaaa",
            "color_linea_impresion":  "#000000",
        }
    }

def cargar_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            cfg = config_default()
            cfg.update(data)
            cfg["hoja"].update(data.get("hoja", {}))
            return cfg
        except Exception:
            pass
    return config_default()

def guardar_config(cfg):
    os.makedirs(DATOS_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

# ── Layout ────────────────────────────────────────────────────────
def layout_default():
    return {"elementos": []}

def cargar_layout(path):
    if path and os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return layout_default()

def guardar_layout(layout, path):
    os.makedirs(LAYOUTS_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(layout, f, indent=2, ensure_ascii=False)

# ── Elementos del layout ──────────────────────────────────────────
def elemento_texto(x_mm, y_mm, ancho_mm, alto_mm,
                   campo_excel=None, texto_fijo="Texto",
                   fuente_size=24, color_texto="#000000",
                   color_fondo=None, negrita=True):
    return {
        "tipo": "texto",
        "x_mm": x_mm, "y_mm": y_mm,
        "ancho_mm": ancho_mm, "alto_mm": alto_mm,
        "campo_excel":  campo_excel,
        "texto_fijo":   texto_fijo,
        "fuente_size":  fuente_size,   # en puntos tipográficos
        "color_texto":  color_texto,
        "color_fondo":  color_fondo,
        "negrita":      negrita,
    }

def elemento_imagen(x_mm, y_mm, ancho_mm, alto_mm,
                    ruta="", campo_excel=None):
    return {
        "tipo":        "imagen",
        "x_mm":        x_mm, "y_mm": y_mm,
        "ancho_mm":    ancho_mm, "alto_mm": alto_mm,
        "ruta":        ruta,
        "campo_excel": campo_excel,   # si no es None, la ruta viene del Excel
    }

def elemento_qr(x_mm, y_mm, ancho_mm, alto_mm,
                campo_excel=None, texto_fijo=None):
    return {
        "tipo":          "qr",
        "x_mm":          x_mm,  "y_mm": y_mm,
        "ancho_mm":      ancho_mm, "alto_mm": alto_mm,
        "campo_excel":   campo_excel,
        "texto_fijo":    texto_fijo,
        "color_qr":      "#000000",
        "color_fondo_qr": "#ffffff",
    }

def elemento_rectangulo(x_mm, y_mm, ancho_mm, alto_mm,
                         color_relleno=None, color_borde="#000000",
                         grosor_borde=2):
    return {
        "tipo": "rectangulo",
        "x_mm": x_mm, "y_mm": y_mm,
        "ancho_mm": ancho_mm, "alto_mm": alto_mm,
        "color_relleno": color_relleno,
        "color_borde":   color_borde,
        "grosor_borde":  grosor_borde,   # en px a 96 DPI
    }

def elemento_linea(x_mm, y_mm, x2_mm, y2_mm,
                   color="#000000", grosor=2):
    return {
        "tipo": "linea",
        "x_mm":  x_mm,  "y_mm":  y_mm,
        "x2_mm": x2_mm, "y2_mm": y2_mm,
        "ancho_mm": abs(x2_mm - x_mm),
        "alto_mm":  abs(y2_mm - y_mm),
        "color":  color,
        "grosor": grosor,   # en px a 96 DPI
    }

def elemento_flecha(x_mm, y_mm, x2_mm, y2_mm,
                    color="#000000", grosor=2, tamano_cabeza=4):
    return {
        "tipo":          "flecha",
        "x_mm":  x_mm,  "y_mm":  y_mm,
        "x2_mm": x2_mm, "y2_mm": y2_mm,
        "ancho_mm": abs(x2_mm - x_mm),
        "alto_mm":  abs(y2_mm - y_mm),
        "color":         color,
        "grosor":        grosor,
        "tamano_cabeza": tamano_cabeza,
        "cabeza_manual": False,
    }

def elemento_elipse(x_mm, y_mm, ancho_mm, alto_mm,
                    color_relleno=None, color_borde="#000000",
                    grosor_borde=2):
    return {
        "tipo":          "elipse",
        "x_mm":          x_mm,  "y_mm": y_mm,
        "ancho_mm":      ancho_mm, "alto_mm": alto_mm,
        "color_relleno": color_relleno,
        "color_borde":   color_borde,
        "grosor_borde":  grosor_borde,
    }


# ── Calcular tamaño de etiqueta ───────────────────────────────────
def calcular_tamano_etiqueta(cfg_hoja):
    ancho_hoja = cfg_hoja["ancho_mm"]
    alto_hoja  = cfg_hoja["alto_mm"]

    if cfg_hoja["orientacion"] == "horizontal":
        ancho_hoja, alto_hoja = alto_hoja, ancho_hoja

    cols     = cfg_hoja["cols"]
    rows     = cfg_hoja["rows"]
    margen   = cfg_hoja["margen_mm"]
    sangrado = cfg_hoja["sangrado_mm"]

    etiq_w = (ancho_hoja - 2 * margen - (cols - 1) * sangrado) / cols
    etiq_h = (alto_hoja  - 2 * margen - (rows - 1) * sangrado) / rows

    return etiq_w, etiq_h

# ── Renderizar una etiqueta ───────────────────────────────────────
def renderizar_etiqueta(layout, datos_fila, imagenes, cfg_hoja, dpi=DPI):
    etiq_w_mm, etiq_h_mm = calcular_tamano_etiqueta(cfg_hoja)
    etiq_w_px = mm_to_px(etiq_w_mm, dpi)
    etiq_h_px = mm_to_px(etiq_h_mm, dpi)

    img  = Image.new("RGB", (etiq_w_px, etiq_h_px), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    for idx, elem in enumerate(layout.get("elementos", [])):
        tipo = elem["tipo"]

        x_px = mm_to_px(elem["x_mm"], dpi)
        y_px = mm_to_px(elem["y_mm"], dpi)
        w_px = mm_to_px(elem["ancho_mm"], dpi)
        h_px = mm_to_px(elem["alto_mm"], dpi)

        # ── Rectángulo ───────────────────────────────────────
        if tipo == "rectangulo":
            relleno = hex_to_rgb(elem["color_relleno"]) \
                      if elem.get("color_relleno") else None
            borde   = hex_to_rgb(elem.get("color_borde", "#000000"))
            grosor  = dpi_scale(elem.get("grosor_borde", 2), dpi)
            draw.rectangle(
                [(x_px, y_px), (x_px + w_px, y_px + h_px)],
                fill=relleno, outline=borde, width=grosor
            )

        # ── Línea ────────────────────────────────────────────
        elif tipo == "linea":
            x2_px  = mm_to_px(elem["x2_mm"], dpi)
            y2_px  = mm_to_px(elem["y2_mm"], dpi)
            color  = hex_to_rgb(elem.get("color", "#000000"))
            grosor = dpi_scale(elem.get("grosor", 2), dpi)
            draw.line([(x_px, y_px), (x2_px, y2_px)],
                      fill=color, width=grosor)

        # ── Texto ────────────────────────────────────────────
        elif tipo == "texto":
            campo = elem.get("campo_excel")
            if campo and datos_fila and campo in datos_fila:
                texto = str(datos_fila[campo])
            elif campo:
                texto = f"[{campo}]"   # preview: muestra nombre del campo
            else:
                texto = elem.get("texto_fijo", "")

            size_pt  = elem.get("fuente_size", 24)
            negrita  = elem.get("negrita", False)
            color    = hex_to_rgb(elem.get("color_texto", "#000000"))
            fondo    = hex_to_rgb(elem["color_fondo"]) \
                       if elem.get("color_fondo") else None

            size_px  = pt_to_px(size_pt, dpi)
            fuente   = cargar_fuente(size_px, elem.get("fuente_nombre"))

            if fondo:
                draw.rectangle(
                    [(x_px, y_px), (x_px + w_px, y_px + h_px)],
                    fill=fondo
                )

            # Ajuste de texto dentro del bounding box
            bbox = draw.textbbox((0, 0), texto, font=fuente)
            tw   = bbox[2] - bbox[0]
            th   = bbox[3] - bbox[1]
            tx   = x_px + (w_px - tw) // 2
            ty   = y_px + (h_px - th) // 2
            draw.text((tx, ty), texto, font=fuente, fill=color)

        # ── Imagen ───────────────────────────────────────────
        elif tipo == "imagen":
            campo = elem.get("campo_excel")
            if campo and datos_fila and campo in datos_fila:
                ruta = str(datos_fila[campo])
            else:
                ruta = imagenes.get(idx) or elem.get("ruta", "")

            if ruta and os.path.exists(ruta):
                try:
                    im = Image.open(ruta).convert("RGBA")
                    im = im.resize((w_px, h_px), Image.LANCZOS)
                    img.paste(im, (x_px, y_px), mask=im.split()[3])
                except Exception:
                    pass
            elif campo and (not datos_fila or campo not in (datos_fila or {})):
                # Placeholder: caja gris con nombre del campo
                draw.rectangle(
                    [(x_px, y_px), (x_px + w_px, y_px + h_px)],
                    fill=(220, 220, 220), outline=(150, 150, 150), width=1)
                fuente_ph = cargar_fuente(pt_to_px(8, dpi))
                label = f"[{campo}]"
                bbox = draw.textbbox((0, 0), label, font=fuente_ph)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
                tx = x_px + (w_px - tw) // 2
                ty = y_px + (h_px - th) // 2
                draw.text((tx, ty), label, font=fuente_ph,
                          fill=(100, 100, 100))

        # ── QR ───────────────────────────────────────────────
        elif tipo == "qr":
            campo      = elem.get("campo_excel")
            texto_fijo = elem.get("texto_fijo")
            if campo and datos_fila and campo in datos_fila:
                contenido = str(datos_fila[campo])
            elif texto_fijo:
                contenido = texto_fijo
            else:
                contenido = ""

            if contenido:
                try:
                    color_qr    = elem.get("color_qr", "#000000")
                    color_fondo = elem.get("color_fondo_qr", "#ffffff")

                    # Sin fondo → transparente
                    if color_fondo is None:
                        back = "transparent"
                        modo_img = "RGBA"
                    else:
                        back     = color_fondo
                        modo_img = "RGBA"

                    qr = qrcode.QRCode(
                        error_correction=qrcode.constants.ERROR_CORRECT_L,
                        box_size=10, border=1)
                    qr.add_data(contenido)
                    qr.make(fit=True)
                    qr_img = qr.make_image(
                        fill_color=color_qr,
                        back_color=back).convert(modo_img)
                    qr_img = qr_img.resize((w_px, h_px), Image.NEAREST)

                    if color_fondo is None:
                        # Pegar con transparencia
                        img.paste(qr_img, (x_px, y_px), mask=qr_img.split()[3])
                    else:
                        img.paste(qr_img, (x_px, y_px))
                except Exception:
                    pass


        # ── Flecha ───────────────────────────────────────────
        elif tipo == "flecha":
            import math
            x2_px  = mm_to_px(elem["x2_mm"], dpi)
            y2_px  = mm_to_px(elem["y2_mm"], dpi)
            color  = hex_to_rgb(elem.get("color", "#000000"))
            grosor = dpi_scale(elem.get("grosor", 2), dpi)
            cab    = dpi_scale(elem.get("tamano_cabeza", 4), dpi)

            # Ángulo de la flecha
            angle = math.atan2(y2_px - y_px, x2_px - x_px)

            # Puntos de la cabeza (triángulo)
            a1 = angle + math.radians(150)
            a2 = angle - math.radians(150)
            p1 = (x2_px + cab * math.cos(a1),
                  y2_px + cab * math.sin(a1))
            p2 = (x2_px + cab * math.cos(a2),
                  y2_px + cab * math.sin(a2))

            # Base de la cabeza — punto donde termina la línea
            base_x = (p1[0] + p2[0]) / 2
            base_y = (p1[1] + p2[1]) / 2

            # Línea hasta la BASE de la cabeza, no hasta la punta
            draw.line([(x_px, y_px), (base_x, base_y)],
                      fill=color, width=grosor)

            # Cabeza de flecha
            draw.polygon([(x2_px, y2_px), p1, p2], fill=color)


        # ── Elipse ───────────────────────────────────────────
        elif tipo == "elipse":
            relleno = hex_to_rgb(elem["color_relleno"]) \
                      if elem.get("color_relleno") else None
            borde   = hex_to_rgb(elem.get("color_borde", "#000000"))
            grosor  = dpi_scale(elem.get("grosor_borde", 2), dpi)
            draw.ellipse(
                [(x_px, y_px), (x_px + w_px, y_px + h_px)],
                fill=relleno, outline=borde, width=grosor
            )

    return img

# ── Renderizar hoja completa ──────────────────────────────────────
def renderizar_hoja(layout, filas_datos, imagenes_por_etiqueta,
                    copias_por_etiqueta, cfg_hoja,
                    linea_corte=False, color_linea="#aaaaaa",
                    dpi=DPI):
    ancho_hoja_mm = cfg_hoja["ancho_mm"]
    alto_hoja_mm  = cfg_hoja["alto_mm"]

    if cfg_hoja["orientacion"] == "horizontal":
        ancho_hoja_mm, alto_hoja_mm = alto_hoja_mm, ancho_hoja_mm

    hoja_w_px = mm_to_px(ancho_hoja_mm, dpi)
    hoja_h_px = mm_to_px(alto_hoja_mm,  dpi)

    hoja = Image.new("RGB", (hoja_w_px, hoja_h_px), color=(255, 255, 255))
    draw = ImageDraw.Draw(hoja)

    cols        = cfg_hoja["cols"]
    rows        = cfg_hoja["rows"]
    margen      = cfg_hoja["margen_mm"]
    sangrado    = cfg_hoja["sangrado_mm"]

    etiq_w_mm, etiq_h_mm = calcular_tamano_etiqueta(cfg_hoja)
    etiq_w_px   = mm_to_px(etiq_w_mm, dpi)
    etiq_h_px   = mm_to_px(etiq_h_mm, dpi)
    margen_px   = mm_to_px(margen,    dpi)
    sangrado_px = mm_to_px(sangrado,  dpi)
    # Expandir lista de etiquetas según copias
    etiquetas_expandidas = []
    for i, fila in enumerate(filas_datos):
        copias   = copias_por_etiqueta[i] if i < len(copias_por_etiqueta) else 1
        imagenes = imagenes_por_etiqueta[i] if i < len(imagenes_por_etiqueta) else {}
        for _ in range(copias):
            etiquetas_expandidas.append((fila, imagenes))

    # Comprobar que caben en la hoja
    max_etiquetas = cols * rows
    if len(etiquetas_expandidas) > max_etiquetas:
        raise ValueError(
            f"No caben {len(etiquetas_expandidas)} etiquetas en la hoja "
            f"({cols}×{rows} = {max_etiquetas} máximo).\n"
            f"Reduce las copias o aumenta el grid."
        )

    # Pegar etiquetas en la hoja
    for i, (fila, imagenes) in enumerate(etiquetas_expandidas):
        col = i % cols
        row = i // cols

        x_px = margen_px + col * (etiq_w_px + sangrado_px)
        y_px = margen_px + row * (etiq_h_px + sangrado_px)

        etiq_img = renderizar_etiqueta(layout, fila, imagenes, cfg_hoja, dpi)
        hoja.paste(etiq_img, (x_px, y_px))

    # Líneas de corte — grosor escalado al DPI
    if linea_corte:
        color_rgb    = hex_to_rgb(color_linea)
        grosor_linea = dpi_scale(1, dpi)

        # Líneas verticales
        for col in range(cols + 1):
            x_px = margen_px + col * (etiq_w_px + sangrado_px)
            if col > 0:
                x_px -= sangrado_px // 2
            draw.line([(x_px, 0), (x_px, hoja_h_px)],
                      fill=color_rgb, width=grosor_linea)

        # Líneas horizontales
        for row in range(rows + 1):
            y_px = margen_px + row * (etiq_h_px + sangrado_px)
            if row > 0:
                y_px -= sangrado_px // 2
            draw.line([(0, y_px), (hoja_w_px, y_px)],
                      fill=color_rgb, width=grosor_linea)

    return hoja

# ── Exportar PDF ──────────────────────────────────────────────────
def exportar_pdf_etiquetas(hoja_img, path):
    hoja_rgb = hoja_img.convert("RGB")
    hoja_rgb.save(path, "PDF", resolution=DPI)

# ── Exportar múltiples hojas PDF ──────────────────────────────────
def exportar_pdf_multipage(hojas, path):
    if not hojas:
        return
    primero = hojas[0].convert("RGB")
    resto   = [h.convert("RGB") for h in hojas[1:]]
    primero.save(path, "PDF", resolution=DPI,
                 save_all=True, append_images=resto)

# ── Preview escalado ──────────────────────────────────────────────
def escalar_preview(hoja_img, max_w, max_h):
    """
    Escala la hoja para caber en max_w x max_h manteniendo proporción.
    """
    orig_w, orig_h = hoja_img.size
    ratio   = min(max_w / orig_w, max_h / orig_h)
    nuevo_w = int(orig_w * ratio)
    nuevo_h = int(orig_h * ratio)
    return hoja_img.resize((nuevo_w, nuevo_h), Image.LANCZOS)

# ── Coordenadas de etiqueta en preview ───────────────────────────
def etiqueta_rect_preview(col, row, cfg_hoja, preview_w, preview_h, dpi=DPI):
    """
    Devuelve (x1, y1, x2, y2) en píxeles de preview para
    la etiqueta en posición (col, row).
    """
    ancho_hoja_mm = cfg_hoja["ancho_mm"]
    alto_hoja_mm  = cfg_hoja["alto_mm"]
    if cfg_hoja["orientacion"] == "horizontal":
        ancho_hoja_mm, alto_hoja_mm = alto_hoja_mm, ancho_hoja_mm

    hoja_w_px   = mm_to_px(ancho_hoja_mm, dpi)
    hoja_h_px   = mm_to_px(alto_hoja_mm,  dpi)

    etiq_w_mm, etiq_h_mm = calcular_tamano_etiqueta(cfg_hoja)
    etiq_w_px   = mm_to_px(etiq_w_mm, dpi)
    etiq_h_px   = mm_to_px(etiq_h_mm, dpi)
    margen_px   = mm_to_px(cfg_hoja["margen_mm"],   dpi)
    sangrado_px = mm_to_px(cfg_hoja["sangrado_mm"], dpi)

    x1 = margen_px + col * (etiq_w_px + sangrado_px)
    y1 = margen_px + row * (etiq_h_px + sangrado_px)
    x2 = x1 + etiq_w_px
    y2 = y1 + etiq_h_px

    # Escalar a coordenadas de preview
    rx = preview_w / hoja_w_px
    ry = preview_h / hoja_h_px

    return (int(x1 * rx), int(y1 * ry),
            int(x2 * rx), int(y2 * ry))
