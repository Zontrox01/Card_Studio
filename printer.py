import os
import winreg
import tempfile
import platform
import subprocess
import win32print
import win32ui
import win32api
import threading
from PIL import Image, ImageWin
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

CARD_W_MM = 85.6
CARD_H_MM = 54.0
DPI = 300


def exportar_pdf(img_anverso: Image.Image, img_reverso: Image.Image, output_path: str, paginas: int = 2):
    tmp1 = tempfile.mktemp(suffix=".png")
    img_anverso.save(tmp1, dpi=(DPI, DPI))

    c = canvas.Canvas(output_path, pagesize=(CARD_W_MM * mm, CARD_H_MM * mm))
    c.drawImage(tmp1, 0, 0, width=CARD_W_MM * mm, height=CARD_H_MM * mm)

    if paginas == 2:
        tmp2 = tempfile.mktemp(suffix=".png")
        img_reverso.save(tmp2, dpi=(DPI, DPI))
        c.showPage()
        c.drawImage(tmp2, 0, 0, width=CARD_W_MM * mm, height=CARD_H_MM * mm)
        os.remove(tmp2)

    c.save()
    os.remove(tmp1)

def listar_impresoras():
    sistema = platform.system()
    impresoras = []
    if sistema == "Windows":
        import win32print
        impresoras = [p[2] for p in win32print.EnumPrinters(
            win32print.PRINTER_ENUM_LOCAL |
            win32print.PRINTER_ENUM_CONNECTIONS)]
    elif sistema in ("Linux", "Darwin"):
        result = subprocess.run(["lpstat", "-a"], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            impresoras.append(line.split()[0])
    return impresoras


def get_acrobat_path() -> str:
    """Obtiene la ruta de AcroRd32.exe desde el registro de Windows."""
    rutas_registro = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\AcroRd32.exe",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\AcroRd32.exe",
    ]
    for ruta in rutas_registro:
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, ruta)
            path, _ = winreg.QueryValueEx(key, "")
            winreg.CloseKey(key)
            if os.path.exists(path):
                return path
        except FileNotFoundError:
            continue

    fallback = r"C:\Program Files (x86)\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe"
    if os.path.exists(fallback):
        return fallback

    raise FileNotFoundError("No se encontró AcroRd32.exe. ¿Está instalado Adobe Reader?")


def imprimir(img_anverso: Image.Image, img_reverso: Image.Image, nombre_impresora: str = None, doble_cara: bool = True) -> None:
    printer_name = nombre_impresora or win32print.GetDefaultPrinter()

    impresoras_disponibles = listar_impresoras()
    if printer_name not in impresoras_disponibles:
        raise ValueError(
            f"Impresora '{printer_name}' no encontrada.\n"
            f"Disponibles: {impresoras_disponibles}"
        )

    card_w_px = int(CARD_W_MM / 25.4 * DPI)
    card_h_px = int(CARD_H_MM / 25.4 * DPI)

    hprinter = win32print.OpenPrinter(printer_name)
    try:
        hdc = win32ui.CreateDC()
        hdc.CreatePrinterDC(printer_name)
        hdc.StartDoc("Tarjeta NFC")

        imagenes = [img_anverso, img_reverso] if doble_cara else [img_anverso]

        for img in imagenes:
            hdc.StartPage()
            printer_w = hdc.GetDeviceCaps(110)
            printer_h = hdc.GetDeviceCaps(111)
            scale = min(printer_w / card_w_px, printer_h / card_h_px)
            dest_w = int(card_w_px * scale)
            dest_h = int(card_h_px * scale)
            offset_x = (printer_w - dest_w) // 2
            offset_y = (printer_h - dest_h) // 2
            img_resized = img.resize((dest_w, dest_h), Image.LANCZOS)
            dib = ImageWin.Dib(img_resized)
            dib.draw(hdc.GetHandleOutput(),
                     (offset_x, offset_y, offset_x + dest_w, offset_y + dest_h))
            hdc.EndPage()

        hdc.EndDoc()
        hdc.DeleteDC()

    finally:
        win32print.ClosePrinter(hprinter)


def imprimir_hoja(img_hoja: Image.Image) -> None:
    """Abre la hoja como PDF en el visor predeterminado para imprimir."""
    hoja_w_px, hoja_h_px = img_hoja.size
    hoja_w_mm = hoja_w_px / DPI * 25.4
    hoja_h_mm = hoja_h_px / DPI * 25.4

    tmp_pdf = tempfile.mktemp(suffix=".pdf")
    tmp_png = tempfile.mktemp(suffix=".png")

    try:
        img_hoja.save(tmp_png, dpi=(DPI, DPI))
        c = canvas.Canvas(tmp_pdf,
                          pagesize=(hoja_w_mm * mm, hoja_h_mm * mm))
        c.drawImage(tmp_png, 0, 0,
                    width=hoja_w_mm * mm,
                    height=hoja_h_mm * mm)
        c.save()
    finally:
        if os.path.exists(tmp_png):
            os.remove(tmp_png)

    os.startfile(tmp_pdf)
    # El PDF queda en %TEMP% — Windows lo limpia periódicamente
