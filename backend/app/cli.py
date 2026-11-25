from datetime import datetime

import click
from flask import current_app
from sqlalchemy import func, select

from .extensions import db
from .models import Policy
from .services import regions
from .services.sync import prune_missing, upsert_policies
from .services.youthcenter import YouthCenterClient


def sync_all(echo=print, page_size=100, max_pages=None, prune=False) -> int:
    db.create_all()
    cfg = current_app.config
    client = YouthCenterClient(cfg["YOUTHCENTER_API_KEY"], cfg["YOUTHCENTER_API_URL"])
    synced_at = datetime.now()
    seen: set = set()
    total = 0
    for page, items, total in client.iter_pages(size=page_size, max_pages=max_pages):
        seen.update(upsert_policies(items, synced_at))
        echo(f"  {page} 페이지 저장 ({len(seen)}/{total})")
    echo(f"수집 완료: {len(seen)}건")
    if prune:
        if max_pages or len(seen) < total:
            echo("일부만 수집해서 --prune 은 건너뜀")
        else:
            echo(f"삭제된 정책: {prune_missing(seen)}건")
    return len(seen)


def prepare_database(echo=print) -> None:
    db.create_all()
    if db.session.scalar(select(func.count(Policy.policy_id))):
        return
    if not current_app.config["YOUTHCENTER_API_KEY"]:
        echo("⚠ .env 에 YOUTHCENTER_API_KEY 가 없어서 정책 수집을 건너뜀 (빈 DB로 실행)")
        return
    echo("DB가 비어 있어서 온통청년 정책을 처음 수집함 (약 30초~1분)")
    sync_all(echo)


def register_cli(app):
    @app.cli.command("init-db")
    def init_db():
        """테이블을 생성한다."""
        db.create_all()
        click.echo("테이블 생성 완료")

    @app.cli.command("drop-db")
    @click.confirmation_option(prompt="모든 테이블을 삭제할까요?")
    def drop_db():
        """모든 테이블을 삭제한다."""
        db.drop_all()
        click.echo("테이블 삭제 완료")

    @app.cli.command("sync-policies")
    @click.option("--page-size", default=100, show_default=True, help="한 번에 받아올 정책 수")
    @click.option("--max-pages", default=None, type=int, help="테스트용: 이 페이지까지만 수집")
    @click.option("--prune", is_flag=True, help="이번 수집에 없는 정책을 DB에서 삭제")
    def sync_policies(page_size, max_pages, prune):
        """온통청년 정책을 받아 DB에 저장한다."""
        sync_all(click.echo, page_size, max_pages, prune)

    @app.cli.command("import-regions")
    @click.argument("csv_path")
    def import_regions(csv_path):
        """국토교통부 '전국 법정동' CSV로 지역 목록(app/data/regions.json)을 다시 만든다."""
        click.echo(f"시군구 {regions.build_from_csv(csv_path)}개 저장")
