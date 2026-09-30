"""Одноразовая диагностика VK-ключей на Error 9 и права.
На каждый ключ: ровно 3 запроса с интервалом 2 сек. В цикле НЕ гонять!"""
import os
import time

import requests

API = "https://api.vk.com/method"
VERSION = "5.199"
GROUP_ID = os.environ.get("VK_GROUP_ID", "").strip().lstrip("-")


def call(token: str, method: str, params: dict = None):
    p = {"access_token": token, "v": VERSION}
    if params:
        p.update(params)
    try:
        r = requests.post(f"{API}/{method}", data=p, timeout=30)
        data = r.json()
    except Exception as e:
        return {"network": str(e)}
    if "error" in data:
        err = data["error"]
        return {"code": err.get("error_code"), "msg": err.get("error_msg", "")}
    return {"ok": True, "response": data.get("response")}


def describe(res):
    if res.get("ok"):
        return "✅ OK"
    if "network" in res:
        return f"🌐 Сетевая ошибка: {res['network'][:80]}"
    code = res.get("code")
    return {
        9:   "⛔ Error 9 — ФЛУД-КОНТРОЛЬ активен",
        5:   "❌ Error 5 — ключ невалиден/истёк",
        15:  "❌ Error 15 — доступ запрещён (нет прав)",
        27:  "❌ Error 27 — групповому ключу метод недоступен",
        100: "✅ Error 100 — метод ДОСТУПЕН, не хватает параметра (флуда нет, права есть)",
        200: "❌ Error 200 — нет доступа к альбому/объекту",
    }.get(code, f"❓ Error {code}: {res.get('msg', '')[:80]}")


def probe(name: str, token: str):
    print(f"\n{'=' * 60}\n🔑 {name}\n{'=' * 60}")
    if not token:
        print("   токен не задан")
        return

    who = call(token, "users.get")
    if who.get("ok") and who.get("response"):
        u = who["response"][0]
        print(f"   Тип: пользовательский ключ ({u.get('first_name')} {u.get('last_name')}, id {u.get('id')})")
    else:
        grp = call(token, "groups.getById")
        if grp.get("ok") and grp.get("response"):
            print(f"   Тип: групповой ключ ({grp['response'][0].get('name')})")
        else:
            print(f"   Тип: не опознан — users.get -> {describe(who)}")
    time.sleep(2)

    # зонд стены: БЕЗ message → успех невозможен, но код ошибки всё говорит:
    # 100 = стена доступна и флуда нет, 9 = флуд, 15 = нет прав
    wall = call(token, "wall.post", {"owner_id": f"-{GROUP_ID}", "from_group": 1})
    print(f"   wall.post (без текста):        {describe(wall)}")
    time.sleep(2)

    photo = call(token, "photos.getWallUploadServer", {"group_id": GROUP_ID})
    print(f"   photos.getWallUploadServer:    {describe(photo)}")
    time.sleep(2)


def main():
    keys = {k: v.strip() for k, v in os.environ.items()
            if k.startswith("VK_TOKEN") and v.strip()}
    if not keys:
        print("❌ В окружении нет ни одного VK_TOKEN*")
        return
    for name, token in sorted(keys.items()):
        probe(name, token)
    print("\n🏁 Готово. Это была ОДНОРАЗОВАЯ проверка — не повторяйте часто.")


if __name__ == "__main__":
    main()