import json
import re
import subprocess

def load_db():
    with open("scam_db.json", "r") as f:
        return json.load(f)

def whois_check(domain):
    flags = []
    try:
        result = subprocess.run(
            ["whois", "-h", "whois.verisign-grs.com", domain],
            capture_output=True, text=True, timeout=10
        )
        text = result.stdout

        if "SUSPENDED-DOMAIN" in text.upper():
            flags.append("❌ Домен ЗАБЛОКИРОВАН регистратором")

        if "PDR Ltd" in text or "PublicDomainRegistry" in text:
            flags.append("⚠️ Регистратор: PDR Ltd. (подозрительный)")

        import re as _re
        m = _re.search(r"Creation Date:\s*(\d{4})-(\d{2})-(\d{2})", text)
        if m:
            year = int(m.group(1))
            if year >= 2026:
                flags.append(f"⚠️ Домен молодой (создан {year})")
    except Exception:
        pass
    return flags

def check_target(target):
    db = load_db()
    flags = []

    target = target.lower().strip()
    target = re.sub(r"^https?://", "", target)
    target = target.split("/")[0]

    if target in db["domains"]:
        flags.append("❌ Домен в базе скамов")

    if target in db["emails"]:
        flags.append("❌ Email в базе скамов")

    for d in db["domains"]:
        if target != d and (target in d or d in target):
            flags.append(f"⚠️ Похож на скам: {d}")

    for n in db["names"]:
        if n.lower() in target:
            flags.append(f"⚠️ Имя из базы: {n}")

    if "." in target and "@" not in target:
        flags.extend(whois_check(target))

    if any("❌" in f for f in flags):
        verdict = "🔴 СКАМ"
    elif len(flags) > 0:
        verdict = "🟡 ПОДОЗРИТЕЛЬНО"
    else:
        verdict = "🟢 НЕИЗВЕСТНО"

    return {"target": target, "flags": flags, "verdict": verdict}

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        r = check_target(sys.argv[1])
        print(f"\n🔍 ПРОВЕРКА: {r['target']}\n")
        if r["flags"]:
            for f in r["flags"]:
                print(f)
        else:
            print("✅ Совпадений не найдено")
        print(f"\nВЕРДИКТ: {r['verdict']}\n")
