"""Test de bout en bout du backend omnibot-lite contre le faux serveur LLM.

Prérequis : faux serveur sur 9999 et hub sur 8090 (voir scripts/smoke.sh).
"""

import asyncio
import json
import os
import sys

import requests
import websockets

HUB = "http://127.0.0.1:8090"
WS = "ws://127.0.0.1:8090/ws/monitor"


def check(cond: bool, msg: str):
    if not cond:
        print(f"ÉCHEC : {msg}")
        sys.exit(1)
    print(f"OK   : {msg}")


async def main():
    h = requests.get(f"{HUB}/api/health", timeout=5).json()
    check(h.get("ok") and h.get("llm_reachable"), "health + LLM joignable")

    anims = requests.get(f"{HUB}/api/animations", timeout=5).json()["animations"]
    check(len(anims) == 11 and {a["name"] for a in anims} >= {"speaking", "love", "mad"}, "catalogue 11 animations")

    bot = requests.post(f"{HUB}/api/bots", json={"display_name": "PixelTest"}, timeout=5).json()
    did = bot["device_id"]
    check(did == "pixeltest", f"création bot device_id={did}")

    p = requests.get(f"{HUB}/api/persona/{did}/soul", timeout=5).json()
    check("SOUL.md" in p["markdown"] or "âme" in p["markdown"], "persona SOUL seedé")

    r = requests.put(f"{HUB}/api/persona/{did}/identity", json={"markdown": "# ID\nNom: Testou"}, timeout=5)
    check(r.status_code == 200, "écriture persona identity")

    events: list[dict] = []
    async with websockets.connect(WS) as ws:
        r = requests.post(f"{HUB}/api/bots/{did}/chat", json={"message": "Affiche ton visage content"}, timeout=5).json()
        check(r.get("ok"), "chat accepté")
        deadline = asyncio.get_event_loop().time() + 30
        while asyncio.get_event_loop().time() < deadline:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=15)
            except asyncio.TimeoutError:
                break
            ev = json.loads(raw)
            events.append(ev)
            if ev.get("type") == "chat_done":
                break
        await ws.send("ping")

    types = [e["type"] for e in events]
    print("events:", types)
    check("processing_started" in types, "événement processing_started")
    check("tool_call" in types, "événement tool_call (face_animation)")
    check(any(e.get("animation") == "happy" for e in events if e["type"] == "face_animation"), "événement face_animation happy")
    check("chat_done" in types, "événement chat_done")
    done_text = next(e.get("text", "") for e in reversed(events) if e["type"] == "chat_done")
    check("é" in done_text and "â" in done_text, "accents intacts (utf-8 streaming)")
    check("’" in done_text, "apostrophe typographique intacte")
    check("🐶" in done_text, "emoji intact")

    r = requests.post(f"{HUB}/api/bots/{did}/face-animation", json={"animation": "love"}, timeout=5)
    check(r.status_code == 200, "face-animation manuel OK")
    r = requests.post(f"{HUB}/api/bots/{did}/face-animation", json={"animation": "nope"}, timeout=5)
    check(r.status_code == 400, "face-animation invalide rejetée")

    # web_search : tool_call dispatché + vrai appel HTTP vers le mock Tavily + retour au LLM.
    events2: list[dict] = []
    async with websockets.connect(WS) as ws:
        r = requests.post(f"{HUB}/api/bots/{did}/chat", json={"message": "Cherche des infos récentes"}, timeout=5).json()
        check(r.get("ok"), "chat web_search accepté")
        deadline = asyncio.get_event_loop().time() + 30
        while asyncio.get_event_loop().time() < deadline:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=15)
            except asyncio.TimeoutError:
                break
            ev = json.loads(raw)
            events2.append(ev)
            if ev.get("type") == "chat_done":
                break
    ws_search = next((e for e in events2 if e["type"] == "tool_call" and e.get("name") == "web_search"), None)
    check(ws_search is not None, "événement tool_call web_search")
    done2 = next((e.get("text", "") for e in reversed(events2) if e["type"] == "chat_done"), "")
    check("example.com/mock" in done2, "outil web_search exécuté puis relu par le LLM (mock Tavily)")

    hist = requests.get(f"{HUB}/api/bots/{did}/history", timeout=5).json()["messages"]
    check(len(hist) == 4 and hist[0]["role"] == "user", "historique persisté (2 tours user+assistant)")

    st = requests.post(f"{HUB}/api/bots/{did}/settings", json={"heartbeat_enabled": False}, timeout=5).json()
    check(st["heartbeat_enabled"] is False, "réglages heartbeat")

    r = requests.delete(f"{HUB}/api/bots/{did}", timeout=5)
    check(r.status_code == 200, "suppression bot")
    bots = requests.get(f"{HUB}/api/bots", timeout=5).json()["bots"]
    check(all(b["device_id"] != did for b in bots), "bot disparu de la liste")

    print("\nTOUS LES TESTS PASSENT")


asyncio.run(main())
