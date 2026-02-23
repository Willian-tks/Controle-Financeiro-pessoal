import os
import streamlit.components.v1 as components


_COMPONENT_PATH = os.path.join(os.path.dirname(__file__), "components", "sidebar_nav")
_sidebar_nav = components.declare_component("sidebar_nav", path=_COMPONENT_PATH)


def sidebar_nav(options: list[str], icons: dict[str, str], selected: str, key: str) -> str:
    default_value = selected if selected in options else (options[0] if options else "")
    value = _sidebar_nav(
        options=options,
        icons=icons,
        selected=default_value,
        key=key,
        default=default_value,
    )
    return value if value in options else default_value
