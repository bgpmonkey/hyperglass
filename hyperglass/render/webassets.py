"""Renders Jinja2 & Sass templates for use by the front end application."""

# Standard Library Imports
import json
import subprocess
from pathlib import Path

# Third Party Imports
import jinja2

# Project Imports
from hyperglass.configuration import frontend_devices
from hyperglass.configuration import frontend_networks
from hyperglass.configuration import frontend_params
from hyperglass.configuration import params
from hyperglass.exceptions import HyperglassError
from hyperglass.util import log

# Module Directories
working_directory = Path(__file__).resolve().parent
hyperglass_root = working_directory.parent
file_loader = jinja2.FileSystemLoader(str(working_directory))
env = jinja2.Environment(
    loader=file_loader, autoescape=True, extensions=["jinja2.ext.autoescape"]
)


def render_frontend_config():
    """Render user config to JSON for use by frontend."""
    rendered_frontend_file = hyperglass_root.joinpath("static/src/js/frontend.json")
    try:
        with rendered_frontend_file.open(mode="w") as frontend_file:
            frontend_file.write(
                json.dumps(
                    {
                        "config": frontend_params,
                        "networks": frontend_networks,
                        "devices": frontend_devices,
                    }
                )
            )
    except jinja2.exceptions as frontend_error:
        log.error(f"Error rendering front end config: {frontend_error}")
        raise HyperglassError(frontend_error)


def get_fonts():
    """Download Google fonts."""
    font_dir = hyperglass_root.joinpath("static/src/sass/fonts")
    font_bin = str(
        hyperglass_root.joinpath("static/src/node_modules/get-google-fonts/cli.js")
    )
    font_base = "https://fonts.googleapis.com/css?family={p}|{m}&display=swap"
    font_primary = "+".join(params.branding.font.primary.split(" ")).strip()
    font_mono = "+".join(params.branding.font.mono.split(" ")).strip()
    font_url = font_base.format(p=font_primary + ":300,400,700", m=font_mono + ":400")
    proc = subprocess.Popen(
        ["node", font_bin, "-w", "-i", font_url, "-o", font_dir],
        cwd=hyperglass_root.joinpath("static"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        stdout, stderr = proc.communicate(timeout=60)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
    if proc.returncode != 0:
        output_error = stderr.decode("utf-8")
        log.error(output_error)
        raise HyperglassError(f"Error downloading font from URL {font_url}")
    else:
        proc.kill()


def render_theme():
    """Render Jinja2 template to Sass file."""
    rendered_theme_file = hyperglass_root.joinpath("static/src/sass/theme.sass")
    try:
        template = env.get_template("templates/theme.sass.j2")
        log.debug(f"Branding variables:\n{params.branding.json(indent=4)}")
        rendered_theme = template.render(params.branding)
        log.debug(f"Rendered theme:\n{str(rendered_theme)}")
        with rendered_theme_file.open(mode="w") as theme_file:
            theme_file.write(rendered_theme)
    except jinja2.exceptions as theme_error:
        log.error(f"Error rendering theme: {theme_error}")
        raise HyperglassError(theme_error)


def build_assets():
    """Build, bundle, and minify Sass/CSS/JS web assets."""
    proc = subprocess.Popen(
        ["yarn", "--silent", "--emoji", "false", "--json", "--no-progress", "build"],
        cwd=hyperglass_root.joinpath("static/src"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        stdout, stderr = proc.communicate(timeout=60)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
    output_out = json.loads(stdout.decode("utf-8").split("\n")[0])
    if proc.returncode != 0:
        output_error = json.loads(stderr.decode("utf-8").strip("\n"))
        log.error(output_error["data"])
        raise HyperglassError(
            f'Error building web assets with script {output_out["data"]}:'
            f'{output_error["data"]}'
        )
    log.debug(f'Built web assets with script {output_out["data"]}')


def render_assets():
    """Run web asset rendering functions."""
    try:
        log.debug("Rendering front end config...")
        render_frontend_config()
        log.debug("Rendered front end config")
    except HyperglassError as frontend_error:
        raise HyperglassError(frontend_error) from None

    try:
        log.debug("Downloading theme fonts...")
        get_fonts()
        log.debug("Downloaded theme fonts")
    except HyperglassError as theme_error:
        raise HyperglassError(theme_error) from None

    try:
        log.debug("Rendering theme elements...")
        render_theme()
        log.debug("Rendered theme elements")
    except HyperglassError as theme_error:
        raise HyperglassError(theme_error) from None

    try:
        log.debug("Building web assets...")
        build_assets()
        log.debug("Built web assets")
    except HyperglassError as assets_error:
        raise HyperglassError(str(assets_error)) from None
