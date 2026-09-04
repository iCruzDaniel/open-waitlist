from __future__ import annotations


class RedisKeys:
    """Build namespaced Redis keys.

    Every key is prefixed with `{org}:` for multi-tenant isolation between
    deployments sharing an Upstash instance, plus a per-entity sub-namespace.
    """

    def __init__(self, org: str, *, separator: str = ":") -> None:
        clean = org.strip().lower()
        clean = "".join(c if c.isalnum() or c in ("-", "_") else "-" for c in clean)
        self._org = clean or "waitlistgo"
        self._sep = separator

    def _k(self, *parts: str) -> str:
        return self._sep.join((self._org, *parts))

    # --- counters ---
    def waitlist_seq(self) -> str:
        return self._k("wl", "seq")

    def entry_seq(self) -> str:
        return self._k("entry", "seq")

    def admin_seq(self) -> str:
        return self._k("admin", "seq")

    # --- waitlists ---
    def waitlist_slug_index(self) -> str:
        return self._k("wl", "by-slug")

    def waitlist_id_index(self) -> str:
        return self._k("wl", "by-id")

    def waitlist_by_slug(self, slug: str) -> str:
        return self._k("wl", "slug", slug)

    def waitlist_by_id(self, waitlist_id: int) -> str:
        return self._k("wl", "id", str(waitlist_id))

    # --- entries ---
    def entries_by_waitlist(self, waitlist_id: int) -> str:
        return self._k("wl", str(waitlist_id), "entries")

    def entry_by_id(self, entry_id: int) -> str:
        return self._k("entry", "id", str(entry_id))

    def entry_emails(self, waitlist_id: int) -> str:
        return self._k("wl", str(waitlist_id), "emails")

    # --- admins ---
    def admins_by_email(self) -> str:
        return self._k("admin", "by-email")

    def admin_by_email(self, email: str) -> str:
        return self._k("admin", "email", email.lower())

    def admin_by_id(self, admin_id: int) -> str:
        return self._k("admin", "id", str(admin_id))
