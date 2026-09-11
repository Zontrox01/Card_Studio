# Card Studio

Aplicación de escritorio para el diseño e impresión de tarjetas NFC y etiquetas.

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![PySide6](https://img.shields.io/badge/UI-PySide6%20(Qt6)-green)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)
![License](https://img.shields.io/badge/license-MIT-yellow)

---

## 📋 Descripción
Card Studio es una suite de aplicaciones integradas para el diseño e impresión de tarjetas de identificación y etiquetas con tecnología NFC. La aplicación permite:

Diseño de tarjetas de presencia personalizadas (anverso/reverso)

Creación de tarjetas NFC con datos variables desde Excel

Diseñador de etiquetas avanzado con arrastrar y soltar (drag & drop)

Generación de códigos QR dinámicos

Impresión directa o exportación a PDF

## ✨ Características principales
Tarjetas de Presencia
Diseño a doble cara con contenido personalizable

Campos variables: Nombre, Cargo, Empresa, Email, Teléfono

Personalización de colores de fondo, barra inferior y texto

Inserción de foto y logo

Impresión directa o guardado en PDF

Tarjetas NFC
Carga de datos desde archivos Excel

Vista previa en tiempo real

Impresión a una o dos caras

Generación de códigos QR en el reverso

Selección de campos variables

Diseñador de Etiquetas
Configuración de hoja personalizable (tamaño, orientación, márgenes)

Sistema de plantillas reutilizables

Editor drag & drop

Elementos: Texto, Imagen, QR, Rectángulos, Elipses, Líneas y Flechas

Campos fijos o variables desde Excel

Líneas de corte configurables

## 🚀 Requisitos del sistema
Sistema Operativo: Windows 10 o superior

Python: 3.10 o superior

Impresora: Impresora de tarjetas compatible (conexión USB)

Tarjetas: Tarjetas NFC215 (para funcionalidad NFC)

## 📦 Instalación
1. Clonar el repositorio
bash
git clone https://github.com/Zontrox01/Card_Studio.git
cd Card_Studio
2. Crear entorno virtual (recomendado)
bash
python -m venv venv
Activar en Windows:
venv\Scripts\activate
3. Instalar dependencias
bash
pip install -r requirements.txt
4. Estructura de archivos
Asegúrate de tener la siguiente estructura:

text
- 📁Card Studio/
  - 📄 card_designer.py
  - 📄 card_designer_excel.py
  - 📄 editor_etiqueta.py
  - 📄 etiqueta_designer.py
  - 📄 gui.py
  - 📄 gui_etiquetas.py
  - 📄 gui_excel.py
  - 📄 logo.ico
  - 📄 main.py
  - 📄 printer.py
  - 📄 qr_generator.py
  - 📄 requirements.txt
  - 📁 Datos
    - 📄 Etiquetas.xlsx
    - 📄 Etiquetas2.xlsx
    - 📄 caras.txt
    - 📄 empresa.txt
    - 📄 etiquetas_config.txt
    - 📄 excel.txt
    - 📄 logo.png
    - 📁 Fotos
    - 📁 layouts

## 🎯 Uso
Ejecutar la aplicación
bash
python main.py
Compilar a ejecutable (opcional)
bash
python -m PyInstaller --onefile --windowed --icon=datos\logo.png --add-data "datos;datos" main.py
Formato del archivo Excel
Primera fila: Encabezados/títulos de cada campo

Segunda fila en adelante: Registros de datos

Columna obligatoria: UID (primera columna)

Columna opcional: URL (última columna para URLs)

## 🖥️ Módulos
### Tarjetas de Presencia
Diseña tarjetas de identificación a doble cara con:

Campos personalizables (Nombre, Cargo, Empresa, Email, Teléfono)

Colores configurables (fondo, barra inferior, texto)

Foto y logo personalizados

Vista previa en tiempo real

### Tarjetas Informativas
Crea tarjetas con tecnología NFC:

Carga de datos desde Excel

Selección de campos variables (hasta 5 campos)

Impresión a una/dos caras

Generación de QR dinámico en el reverso

Navegación entre registros

### Diseñador de Etiquetas
Editor avanzado de etiquetas:

Configuración de hoja: tamaño, orientación, márgenes, sangrado

Sistema de plantillas (guardar/cargar)

Editor drag & drop con cuadrícula

Elementos: Texto, Imagen, QR, Formas geométricas

Campos fijos o variables desde Excel

Vista previa en tiempo real

Líneas de corte personalizables

## 📝 Dependencias principales
pandas: Manejo de datos Excel

openpyxl: Lectura/escritura de archivos Excel

Pillow: Manipulación de imágenes

qrcode: Generación de códigos QR

reportlab: Generación de PDFs

pywin32: Integración con Windows (impresión)

PyInstaller: Compilación a ejecutable

## 🤝 Contribuciones
Las contribuciones son bienvenidas. Por favor:

Fork el repositorio

Crea una rama para tu feature (git checkout -b feature/NuevaCaracteristica)

Commit tus cambios (git commit -m 'Agrega nueva característica')

Push a la rama (git push origin feature/NuevaCaracteristica)

Abre un Pull Request

## 📄 Licencia
Este proyecto está bajo la Licencia MIT. Ver el archivo LICENSE para más detalles.

## 🙏 Agradecimientos
Pillow: Biblioteca de procesamiento de imágenes

ReportLab: Generación de PDFs

qrcode: Generación de códigos QR

pandas: Manipulación de datos

## 📞 Soporte
Para soporte, reporte de bugs o sugerencias, por favor abre un issue en el repositorio de GitHub.

Nota: Para el funcionamiento completo de la aplicación, asegúrate de tener una impresora de tarjetas compatible conectada al sistema.
