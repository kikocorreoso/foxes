# -*- coding: utf-8 -*-
#
# Configuration file for the Sphinx documentation builder.
#
# This file does only contain a selection of the most common options. For a
# full list see the documentation:
# http://www.sphinx-doc.org/en/master/config

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys

sys.path.insert(0, os.path.abspath("../.."))

from foxes import __version__

# -- Project information -----------------------------------------------------

project = "foxes"
copyright = "2023, Fraunhofer IWES"
author = "Fraunhofer IWES"

# The short X.Y version
version = __version__
# The full version, including alpha/beta/rc tags
release = __version__


# -- General configuration ---------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#
# needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "nbsphinx",
    "sphinx_immaterial",
    "sphinx_immaterial.apidoc.python.apigen",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosectionlabel",
    # "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.mathjax",
    # "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    # "sphinx.ext.inheritance_diagram",
    "sphinx.ext.doctest",
    "m2r2",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "numpy": ("https://docs.scipy.org/doc/numpy/", None),
    "scipy": ("https://docs.scipy.org/doc/scipy/reference/", None),
}

# Add any paths that contain templates here, relative to this directory.
# templates_path = ["_templates"]
# autosummary_generate = False

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
#
source_suffix = [".rst", ".md"]

# The master toctree document.
master_doc = "index"

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = "en"

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = [
    # ipynb checkpoints
    "notebooks/.ipynb_checkpoints/*.ipynb",
    "build/*",
    # "_templates/*",
    # DEBUG
    "examples.rst",
    "notebooks/*",
    # "notebooks/layout_opt.ipynb,"
    # "api.rst"
]

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = None

# autosummary_generate = True
napolean_use_rtype = False

# -- Options for sphinxcontrib.email ------------------------------------------
# email_automode = True


# -- Options for nbsphinx -----------------------------------------------------

# Execute notebooks before conversion: 'always', 'never', 'auto' (default)
# We execute all notebooks, exclude the slow ones using 'exclude_patterns'
nbsphinx_execute = "always"

# Use this kernel instead of the one stored in the notebook metadata:
# nbsphinx_kernel_name = 'python3'

# List of arguments to be passed to the kernel that executes the notebooks:
# nbsphinx_execute_arguments = []

# If True, the build process is continued even if an exception occurs:
# nbsphinx_allow_errors = True


# Controls when a cell will time out (defaults to 30; use -1 for no timeout):
nbsphinx_timeout = 500

# Default Pygments lexer for syntax highlighting in code cells:
# nbsphinx_codecell_lexer = 'ipython3'

# Width of input/output prompts used in CSS:
# nbsphinx_prompt_width = '8ex'

# If window is narrower than this, input/output prompts are on separate lines:
# nbsphinx_responsive_width = '700px'

# This is processed by Jinja2 and inserted before each notebook
# Fix for issue with pyplot, cf
# https://github.com/readthedocs/sphinx_rtd_theme/issues/788#issuecomment-585785027
nbsphinx_prolog = r"""
.. raw:: html

    <script src='http://cdnjs.cloudflare.com/ajax/libs/require.js/2.1.10/require.min.js'></script>
    <script>require=requirejs;</script>


"""

# This is processed by Jinja2 and inserted after each notebook
# nbsphinx_epilog = r"""
# """

# Input prompt for code cells. "%s" is replaced by the execution count.
nbsphinx_input_prompt = "In [%s]:"

# Output prompt for code cells. "%s" is replaced by the execution count.
nbsphinx_output_prompt = "Out[%s]:"

# Specify conversion functions for custom notebook formats:
# import jupytext
# nbsphinx_custom_formats = {
#    '.Rmd': lambda s: jupytext.reads(s, '.Rmd'),
# }

# Link or path to require.js, set to empty string to disable
# nbsphinx_requirejs_path = ''

# Options for loading require.js
# nbsphinx_requirejs_options = {'async': 'async'}

mathjax3_config = {
    "TeX": {"equationNumbers": {"autoNumber": "AMS", "useLabelIds": True}},
}

# Additional files needed for generating LaTeX/PDF output:
# latex_additional_files = ['references.bib']

# -- Options for autodoc ----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#configuration

# Automatically extract typehints when specified and place them in
# descriptions of the relevant function/method.
autodoc_typehints = "description"

# Don't show class signature with the class' name.
autodoc_class_signature = "separated"

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_immaterial"

# html_theme = 'cloud'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = {
    # TOC options
    #'navigation_depth': 2,  # only show 2 levels on left sidebar
    # "collapse_navigation": False,  # don't allow sidebar to collapse,
    "site_url": "https://fraunhoferiwes.github.io/foxes.docs/index.html",
    "repo_url": "https://github.com/FraunhoferIWES/foxes",
    "icon": {"repo": "fontawesome/brands/github", "edit": "material/file-edit-outline"},
    "palette": {"primary": "teal"},
    "toc_title_is_page_title": True,
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# html_static_path = ["_static"]

