# =============================================================
# NEKOVA Marketplace — Search System
# =============================================================
# Searches the package catalog by name, description,
# category, tags, and author.

from marketplace.registry import get_catalog


def search(query: str = "",
           category: str = None,
           sort_by: str = "downloads") -> list:
    """
    Search the marketplace catalog.

    Args:
        query    — search term (name, description, tags)
        category — filter by category
        sort_by  — 'downloads', 'stars', 'name'

    Returns list of matching packages sorted by sort_by.
    """
    catalog  = get_catalog()
    results  = []
    query_lc = query.lower().strip()

    for name, pkg in catalog.items():
        # Category filter
        if category and pkg.get("category") != category:
            continue

        # Query filter
        if query_lc:
            searchable = " ".join([
                pkg.get("name", ""),
                pkg.get("description", ""),
                pkg.get("author", ""),
                " ".join(pkg.get("tags", [])),
            ]).lower()

            if query_lc not in searchable:
                continue

        results.append(pkg)

    # Sort results
    if sort_by == "downloads":
        results.sort(
            key=lambda p: p.get("downloads", 0),
            reverse=True
        )
    elif sort_by == "stars":
        results.sort(
            key=lambda p: p.get("stars", 0),
            reverse=True
        )
    elif sort_by == "name":
        results.sort(key=lambda p: p.get("name", ""))

    return results


def get_categories() -> list:
    """Return all unique categories."""
    catalog    = get_catalog()
    categories = set()
    for pkg in catalog.values():
        cat = pkg.get("category")
        if cat:
            categories.add(cat)
    return sorted(categories)


def get_featured() -> list:
    """Return top featured packages by downloads."""
    return search(sort_by="downloads")[:5]


def get_by_category(category: str) -> list:
    """Return all packages in a category."""
    return search(category=category)