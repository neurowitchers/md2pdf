"""md2pdf — Markdown to branded PDF slides (Pandoc + Beamer).

A theme-as-data CLI: the engine renders slides and a theme supplies the
branding (palette, fonts, logos, title/thank-you frames) as data plus Jinja2
`.tex.j2` templates. Bundled themes ship inside this package under
``md2pdf.themes`` and are loaded via :mod:`importlib.resources`.
"""

__version__ = "0.1.0"
