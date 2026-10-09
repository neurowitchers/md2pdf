"""Theme loading + Jinja2 rendering layer (theme-as-data).

A *theme* is a directory containing:

* ``theme.yaml``       — palette, font, logos[], required_fields[],
                          optional_fields[], font_scales{}, default_font_scale.
                          (NO ``headline`` expression — critique E2: the headline
                          is composed inside ``title.tex.j2``.)
* ``preamble.tex.j2``  — colours/fonts/beamer setup (header include).
* ``title.tex.j2``     — title frame template (composes the headline from fields).
* ``thankyou.tex.j2``  — thank-you frame template.
* ``assets/`` (optional) — logo images driving the ``logos`` loop.

Themes are resolved either from the **bundled** package data
(``importlib.resources.files("md2pdf.themes") / name`` — critique E1) or from an
**external** directory (``--theme-dir``). Bundled themes are trusted and use a
standard :class:`jinja2.Environment`; external themes are rendered through a
:class:`jinja2.sandbox.SandboxedEnvironment` (critique E5).

Field handling (critique P5 + E8): every front-matter value is coerced to
``str`` and LaTeX-escaped, then placed in the template context under its field
name — so templates need no per-token ``| latexescape`` filter. The *unescaped*
values are also exposed as a ``raw_fields`` mapping for the rare case a template
needs the raw text (e.g. to emit its own markup).
"""
from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, StrictUndefined, TemplateSyntaxError
from jinja2.sandbox import SandboxedEnvironment

from .latex import latex_escape, latex_path

# Required template/config files that must exist in every theme directory.
REQUIRED_THEME_FILES = (
    "theme.yaml",
    "preamble.tex.j2",
    "title.tex.j2",
    "thankyou.tex.j2",
)

_PREAMBLE_TEMPLATE = "preamble.tex.j2"
_TITLE_TEMPLATE = "title.tex.j2"
_THANKYOU_TEMPLATE = "thankyou.tex.j2"

# LaTeX-safe Jinja2 delimiters. Variables keep the familiar ``{{ field }}``
# form (and literal ``{{ '{' }}`` to emit a brace), but *statement* and
# *comment* delimiters are moved off ``{%``/``{#`` because LaTeX uses ``{%``
# pervasively (an opening group immediately followed by a comment, e.g.
# ``\setbeamertemplate{frametitle}{%``). Blocks therefore use ``<% ... %>`` and
# comments ``<# ... #>``. These must be identical for both the compile-only
# validation environment and the render environment, otherwise a template that
# validates would fail to render (or vice versa).
_JINJA_SYNTAX = dict(
    block_start_string="<%",
    block_end_string="%>",
    variable_start_string="{{",
    variable_end_string="}}",
    comment_start_string="<#",
    comment_end_string="#>",
)


def _make_env(env_cls: type[Environment], **kwargs: Any) -> Environment:
    """Construct a Jinja2 environment with the LaTeX-safe delimiters."""
    return env_cls(
        undefined=StrictUndefined,
        autoescape=False,  # values are pre-escaped into the context (P5).
        keep_trailing_newline=True,
        **_JINJA_SYNTAX,
        **kwargs,
    )