# custom.css is inside one of the html_static_path folders (e.g. _static)
# html_css_files = ["custom.css"]

# Custom sidebar templates, must be a dictionary that maps document names
# to template names.
#
# The default sidebars (for documents that don't match any pattern) are
# defined by theme itself.  Builtin themes are using these templates by
# default: ``['localtoc.html', 'relations.html', 'sourcelink.html',
# 'searchbox.html']``.
#
# html_sidebars = {}


# -- Options for HTMLHelp output ---------------------------------------------

# Output file base name for HTML help builder.
htmlhelp_basename = "foxesdoc"


# -- Options for LaTeX output ------------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    #
    # 'papersize': 'letterpaper',
    # The font size ('10pt', '11pt' or '12pt').
    #
    # 'pointsize': '10pt',
    # Additional stuff for the LaTeX preamble.
    #
    # 'preamble': '',
    # Latex figure (float) alignment
    #
    # 'figure_align': 'htbp',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    (master_doc, "foxes.tex", "foxes Documentation", "Fraunhofer IWES", "manual"),
]


# -- Options for manual page output ------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [(master_doc, "foxes", "foxes Documentation", [author], 1)]


# -- Options for Texinfo output ----------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (
        master_doc,
        "foxes",
        "foxes Documentation",
        author,
        "foxes",
        "Farm Optimization and eXtended yield Evaluation Software",
        "Miscellaneous",
    ),
]


# -- Options for Epub output -------------------------------------------------

# Bibliographic Dublin Core info.
epub_title = project

# The unique identifier of the text. This can be a ISBN number
# or the project homepage.
#
# epub_identifier = ''

# A unique identification for the text.
#
# epub_uid = ''

# A list of files that should not be packed into the epub file.
epub_exclude_files = ["search.html"]

# -- python_apigen configuration -------------------------------------------------

python_apigen_modules = {
    "foxes.variables": "_foxes/variables/",
    "foxes.constants": "_foxes/constants/",
    "foxes.algorithms": "_algorithms/",
    "foxes.algorithms.downwind": "_algorithms/downwind/",
    "foxes.algorithms.downwind.models": "_algorithms/downwind/models/",
    "foxes.algorithms.iterative": "_algorithms/iterative/",
    "foxes.algorithms.iterative.models": "_algorithms/iterative/models/",
    "foxes.core": "_core/",
    "foxes.data": "_data/",
    "foxes.input.farm_layout": "_input/farm_layout/",
    "foxes.input.states": "_input/states/",
    "foxes.input.windio": "_input/windio/",
    "foxes.output": "_output/",
    "foxes.models.model_book": "_models/model_book/",
    "foxes.models.farm_controllers": "_models/farm_controllers/",
    "foxes.models.farm_models": "_models/farm_models/",
    "foxes.models.partial_wakes": "_models/partial_wakes/",
    "foxes.models.point_models": "_models/point_models/",
    "foxes.models.rotor_models": "_models/rotor_models/",
    "foxes.models.turbine_models": "_models/turbine_models/",
    "foxes.models.turbine_types": "_models/turbine_types/",
    "foxes.models.vertical_profiles": "_models/vertical_profiles/",
    "foxes.models.wake_frames": "_models/wake_frames/",
    "foxes.models.wake_models": "_models/wake_models/",
    "foxes.models.wake_models.wind": "_models/wake_models/wind/",
    "foxes.models.wake_models.ti": "_models/wake_models/ti/",
    "foxes.models.wake_superpositions": "_models/wake_superpositions/",
    "foxes.utils": "_utils/",
    "foxes.utils.abl": "_utils/abl",
    "foxes.utils.geom2d": "_utils/geom2d/",
    "foxes.utils.runners": "_utils/runners/",
    "foxes.utils.two_circles": "_utils/two_circles/",
    "foxes.utils.abl.neutral": "_utils/abl/neutral/",
    "foxes.utils.abl.stable": "_utils/abl/stable/",
    "foxes.utils.abl.unstable": "_utils/abl/unstable/",
    "foxes.utils.abl.sheared": "_utils/abl/sheared/",
    "foxes.opt.core": "_utils/opt/core/",
    "foxes.opt.problems": "_utils/opt/problems/",
    "foxes.opt.problems.layout": "_utils/opt/problems/layout",
    "foxes.opt.problems.layout.geom_layouts": "_utils/opt/problems/layout/geom_layouts",
    "foxes.opt.problems.layout.geom_layouts.objectives": "_utils/opt/problems/layout/geom_layouts/objectives",
    "foxes.opt.problems.layout.geom_layouts.constraints": "_utils/opt/problems/layout/geom_layouts/constraints",
    "foxes.opt.objectives": "_utils/opt/objectives/",
    "foxes.opt.constraints": "_utils/opt/constraints/",
}
