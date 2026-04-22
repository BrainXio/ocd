"""mdformat plugin that preserves YAML frontmatter quote styles.

Identical to mdformat-frontmatter except that ruamel.yaml is configured
with ``preserve_quotes = True`` so that double-quoted frontmatter values
(e.g. ``description: "text"``) are not normalised to single quotes.
"""

import io
import sys
from collections.abc import Mapping

import mdformat.renderer
import ruamel.yaml
from markdown_it import MarkdownIt
from mdformat.renderer import RenderContext, RenderTreeNode
from mdformat.renderer.typing import Render
from mdit_py_plugins.front_matter import front_matter_plugin

yaml = ruamel.yaml.YAML()
yaml.preserve_quotes = True
yaml.indent(mapping=2, sequence=4, offset=2)
yaml.width = sys.maxsize


def update_mdit(mdit: MarkdownIt) -> None:
    """Register the front_matter parser extension with markdown-it."""
    mdit.use(front_matter_plugin)


def _render_frontmatter(node: RenderTreeNode, context: RenderContext) -> str:
    """Render frontmatter, preserving original quote styles."""
    dump_stream = io.StringIO()
    try:
        parsed = yaml.load(node.content)
        yaml.dump(parsed, stream=dump_stream)
    except ruamel.yaml.error.YAMLError as e:
        mdformat.renderer.LOGGER.warning(f"Invalid YAML in a front matter block: {e}.")
        formatted_yaml = node.content + "\n"
    else:
        formatted_yaml = dump_stream.getvalue()
        # Remove the YAML closing tag if added by ruamel.yaml
        if formatted_yaml.endswith("\n...\n"):
            formatted_yaml = formatted_yaml[:-4]

    return node.markup + "\n" + formatted_yaml + node.markup


RENDERERS: Mapping[str, Render] = {"front_matter": _render_frontmatter}
