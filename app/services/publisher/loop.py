"""In-process publisher + scheduled-report loops.

Per the deployment constraint (no Redis, no Celery, no separate worker), both loops
run as ``asyncio.Task`` instances inside the FastAPI process — launched from
``main.py``'s ``@app.on_event('startup')``. Concurrency safety across multiple uvicorn
workers comes from Postgres row locking (``FOR UPDATE SKIP LOCKED``).

Loops:
1. ``publish_pending_loop`` — polls ``scheduled_posts`` for due rows, publishes to
   each requested platform, marks the row published or failed.
2. ``send_due_reports_loop`` — polls ``report_schedules`` for due runs, builds the
   PDF, emails it via the existing Gmail SMTP path, advances ``next_sent_at``.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import text as sql_text

from app.database import get_session_local
from app.models.media_asset import MediaAssetModel
from app.models.report_run import (
    RUN_STATUS_FAILED,
    RUN_STATUS_GENERATING,
    RUN_STATUS_READY,
    ReportRunModel,
)
from app.models.report_schedule import (
    CADENCE_MONTHLY,
    CADENCE_WEEKLY,
    ReportScheduleModel,
)
from app.models.scheduled_post import (
    STATUS_FAILED,
    STATUS_PUBLISHED,
    STATUS_PUBLISHING,
    STATUS_SCHEDULED,
    ScheduledPostModel,
)
from app.repositories.facebook_session import FacebookSessionRepository
from app.repositories.instagram_session import InstagramSessionRepository
from app.repositories.tiktok_session import TikTokSessionRepository
from app.services.facebook.pages import PagesService
from app.services.publisher import platforms

logger = logging.getLogger(__name__)


POLL_INTERVAL_SECONDS = 30
MAX_ATTEMPTS = 3


# ── Publisher loop ──────────────────────────────────────────────────────────

async def publish_pending_loop() -> None:
    """Forever-loop that picks up scheduled posts whose ``scheduled_at`` is due.

    Per iteration:
      1. ``SELECT ... FOR UPDATE SKIP LOCKED`` one ready row + flip its status to
         ``publishing`` in the same transaction. The lock + status flip together
         act as the "claim" so two API workers cannot both pick up the same row.
      2. Publish to each requested platform.
      3. On success, status=``published`` + record platform_post_ids.
      4. On failure, increment attempts; status=``failed`` once attempts == MAX.
    """
    logger.info("Publisher loop starting (poll=%ds, max_attempts=%d)", POLL_INTERVAL_SECONDS, MAX_ATTEMPTS)
    while True:
        try:
            await _process_one_due_post()
        except Exception:  # noqa: BLE001
            logger.exception("Publisher loop iteration crashed; continuing")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


async def _process_one_due_post() -> None:
    db = get_session_local()()
    post: ScheduledPostModel | None = None
    try:
        # Atomic claim — single row update returning the row we picked.
        sql = sql_text(
            """
            UPDATE scheduled_posts
               SET status = :publishing,
                   updated_at = now()
             WHERE id = (
                SELECT id FROM scheduled_posts
                 WHERE status = :scheduled
                   AND scheduled_at IS NOT NULL
                   AND scheduled_at <= now()
                   AND deleted_at IS NULL
                 ORDER BY scheduled_at ASC
                 FOR UPDATE SKIP LOCKED
                 LIMIT 1
             )
            RETURNING id
            """
        )
        row = db.execute(sql, {"publishing": STATUS_PUBLISHING, "scheduled": STATUS_SCHEDULED}).first()
        if not row:
            db.commit()
            return
        db.commit()

        post = (
            db.query(ScheduledPostModel)
            .filter(ScheduledPostModel.id == row.id)
            .first()
        )
        if not post:
            return

        await _publish_post(db, post)
    finally:
        db.close()


async def _publish_post(db, post: ScheduledPostModel) -> None:
    media = (
        db.query(MediaAssetModel)
        .filter(
            MediaAssetModel.id.in_(post.media_asset_ids_json or []),
            MediaAssetModel.deleted_at.is_(None),
        )
        .all()
    )
    media_map = {a.id: a for a in media}
    ordered_media = [media_map[i] for i in (post.media_asset_ids_json or []) if i in media_map]

    platform_post_ids: dict[str, str] = post.platform_post_ids_json or {}
    errors: list[str] = []

    for platform in post.platforms_json or []:
        per = (post.per_platform_payload_json or {}).get(platform) or {}
        text = per.get("text") or post.text
        try:
            if platform == "facebook":
                pid = await _publish_facebook(db, post.brand_id, text, ordered_media)
            elif platform == "instagram":
                pid = await _publish_instagram(db, post.brand_id, text, ordered_media)
            elif platform == "tiktok":
                pid = await _publish_tiktok(db, post.brand_id, text, ordered_media)
            else:
                raise ValueError(f"Unsupported platform: {platform}")
            platform_post_ids[platform] = pid
        except Exception as exc:  # noqa: BLE001
            logger.warning("Publish to %s failed for post %d: %s", platform, post.id, exc)
            errors.append(f"{platform}: {exc}")

    post.platform_post_ids_json = platform_post_ids
    post.attempt_count = (post.attempt_count or 0) + 1
    if errors:
        post.error_message = "; ".join(errors)
        if post.attempt_count >= MAX_ATTEMPTS:
            post.status = STATUS_FAILED
        else:
            # Reschedule with exponential backoff.
            post.status = STATUS_SCHEDULED
            post.scheduled_at = datetime.utcnow() + timedelta(minutes=2 ** post.attempt_count)
    else:
        post.status = STATUS_PUBLISHED
        post.published_at = datetime.utcnow()
        post.error_message = None
    db.commit()


async def _publish_facebook(db, brand_id: int, text: str, media: list[MediaAssetModel]) -> str:
    fb_session = FacebookSessionRepository(db).get_by_brand_id(brand_id)
    if not fb_session:
        raise RuntimeError("Facebook not connected")
    user_token = fb_session.access_token
    pages = (await PagesService(access_token=user_token).fetch_pages()).get("data", [])
    if not pages:
        raise RuntimeError("No Facebook Pages on this account")
    page = pages[0]
    return await platforms.publish_to_facebook(
        page_id=page["id"],
        page_token=page.get("access_token", user_token),
        text=text,
        media=media,
    )


async def _publish_instagram(db, brand_id: int, text: str, media: list[MediaAssetModel]) -> str:
    ig_session = InstagramSessionRepository(db).get_by_brand_id(brand_id)
    if not ig_session:
        raise RuntimeError("Instagram not connected")
    if not media:
        raise RuntimeError("Instagram requires a media asset")
    asset = media[0]
    public_url = getattr(asset, "public_url", None)
    if not public_url:
        # Without an external URL we cannot publish to IG. Surface a clear error so
        # the FE can prompt the user to set the public host.
        raise RuntimeError(
            "Instagram needs a publicly reachable media URL. Set BRAND_PUBLIC_HOST and "
            "ensure /publish/media/{id}/raw is reachable from the public internet."
        )
    return await platforms.publish_to_instagram(
        ig_user_id=ig_session.ig_user_id,
        access_token=ig_session.access_token,
        text=text,
        media_url=public_url,
        is_video=(asset.kind == "video"),
    )


async def _publish_tiktok(db, brand_id: int, text: str, media: list[MediaAssetModel]) -> str:
    tt_session = TikTokSessionRepository(db).get_by_brand_id(brand_id)
    if not tt_session:
        raise RuntimeError("TikTok not connected")
    return await platforms.publish_to_tiktok(
        access_token=tt_session.access_token,
        text=text,
        media=media,
    )


# ── Scheduled report loop ───────────────────────────────────────────────────

async def send_due_reports_loop() -> None:
    """Poll ``report_schedules`` for due runs, build PDF, email it, advance ``next_sent_at``."""
    logger.info("Scheduled-report loop starting (poll=%ds)", POLL_INTERVAL_SECONDS)
    while True:
        try:
            await _process_one_due_report()
        except Exception:  # noqa: BLE001
            logger.exception("Report loop iteration crashed; continuing")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


async def _process_one_due_report() -> None:
    from app.services.reports.builder import build_pdf
    from app.services.email import send_email_with_attachment

    db = get_session_local()()
    try:
        sched: ReportScheduleModel | None = (
            db.query(ReportScheduleModel)
            .filter(
                ReportScheduleModel.next_sent_at <= datetime.utcnow(),
                ReportScheduleModel.deleted_at.is_(None),
            )
            .order_by(ReportScheduleModel.next_sent_at.asc())
            .first()
        )
        if not sched:
            return

        period_end = datetime.utcnow()
        window_days = int((sched.template_json or {}).get("window_days") or 30)
        period_start = period_end - timedelta(days=window_days)

        run = ReportRunModel(
            brand_id=sched.brand_id,
            schedule_id=sched.id,
            status=RUN_STATUS_GENERATING,
            period_start=period_start,
            period_end=period_end,
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        try:
            pdf = await build_pdf(
                db,
                brand_id=sched.brand_id,
                period_start=period_start,
                period_end=period_end,
                sections=(sched.template_json or {}).get("sections") or ["overview"],
            )
            run.pdf_bytes = pdf
            run.status = RUN_STATUS_READY
            run.generated_at = datetime.utcnow()

            # Email recipients.
            recipients = [r.strip() for r in (sched.recipients_csv or "").split(",") if r.strip()]
            for to_email in recipients:
                try:
                    await send_email_with_attachment(
                        to=to_email,
                        subject=f"{sched.name} — {period_start.date()} → {period_end.date()}",
                        body=f"Your scheduled report is attached.",
                        attachment=pdf,
                        attachment_filename=f"{sched.name}.pdf",
                        attachment_mime="application/pdf",
                    )
                except Exception:  # noqa: BLE001
                    logger.exception("Email send failed for %s", to_email)
            run.delivered_at = datetime.utcnow()
        except Exception as exc:  # noqa: BLE001
            run.status = RUN_STATUS_FAILED
            run.error_message = str(exc)
            logger.exception("Report build failed for schedule %d", sched.id)

        # Advance next_sent_at regardless of success.
        sched.last_sent_at = datetime.utcnow()
        if sched.cadence == CADENCE_WEEKLY:
            sched.next_sent_at = datetime.utcnow() + timedelta(weeks=1)
        elif sched.cadence == CADENCE_MONTHLY:
            sched.next_sent_at = datetime.utcnow() + timedelta(days=30)
        db.commit()
    finally:
        db.close()


# ── Orphan recovery on startup ──────────────────────────────────────────────

def recover_orphans() -> None:
    """Mark any ``publishing`` rows as ``failed`` — they were interrupted by a restart.

    Same pattern as the existing competitor-analysis recovery in main.py. Called
    synchronously during startup before the loops start.
    """
    db = get_session_local()()
    try:
        stuck = (
            db.query(ScheduledPostModel)
            .filter(
                ScheduledPostModel.status == STATUS_PUBLISHING,
                ScheduledPostModel.deleted_at.is_(None),
            )
            .all()
        )
        if not stuck:
            return
        for p in stuck:
            p.status = STATUS_FAILED
            p.error_message = "Server restarted while publishing — please retry."
            p.updated_at = datetime.utcnow()
        db.commit()
        logger.info("Recovered %d orphaned publishing post(s)", len(stuck))
    finally:
        db.close()
