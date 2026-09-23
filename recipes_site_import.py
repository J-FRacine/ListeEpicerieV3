from __future__ import annotations

from collections import deque
from html.parser import HTMLParser
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen
import re
import unicodedata


SITE_ROOT = "https://sites.google.com/view/recettes-de-lours"
DEFAULT_SITE_URL = SITE_ROOT + "/accueil"
MAX_PAGES_DEFAULT = 150

_BLOCK_TAGS = {
    "address", "article", "aside", "blockquote", "br", "div", "footer",
    "h1", "h2", "h3", "h4", "h5", "h6", "header", "li", "main",
    "nav", "p", "section", "td", "th", "tr",
}
_SKIP_TAGS = {"script", "style", "noscript", "svg", "template"}
_CHROME_LINES = {
    "search this site",
    "skip to main content",
    "skip to navigation",
    "page updated",
    "report abuse",
    "accueil",
    "home",
}
_INGREDIENT_HEADINGS = {
    "ingredient", "ingredients", "ingrédient", "ingrédients",
}
_PREPARATION_HEADINGS = {
    "preparation", "préparation", "instructions", "instruction",
    "realisation", "réalisation", "methode", "méthode", "etapes", "étapes",
    "marche a suivre", "marche à suivre", "directions",
}
_FOOTER_PREFIXES = ("page updated", "report abuse")

_QUANTITY = (
    r"(?:\d+(?:[.,]\d+)?|\d+\s*[\/⁄]\s*\d+|"
    r"[¼½¾⅓⅔⅛⅜⅝⅞]|une?|deux|trois|quatre|cinq|six|sept|huit|neuf|dix)"
)
_UNIT = (
    r"(?:kg|g|mg|l|ml|cl|oz|lb|lbs|tasses?|cups?|t\.?|"
    r"cuill(?:ere|ère)s?\s+à\s+soupe|cuill(?:ere|ère)s?\s+a\s+soupe|"
    r"cuill(?:ere|ère)s?\s+à\s+table|cuill(?:ere|ère)s?\s+a\s+table|"
    r"cuill(?:ere|ère)s?\s+à\s+caf(?:e|é)|cuill(?:ere|ère)s?\s+a\s+caf(?:e|é)|"
    r"c\.\s*à\s*s\.?|c\.\s*a\s*s\.?|c\s+à\s+soupe|c\s+a\s+soupe|"
    r"c\.\s*à\s*c\.?|c\.\s*a\s*c\.?|c\s+à\s+caf(?:e|é)|c\s+a\s+caf(?:e|é)|"
    r"bo[iî]tes?|gousses?|tranches?|pinc(?:e|é)es?|sachets?|paquets?|branches?)"
)
_INSTRUCTION_VERBS = (
    r"\b(?:ajouter|arroser|battre|blanchir|bouillir|brasser|chauffer|"
    r"couper|cuire|déposer|deposer|déguster|deguster|étendre|etendre|"
    r"faire|fouetter|incorporer|laisser|mélanger|melanger|mettre|"
    r"mijoter|préchauffer|prechauffer|remettre|répartir|repartir|"
    r"réserver|reserver|servir|sortir|verser)\b"
)

_CATEGORY_ALIASES = {
    "entrees": "Entrées",
    "entree": "Entrées",
    "plats principaux": "Plats principaux",
    "desserts": "Desserts",
    "les bases": "Les bases",
    "autres": "Autres",
    "momo": "Momo",
    "airfryer": "AirFryer",
    "air fryer": "AirFryer",
    "boissons": "Boissons",
    "listes": "Listes",
    "sandwiches": "Sandwiches",
}