@dataclass
class Theme:
    """A loaded, render-ready theme.

    NO ``headline`` field (critique E2): the headline is composed directly in
    the theme's ``title.tex.j2`` from the available fields.
    """

    name: str
    dir: Path
    palette: dict[str, str]
    font: dict[str, Any]
    logos: list[dict[str, Any]]
    required_fields: list[str]
    optional_fields: list[str]
    font_scales: dict[str, str]
    default_font_scale: str
    assets_dir: Path
    # The compiled Jinja2 environment (standard for bundled, sandboxed for
    # external). Not part of the declarative schema; populated by load_theme.
    _env: Environment = dc_field(repr=False, default=None)  # type: ignore[assignment]

    # -- field validation ---------------------------------------------------
    def validate_fields(self, fields: dict[str, str]) -> None:
        """Enforce ``required_fields``; raise a loud, actionable error.

        A field counts as present only if it is a non-empty (stripped) string,
        mirroring the legacy ``require_fields`` semantics.
        """
        missing = [
            k for k in self.required_fields
            if not str(fields.get(k, "")).strip()
        ]
        if missing:
            raise SystemExit(
                f"ERROR: theme '{self.name}' is missing required front-matter "
                f"field(s): {', '.join(missing)}\n"
                f"Required: {', '.join(self.required_fields)}\n"
                f"Optional: {', '.join(self.optional_fields) or '(none)'}"
            )

    def resolve_font_scale(self, fields: dict[str, str]) -> str:
        """Return the body-font point size for the deck's ``fontsize`` field.

        Optional. Omitted/empty -> ``default_font_scale``. Unknown names fail
        loudly with the valid set (matching the legacy behaviour).
        """
        raw = str(fields.get("fontsize", "")).strip().lower()
        if not raw:
            raw = self.default_font_scale
        if raw not in self.font_scales:
            raise SystemExit(
                f"ERROR: unknown fontsize '{raw}' for theme '{self.name}'. "
                f"Valid named scales: {', '.join(self.font_scales)}"
            )
        return self.font_scales[raw]

    # -- context preparation ------------------------------------------------
    def _context(self, fields: dict[str, str]) -> dict[str, Any]:
        """Build the Jinja2 render context from front-matter fields.

        Each field value is coerced to ``str`` and LaTeX-escaped, then exposed
        under its own name (so templates reference ``{{ title }}`` directly and
        get safe output without a filter — critique P5). The unescaped values
        are available under ``raw_fields``. Theme metadata (palette, font,
        logos, assets_dir) is also exposed.
        """
        raw_fields = {k: str(v) for k, v in fields.items()}
        escaped = {k: latex_escape(v) for k, v in raw_fields.items()}

        # Short title for the Beamer footer: optional `short_title` override,
        # else fall back to `title` (both already escaped).
        short_title = escaped.get("short_title") or escaped.get("title", "")

        ctx: dict[str, Any] = {}
        # Field values (escaped) at the top level.
        ctx.update(escaped)
        # Theme metadata + unescaped raw fields.
        ctx["raw_fields"] = raw_fields
        ctx["palette"] = self.palette
        ctx["font"] = self.font
        ctx["logos"] = self.logos
        ctx["assets_dir"] = latex_path(self.assets_dir)
        ctx["short_title"] = short_title
        ctx["font_scale"] = self.resolve_font_scale(fields)
        return ctx

    # -- rendering ----------------------------------------------------------
    def _render(self, template_name: str, fields: dict[str, str]) -> str:
        tmpl = self._env.get_template(template_name)
        return tmpl.render(**self._context(fields))

    def render_preamble(self, fields: dict[str, str]) -> str:
        return self._render(_PREAMBLE_TEMPLATE, fields)

    def render_title(self, fields: dict[str, str]) -> str:
        return self._render(_TITLE_TEMPLATE, fields)

    def render_thankyou(self, fields: dict[str, str]) -> str:
        return self._render(_THANKYOU_TEMPLATE, fields)


def _read_yaml(path: Path, theme_name: str) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:  # pragma: no cover - exercised via validate_theme
        raise SystemExit(
            f"ERROR: theme '{theme_name}': cannot read {path.name}: {exc}"
        )
    try:
        data = yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        raise SystemExit(
            f"ERROR: theme '{theme_name}': {path.name} is not valid YAML:\n{exc}"
        )
    if not isinstance(data, dict):
        raise SystemExit(
            f"ERROR: theme '{theme_name}': {path.name} must be a YAML mapping "
            f"at the top level (got {type(data).__name__})."
        )
    return data


def validate_theme(theme_dir: Path) -> None:
    """Validate a theme directory before use (critique E3).

    Asserts the required files exist, the YAML parses, and each ``.tex.j2``
    template compiles. Raises :class:`SystemExit` with an actionable message
    naming the theme and the offending file.
    """
    theme_dir = Path(theme_dir)
    name = theme_dir.name

    if not theme_dir.is_dir():
        raise SystemExit(
            f"ERROR: theme directory not found: {theme_dir}"
        )

    missing = [f for f in REQUIRED_THEME_FILES if not (theme_dir / f).is_file()]
    if missing:
        raise SystemExit(
            f"ERROR: theme '{name}' at {theme_dir} is missing required "
            f"file(s): {', '.join(missing)}\n"
            f"Every theme must provide: {', '.join(REQUIRED_THEME_FILES)}"
        )

    # YAML parses?
    _read_yaml(theme_dir / "theme.yaml", name)

    # Templates compile? Use a plain Environment purely for compilation checks;
    # the real render env (standard vs sandboxed) is built in load_theme. The
    # delimiters MUST match the render environment (critique E3/E5).
    compile_env = _make_env(Environment)
    for tmpl_name in ("preamble.tex.j2", "title.tex.j2", "thankyou.tex.j2"):
        src = (theme_dir / tmpl_name).read_text(encoding="utf-8")
        try:
            compile_env.from_string(src)
        except TemplateSyntaxError as exc:
            raise SystemExit(
                f"ERROR: theme '{name}': template {tmpl_name} failed to "
                f"compile at line {exc.lineno}: {exc.message}"
            )


