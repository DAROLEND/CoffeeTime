"""1:1 port of includes/icons.php's icon() helper — same SVG strings, same
wrapper markup, same size/color/class parameterization and same
empty-fallback for an unknown name (call sites across the templates rely
on all of that)."""
from __future__ import annotations

from html import escape

from markupsafe import Markup

_ICONS: dict[str, str] = {
    "fire": """<svg viewBox="0 0 24 24" fill="{c}" stroke="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 2C9 6 7 8 7 11a5 5 0 0010 0c0-1-.3-2-.8-3C15 10 14 11 12 11c1-2 0-6 0-9z"/>
        <path d="M10 17c0 1.1.9 2 2 2s2-.9 2-2-1-2-2-3c-1 1-2 2-2 3z" fill="white" opacity="0.4"/>
    </svg>""",
    "snowflake": """<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round">
        <line x1="12" y1="2" x2="12" y2="22"/>
        <line x1="2" y1="12" x2="22" y2="12"/>
        <polyline points="9 5 12 2 15 5"/>
        <polyline points="9 19 12 22 15 19"/>
        <polyline points="5 9 2 12 5 15"/>
        <polyline points="19 9 22 12 19 15"/>
        <line x1="6.34" y1="6.34" x2="17.66" y2="17.66"/>
        <line x1="17.66" y1="6.34" x2="6.34" y2="17.66"/>
    </svg>""",
    "icecream": """<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 22l-4-8h8l-4 8z"/>
        <circle cx="12" cy="10" r="5"/>
    </svg>""",
    "pepper": """<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 2c1 0 2 1 2 2-2 0-3 1-3 3 0 3 3 5 3 9a4 4 0 01-8 0c0-4 3-7 3-10 0-2-1-3-1-4"/>
        <path d="M14 4c1-1 3-1 4 0"/>
    </svg>""",
    "coffee-cup": """<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M17 8h1a4 4 0 010 8h-1"/>
        <path d="M3 8h14v9a4 4 0 01-4 4H7a4 4 0 01-4-4V8z"/>
        <line x1="6" y1="1" x2="6" y2="4"/>
        <line x1="10" y1="1" x2="10" y2="4"/>
        <line x1="14" y1="1" x2="14" y2="4"/>
    </svg>""",
    "cake": """<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M20 21v-8a2 2 0 00-2-2H6a2 2 0 00-2 2v8"/>
        <path d="M4 16s.5-1 2-1 2.5 2 4 2 2.5-2 4-2 1.5 1 2 1"/>
        <path d="M2 21h20"/>
        <path d="M7 8v2M12 8v2M17 8v2"/>
    </svg>""",
    "leaf": """<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M17 8C8 10 5.9 16.17 3.82 19.34L5.71 21c2-3 5.29-9 13.29-9"/>
        <path d="M17 8c-1 3-3.5 5-7 6"/>
        <path d="M21 4C10 4 6 10 5 18"/>
    </svg>""",
    "clock": """<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"/>
        <polyline points="12 6 12 12 16 14"/>
    </svg>""",
    "warning": """<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
        <line x1="12" y1="9" x2="12" y2="13"/>
        <line x1="12" y1="17" x2="12.01" y2="17"/>
    </svg>""",
    "dine-in": """<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M3 3h18v4H3z"/>
        <path d="M3 7v14M21 7v14M8 7v14M16 7v14"/>
        <line x1="8" y1="12" x2="16" y2="12"/>
    </svg>""",
    "takeaway": """<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z"/>
        <line x1="3" y1="6" x2="21" y2="6"/>
        <path d="M16 10a4 4 0 01-8 0"/>
    </svg>""",
    "cash": """<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="2" y="6" width="20" height="12" rx="2"/>
        <circle cx="12" cy="12" r="2"/>
        <path d="M6 12h.01M18 12h.01"/>
    </svg>""",
    "card": """<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="1" y="4" width="22" height="16" rx="2" ry="2"/>
        <line x1="1" y1="10" x2="23" y2="10"/>
    </svg>""",
    "lock": """<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
        <path d="M7 11V7a5 5 0 0110 0v4"/>
    </svg>""",
    "cart": """<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="9" cy="21" r="1"/>
        <circle cx="20" cy="21" r="1"/>
        <path d="M1 1h4l2.68 13.39a2 2 0 002 1.61h9.72a2 2 0 002-1.61L23 6H6"/>
    </svg>""",
    "receipt": """<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M4 2v20l3-2 2 2 3-2 3 2 2-2 3 2V2l-3 2-2-2-3 2-3-2-2 2-3-2z"/>
        <line x1="9" y1="9" x2="15" y2="9"/>
        <line x1="9" y1="13" x2="15" y2="13"/>
    </svg>""",
    "pizza": """<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 2L2 19.5h20L12 2z"/>
        <path d="M7.5 14.5c0 0 1-2 4.5-2s4.5 2 4.5 2"/>
        <circle cx="12" cy="12" r="1" fill="{c}"/>
    </svg>""",
    "paid-card": """<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="1" y="4" width="22" height="16" rx="2"/>
        <line x1="1" y1="10" x2="23" y2="10"/>
    </svg>""",
    "paid-cash": """<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="2" y="6" width="20" height="12" rx="2"/>
        <circle cx="12" cy="12" r="2"/>
    </svg>""",
    "paid-pending": """<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"/>
        <polyline points="12 6 12 12 16 14"/>
    </svg>""",
    "heart": """<svg viewBox="0 0 24 24" fill="{c}" stroke="{c}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z"/>
    </svg>""",
    "filter-spicy": """<svg viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
        <path fill="#d50000" d="M22.25,10.82a3.52,3.52,0,0,1-1.56,1,.5.5,0,0,1-.47-.13,2.56,2.56,0,0,1-.7-1.48,3.66,3.66,0,0,0-2.37.72.49.49,0,0,1-.41,0,16.56,16.56,0,0,0-1.63,4.89C14,21.78,13.42,24.49,6.67,27a.48.48,0,0,0-.32.43.49.49,0,0,0,.25.47,8.94,8.94,0,0,0,4.47,1.19c3.92,0,7.9-2.55,10.46-7.08a22,22,0,0,0,3.1-9.44A6.19,6.19,0,0,0,22.25,10.82Z"/>
        <path fill="#00c853" d="M23.22,8.54a4.48,4.48,0,0,1-.39.61l-.08.09-.14.09a1.09,1.09,0,0,1-.62.21.87.87,0,0,1-.25,0,1,1,0,0,1-.68-.7s0,0,0,0a.51.51,0,0,1,.07-.43A.91.91,0,0,0,21.26,8c-1-.28-3.22-.55-4.81,2.21a.49.49,0,0,0,.09.61.42.42,0,0,0,.2.1.49.49,0,0,0,.41,0,3.66,3.66,0,0,1,2.37-.72,2.56,2.56,0,0,0,.7,1.48.5.5,0,0,0,.47.13,3.52,3.52,0,0,0,1.56-1,6.19,6.19,0,0,1,2.38,1.79.91.91,0,0,1,.13.16.53.53,0,0,0,.39.18.41.41,0,0,0,.16,0,.49.49,0,0,0,.34-.46A3.77,3.77,0,0,0,23.22,8.54Z"/>
        <path fill="#795548" d="M24.06,3.49a.51.51,0,0,0-.55-.41l-2.1.27a.51.51,0,0,0-.35.22A.49.49,0,0,0,21,4,10.55,10.55,0,0,1,21.26,8a.91.91,0,0,1-.14.33.51.51,0,0,0-.07.43s0,0,0,0a1,1,0,0,0,.68.7.87.87,0,0,0,.25,0,1.09,1.09,0,0,0,.62-.21l.14-.09.08-.09a4.48,4.48,0,0,0,.39-.61A8.11,8.11,0,0,0,24.06,3.49Z"/>
    </svg>""",
    "filter-sauce-tomato": """<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="14" r="7"/>
        <path d="M12 7V3"/>
        <path d="M9 5c0-1.5 1-2 3-2s3 1 3 2"/>
        <path d="M9 14c0 1.7 1.3 3 3 3"/>
    </svg>""",
    "filter-sauce-cream": """<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 2l8 12a8 8 0 11-16 0L12 2z"/>
    </svg>""",
    "filter-bbq": """<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="15" r="7"/>
        <line x1="5" y1="15" x2="19" y2="15"/>
        <line x1="12" y1="8" x2="12" y2="22"/>
        <path d="M8 5c0-2 1-3 4-3s4 1 4 3"/>
        <path d="M7 3c-1 1-1 3 0 4M17 3c1 1 1 3 0 4"/>
    </svg>""",
    "sort": """<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round">
        <line x1="3" y1="6" x2="21" y2="6"/>
        <line x1="3" y1="12" x2="15" y2="12"/>
        <line x1="3" y1="18" x2="9" y2="18"/>
    </svg>""",
    "arrow-up": """<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <line x1="12" y1="19" x2="12" y2="5"/>
        <polyline points="5 12 12 5 19 12"/>
    </svg>""",
    "arrow-down": """<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <line x1="12" y1="5" x2="12" y2="19"/>
        <polyline points="19 12 12 19 5 12"/>
    </svg>""",
    "trending": """<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/>
        <polyline points="17 6 23 6 23 12"/>
    </svg>""",
    "default-sort": """<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <line x1="8" y1="6" x2="21" y2="6"/>
        <line x1="8" y1="12" x2="21" y2="12"/>
        <line x1="8" y1="18" x2="21" y2="18"/>
        <line x1="3" y1="6" x2="3.01" y2="6"/>
        <line x1="3" y1="12" x2="3.01" y2="12"/>
        <line x1="3" y1="18" x2="3.01" y2="18"/>
    </svg>""",
    "scoop-1": """<svg viewBox="0 0 32 32" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="16" cy="11" r="7"/>
        <path d="M11 18l-3 11h16l-3-11"/>
    </svg>""",
    "scoop-2": """<svg viewBox="0 0 32 32" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="10" cy="13" r="6"/>
        <circle cx="22" cy="13" r="6"/>
        <path d="M6 19l-3 10h26l-3-10"/>
    </svg>""",
    "scoop-3": """<svg viewBox="0 0 32 32" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="7" cy="14" r="5"/>
        <circle cx="16" cy="11" r="6"/>
        <circle cx="25" cy="14" r="5"/>
        <path d="M4 19l-2 10h28l-2-10"/>
    </svg>""",
}


def icon(name: str, size: int = 20, color: str = "currentColor", css_class: str = "") -> Markup:
    c = escape(color)
    svg_template = _ICONS.get(name, '<svg viewBox="0 0 24 24"></svg>')
    svg = svg_template.format(c=c) if "{c}" in svg_template else svg_template
    svg = svg.replace("<svg ", '<svg width="100%" height="100%" ', 1)
    cls = f' class="{escape(css_class)}"' if css_class else ""
    return Markup(
        f'<span{cls} style="display:inline-flex;align-items:center;justify-content:center;'
        f"width:{int(size)}px;height:{int(size)}px;flex-shrink:0;vertical-align:middle;\">"
        f"{svg}</span>"
    )