def _fold(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.casefold().replace("’", "'")
    text = re.sub(r"\s+", " ", text).strip(" \t\r\n:;.-")
    return text


def normalize_name(value: str) -> str:
    text = _fold(value)
    text = re.sub(r"[^a-z0-9' ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_site_url(value: str) -> str:
    raw = str(value or "").strip() or DEFAULT_SITE_URL
    parts = urlsplit(raw)
    if parts.scheme.lower() != "https" or parts.netloc.lower() != "sites.google.com":
        raise ValueError("L’adresse doit être une page HTTPS de votre Google Sites.")
    path = re.sub(r"/{2,}", "/", parts.path or "/")
    root_path = urlsplit(SITE_ROOT).path.rstrip("/")
    if path.rstrip("/") != root_path and not path.startswith(root_path + "/"):
        raise ValueError("Cette adresse ne fait pas partie du site Recettes de l’Ours.")
    return urlunsplit(
        ("https", "sites.google.com", path.rstrip("/") or root_path, "", "")
    )


def _relative_segments(value: str) -> list[str]:
    clean = normalize_site_url(value)
    root_path = urlsplit(SITE_ROOT).path.rstrip("/")
    path = urlsplit(clean).path.rstrip("/")
    remainder = path[len(root_path):].strip("/")
    if not remainder:
        return []
    segments = [unquote(part).strip() for part in remainder.split("/") if part.strip()]
    if segments and _fold(segments[0]) in {"accueil", "home"}:
        segments = segments[1:]
    return segments


def _pretty_segment(value: str) -> str:
    text = unquote(str(value or "")).replace("-", " ").replace("_", " ")
    text = re.sub(r"\s+", " ", text).strip()
    folded = _fold(text)
    if folded in _CATEGORY_ALIASES:
        return _CATEGORY_ALIASES[folded]
    if not text:
        return ""
    return text[0].upper() + text[1:]


def source_recipe_category(source_url: str) -> tuple[str, str]:
    """Déduit catégorie et sous-catégorie de l'arborescence Google Sites.

    Le dernier segment est la page de recette. Le premier segment avant celle-ci
    devient la catégorie; le deuxième devient la sous-catégorie lorsqu'il existe.
    """
    segments = _relative_segments(source_url)
    if len(segments) < 2:
        return "", ""
    category = _pretty_segment(segments[0])
    subcategory = _pretty_segment(segments[1]) if len(segments) >= 3 else ""
    return category, subcategory


class _GoogleSiteParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._current_heading = None
        self._heading_parts = []
        self._text_parts = []
        self._title_parts = []
        self._in_title = False
        self._li_depth = 0
        self._li_parts = []
        self._list_stack: list[str] = []
        self.links: list[str] = []
        self.headings: list[tuple[str, str]] = []
        self.list_items: list[str] = []
        self.list_entries: list[tuple[str, str]] = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        attrs_dict = dict(attrs)
        if tag == "a" and attrs_dict.get("href"):
            self.links.append(attrs_dict["href"])
        if tag == "title":
            self._in_title = True
        if tag in {"h1", "h2", "h3", "h4"}:
            self._current_heading = tag
            self._heading_parts = []
        if tag in {"ul", "ol"}:
            self._list_stack.append(tag)
        if tag == "li":
            if self._li_depth == 0:
                self._li_parts = []
            self._li_depth += 1
        if tag in _BLOCK_TAGS:
            self._text_parts.append("\n")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in _SKIP_TAGS:
            if self._skip_depth:
                self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if tag == "title":
            self._in_title = False
        if self._current_heading == tag:
            text = re.sub(r"\s+", " ", " ".join(self._heading_parts)).strip()
            if text:
                self.headings.append((tag, text))
            self._current_heading = None
            self._heading_parts = []
        if tag == "li" and self._li_depth:
            self._li_depth -= 1
            if self._li_depth == 0:
                text = re.sub(r"\s+", " ", " ".join(self._li_parts)).strip()
                if text:
                    self.list_items.append(text)
                    self.list_entries.append(
                        (
                            self._list_stack[-1] if self._list_stack else "",
                            text,
                        )
                    )
                self._li_parts = []
        if tag in {"ul", "ol"} and self._list_stack:
            self._list_stack.pop()
        if tag in _BLOCK_TAGS:
            self._text_parts.append("\n")

    def handle_data(self, data):
        if self._skip_depth:
            return
        text = re.sub(r"\s+", " ", data or "").strip()
        if not text:
            return
        self._text_parts.append(text)
        if self._in_title:
            self._title_parts.append(text)
        if self._current_heading:
            self._heading_parts.append(text)
        if self._li_depth:
            self._li_parts.append(text)

    @property
    def title(self) -> str:
        return re.sub(r"\s+", " ", " ".join(self._title_parts)).strip()

    def lines(self) -> list[str]:
        text = " ".join(self._text_parts).replace(" \n ", "\n")
        text = text.replace("\n ", "\n").replace(" \n", "\n")
        result = []
        for raw in text.splitlines():
            line = re.sub(r"\s+", " ", raw).strip()
            if line and (not result or line != result[-1]):
                result.append(line)
        return result


def _clean_page_lines(lines: list[str]) -> list[str]:
    result = []
    for line in lines:
        folded = _fold(line)
        if not folded or folded in _CHROME_LINES:
            continue
        if any(folded.startswith(prefix) for prefix in _FOOTER_PREFIXES):
            break
        if result and line == result[-1]:
            continue
        result.append(line.strip())
    return result


def _heading_kind(line: str) -> tuple[str | None, str]:
    stripped = str(line or "").strip()
    folded = _fold(stripped)
    for heading in _INGREDIENT_HEADINGS:
        h = _fold(heading)
        if folded == h:
            return "ingredients", ""
        if folded.startswith(h + " ") or folded.startswith(h + ":"):
            match = re.match(r"^[^:]+:\s*(.*)$", stripped)
            return "ingredients", match.group(1).strip() if match else ""
    for heading in _PREPARATION_HEADINGS:
        h = _fold(heading)
        if folded == h:
            return "preparation", ""
        if folded.startswith(h + " ") or folded.startswith(h + ":"):
            match = re.match(r"^[^:]+:\s*(.*)$", stripped)
            return "preparation", match.group(1).strip() if match else ""
    return None, ""


def _title_from_parser(parser: _GoogleSiteParser, lines: list[str]) -> str:
    for tag, heading in parser.headings:
        folded = _fold(heading)
        if tag == "h1" and folded not in {"recettes de l'ours", "recettes de lours"}:
            return heading.strip()
    title = parser.title
    if title:
        for suffix in (
            " - Recettes de l'Ours",
            " – Recettes de l'Ours",
            " | Recettes de l'Ours",
        ):
            if title.endswith(suffix):
                title = title[: -len(suffix)].strip()
        if _fold(title) not in {"recettes de l'ours", "recettes de lours"}:
            return title
    for line in lines:
        folded = _fold(line)
        if folded not in _CHROME_LINES and folded not in {
            "recettes de l'ours",
            "recettes de lours",
        }:
            return line
    return "Recette importée"


def _extract_servings(lines: list[str]) -> int:
    text = " ".join(lines[:30])
    patterns = (
        r"\b(?:pour\s+)?(\d{1,2})\s*(?:portions?|personnes?|pers\.?)(?:\b|\))",
        r"\b(?:rendement|portions?)\s*[:\-]?\s*(\d{1,2})\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = int(match.group(1))
            if 1 <= value <= 50:
                return value
    return 4


def _strip_bullet(value: str) -> str:
    text = str(value or "").strip()
    text = re.sub(r"^[\u2022\u25cf\u25e6\-*–—]+\s*", "", text)
    return text.strip()


def item_name_from_ingredient_line(value: str) -> str:
    text = _strip_bullet(value)
    text = re.sub(r"^\(?\d{1,2}\)?[.)]\s+", "", text)
    text = re.sub(r"\s*\([^)]*\)\s*$", "", text).strip()
    text = re.sub(rf"^{_QUANTITY}\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(rf"^{_UNIT}\b\s*(?:de\s+|d['’])?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^(?:de\s+|d['’])", "", text, flags=re.IGNORECASE)

    trailing_measure = re.search(
        rf"\s+{_QUANTITY}\s*[,;:]?\s*{_UNIT}\b.*$",
        text,
        flags=re.IGNORECASE,
    )
    if trailing_measure and trailing_measure.start() >= 2:
        text = text[: trailing_measure.start()].strip()

    text = re.sub(r"\s+au\s+go[uû]t\b.*$", "", text, flags=re.IGNORECASE).strip()
    text = text.strip(" ,;:-")
    if "," in text:
        first = text.split(",", 1)[0].strip()
        if len(first) >= 2:
            text = first
    if not text:
        text = _strip_bullet(value)
    return text[:160]


def _ingredient_lines_to_entries(lines: list[str]) -> list[dict]:
    entries = []
    for line in lines:
        raw = _strip_bullet(line)
        if not raw:
            continue
        kind, tail = _heading_kind(raw)
        if kind:
            if tail:
                raw = tail
            else:
                continue
        if raw.endswith(":") and len(raw.split()) <= 5 and not re.search(r"\d", raw):
            continue
        name = item_name_from_ingredient_line(raw)
        if len(normalize_name(name)) < 2:
            continue
        entries.append({"item_name": name, "original": raw})
    return entries


def _line_index(lines: list[str], value: str, start: int = 0) -> int | None:
    target = _fold(value)
    if not target:
        return None
    for index in range(max(0, start), len(lines)):
        if _fold(lines[index]) == target:
            return index
    return None


def _has_ingredient_signal(lines: list[str]) -> bool:
    for line in lines:
        text = str(line or "")
        if re.search(rf"{_QUANTITY}", text, flags=re.IGNORECASE):
            return True
        if re.search(rf"\b{_UNIT}\b", text, flags=re.IGNORECASE):
            return True
        if re.search(
            r"\b(?:au\s+go[uû]t|pinc(?:e|é)e|sel|poivre|huile|vinaigre|sucre)\b",
            text,
            flags=re.IGNORECASE,
        ):
            return True
    return False


def _has_instruction_signal(lines: list[str]) -> bool:
    return any(
        re.search(_INSTRUCTION_VERBS, str(line or ""), flags=re.IGNORECASE)
        for line in lines
    )


def _headingless_sections(
    parser: _GoogleSiteParser,
    lines: list[str],
    title: str,
) -> tuple[list[str], list[str]] | None:
    if not parser.list_items:
        return None

    title_index = _line_index(lines, title)
    if title_index is None:
        title_index = 0

    list_item_keys = {_fold(item) for item in parser.list_items if _fold(item)}
    preparation_index = None
    for index in range(title_index + 1, len(lines)):
        if _fold(lines[index]) in list_item_keys:
            preparation_index = index
            break
    if preparation_index is None:
        return None

    heading_keys = {_fold(value) for _, value in parser.headings}
    ingredient_lines = []
    for line in lines[title_index + 1 : preparation_index]:
        folded = _fold(line)
        if not folded or folded in _CHROME_LINES or folded == _fold(title):
            continue
        if folded in heading_keys:
            continue
        if re.search(
            r"\b(?:preparation|préparation|cuisson|temps|rendement|portions?|personnes?)\s*[:\-]",
            line,
            flags=re.IGNORECASE,
        ):
            continue
        ingredient_lines.append(line)

    ingredient_entries = _ingredient_lines_to_entries(ingredient_lines)
    if len(ingredient_entries) < 2 or not _has_ingredient_signal(ingredient_lines):
        return None

    preparation_lines = []
    for line in lines[preparation_index:]:
        folded = _fold(line)
        if not folded or folded in _CHROME_LINES:
            continue
        if any(folded.startswith(prefix) for prefix in _FOOTER_PREFIXES):
            break
        if folded == _fold(title):
            continue
        cleaned = _strip_bullet(
            re.sub(r"^\s*\d{1,2}[.)]\s*", "", line)
        ).strip()
        if cleaned:
            preparation_lines.append(cleaned)

    if not preparation_lines or not _has_instruction_signal(preparation_lines):
        return None
    return ingredient_lines, preparation_lines


def _ingredients_heading_without_preparation(
    parser: _GoogleSiteParser,
    lines: list[str],
    ingredient_index: int,
    ingredient_tail: str = "",
) -> tuple[list[str], list[str]] | None:
    """Format historique : titre Ingrédients, puis UL, puis étapes OL sans titre.

    Certaines pages de Recettes de l'Ours ont un en-tête « Ingrédients », une
    liste à puces d'ingrédients, puis directement une liste numérotée de
    préparation. Google Sites ne fournit alors aucun en-tête « Préparation ».
    """
    ordered_keys = {
        _fold(text)
        for list_type, text in parser.list_entries
        if list_type == "ol" and _fold(text)
    }

    preparation_index = None
    if ordered_keys:
        for index in range(ingredient_index + 1, len(lines)):
            if _fold(lines[index]) in ordered_keys:
                preparation_index = index
                break

    # Repli pour les anciennes pages où Google Sites ne conserve pas OL/UL :
    # la première vraie action culinaire marque le début de la préparation.
    if preparation_index is None:
        list_item_keys = {
            _fold(item)
            for item in parser.list_items
            if _fold(item)
        }
        for index in range(ingredient_index + 1, len(lines)):
            line = lines[index]
            if (
                _fold(line) in list_item_keys
                and _has_instruction_signal([line])
            ):
                preparation_index = index
                break

    if preparation_index is None:
        return None

    ingredient_lines = []
    if ingredient_tail:
        ingredient_lines.append(ingredient_tail)
    ingredient_lines.extend(
        lines[ingredient_index + 1 : preparation_index]
    )
    ingredients = _ingredient_lines_to_entries(ingredient_lines)
    if len(ingredients) < 2 or not _has_ingredient_signal(ingredient_lines):
        return None

    preparation_lines = []
    for line in lines[preparation_index:]:
        folded = _fold(line)
        if not folded or folded in _CHROME_LINES:
            continue
        if any(
            folded.startswith(prefix)
            for prefix in _FOOTER_PREFIXES
        ):
            break
        kind, _ = _heading_kind(line)
        if kind == "ingredients":
            break
        cleaned = _strip_bullet(
            re.sub(r"^\s*\d{1,2}[.)]\s*", "", line)
        ).strip()
        if cleaned:
            preparation_lines.append(cleaned)

    if not preparation_lines or not _has_instruction_signal(preparation_lines):
        return None
    return ingredient_lines, preparation_lines


def _is_url_line(value: str) -> bool:
    text = str(value or "").strip().lower()
    return text.startswith(("http://", "https://", "www."))


def _internal_links(html: str, page_url: str) -> list[str]:
    parser = _GoogleSiteParser()
    parser.feed(str(html or ""))
    result = []
    seen = set()
    root_path = urlsplit(SITE_ROOT).path.rstrip("/")
    for href in parser.links:
        absolute = urljoin(page_url + "/", href)
        parts = urlsplit(absolute)
        if parts.scheme.lower() != "https" or parts.netloc.lower() != "sites.google.com":
            continue
        path = re.sub(r"/{2,}", "/", parts.path or "/").rstrip("/")
        if path != root_path and not path.startswith(root_path + "/"):
            continue
        folded = path.casefold()
        if any(token in folded for token in ("/search", "/system/", "/_", "/preview")):
            continue
        clean = urlunsplit(("https", "sites.google.com", path, "", ""))
        if clean not in seen:
            seen.add(clean)
            result.append(clean)
    return result


def is_navigation_page(html: str, source_url: str) -> bool:
    """Détecte une page de catégorie/sous-catégorie plutôt qu'une recette."""
    clean = normalize_site_url(source_url)
    current_path = urlsplit(clean).path.rstrip("/")
    children = []
    for link in _internal_links(html, clean):
        path = urlsplit(link).path.rstrip("/")
        if path.startswith(current_path + "/"):
            children.append(link)

    depth = len(_relative_segments(clean))
    if len(children) >= 2:
        return True
    if depth <= 1 and children:
        return True
    return False


def parse_recipe_html(html: str, source_url: str) -> dict | None:
    if is_navigation_page(html, source_url):
        return None

    parser = _GoogleSiteParser()
    parser.feed(str(html or ""))
    lines = _clean_page_lines(parser.lines())
    if not lines:
        return None

    title = _title_from_parser(parser, lines)
    ingredient_index = None
    ingredient_tail = ""
    preparation_index = None
    preparation_tail = ""
    for index, line in enumerate(lines):
        kind, tail = _heading_kind(line)
        if kind == "ingredients" and ingredient_index is None:
            ingredient_index = index
            ingredient_tail = tail
            continue
        if (
            kind == "preparation"
            and ingredient_index is not None
            and index > ingredient_index
        ):
            preparation_index = index
            preparation_tail = tail
            break

    description_anchor = None
    if ingredient_index is not None and preparation_index is not None:
        ingredient_lines = []
        if ingredient_tail:
            ingredient_lines.append(ingredient_tail)
        ingredient_lines.extend(lines[ingredient_index + 1 : preparation_index])
        preparation_lines = []
        if preparation_tail:
            preparation_lines.append(preparation_tail)
        for line in lines[preparation_index + 1 :]:
            folded = _fold(line)
            if any(folded.startswith(prefix) for prefix in _FOOTER_PREFIXES):
                break
            kind, _ = _heading_kind(line)
            if kind == "ingredients":
                break
            cleaned = _strip_bullet(
                re.sub(r"^\s*\d{1,2}[.)]\s*", "", line)
            ).strip()
            if cleaned:
                preparation_lines.append(cleaned)
        description_anchor = ingredient_index
    elif ingredient_index is not None:
        hybrid = _ingredients_heading_without_preparation(
            parser,
            lines,
            ingredient_index,
            ingredient_tail,
        )
        if hybrid is None:
            return None
        ingredient_lines, preparation_lines = hybrid
        description_anchor = ingredient_index
    else:
        fallback = _headingless_sections(parser, lines, title)
        if fallback is None:
            return None
        ingredient_lines, preparation_lines = fallback
        title_index = _line_index(lines, title)
        description_anchor = title_index if title_index is not None else 0

    ingredients = _ingredient_lines_to_entries(ingredient_lines)
    if not ingredients or not preparation_lines:
        return None

    description_lines = []
    if ingredient_index is not None:
        for line in lines[:description_anchor]:
            folded_line = _fold(line)
            if folded_line in {
                _fold(title),
                "recettes de l'ours",
                "recettes de lours",
            }:
                continue
            if (
                folded_line.startswith(_fold(title))
                and "recettes de l'ours" in folded_line
            ):
                continue
            if _is_url_line(line):
                continue
            if re.search(
                r"\b(?:preparation|préparation|cuisson|temps|portions?|personnes?)\s*[:\-]",
                line,
                flags=re.I,
            ):
                continue
            if len(line) >= 12:
                description_lines.append(line)
            if len(description_lines) >= 2:
                break

    category, subcategory = source_recipe_category(source_url)
    return {
        "name": title[:180],
        "servings": _extract_servings(lines),
        "description": " ".join(description_lines)[:800],
        "instructions": "\n".join(preparation_lines)[:12000],
        "ingredients": ingredients,
        "source_url": normalize_site_url(source_url),
        "source_category": category,
        "source_subcategory": subcategory,
    }


def _fetch_html(url: str, timeout: int = 20) -> str:
    clean = normalize_site_url(url)
    request = Request(
        clean,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153 Safari/537.36"
            ),
            "Accept-Language": "fr-CA,fr;q=0.9,en;q=0.5",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        final_parts = urlsplit(response.geturl())
        if final_parts.netloc.lower() != "sites.google.com":
            raise ValueError(
                "Le site semble demander une connexion Google. "
                "Vérifiez que sa version publiée est publique."
            )
        content_type = str(response.headers.get("Content-Type") or "")
        if "text/html" not in content_type.lower():
            raise ValueError("La page Google Sites retournée n’est pas une page HTML.")
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read(4_000_000).decode(charset, errors="replace")


def crawl_google_site(
    start_url: str = DEFAULT_SITE_URL,
    max_pages: int = MAX_PAGES_DEFAULT,
) -> dict:
    start = normalize_site_url(start_url)
    limit = max(1, min(int(max_pages or MAX_PAGES_DEFAULT), 250))
    queue = deque([start])
    queued = {start}
    visited = set()
    candidates = []
    errors = []
    sections_ignored = 0
    pages_unrecognized = 0

    while queue and len(visited) < limit:
        url = queue.popleft()
        if url in visited:
            continue
        visited.add(url)
        try:
            html = _fetch_html(url)
        except Exception as error:
            errors.append({"url": url, "error": str(error)[:300]})
            continue

        if is_navigation_page(html, url):
            sections_ignored += 1
        else:
            candidate = parse_recipe_html(html, url)
            if candidate:
                candidates.append(candidate)
            else:
                pages_unrecognized += 1

        for link in _internal_links(html, url):
            if (
                link not in visited
                and link not in queued
                and len(queued) < limit * 3
            ):
                queued.add(link)
                queue.append(link)

    unique = []
    seen_names = set()
    for candidate in candidates:
        key = normalize_name(candidate.get("name"))
        if not key or key in seen_names:
            continue
        seen_names.add(key)
        unique.append(candidate)

    return {
        "start_url": start,
        "pages_scanned": len(visited),
        "recipes": unique,
        "sections_ignored": sections_ignored,
        "pages_unrecognized": pages_unrecognized,
        "errors": errors,
        "truncated": bool(queue),
    }


def preview_recipe_matches(candidates, existing_items, existing_recipes) -> list[dict]:
    item_keys = {normalize_name(row.get("name")) for row in existing_items or []}
    recipe_keys = {normalize_name(row.get("name")) for row in existing_recipes or []}
    result = []
    for candidate in candidates or []:
        matched = 0
        missing = []
        for ingredient in candidate.get("ingredients") or []:
            key = normalize_name(ingredient.get("item_name"))
            if key and key in item_keys:
                matched += 1
            else:
                missing.append(ingredient.get("item_name") or "Ingrédient")
        row = dict(candidate)
        row["duplicate"] = normalize_name(candidate.get("name")) in recipe_keys
        row["matched_ingredients"] = matched
        row["missing_ingredients"] = missing
        result.append(row)
    return result


def _ensure_recipe_category_in_cursor(cur, family_id, name, parent_id=None):
    clean = str(name or "").strip()
    if not clean:
        return None
    cur.execute(
        """
        SELECT id, name
        FROM grocery_recipe_categories
        WHERE family_id = %s
          AND parent_id IS NOT DISTINCT FROM %s
        ORDER BY id;
        """,
        (family_id, parent_id),
    )
    target = normalize_name(clean)
    for row in cur.fetchall():
        if normalize_name(row["name"]) == target:
            return int(row["id"])

    cur.execute(
        """
        SELECT COALESCE(MAX(sort_order), 0) + 10 AS next_order
        FROM grocery_recipe_categories
        WHERE family_id = %s
          AND parent_id IS NOT DISTINCT FROM %s;
        """,
        (family_id, parent_id),
    )
    sort_order = int(cur.fetchone()["next_order"] or 10)
    cur.execute(
        """
        INSERT INTO grocery_recipe_categories (
            family_id, parent_id, name, sort_order
        )
        VALUES (%s, %s, %s, %s)
        RETURNING id;
        """,
        (family_id, parent_id, clean, sort_order),
    )
    return int(cur.fetchone()["id"])


def _source_recipe_category_id(cur, family_id, candidate):
    primary = str(candidate.get("source_category") or "").strip()
    secondary = str(candidate.get("source_subcategory") or "").strip()
    if not primary:
        return None
    primary_id = _ensure_recipe_category_in_cursor(
        cur, family_id, primary, None
    )
    if secondary:
        return _ensure_recipe_category_in_cursor(
            cur, family_id, secondary, primary_id
        )
    return primary_id


def import_recipe_candidates(
    user_id,
    family_id,
    candidates,
    category_id,
    store_id=None,
    create_missing_items=True,
):
    """Importe un lot analysé dans les tables Recettes existantes."""
    from db import get_connection, _require_family_access
    from grocery_common import log_activity

    selected = [dict(row) for row in (candidates or [])]
    if not selected:
        raise ValueError("Sélectionnez au moins une recette à importer.")

    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_family_access(cur, user_id, family_id)

            cur.execute(
                """
                SELECT id, name
                FROM grocery_recipes
                WHERE family_id = %s;
                """,
                (family_id,),
            )
            recipe_keys = {
                normalize_name(row["name"]): int(row["id"])
                for row in cur.fetchall()
            }

            cur.execute(
                """
                SELECT id, name
                FROM items
                WHERE family_id = %s
                  AND deleted_at IS NULL;
                """,
                (family_id,),
            )
            item_map = {
                normalize_name(row["name"]): int(row["id"])
                for row in cur.fetchall()
            }

            if create_missing_items:
                cur.execute(
                    """
                    SELECT id FROM categories
                    WHERE id = %s AND family_id = %s AND deleted_at IS NULL;
                    """,
                    (category_id, family_id),
                )
                if cur.fetchone() is None:
                    raise ValueError(
                        "Choisissez une catégorie valide pour les nouveaux items."
                    )

            if store_id is None:
                cur.execute(
                    """
                    SELECT id FROM stores
                    WHERE family_id = %s AND deleted_at IS NULL
                    ORDER BY sort_order, LOWER(name), id
                    LIMIT 1;
                    """,
                    (family_id,),
                )
                store_row = cur.fetchone()
                store_id = int(store_row["id"]) if store_row else None
            else:
                cur.execute(
                    """
                    SELECT id FROM stores
                    WHERE id = %s AND family_id = %s AND deleted_at IS NULL;
                    """,
                    (store_id, family_id),
                )
                if cur.fetchone() is None:
                    raise ValueError(
                        "Choisissez un magasin valide pour les nouveaux items."
                    )

            imported = 0
            skipped_duplicates = 0
            created_items = 0
            linked_ingredients = 0
            skipped_ingredients = 0
            categories_created_before = None

            cur.execute(
                """
                SELECT COUNT(*)::INTEGER AS total
                FROM grocery_recipe_categories
                WHERE family_id = %s;
                """,
                (family_id,),
            )
            categories_created_before = int(cur.fetchone()["total"] or 0)

            for candidate in selected:
                name = str(candidate.get("name") or "").strip()[:180]
                if not name:
                    continue
                recipe_key = normalize_name(name)
                if recipe_key in recipe_keys:
                    skipped_duplicates += 1
                    continue

                try:
                    servings = int(candidate.get("servings") or 4)
                except (TypeError, ValueError):
                    servings = 4
                servings = max(1, min(servings, 50))
                description = str(
                    candidate.get("description") or ""
                ).strip()[:800]
                instructions = str(
                    candidate.get("instructions") or ""
                ).strip()[:12000]
                recipe_category_id = _source_recipe_category_id(
                    cur, family_id, candidate
                )

                cur.execute(
                    """
                    INSERT INTO grocery_recipes (
                        family_id, recipe_category_id, name, description,
                        instructions, servings, created_by_user_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                    """,
                    (
                        family_id,
                        recipe_category_id,
                        name,
                        description,
                        instructions,
                        servings,
                        user_id,
                    ),
                )
                recipe_id = int(cur.fetchone()["id"])
                recipe_keys[recipe_key] = recipe_id
                log_activity(
                    cur,
                    family_id,
                    user_id,
                    "recipe_created",
                    "recipe",
                    recipe_id,
                    name,
                    {
                        "source": "google_sites_import",
                        "source_category": candidate.get("source_category") or "",
                        "source_subcategory": candidate.get("source_subcategory") or "",
                    },
                )

                sort_order = 10
                for ingredient in candidate.get("ingredients") or []:
                    item_name = str(
                        ingredient.get("item_name") or ""
                    ).strip()[:160]
                    item_key = normalize_name(item_name)
                    if not item_key:
                        continue
                    item_id = item_map.get(item_key)
                    if item_id is None:
                        if not create_missing_items:
                            skipped_ingredients += 1
                            continue
                        cur.execute(
                            """
                            INSERT INTO items (
                                family_id, category_id, store_id, name, note,
                                quantity, needed, times_needed, last_needed_at
                            )
                            VALUES (%s, %s, %s, %s, '', 1, 0, 0, NULL)
                            RETURNING id;
                            """,
                            (family_id, category_id, store_id, item_name),
                        )
                        item_id = int(cur.fetchone()["id"])
                        item_map[item_key] = item_id
                        created_items += 1
                        log_activity(
                            cur,
                            family_id,
                            user_id,
                            "item_created",
                            "item",
                            item_id,
                            item_name,
                            {
                                "needed": False,
                                "source": "google_sites_import",
                            },
                        )

                    note = str(
                        ingredient.get("original") or ""
                    ).strip()[:600]
                    cur.execute(
                        """
                        INSERT INTO grocery_recipe_ingredients (
                            recipe_id, item_id, quantity, note, sort_order
                        )
                        VALUES (%s, %s, 1, %s, %s)
                        ON CONFLICT (recipe_id, item_id) DO NOTHING;
                        """,
                        (recipe_id, item_id, note, sort_order),
                    )
                    if getattr(cur, "rowcount", 0):
                        linked_ingredients += 1
                        sort_order += 10

                imported += 1

            cur.execute(
                """
                SELECT COUNT(*)::INTEGER AS total
                FROM grocery_recipe_categories
                WHERE family_id = %s;
                """,
                (family_id,),
            )
            category_total_after = int(cur.fetchone()["total"] or 0)
            recipe_categories_created = max(
                0, category_total_after - categories_created_before
            )
            conn.commit()

    return {
        "recipes_imported": imported,
        "duplicates_skipped": skipped_duplicates,
        "items_created": created_items,
        "ingredients_linked": linked_ingredients,
        "ingredients_skipped": skipped_ingredients,
        "recipe_categories_created": recipe_categories_created,
    }
