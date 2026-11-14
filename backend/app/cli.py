"""Admin commands. Run from backend/:

    .venv/bin/python -m app.cli telegram-check
    .venv/bin/python -m app.cli add-telegram "Coordenação" 123456789 [--sites chapada-veadeiros] [--kinds fire hotspot]
    .venv/bin/python -m app.cli test-alert [--site chapada-veadeiros] [--kind hotspot]
    .venv/bin/python -m app.cli compare-inpe [--days 30] [--csv out.csv]

Settings come from the environment, backend/.env, and finally ../infra/.env (the Docker stack's file), so the
same Telegram token works for the CLI and the containers.
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

INFRA_ENV = Path(__file__).resolve().parents[2] / "infra" / ".env"


def _load_infra_env() -> None:
    """Fill missing SENTINELA_* variables from infra/.env (never overrides the real environment)."""
    if not INFRA_ENV.exists():
        return
    for line in INFRA_ENV.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key.startswith("SENTINELA_") and value and key not in os.environ:
            os.environ[key] = value.strip().strip('"').strip("'")


def _chat_label(chat: dict) -> str:
    if chat.get("title"):
        return chat["title"]
    name = " ".join(p for p in (chat.get("first_name"), chat.get("last_name")) if p)
    return name + (f" (@{chat['username']})" if chat.get("username") else "")


async def telegram_check() -> int:
    import httpx

    from app.config import settings

    token = settings.telegram_bot_token
    if not token:
        print("SENTINELA_TELEGRAM_BOT_TOKEN is not set. Put it in infra/.env (see the Alerts docs).")
        return 1
    base = f"https://api.telegram.org/bot{token}"
    async with httpx.AsyncClient(timeout=15) as client:
        me = (await client.get(f"{base}/getMe")).json()
        if not me.get("ok"):
            print(f"Token rejected by Telegram: {me.get('description')}")
            return 1
        print(f"Bot OK: @{me['result']['username']} ({me['result']['first_name']})")

        updates = (await client.get(f"{base}/getUpdates")).json()
        if not updates.get("ok"):
            print(f"getUpdates failed: {updates.get('description')}")
            return 1

    chats: dict[int, dict] = {}
    for u in updates["result"]:
        for key in ("message", "edited_message", "channel_post", "my_chat_member"):
            if key in u and "chat" in u[key]:
                chats[u[key]["chat"]["id"]] = u[key]["chat"]
    if not chats:
        print(f"\nNo chats yet. Open https://t.me/{me['result']['username']} and send /start,\n"
              "or add the bot to a group and send a message there. Then run this again.\n"
              "(Telegram only keeps recent updates, about 24 h.)\n"
              "If the backend is running with this token, it consumes the updates itself:\n"
              "send /start to the bot instead, and it replies with the chat ID.")
        return 0
    print("\nChats that talked to the bot:")
    for cid, chat in chats.items():
        print(f"  {cid:>16}  {chat['type']:<10}  {_chat_label(chat)}")
    print('\nAdd one with:  .venv/bin/python -m app.cli add-telegram "<name>" <chat id>')
    return 0


def add_telegram(name: str, chat_id: str, sites: list[str], kinds: list[str]) -> int:
    from app.alerts.dispatch import ALL_KINDS
    from app.config import settings

    if not chat_id.lstrip("-").isdigit():
        print(f"chat id must be a number (groups are negative), got {chat_id!r}")
        return 1
    bad = set(kinds) - set(ALL_KINDS)
    if bad:
        print(f"unknown kinds {sorted(bad)}; valid: {ALL_KINDS}")
        return 1
    path = Path(settings.recipients_file)
    data = json.loads(path.read_text()) if path.exists() else {"recipients": []}
    for r in data["recipients"]:
        if r.get("channels", {}).get("telegram") == chat_id:
            r.update(name=name, sites=sites, kinds=kinds)
            break
    else:
        data["recipients"].append({"name": name, "channels": {"telegram": chat_id}, "sites": sites, "kinds": kinds})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print(f"Saved {name} (telegram {chat_id}) to {path}: sites={sites} kinds={kinds}")
    return 0


async def test_alert(site: str, kind: str) -> int:
    from app.alerts.dispatch import deliver

    msg = (f"✅ Teste do Sentinela do Fogo: alerta '{kind}' para '{site}'. "
           "Se você recebeu esta mensagem, os alertas estão funcionando.")
    results = await deliver(site, kind, msg)
    if not results:
        print(f"No recipient wants kind={kind!r} for site={site!r}. Check config/recipients.json.")
        return 1
    for d in results:
        print(f"  {'OK  ' if d.ok else 'FAIL'}  {d.recipient:<24} {d.channel:<9} {d.detail}")
    return 0 if all(d.ok for d in results) else 1


async def compare_inpe(n_days: int, csv_out: str | None) -> int:
    import csv as _csv
    from datetime import date, timedelta

    import httpx

    from app.sites import load_sites
    from app.validation import inpe_risk as v

    sites = load_sites()
    if not sites:
        print("No sites configured.")
        return 1
    # INPE publishes day D's grid on D+1, so stop at yesterday.
    days = [date.today() - timedelta(days=i) for i in range(n_days, 0, -1)]
    print(f"INPE Risco de Fogo grids for {days[0]} .. {days[-1]} (cached samples are reused):")
    with httpx.Client(timeout=120, follow_redirects=True) as client:
        rf = v.fetch_rf_samples(client, days, sites)

    all_rows = []
    print(f"\n{'site':<20} {'n':>3} {'exact':>6} {'±1 cls':>7} {'gap':>5} {'spearman':>9}   FMA+ / INPE classes (latest day)")
    for s in sites:
        fma = await v.fma_by_day(s)
        rows = v.build_rows(s["id"], fma, rf, days)
        all_rows += rows
        st = v.summarize(rows)
        if not st["n"]:
            print(f"{s['id']:<20}   0  (no overlapping data)")
            continue
        last = rows[-1]
        print(f"{s['id']:<20} {st['n']:>3} {st['exact']:>6.0%} {st['within_one']:>7.0%} {st['mean_gap']:>+5.1f} "
              f"{st['spearman']:>9.2f}   {last.fma:.1f} {last.fma_class} / {last.rf:.2f} {last.rf_class}")
    st = v.summarize(all_rows)
    if st["n"]:
        print(f"{'ALL':<20} {st['n']:>3} {st['exact']:>6.0%} {st['within_one']:>7.0%} {st['mean_gap']:>+5.1f} "
              f"{st['spearman']:>9.2f}")
        print("\nexact/±1 cls: share of days where the 5-level classes match / differ by at most one level.\n"
              "gap: mean class difference (FMA+ minus INPE); positive = FMA+ more alarming.\n"
              "spearman: rank correlation of FMA+ vs INPE RF (1 = same ordering of days).")
    if csv_out:
        with open(csv_out, "w", newline="") as f:
            w = _csv.writer(f)
            w.writerow(["site", "date", "fma_plus", "fma_class", "inpe_rf_mean", "inpe_class"])
            for r in all_rows:
                w.writerow([r.site, r.day, round(r.fma, 2), r.fma_class, round(r.rf, 3), r.rf_class])
        print(f"\nPer-day rows written to {csv_out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    _load_infra_env()
    ap = argparse.ArgumentParser(prog="python -m app.cli", description="Sentinela do Fogo admin commands")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("telegram-check", help="validate the bot token and list chats that messaged the bot")
    p = sub.add_parser("add-telegram", help="add or update a Telegram recipient in recipients.json")
    p.add_argument("name")
    p.add_argument("chat_id")
    p.add_argument("--sites", nargs="+", default=["*"])
    p.add_argument("--kinds", nargs="+", default=["fire", "hotspot", "danger"])
    p = sub.add_parser("test-alert", help="send a test alert through the configured recipients")
    p.add_argument("--site", default="teste")
    p.add_argument("--kind", default="fire", choices=["fire", "hotspot", "danger"])
    p = sub.add_parser("compare-inpe", help="compare our FMA+ with INPE's Risco de Fogo at each site")
    p.add_argument("--days", type=int, default=30, help="how many past days to compare (max ~85)")
    p.add_argument("--csv", default=None, help="write per-day rows to this CSV file")
    args = ap.parse_args(argv)

    if args.cmd == "telegram-check":
        return asyncio.run(telegram_check())
    if args.cmd == "add-telegram":
        return add_telegram(args.name, args.chat_id, args.sites, args.kinds)
    if args.cmd == "compare-inpe":
        return asyncio.run(compare_inpe(min(args.days, 85), args.csv))
    return asyncio.run(test_alert(args.site, args.kind))


if __name__ == "__main__":
    sys.exit(main())
