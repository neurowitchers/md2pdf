"""Bundled md2pdf themes (packaged into the wheel).

Each theme is a subdirectory containing ``theme.yaml`` plus ``.tex.j2``
templates. Resolve bundled themes via
``importlib.resources.files("md2pdf.themes") / "<name>"``.
"""
