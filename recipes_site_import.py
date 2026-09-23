from __future__ import annotations

from collections import deque
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, urlunsplit
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
_FOOTER_PREFIXES = (
    "page updated",
    "report abuse",
)

_QUANTITY = r"(?:\d+(?:[.,]\d+)?|\d+\s*[\/⁄]\s*\d+|[¼½¾⅓⅔⅛⅜⅝⅞]|une?|deux|trois|quatre|cinq|six|sept|huit|neuf|dix)"
_UNIT = (
    r"(?:kg|g|mg|l|ml|cl|oz|lb|lbs|tasses?|cups?|t\.?|"
    r"cuill(?:ere|ère)s?\s+à\s+soupe|cuill(?:ere|ère)s?\s+a\s+soupe|"
    r"cuill(?:ere|ère)s?\s+à\s+table|cuill(?:ere|ère)s?\s+a\s+table|"
    r"cuill(?:ere|ère)s?\s+à\s+caf(?:e|é)|cuill(?:ere|ère)s?\s+a\s+caf(?:e|é)|"
    r"c\.\s*à\s*s\.?|c\.\s*a\s*s\.?|c\s+à\s+soupe|c\s+a\s+soupe|"
    r"c\.\s*à\s*c\.?|c\.\s*a\s*c\.?|c\s+à\s+caf(?:e|é)|c\s+a\s+caf(?:e|é)|"
    r"bo[iî]tes?|gousses?|tranches?|pinc(?:e|é)es?|sachets?|paquets?|branches?)"
)


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
    raw = str(value or "").strip()
    if not raw:
        raw = DEFAULT_SITE_URL
    parts = urlsplit(raw)
    if parts.scheme.lower() != "https" or parts.netloc.lower() != "sites.google.com":
        raise ValueError("L’adresse doit être une page HTTPS de votre Google Sites.")
    path = re.sub(r"/{2,}", "/", parts.path or "/")
    root_path = urlsplit(SITE_ROOT).path.rstrip("/")
    if path.rstrip("/") != root_path and not path.startswith(root_path + "/"):
        raise ValueError("Cette adresse ne fait pas partie du site Recettes de l’Ours.")
    clean = urlunsplit(("https", "sites.google.com", path.rstrip("/") or root_path, "", ""))
    return clean


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
        self.links: list[str] = []
        self.headings: list[tuple[str, str]] = []
        self.list_items: list[str] = []

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
                self._li_parts = []
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
        for suffix in (" - Recettes de l'Ours", " – Recettes de l'Ours", " | Recettes de l'Ours"):
            if title.endswith(suffix):
                title = title[: -len(suffix)].strip()
        if _fold(title) not in {"recettes de l'ours", "recettes de lours"}:
            return title
    for line in lines:
        folded = _fold(line)
        if folded not in _CHROME_LINES and folded not in {"recettes de l'ours", "recettes de lours"}:
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

    # Retire une précision finale entre parenthèses avant d'isoler le nom.
    text = re.sub(r"\s*\([^)]*\)\s*$", "", text).strip()

    # Cas classique : quantité + unité avant le nom (ex. « 1 tasse de crème »).
    text = re.sub(rf"^{_QUANTITY}\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(rf"^{_UNIT}\b\s*(?:de\s+|d['’])?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^(?:de\s+|d['’])", "", text, flags=re.IGNORECASE)

    # Certaines recettes de l'Ours placent la mesure après l'ingrédient,
    # ex. « Huile olive 60% 1/3 tasse ». Conserve le nom situé avant la mesure.
    trailing_measure = re.search(
        rf"\s+{_QUANTITY}\s*{_UNIT}\b.*$",
        text,
        flags=re.IGNORECASE,
    )
    if trailing_measure and trailing_measure.start() >= 2:
        text = text[: trailing_measure.start()].strip()

    # « au goût » est une précision culinaire, pas une partie du nom de l'item.
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
        # Évite les sous-titres du genre « Sauce : » ou « Garniture : ».
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


def _headingless_sections(
    parser: _GoogleSiteParser,
    lines: list[str],
    title: str,
) -> tuple[list[str], list[str]] | None:
    """Reconnaît le format historique de Recettes de l'Ours.

    Plusieurs pages ne portent aucun titre « Ingrédients » / « Préparation » :
    les ingrédients sont du texte simple sous le titre, puis la méthode commence
    avec une liste à puces. Les paragraphes qui suivent cette liste appartiennent
    aussi à la préparation.
    """
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
        # Ignore des métadonnées éventuelles sans les transformer en ingrédients.
        if re.search(
            r"\b(?:preparation|préparation|cuisson|temps|rendement|portions?|personnes?)\s*[:\-]",
            line,
            flags=re.IGNORECASE,
        ):
            continue
        ingredient_lines.append(line)

    # Le format sans titres est accepté seulement si plusieurs ingrédients sont
    # trouvés avant la première puce. Cela évite de prendre une page de menu pour
    # une recette.
    if len(_ingredient_lines_to_entries(ingredient_lines)) < 2:
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
        cleaned = _strip_bullet(re.sub(r"^\s*\d{1,2}[.)]\s*", "", line)).strip()
        if cleaned:
            preparation_lines.append(cleaned)

    if not preparation_lines:
        return None
    return ingredient_lines, preparation_lines


def parse_recipe_html(html: str, source_url: str) -> dict | None:
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
        if kind == "preparation" and ingredient_index is not None and index > ingredient_index:
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
            cleaned = _strip_bullet(re.sub(r"^\s*\d{1,2}[.)]\s*", "", line)).strip()
            if cleaned:
                preparation_lines.append(cleaned)
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
            if _fold(line) in {_fold(title), "recettes de l'ours", "recettes de lours"}:
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

    description = " ".join(description_lines)[:800]
    return {
        "name": title[:180],
        "servings": _extract_servings(lines),
        "description": description,
        "instructions": "\n".join(preparation_lines)[:12000],
        "ingredients": ingredients,
        "source_url": normalize_site_url(source_url),
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
                "Le site semble demander une connexion Google. Vérifiez que sa version publiée est publique."
            )
        content_type = str(response.headers.get("Content-Type") or "")
        if "text/html" not in content_type.lower():
            raise ValueError("La page Google Sites retournée n’est pas une page HTML.")
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read(4_000_000).decode(charset, errors="replace")


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


def crawl_google_site(start_url: str = DEFAULT_SITE_URL, max_pages: int = MAX_PAGES_DEFAULT) -> dict:
    start = normalize_site_url(start_url)
    limit = max(1, min(int(max_pages or MAX_PAGES_DEFAULT), 250))
    queue = deque([start])
    queued = {start}
    visited = set()
    candidates = []
    errors = []

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

        candidate = parse_recipe_html(html, url)
        if candidate:
            candidates.append(candidate)

        for link in _internal_links(html, url):
            if link not in visited and link not in queued and len(queued) < limit * 3:
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


def import_recipe_candidates(
    user_id,
    family_id,
    candidates,
    category_id,
    store_id=None,
    create_missing_items=True,
):
    """Importe un lot analysé dans les tables Recettes existantes.

    L'opération est transactionnelle : si une erreur survient, aucune recette ni
    aucun item du lot n'est laissé partiellement importé.
    """
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
            recipe_keys = {normalize_name(row["name"]): int(row["id"]) for row in cur.fetchall()}

            cur.execute(
                """
                SELECT id, name
                FROM items
                WHERE family_id = %s
                  AND deleted_at IS NULL;
                """,
                (family_id,),
            )
            item_map = {normalize_name(row["name"]): int(row["id"]) for row in cur.fetchall()}

            if create_missing_items:
                cur.execute(
                    """
                    SELECT id FROM categories
                    WHERE id = %s AND family_id = %s AND deleted_at IS NULL;
                    """,
                    (category_id, family_id),
                )
                if cur.fetchone() is None:
                    raise ValueError("Choisissez une catégorie valide pour les nouveaux items.")

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
            elif store_id is not None:
                cur.execute(
                    """
                    SELECT id FROM stores
                    WHERE id = %s AND family_id = %s AND deleted_at IS NULL;
                    """,
                    (store_id, family_id),
                )
                if cur.fetchone() is None:
                    raise ValueError("Choisissez un magasin valide pour les nouveaux items.")

            imported = 0
            skipped_duplicates = 0
            created_items = 0
            linked_ingredients = 0
            skipped_ingredients = 0

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
                description = str(candidate.get("description") or "").strip()[:800]
                instructions = str(candidate.get("instructions") or "").strip()[:12000]

                cur.execute(
                    """
                    INSERT INTO grocery_recipes (
                        family_id, name, description, instructions,
                        servings, created_by_user_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id;
                    """,
                    (family_id, name, description, instructions, servings, user_id),
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
                    {"source": "google_sites_import"},
                )

                sort_order = 10
                for ingredient in candidate.get("ingredients") or []:
                    item_name = str(ingredient.get("item_name") or "").strip()[:160]
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
                            {"needed": False, "source": "google_sites_import"},
                        )

                    note = str(ingredient.get("original") or "").strip()[:600]
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

            conn.commit()

    return {
        "recipes_imported": imported,
        "duplicates_skipped": skipped_duplicates,
        "items_created": created_items,
        "ingredients_linked": linked_ingredients,
        "ingredients_skipped": skipped_ingredients,
    }
