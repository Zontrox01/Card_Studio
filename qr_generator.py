import qrcode
from PIL import Image, ImageDraw, ImageFont
import os

CARD_W_MM = 85.6
CARD_H_MM = 54.0
DPI = 300

def mm_to_px(mm_val, dpi=DPI):
    return int(mm_val / 25.4 * dpi)

CARD_W_PX = mm_to_px(CARD_W_MM)
CARD_H_PX = mm_to_px(CARD_H_MM)

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def fuente(size):
    for nombre in ["arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans.ttf"]:
        try:
            return ImageFont.truetype(nombre, size)
        except:
            pass
    return ImageFont.load_default()

def crear_cara_qr(datos: dict) -> Image.Image:
    color_fondo     = hex_to_rgb(datos.get("color_fondo", "#ffffff"))
    color_texto_hex = datos.get("color_texto", "#000000")

    img  = Image.new("RGB", (CARD_W_PX, CARD_H_PX), color=color_fondo)

    # Construir texto a codificar en el QR
    qr_campos    = datos.get("qr_campos",    [])
    qr_etiquetas = datos.get("qr_etiquetas", [])

    lineas_qr = []
    for etiqueta, valor in zip(qr_etiquetas, qr_campos):
        if valor.strip():
            if etiqueta.strip():
                lineas_qr.append(f"{etiqueta}: {valor}")
            else:
                lineas_qr.append(valor)

    texto_qr = "\n".join(lineas_qr) if lineas_qr else "Sin datos"

    # Tamaño objetivo
    max_qr = min(CARD_W_PX - 100, CARD_H_PX - 100)

    # box_size calculado para aproximarse al tamaño objetivo sin escalar
    modulos_estimados = 29
    box_size = max(1, max_qr // modulos_estimados)

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=2,
    )
    qr.add_data(texto_qr)
    qr.make(fit=True)

    qr_img = qr.make_image(
        fill_color=color_texto_hex,
        back_color=datos.get("color_fondo", "#ffffff")
    ).convert("RGB")

    # Redimensionar con NEAREST para preservar nitidez
    qr_img = qr_img.resize((max_qr, max_qr), Image.NEAREST)

    # Centrar en la tarjeta completa (sin barra)
    qr_w, qr_h = qr_img.size
    qr_x = (CARD_W_PX - qr_w) // 2
    qr_y = (CARD_H_PX - qr_h) // 2

    img.paste(qr_img, (qr_x, qr_y))

    return img