def _resolve_theme_dir(name: str | None, theme_dir: Path | str | None) -> tuple[Path, bool]:
    """Return ``(resolved_dir, is_external)``.

    ``theme_dir`` (external ``--theme-dir``) takes precedence over the bundled
    ``name``. When neither is given, the bundled ``default`` theme is used.
    """
    if theme_dir is not None:
        resolved = Path(theme_dir)
        if not resolved.is_dir():
            raise SystemExit(
                f"ERROR: --theme-dir path is not a directory: {resolved}"
            )
        return resolved, True

    # Bundled theme via importlib.resources (critique E1).
    from importlib.resources import files

    theme_name = name or "default"
    try:
        base = files("md2pdf.themes")
    except ModuleNotFoundError as exc:  # pragma: no cover - packaging error
        raise SystemExit(f"ERROR: bundled themes package missing: {exc}")
    candidate = base / theme_name
    # ``files()`` returns a Traversable; for a normal installed/editable
    # package this is a real filesystem path.
    resolved = Path(str(candidate))
    if not resolved.is_dir():
        available = sorted(
            p.name for p in Path(str(base)).iterdir() if p.is_dir()
            and (p / "theme.yaml").is_file()
        )
        raise SystemExit(
            f"ERROR: bundled theme '{theme_name}' not found.\n"
            f"Available bundled themes: {', '.join(available) or '(none)'}\n"
            f"Or supply an external theme with --theme-dir <path>."
        )
    return resolved, False


def load_theme(
    name: str | None = None,
    theme_dir: Path | str | None = None,
) -> Theme:
    """Load a theme (bundled by ``name`` or external via ``theme_dir``).

    Bundled themes use a standard :class:`jinja2.Environment`; external themes
    (``--theme-dir``) are rendered through a
    :class:`jinja2.sandbox.SandboxedEnvironment` (critique E5). The theme
    directory is validated (:func:`validate_theme`) before the environment is
    built.
    """
    resolved_dir, is_external = _resolve_theme_dir(name, theme_dir)
    validate_theme(resolved_dir)

    cfg = _read_yaml(resolved_dir / "theme.yaml", resolved_dir.name)

    palette = dict(cfg.get("palette") or {})
    font = dict(cfg.get("font") or {})
    logos = list(cfg.get("logos") or [])
    required_fields = list(cfg.get("required_fields") or [])
    optional_fields = list(cfg.get("optional_fields") or [])
    font_scales = {str(k): str(v) for k, v in (cfg.get("font_scales") or {}).items()}
    default_font_scale = str(cfg.get("default_font_scale") or "normal")

    if default_font_scale not in font_scales and font_scales:
        raise SystemExit(
            f"ERROR: theme '{resolved_dir.name}': default_font_scale "
            f"'{default_font_scale}' is not one of the declared font_scales: "
            f"{', '.join(font_scales)}"
        )

    # Theme assets directory. Default: the theme's own ``assets/`` subdir.
    # Asset-dir override: a theme whose logo assets are proprietary or supplied
    # out-of-tree may redirect the assets directory to a non-committed location
    # via, in order of precedence:
    #   1. the ``MD2PDF_<THEMENAME>_ASSETS_DIR`` environment variable
    #      (theme name upper-cased, non-alnum -> ``_``), then the generic
    #      ``MD2PDF_ASSETS_DIR``;
    #   2. an ``assets_dir`` key in ``theme.yaml`` (absolute, or relative to
    #      the theme directory).
    # Templates reference files under ``assets_dir``; the files need only exist
    # at render/compile time.
    import os as _os
    import re as _re

    assets_dir = resolved_dir / "assets"
    env_key = "MD2PDF_" + _re.sub(r"[^A-Z0-9]", "_", resolved_dir.name.upper()) + "_ASSETS_DIR"
    override = _os.environ.get(env_key) or _os.environ.get("MD2PDF_ASSETS_DIR")
    if not override:
        yaml_assets = cfg.get("assets_dir")
        if yaml_assets:
            override = str(yaml_assets)
    if override:
        od = Path(override)
        assets_dir = od if od.is_absolute() else (resolved_dir / od)

    # Build the Jinja2 environment. Templates are loaded from the theme dir.
    # External themes are sandboxed (critique E5); bundled themes are trusted.
    from jinja2 import FileSystemLoader

    loader = FileSystemLoader(str(resolved_dir))
    env_cls = SandboxedEnvironment if is_external else Environment
    env = _make_env(env_cls, loader=loader)

    return Theme(
        name=resolved_dir.name,
        dir=resolved_dir,
        palette=palette,
        font=font,
        logos=logos,
        required_fields=required_fields,
        optional_fields=optional_fields,
        font_scales=font_scales,
        default_font_scale=default_font_scale,
        assets_dir=assets_dir,
        _env=env,
    )
