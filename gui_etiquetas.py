import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
from PIL import Image, ImageTk
import pandas as pd
import threading
import os
import sys

from etiqueta_designer import (
    cargar_config, guardar_config,
    cargar_layout, guardar_layout, layout_default,
    renderizar_hoja, escalar_preview,
    etiqueta_rect_preview, exportar_pdf_etiquetas,
    exportar_pdf_multipage, LAYOUTS_DIR, DPI
)
from printer import listar_impresoras, imprimir, imprimir_hoja, exportar_pdf

def _get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = _get_base_dir()

PREVIEW_MAX_W = 500
PREVIEW_MAX_H = 650

class AppEtiquetas(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Card Studio — Etiquetas")
        self.resizable(True, True)
        self.configure(bg="#f0f4f8")

        # ── Estado ───────────────────────────────────────────
        self.cfg         = cargar_config()
        self.layout      = layout_default()
        self.df          = None
        self.filas_datos = []
        self.imagenes_por_etiqueta = []
        self.slots                 = []
        self.slot_actual           = 0
        self._ultimo_dir_layout = self.cfg.get(
            "ultimo_layout_dir",
            os.path.join(BASE_DIR, "datos", "layouts"))

        self._preview_img          = None
        self._preview_w            = PREVIEW_MAX_W
        self._preview_h            = PREVIEW_MAX_H

        self._build_ui()

        self.update_idletasks()
        
        h_actual = self.winfo_height()
        w_actual = self.winfo_width()
        self.geometry(f"{w_actual}x{h_actual + 80}")

        self._cargar_excel_auto()
        self._cargar_layout_auto()
        self._sincronizar_slots()
        self._actualizar_nav_slot()
        self._actualizar_preview()

    # ═══════════════════════════════════════════════════════════════
    #  UI
    # ═══════════════════════════════════════════════════════════════
    def _build_ui(self):

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)

        # ── Contenedor scrollable para el panel izquierdo ────
        outer_left = tk.Frame(self, bg="#f0f4f8")
        outer_left.grid(row=0, column=0, sticky="ns")

        canvas_scroll = tk.Canvas(
            outer_left, bg="#f0f4f8",
            highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            outer_left, orient="vertical",
            command=canvas_scroll.yview)

        canvas_scroll.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas_scroll.pack(side="left", fill="both", expand=True)

        left = tk.Frame(canvas_scroll, bg="#f0f4f8", padx=12, pady=12)
        left_window = canvas_scroll.create_window(
            (0, 0), window=left, anchor="nw")

        def _on_frame_configure(event):
            canvas_scroll.configure(
                scrollregion=canvas_scroll.bbox("all"))

        def _on_canvas_configure(event):
            canvas_scroll.itemconfig(
                left_window, width=event.width)

        left.bind("<Configure>", _on_frame_configure)
        canvas_scroll.bind("<Configure>", _on_canvas_configure)

        def _on_mousewheel(event):
            canvas_scroll.yview_scroll(
                int(-1 * (event.delta / 120)), "units")

        canvas_scroll.bind_all("<MouseWheel>", _on_mousewheel)
    
        self.update_idletasks()
        contenido_h = left.winfo_reqheight()
        pantalla_h  = self.winfo_screenheight() - 80
        canvas_scroll.config(height=min(contenido_h, pantalla_h))
        
        def _on_frame_configure(event):
            canvas_scroll.configure(
                scrollregion=canvas_scroll.bbox("all"))

        def _on_canvas_configure(event):
            canvas_scroll.itemconfig(
                left_window, width=event.width)

        left.bind("<Configure>", _on_frame_configure)
        canvas_scroll.bind("<Configure>", _on_canvas_configure)

        # Scroll con rueda del ratón
        def _on_mousewheel(event):
            canvas_scroll.yview_scroll(
                int(-1 * (event.delta / 120)), "units")

        canvas_scroll.bind_all("<MouseWheel>", _on_mousewheel)

        # Ajustar altura del canvas al monitor
        screen_h = self.winfo_screenheight()
        canvas_scroll.config(height=min(screen_h - 80, 900))
        
        # ── Panel izquierdo ──────────────────────────────────
        tk.Label(left, text="🏷 Diseñador de Etiquetas",
                 bg="#f0f4f8", font=("Arial", 13, "bold"),
                 fg="#00509F").grid(row=0, column=0,
                                    columnspan=2, pady=(0, 10))

        # ── Sección: Hoja ────────────────────────────────────
        self._seccion(left, "📄 Configuración de hoja", row=1)

        tk.Label(left, text="Ancho hoja (mm):",
                 bg="#f0f4f8", anchor="w").grid(
            row=2, column=0, sticky="w", pady=2)
        self.entry_ancho = ttk.Entry(left, width=10)
        self.entry_ancho.insert(0, str(self.cfg["hoja"]["ancho_mm"]))
        self.entry_ancho.grid(row=2, column=1, sticky="w", padx=(8,0))

        tk.Label(left, text="Alto hoja (mm):",
                 bg="#f0f4f8", anchor="w").grid(
            row=3, column=0, sticky="w", pady=2)
        self.entry_alto = ttk.Entry(left, width=10)
        self.entry_alto.insert(0, str(self.cfg["hoja"]["alto_mm"]))
        self.entry_alto.grid(row=3, column=1, sticky="w", padx=(8,0))

        tk.Label(left, text="Orientación:",
                 bg="#f0f4f8", anchor="w").grid(
            row=4, column=0, sticky="w", pady=2)
        self.var_orientacion = tk.StringVar(
            value=self.cfg["hoja"]["orientacion"])
        frame_ori = tk.Frame(left, bg="#f0f4f8")
        frame_ori.grid(row=4, column=1, sticky="w", padx=(8,0))
        tk.Radiobutton(frame_ori, text="Vertical",
                       variable=self.var_orientacion,
                       value="vertical", bg="#f0f4f8",
                       command=self._actualizar_preview).pack(side="left")
        tk.Radiobutton(frame_ori, text="Horizontal",
                       variable=self.var_orientacion,
                       value="horizontal", bg="#f0f4f8",
                       command=self._actualizar_preview).pack(side="left")

        tk.Label(left, text="Nº Columnas de etiquetas:",
                 bg="#f0f4f8", anchor="w").grid(
            row=5, column=0, sticky="w", pady=2)
        self.spin_cols = ttk.Spinbox(left, from_=1, to=20, width=5)
        self.spin_cols.set(self.cfg["hoja"]["cols"])
        self.spin_cols.grid(row=5, column=1, sticky="w", padx=(8,0))

        tk.Label(left, text="Nº Filas de etiquetas:",
                 bg="#f0f4f8", anchor="w").grid(
            row=6, column=0, sticky="w", pady=2)
        self.spin_rows = ttk.Spinbox(left, from_=1, to=30, width=5)
        self.spin_rows.set(self.cfg["hoja"]["rows"])
        self.spin_rows.grid(row=6, column=1, sticky="w", padx=(8,0))

        tk.Label(left, text="Margen (mm):",
                 bg="#f0f4f8", anchor="w").grid(
            row=7, column=0, sticky="w", pady=2)
        self.entry_margen = ttk.Entry(left, width=10)
        self.entry_margen.insert(0, str(self.cfg["hoja"]["margen_mm"]))
        self.entry_margen.grid(row=7, column=1, sticky="w", padx=(8,0))

        tk.Label(left, text="Sangrado (mm):",
                 bg="#f0f4f8", anchor="w").grid(
            row=8, column=0, sticky="w", pady=2)
        self.entry_sangrado = ttk.Entry(left, width=10)
        self.entry_sangrado.insert(0, str(self.cfg["hoja"]["sangrado_mm"]))
        self.entry_sangrado.grid(row=8, column=1, sticky="w", padx=(8,0))

        tk.Button(left, text="✅ Aplicar configuración",
                  command=self._aplicar_config,
                  bg="#00509F", fg="white",
                  relief="flat", cursor="hand2").grid(
            row=9, column=0, columnspan=2, pady=(8,4), sticky="ew")

        # ── Sección: Líneas de corte ─────────────────────────
        self._seccion(left, "✂ Líneas de corte", row=10)

        self.var_linea_preview = tk.BooleanVar(
            value=self.cfg["hoja"]["linea_corte_preview"])
        tk.Checkbutton(left, text="Mostrar en vista previa",
                       variable=self.var_linea_preview,
                       bg="#f0f4f8",
                       command=self._actualizar_preview).grid(row=11, column=0, columnspan=2, sticky="w")

        self.var_linea_impresion = tk.BooleanVar(
            value=self.cfg["hoja"]["linea_corte_impresion"])
        tk.Checkbutton(left, text="Imprimir línea de corte",
                       variable=self.var_linea_impresion,
                       bg="#f0f4f8").grid(
            row=12, column=0, columnspan=2, sticky="w")

        # Color línea preview
        tk.Label(left, text="Color vista previa:",
                 bg="#f0f4f8", anchor="w").grid(
            row=13, column=0, sticky="w", pady=2)
        self._color_linea_preview = self.cfg["hoja"]["color_linea_preview"]
        self.btn_color_prev = tk.Button(
            left, bg=self._color_linea_preview, width=4,
            relief="flat", cursor="hand2",
            command=self._elegir_color_linea_preview)
        self.btn_color_prev.grid(row=13, column=1, sticky="w", padx=(8,0))

        # Color línea impresión
        tk.Label(left, text="Color impresión:",
                 bg="#f0f4f8", anchor="w").grid(
            row=14, column=0, sticky="w", pady=2)
        self._color_linea_impresion = self.cfg["hoja"]["color_linea_impresion"]
        self.btn_color_imp = tk.Button(
            left, bg=self._color_linea_impresion, width=4,
            relief="flat", cursor="hand2",
            command=self._elegir_color_linea_impresion)
        self.btn_color_imp.grid(row=14, column=1, sticky="w", padx=(8,0))

        # ── Sección: Excel ───────────────────────────────────
        self._seccion(left, "📊 Datos Excel", row=15)

        self.lbl_excel = tk.Label(left, text="Sin archivo",
                                  bg="#f0f4f8", fg="gray",
                                  font=("Arial", 8), anchor="w")
        self.lbl_excel.grid(row=16, column=0, columnspan=2,
                            sticky="w", pady=2)

        tk.Button(left, text="📂 Cargar Excel",
                  command=self._cargar_excel,
                  bg="#e8f0fe", relief="flat",
                  cursor="hand2").grid(
            row=17, column=0, columnspan=2,
            sticky="ew", pady=2)

        # ── Sección: Layout ──────────────────────────────────
        self._seccion(left, "🎨 Plantilla", row=18)

        frame_layout = tk.Frame(left, bg="#f0f4f8")
        frame_layout.grid(row=19, column=0, columnspan=2,
                          sticky="ew", pady=2)

        tk.Button(frame_layout, text="📂 Cargar",
                  command=self._cargar_layout,
                  bg="#e8f0fe", relief="flat",
                  cursor="hand2", width=10).grid(
            row=0, column=0, padx=(0,4))
        tk.Button(frame_layout, text="💾 Guardar",
                  command=self._guardar_layout,
                  bg="#e8f0fe", relief="flat",
                  cursor="hand2", width=10).grid(
            row=0, column=1, padx=(0,4))
        tk.Button(frame_layout, text="🗑 Nuevo",
                  command=self._nuevo_layout,
                  bg="#e8f0fe", relief="flat",
                  cursor="hand2", width=10).grid(
            row=0, column=2)

        self.lbl_layout = tk.Label(left, text="Sin layout",
                                   bg="#f0f4f8", fg="gray",
                                   font=("Arial", 8), anchor="w")
        self.lbl_layout.grid(row=20, column=0, columnspan=2,
                             sticky="w", pady=2)

        # Botón editar layout
        tk.Button(left, text="✏ Editar plantilla",
                  command=self._abrir_editor,
                  bg="#00bb7e", fg="white",
                  font=("Arial", 10, "bold"),
                  relief="flat", cursor="hand2").grid(
            row=21, column=0, columnspan=2,
            sticky="ew", pady=(4,2))        

        # ── Sección: Etiquetas ───────────────────────────────
        self._seccion(left, "🏷 Etiquetas", row=22)

        frame_nav = tk.Frame(left, bg="#f0f4f8")
        frame_nav.grid(row=23, column=0, columnspan=2,
                       sticky="ew", pady=4)

        tk.Button(frame_nav, text="◀", width=3,
                  command=self._slot_anterior,
                  relief="flat", cursor="hand2",
                  bg="#e8f0fe").grid(row=0, column=0)

        self.lbl_slot = tk.Label(frame_nav,
                                 text="Etiqueta - / -",
                                 bg="#f0f4f8",
                                 font=("Arial", 10, "bold"))
        self.lbl_slot.grid(row=0, column=1, padx=8)

        tk.Button(frame_nav, text="▶", width=3,
                  command=self._slot_siguiente,
                  relief="flat", cursor="hand2",
                  bg="#e8f0fe").grid(row=0, column=2)
        
        # ── Campo ────────────────────────────────────────────
        frame_campo = tk.Frame(left, bg="#f0f4f8")
        frame_campo.grid(row=24, column=0, columnspan=2,
                         sticky="ew", pady=2)
        tk.Label(frame_campo, text="Campo:",
                 bg="#f0f4f8", anchor="w").grid(
            row=0, column=0, sticky="w")
        self.combo_campo = ttk.Combobox(
            frame_campo, width=18, state="readonly")
        self.combo_campo.grid(row=0, column=1,
                              sticky="w", padx=(4, 0))
        self.combo_campo.bind("<<ComboboxSelected>>",
                              self._campo_cambiado)

        # ── Registro Excel ───────────────────────────────────
        frame_reg = tk.Frame(left, bg="#f0f4f8")
        frame_reg.grid(row=25, column=0, columnspan=2,
                       sticky="ew", pady=2)
        tk.Label(frame_reg, text="Registro:",
                 bg="#f0f4f8", anchor="w").grid(
            row=0, column=0, sticky="w")
        self.combo_registro = ttk.Combobox(
            frame_reg, width=18, state="readonly")
        self.combo_registro.grid(row=0, column=1,
                                 sticky="w", padx=(4, 0))
        self.combo_registro.bind("<<ComboboxSelected>>",
                                 self._registro_cambiado)        

        # Copias de este slot
        tk.Label(left, text="Copias:",
                 bg="#f0f4f8", anchor="w").grid(
            row=26, column=0, sticky="w", pady=2)
        self.spin_copias = ttk.Spinbox(
            left, from_=1, to=100, width=5,
            command=self._copias_cambiadas)
        self.spin_copias.set(1)
        self.spin_copias.grid(row=26, column=1,
                              sticky="w", padx=(8,0))

        # Info total etiquetas
        self.lbl_total = tk.Label(
            left, text="Total: 0 / 0 posiciones ocupadas",
            bg="#f0f4f8", fg="gray", font=("Arial", 8))
        self.lbl_total.grid(row=27, column=0,
                            columnspan=2, pady=2)

        # ── Sección: Acciones ────────────────────────────────
        self._seccion(left, "🖨 Acciones", row=28)

        frame_acc = tk.Frame(left, bg="#f0f4f8")
        frame_acc.grid(row=29, column=0, columnspan=2,
                       sticky="ew", pady=6)

        tk.Button(frame_acc, text="🖨 Imprimir",
                  command=self._imprimir,
                  bg="#00509F", fg="white",
                  font=("Arial", 10, "bold"),
                  relief="flat", cursor="hand2").grid(
            row=0, column=0, padx=(0,4), pady=2, sticky="ew")

        tk.Button(frame_acc, text="💾 Guardar PDF",
                  command=self._guardar_pdf,
                  bg="#00bb7e", fg="white",
                  font=("Arial", 10, "bold"),
                  relief="flat", cursor="hand2").grid(
            row=0, column=1, padx=(0,4), pady=2, sticky="ew")

        tk.Button(frame_acc, text="🗑 Limpiar",
                  command=self._limpiar,
                  bg="#e0e0e0", fg="#333",
                  font=("Arial", 10),
                  relief="flat", cursor="hand2").grid(
            row=0, column=2, pady=2, sticky="ew")

        # ── Panel derecho — Preview ──────────────────────────
        right = tk.Frame(self, bg="#f0f4f8", padx=12, pady=12)
        right.grid(row=0, column=1, sticky="n")

        tk.Label(right, text="Vista previa",
                 bg="#f0f4f8", font=("Arial", 10, "bold"),
                 fg="#555").pack()

        self.canvas_preview = tk.Canvas(
            right, width=PREVIEW_MAX_W, height=PREVIEW_MAX_H,
            bg="#cccccc", relief="sunken", bd=2)
        self.canvas_preview.pack(pady=8)
        self.canvas_preview.bind("<Button-1>", self._click_preview)

        self.lbl_estado = tk.Label(
            right, text="Listo.", bg="#f0f4f8",
            fg="gray", font=("Arial", 9))
        self.lbl_estado.pack(pady=(4,0))

    # ═══════════════════════════════════════════════════════════════
    #  HELPERS UI
    # ═══════════════════════════════════════════════════════════════
    def _seccion(self, parent, texto, row):
        ttk.Separator(parent, orient="horizontal").grid(
            row=row, column=0, columnspan=2,
            sticky="ew", pady=(10,2))
        tk.Label(parent, text=texto,
                 bg="#f0f4f8", font=("Arial", 9, "bold"),
                 fg="#00509F", anchor="w").grid(
            row=row, column=0, columnspan=2, sticky="w")

    def _cfg_hoja(self):
        try:
            ancho    = float(self.entry_ancho.get())
            alto     = float(self.entry_alto.get())
            cols     = int(self.spin_cols.get())
            rows     = int(self.spin_rows.get())
            margen   = float(self.entry_margen.get())
            sangrado = float(self.entry_sangrado.get())
        except ValueError:
            return self.cfg["hoja"]

        return {
            "ancho_mm":    ancho,
            "alto_mm":     alto,
            "orientacion": self.var_orientacion.get(),
            "cols":        cols,
            "rows":        rows,
            "margen_mm":   margen,
            "sangrado_mm": sangrado,
            "linea_corte_preview":   self.var_linea_preview.get(),
            "linea_corte_impresion": self.var_linea_impresion.get(),
            "color_linea_preview":   self._color_linea_preview,
            "color_linea_impresion": self._color_linea_impresion,
        }

    def _elegir_color_linea_preview(self):
        color = colorchooser.askcolor(
            color=self._color_linea_preview,
            title="Color línea preview")[1]
        if color:
            self._color_linea_preview = color
            self.btn_color_prev.config(bg=color)
            self._actualizar_preview()

    def _elegir_color_linea_impresion(self):
        color = colorchooser.askcolor(
            color=self._color_linea_impresion,
            title="Color línea impresión")[1]
        if color:
            self._color_linea_impresion = color
            self.btn_color_imp.config(bg=color)

    def _centrar_en_padre(self, hijo):
        self.update_idletasks()
        hijo.update_idletasks()
        px = self.winfo_x()
        py = self.winfo_y()
        x  = px + 20
        y  = max(30, py)
        hijo.geometry(f"+{x}+{y}")
           

    # ═══════════════════════════════════════════════════════════════
    #  CONFIGURACIÓN
    # ═══════════════════════════════════════════════════════════════
    def _aplicar_config(self):
        self.cfg["hoja"] = self._cfg_hoja()
        guardar_config(self.cfg)
        self.slot_actual = 0
        self._sincronizar_slots()
        self._actualizar_nav_slot()
        self._actualizar_preview()
        self.lbl_estado.config(text="Configuración aplicada.")

    # ═══════════════════════════════════════════════════════════════
    #  EXCEL
    # ═══════════════════════════════════════════════════════════════
    def _cargar_excel_auto(self):
        ruta = self.cfg.get("excel_path", "")
        if ruta and os.path.exists(ruta):
            self._cargar_excel_desde(ruta)

    def _cargar_excel(self):
        ruta = filedialog.askopenfilename(
            title="Seleccionar Excel",
            filetypes=[("Excel", "*.xlsx *.xls")])
        if ruta:
            self._cargar_excel_desde(ruta)
            self.cfg["excel_path"] = ruta
            guardar_config(self.cfg)

    def _cargar_excel_desde(self, ruta):
        try:
            self.df = pd.read_excel(ruta, dtype=str).fillna("")
            self.filas_datos = self.df.to_dict(orient="records")

            while len(self.imagenes_por_etiqueta) < len(self.filas_datos):
                self.imagenes_por_etiqueta.append({})
            self.imagenes_por_etiqueta = \
                self.imagenes_por_etiqueta[:len(self.filas_datos)]

            self._actualizar_combo_registros()

            nombre = os.path.basename(ruta)
            self.lbl_excel.config(
                text=f"📊 {nombre} ({len(self.filas_datos)} filas)",
                fg="#00509F")
            self.lbl_estado.config(
                text=f"Excel cargado: {len(self.filas_datos)} registros.")
            self._sincronizar_slots()
            self._actualizar_nav_slot()
            self._actualizar_preview()
        except Exception as e:
            messagebox.showerror("Error",
                f"No se pudo cargar el Excel:\n{e}")

    # ═══════════════════════════════════════════════════════════════
    #  SLOTS
    # ═══════════════════════════════════════════════════════════════
    def _sincronizar_slots(self):
        max_slots = self._cfg_hoja()["cols"] * self._cfg_hoja()["rows"]
        while len(self.slots) < max_slots:
            self.slots.append({"registro_idx": None, "copias": 1})
        self.slots = self.slots[:max_slots]

    def _actualizar_combo_registros(self):
        if self.df is None:
            self.combo_campo["values"] = []
            self.combo_registro["values"] = []
            return
        # Poblar combo de campos (columnas del Excel)
        self.combo_campo["values"] = list(self.df.columns)
        if self.df.columns.any():
            self.combo_campo.current(0)
            self._actualizar_combo_valores()

    def _campo_cambiado(self, event=None):
        self._actualizar_combo_valores()
        # Resetear registro del slot actual
        self.slots[self.slot_actual]["registro_idx"] = None
        if self.combo_registro["values"]:
            self.combo_registro.current(0)
        self._actualizar_total()
        self._actualizar_preview()    

    def _actualizar_combo_valores(self):
        """Rellena combo_registro con los valores del campo seleccionado."""
        if self.df is None:
            self.combo_registro["values"] = []
            return
        campo = self.combo_campo.get()
        if not campo or campo not in self.df.columns:
            self.combo_registro["values"] = ["(vacío)"]
            return
        opciones = ["(vacío)"] + [
            f"{i+1}: {str(row[campo])}"
            for i, row in enumerate(self.filas_datos)
        ]
        self.combo_registro["values"] = opciones

    def _actualizar_nav_slot(self):
        cfg       = self._cfg_hoja()
        max_slots = cfg["cols"] * cfg["rows"]
        self._sincronizar_slots()
        idx  = self.slot_actual
        slot = self.slots[idx]

        self.lbl_slot.config(text=f"Etiqueta {idx+1} / {max_slots}")

        reg_idx = slot.get("registro_idx")
        self._actualizar_combo_valores()
        if self.combo_registro["values"]:
            if reg_idx is None:
                self.combo_registro.current(0)
            else:
                self.combo_registro.current(reg_idx + 1)

        self.spin_copias.set(slot.get("copias", 1))
        self._actualizar_total()

    def _actualizar_total(self):
        cfg     = self._cfg_hoja()
        max_pos = cfg["cols"] * cfg["rows"]
        total   = sum(s["copias"] for s in self.slots
                      if s["registro_idx"] is not None)
        color   = "red" if total > max_pos else "gray"
        self.lbl_total.config(
            text=f"Total: {total} / {max_pos} posiciones ocupadas",
            fg=color)

    def _guardar_slot_actual(self):
        slot = self.slots[self.slot_actual]
        try:
            slot["copias"] = max(1, int(self.spin_copias.get()))
        except ValueError:
            slot["copias"] = 1
        sel = self.combo_registro.current()
        slot["registro_idx"] = None if sel <= 0 else sel - 1

    def _slot_anterior(self):
        if self.slot_actual > 0:
            self._guardar_slot_actual()
            self.slot_actual -= 1
            self._actualizar_nav_slot()
            self._actualizar_preview()

    def _slot_siguiente(self):
        cfg       = self._cfg_hoja()
        max_slots = cfg["cols"] * cfg["rows"]
        if self.slot_actual < max_slots - 1:
            self._guardar_slot_actual()
            self.slot_actual += 1
            self._actualizar_nav_slot()
            self._actualizar_preview()

    def _registro_cambiado(self, event=None):
        self._guardar_slot_actual()
        self._actualizar_total()
        self._actualizar_preview()

    def _copias_cambiadas(self):
        self._guardar_slot_actual()
        self._actualizar_total()
        self._actualizar_preview()

    # ═══════════════════════════════════════════════════════════════
    #  LAYOUT
    # ═══════════════════════════════════════════════════════════════
    def _cargar_layout_auto(self):
        ruta = self.cfg.get("ultimo_layout", "")
        if ruta and os.path.exists(ruta):
            self.layout = cargar_layout(ruta)
            self._restaurar_cfg_hoja_desde_layout()
            self.lbl_layout.config(
                text=f"🎨 {os.path.basename(ruta)}", fg="#00509F")

    def _cargar_layout(self):
        ruta = filedialog.askopenfilename(
            title="Cargar plantilla",
            initialdir=self._ultimo_dir_layout,
            filetypes=[("Layout JSON", "*.json")])
        if ruta:
            self._ultimo_dir_layout = os.path.dirname(ruta)
            self.cfg["ultimo_layout_dir"] = self._ultimo_dir_layout
            self.layout = cargar_layout(ruta)
            self.cfg["ultimo_layout"] = ruta
            guardar_config(self.cfg)
            self._restaurar_cfg_hoja_desde_layout()
            self.lbl_layout.config(
                text=f"🎨 {os.path.basename(ruta)}", fg="#00509F")
            self._sincronizar_slots()
            self._actualizar_nav_slot()
            self._actualizar_preview()

    def _guardar_layout(self):
        ruta = filedialog.asksaveasfilename(
            title="Guardar plantilla",
            initialdir=self._ultimo_dir_layout,
            defaultextension=".json",
            filetypes=[("Layout JSON", "*.json")])
        if ruta:
            self._ultimo_dir_layout = os.path.dirname(ruta)
            self.cfg["ultimo_layout_dir"] = self._ultimo_dir_layout
            self.layout["cfg_hoja"] = self._cfg_hoja()
            guardar_layout(self.layout, ruta)
            self.cfg["ultimo_layout"] = ruta
            guardar_config(self.cfg)
            self.lbl_layout.config(
                text=f"🎨 {os.path.basename(ruta)}", fg="#00509F")
            self.lbl_estado.config(text="Layout guardado.")

    def _restaurar_cfg_hoja_desde_layout(self):
        """Si el layout tiene cfg_hoja guardada, restaura los controles."""
        cfg = self.layout.get("cfg_hoja")
        if not cfg:
            return

        # Entradas numéricas
        self.entry_ancho.delete(0, tk.END)
        self.entry_ancho.insert(0, str(cfg.get("ancho_mm", 210)))

        self.entry_alto.delete(0, tk.END)
        self.entry_alto.insert(0, str(cfg.get("alto_mm", 297)))

        self.entry_margen.delete(0, tk.END)
        self.entry_margen.insert(0, str(cfg.get("margen_mm", 5)))

        self.entry_sangrado.delete(0, tk.END)
        self.entry_sangrado.insert(0, str(cfg.get("sangrado_mm", 0)))

        # Spinboxes
        self.spin_cols.set(cfg.get("cols", 2))
        self.spin_rows.set(cfg.get("rows", 3))

        # Orientación
        self.var_orientacion.set(cfg.get("orientacion", "vertical"))

        # Líneas de corte
        self.var_linea_preview.set(
            cfg.get("linea_corte_preview", True))
        self.var_linea_impresion.set(
            cfg.get("linea_corte_impresion", False))

        # Colores líneas
        color_prev = cfg.get("color_linea_preview", "#aaaaaa")
        self._color_linea_preview = color_prev
        self.btn_color_prev.config(bg=color_prev)

        color_imp = cfg.get("color_linea_impresion", "#cccccc")
        self._color_linea_impresion = color_imp
        self.btn_color_imp.config(bg=color_imp)

        # Actualizar cfg guardada
        self.cfg["hoja"] = cfg
        guardar_config(self.cfg)
            

    def _nuevo_layout(self):
        if messagebox.askyesno("Nueva plantilla",
                "¿Descartar la plantilla actual y empezar una nueva?"):
            self.layout = layout_default()
            self.cfg["ultimo_layout"] = ""
            guardar_config(self.cfg)
            self.lbl_layout.config(text="Plantilla sin guardar", fg="gray")
            self._actualizar_preview()

    # ═══════════════════════════════════════════════════════════════
    #  CLICK EN PREVIEW — seleccionar slot
    # ═══════════════════════════════════════════════════════════════
    def _click_preview(self, event):
        cfg_hoja  = self._cfg_hoja()
        cols      = cfg_hoja["cols"]
        rows      = cfg_hoja["rows"]
        max_slots = cols * rows

        for row in range(rows):
            for col in range(cols):
                idx = row * cols + col
                if idx >= max_slots:
                    break
                x1, y1, x2, y2 = etiqueta_rect_preview(
                    col, row, cfg_hoja,
                    self._preview_w, self._preview_h,
                    dpi=96)
                if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                    self._guardar_slot_actual()
                    self.slot_actual = idx
                    self._actualizar_nav_slot()
                    self._actualizar_preview()
                    return

    # ═══════════════════════════════════════════════════════════════
    #  PREVIEW
    # ═══════════════════════════════════════════════════════════════
    def _actualizar_preview(self, event=None):
        def _generar():
            try:
                cfg_hoja = self._cfg_hoja()

                filas    = []
                imagenes = []
                copias   = []
                for slot in self.slots:
                    idx = slot.get("registro_idx")
                    if idx is not None and idx < len(self.filas_datos):
                        filas.append(self.filas_datos[idx])
                        imagenes.append(
                            self.imagenes_por_etiqueta[idx]
                            if idx < len(self.imagenes_por_etiqueta)
                            else {})
                        copias.append(slot["copias"])

                if not filas:
                    filas    = [{}]
                    imagenes = [{}]
                    copias   = [1]

                total    = sum(copias)
                max_etiq = cfg_hoja["cols"] * cfg_hoja["rows"]
                if total > max_etiq:
                    self.lbl_estado.config(
                        text=f"⚠ {total} etiquetas no caben "
                             f"en {max_etiq} posiciones.",
                        fg="red")
                    return

                hoja = renderizar_hoja(
                    layout=self.layout,
                    filas_datos=filas,
                    imagenes_por_etiqueta=imagenes,
                    copias_por_etiqueta=copias,
                    cfg_hoja=cfg_hoja,
                    linea_corte=cfg_hoja["linea_corte_preview"],
                    color_linea=cfg_hoja["color_linea_preview"],
                    dpi=96
                )


                preview = escalar_preview(
                    hoja, PREVIEW_MAX_W, PREVIEW_MAX_H)
                self._preview_w, self._preview_h = preview.size

                from PIL import ImageDraw
                draw = ImageDraw.Draw(preview)
                idx  = self.slot_actual
                col  = idx % cfg_hoja["cols"]
                row  = idx // cfg_hoja["cols"]
                x1, y1, x2, y2 = etiqueta_rect_preview(
                    col, row, cfg_hoja,
                    self._preview_w, self._preview_h,
                    dpi=96)
                draw.rectangle(
                    [(x1, y1), (x2, y2)],
                    outline="#e6007c", width=2)

                self._preview_img = ImageTk.PhotoImage(preview)
                self.canvas_preview.config(
                    width=self._preview_w,
                    height=self._preview_h)
                self.canvas_preview.create_image(
                    0, 0, anchor="nw", image=self._preview_img)
                self.lbl_estado.config(
                    text="Vista previa actualizada.", fg="gray")

            except Exception as e:
                self.lbl_estado.config(
                    text=f"Error preview: {e}", fg="red")

        threading.Thread(target=_generar, daemon=True).start()

    # ═══════════════════════════════════════════════════════════════
    #  EDITOR
    # ═══════════════════════════════════════════════════════════════
    def _abrir_editor(self):
        from editor_etiqueta import EditorEtiqueta
        columnas = list(self.df.columns) if self.df is not None else []

        slot    = self.slots[self.slot_actual]
        reg_idx = slot.get("registro_idx")
        datos_fila = self.filas_datos[reg_idx] \
                     if reg_idx is not None \
                     and reg_idx < len(self.filas_datos) \
                     else {}
        imagenes = self.imagenes_por_etiqueta[reg_idx] \
                   if reg_idx is not None \
                   and reg_idx < len(self.imagenes_por_etiqueta) \
                   else {}

        def _on_close(layout_nuevo, imagenes_nuevo):
            self.layout = layout_nuevo
            if reg_idx is not None:
                self.imagenes_por_etiqueta[reg_idx] = imagenes_nuevo
            self.deiconify()
            self._actualizar_preview()

        self.withdraw()

        editor = EditorEtiqueta(
            parent=self,
            layout=self.layout,
            columnas=columnas,
            datos_fila=datos_fila,
            imagenes=imagenes,
            cfg_hoja=self._cfg_hoja(),
            on_close=_on_close
        )
        editor.after(10, lambda: self._centrar_en_padre(editor))
        editor.after(10, lambda: self._centrar_en_padre(editor))
    # ═══════════════════════════════════════════════════════════════
    #  IMPRIMIR / PDF
    # ═══════════════════════════════════════════════════════════════
    def _construir_hoja_impresion(self):
        cfg_hoja = self._cfg_hoja()
        filas    = []
        imagenes = []
        copias   = []

        for slot in self.slots:
            idx = slot.get("registro_idx")
            if idx is not None and idx < len(self.filas_datos):
                filas.append(self.filas_datos[idx])
                imagenes.append(
                    self.imagenes_por_etiqueta[idx]
                    if idx < len(self.imagenes_por_etiqueta)
                    else {})
                copias.append(slot["copias"])

        if not filas:
            raise ValueError(
                "No hay ningún slot con registro asignado.")

        total    = sum(copias)
        max_etiq = cfg_hoja["cols"] * cfg_hoja["rows"]
        if total > max_etiq:
            raise ValueError(
                f"No caben {total} etiquetas en la hoja "
                f"({cfg_hoja['cols']}×{cfg_hoja['rows']} = "
                f"{max_etiq} máximo).\n"
                f"Reduce las copias o cambia el grid.")

        return renderizar_hoja(
            layout=self.layout,
            filas_datos=filas,
            imagenes_por_etiqueta=imagenes,
            copias_por_etiqueta=copias,
            cfg_hoja=cfg_hoja,
            linea_corte=cfg_hoja["linea_corte_impresion"],
            color_linea=cfg_hoja["color_linea_impresion"],
            dpi=DPI
        )

    def _imprimir(self):
        self.lbl_estado.config(text="Generando PDF para imprimir...")

        def _job():
            try:
                hoja = self._construir_hoja_impresion()
                imprimir_hoja(hoja)
                self.after(0, lambda: self.lbl_estado.config(
                    text="✅ PDF abierto en visor.", fg="gray"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror(
                    "Error de impresión", str(e)))
                self.after(0, lambda: self.lbl_estado.config(
                    text="❌ Error al imprimir.", fg="red"))

        threading.Thread(target=_job, daemon=True).start()

    def _guardar_pdf(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            title="Guardar hoja como PDF")
        if not path:
            return
        try:
            hoja = self._construir_hoja_impresion()
            exportar_pdf_etiquetas(hoja, path)
            self.lbl_estado.config(
                text=f"✅ PDF guardado: {os.path.basename(path)}",
                fg="gray")
            messagebox.showinfo("Guardado",
                f"PDF guardado correctamente en:\n{path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ═══════════════════════════════════════════════════════════════
    #  LIMPIAR
    # ═══════════════════════════════════════════════════════════════
    def _limpiar(self):
        
        if not messagebox.askyesno(
                "Limpiar todo",
                "Se eliminarán:\n\n"
                "  • Excel seleccionado\n"
                "  • Datos Excel cargados\n"
                "  • Plantilla actual\n"
                "  • Asignaciones de etiquetas\n\n"
                "¿Deseas continuar?",
                icon="warning"):
            return
        self.df                    = None
        self.filas_datos           = []
        self.imagenes_por_etiqueta = []
        self.slots                 = []
        self.slot_actual           = 0
        self.layout                = layout_default()
        self.lbl_excel.config(text="Sin archivo",
                              fg="gray")
        self.lbl_layout.config(text="Plantilla actual sin guardar", fg="gray")
        self.lbl_slot.config(text="Etiqueta - / -")
        self.spin_copias.set(1)
        self.lbl_total.config(text="Total: 0 / 0 posiciones ocupadas")
        self.lbl_estado.config(text="Listo.", fg="gray")
        self._sincronizar_slots()
        self._actualizar_nav_slot()
        self._actualizar_preview()
        self.combo_campo["values"] = []
        self.combo_campo.set("")
        self.combo_registro["values"] = []
        self.combo_registro.set("")

    def destroy(self):
        try:
            self.unbind_all("<MouseWheel>")
        except Exception:
            pass
        super().destroy()
    
# ── Arranque standalone ───────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    app = AppEtiquetas(root)
    app.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()
