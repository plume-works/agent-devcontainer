"""Guard plan slugs against path traversal."""


def is_safe_slug(slug: str) -> bool:
    """Return True when `slug` is safe to use as a plan file name."""
    return not slug.startswith('/') and '..' not in slug
