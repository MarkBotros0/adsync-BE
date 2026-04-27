"""Branded PDF + CSV report builder.

Pulls the brand's identity (logo bytes, colours, font) from ``brand_identities`` and
renders a one-page PDF using ``reportlab``. The KPI numbers come from the same derived
functions that drive the analytics dashboard so a report and the live page show
identical numbers for the same window.

PDF + CSV bytes are returned to the caller; persistence in ``report_runs.pdf_bytes`` /
``csv_bytes`` is the caller's responsibility.
"""
from __future__ import annotations

import csv
import io
import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.brand_identity import BrandIdentityModel

logger = logging.getLogger(__name__)


def _identity(db: Session, brand_id: int) -> BrandIdentityModel | None:
    return (
        db.query(BrandIdentityModel)
        .filter(
            BrandIdentityModel.brand_id == brand_id,
            BrandIdentityModel.deleted_at.is_(None),
        )
        .first()
    )


async def build_pdf(
    db: Session,
    *,
    brand_id: int,
    period_start: datetime,
    period_end: datetime,
    sections: list[str],
    kpis: dict[str, Any] | None = None,
) -> bytes:
    """Render a branded PDF and return the bytes.

    ``kpis`` is the pre-computed top-of-page KPI dict (as returned by
    ``analytics.derived.top_of_page_kpis`` plus the ERR / per-1k / total saves /
    grade distribution figures). When None, the PDF still renders with placeholders so
    a scheduled run that loses the upstream data can still be sent.

    Sections is a list of strings like ``["overview", "audience", "ads", "top_posts"]``;
    rendering currently lays out Overview only. Other sections become headed empty
    blocks so the FE can preview the structure now and we fill them in over time.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib.colors import HexColor
        from reportlab.pdfgen import canvas
    except ImportError:  # pragma: no cover - hard requirement; fail loud
        raise RuntimeError(
            "reportlab is not installed. Add `reportlab` to requirements.txt."
        )

    identity = _identity(db, brand_id)
    primary = HexColor(identity.primary_color) if identity else HexColor("#6366f1")
    secondary = HexColor(identity.secondary_color) if identity else HexColor("#0ea5e9")
    font = (identity.font_family if identity else "Helvetica") or "Helvetica"
    if font not in ("Helvetica", "Times-Roman", "Courier"):
        # reportlab only ships those three by default — silently fall back.
        font = "Helvetica"

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    # ── Header band ────────────────────────────────────────────────────────
    c.setFillColor(primary)
    c.rect(0, height - 30 * mm, width, 30 * mm, stroke=0, fill=1)
    if identity and identity.logo_bytes:
        try:
            from reportlab.lib.utils import ImageReader
            c.drawImage(
                ImageReader(io.BytesIO(identity.logo_bytes)),
                15 * mm, height - 25 * mm, width=20 * mm, height=20 * mm,
                preserveAspectRatio=True, mask="auto",
            )
        except Exception:  # noqa: BLE001
            logger.warning("Could not render brand logo on PDF; continuing without it")

    c.setFillColor(HexColor("#ffffff"))
    c.setFont(f"{font}-Bold", 22)
    c.drawString(45 * mm, height - 17 * mm, "Performance Report")
    c.setFont(font, 10)
    c.drawString(
        45 * mm, height - 23 * mm,
        f"{period_start.date()}  –  {period_end.date()}",
    )

    # ── KPI row ────────────────────────────────────────────────────────────
    y = height - 50 * mm
    c.setFillColor(HexColor("#111827"))
    c.setFont(f"{font}-Bold", 14)
    c.drawString(15 * mm, y, "Headline KPIs")
    y -= 8 * mm

    tile_w = (width - 30 * mm) / 3
    tile_h = 22 * mm
    tiles: list[tuple[str, str]] = []
    if kpis:
        top = kpis.get("top_of_page") or {}
        tiles = [
            ("Engagement Rate / Reach", f"{kpis.get('engagement_rate_per_reach_pct') or 0:.2f} %"),
            ("Interactions / 1k followers", f"{kpis.get('interactions_per_1k_followers') or 0:.2f}"),
            ("Total Saves", f"{kpis.get('total_saves') or 0}"),
            ("Avg Engagements / post", f"{top.get('avg_total_engagements_per_post') or 0:.1f}"),
            ("Avg Reach / post", f"{top.get('avg_reach_per_post') or 0:.0f}"),
            ("Followers Growth %", f"{top.get('followers_growth_rate_pct') or 0:.2f} %"),
        ]
    else:
        tiles = [("KPI " + str(i), "—") for i in range(1, 7)]

    for i, (label, value) in enumerate(tiles):
        col = i % 3
        row = i // 3
        x = 15 * mm + col * tile_w
        ty = y - row * (tile_h + 4 * mm)
        c.setFillColor(HexColor("#f3f4f6"))
        c.roundRect(x, ty - tile_h, tile_w - 4 * mm, tile_h, 4, stroke=0, fill=1)
        c.setFillColor(HexColor("#6b7280"))
        c.setFont(font, 8)
        c.drawString(x + 4 * mm, ty - 6 * mm, label.upper())
        c.setFillColor(secondary)
        c.setFont(f"{font}-Bold", 16)
        c.drawString(x + 4 * mm, ty - 14 * mm, value)

    # ── Grade distribution ─────────────────────────────────────────────────
    if kpis and kpis.get("grade_distribution"):
        y = y - 2 * (tile_h + 4 * mm) - 14 * mm
        c.setFillColor(HexColor("#111827"))
        c.setFont(f"{font}-Bold", 14)
        c.drawString(15 * mm, y, "Post Grade Distribution")
        y -= 6 * mm
        gd = kpis["grade_distribution"]
        c.setFont(font, 11)
        for i, grade in enumerate(("A+", "A", "B", "C", "D")):
            c.setFillColor(secondary if grade.startswith("A") else HexColor("#9ca3af"))
            c.drawString(15 * mm + i * 32 * mm, y - 6 * mm, f"{grade}: {gd.get(grade, 0)}")

    # ── Section placeholders ───────────────────────────────────────────────
    y = 70 * mm
    c.setFillColor(HexColor("#111827"))
    c.setFont(f"{font}-Bold", 12)
    c.drawString(15 * mm, y, "Sections included")
    c.setFont(font, 10)
    c.setFillColor(HexColor("#6b7280"))
    for i, s in enumerate(sections):
        c.drawString(15 * mm, y - 6 * mm * (i + 1), f"•  {s}")

    # ── Footer ─────────────────────────────────────────────────────────────
    c.setFillColor(HexColor("#9ca3af"))
    c.setFont(font, 8)
    c.drawString(
        15 * mm, 12 * mm,
        f"Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} • Echofold",
    )

    c.showPage()
    c.save()
    return buf.getvalue()


def build_csv(rows: list[dict[str, Any]], columns: list[str] | None = None) -> bytes:
    """Flatten any list of dicts to CSV bytes. Columns inferred from first row if omitted."""
    if not rows:
        return b""
    cols = columns or list(rows[0].keys())
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    return buf.getvalue().encode("utf-8")
