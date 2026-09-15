import argparse
import asyncio
import json
import os
import time

import httpx

from .clients import Gemini, Linear, repeatable
from .environment import load_runtime_environment
from .feedback import success_message
from .models import Problem, Report, Settings
from .store import Store


async def doctor(settings, deep=False):
    results = {}
    async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
        linear = Linear(settings, client)
        async def check(name, operation):
            try:
                await operation()
                results[name] = "ok"
            except Problem as exc:
                results[name] = f"falhou ({exc.code}); {exc.message}"
            except Exception:
                results[name] = "falhou; revise credencial, acesso e configuração"
        async def gemini():
            if deep:
                import io

                from PIL import Image
                out = io.BytesIO()
                Image.new("RGB", (64, 64), "white").save(out, "PNG")
                store = Store(settings.data_dir)
                try:
                    store.check_downloads()
                    await Gemini(settings, client, store).analyze("Diagnóstico de visão; descreva a imagem vazia, sem inventar um bug.", out.getvalue(), "image/png")
                finally:
                    store.close()
                return
            await repeatable(client, "GET",
                f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}",
                headers={"x-goog-api-key": settings.gemini_api_key.get_secret_value()})
        async def plow():
            base = os.environ.get("PLOW_API_BASE", "https://api.plow.co")
            if base not in ("https://api.plow.co", "https://api.plow.dev"):
                raise ValueError("unsupported Plow endpoint")
            token = os.environ.get("PLOW_AGENT_TOKEN")
            if not token:
                raise ValueError("missing Plow token")
            await repeatable(client, "GET", base + "/v1/chats/" + settings.allowed_chat_id,
                             headers={"Authorization": "Bearer " + token})
        async def fallback():
            if "ai-pending" not in await linear.labels():
                raise Problem("pending_label", "Execute omni prepare-linear ou crie ai-pending no time configurado.")
        async def storage():
            folder = settings.data_dir / "downloads"
            info = folder.lstat()
            expected_uid = 10000 if os.geteuid() == 0 else os.geteuid()
            if folder.is_symlink() or not folder.is_dir() or info.st_uid != expected_uid or info.st_mode & 0o077:
                raise ValueError("unsafe or inaccessible runtime cache")
            for parent in folder.parents:
                info = parent.stat()
                shift = 6 if info.st_uid == expected_uid else 3 if info.st_gid == expected_uid else 0
                if not ((info.st_mode >> shift) & 1):
                    raise Problem("storage_traversal", "O usuário do gateway não consegue atravessar um diretório do cache. Revise as permissões do volume.")
        await asyncio.gather(check("fallback_label", fallback), check("storage", storage), check("linear", linear.doctor), check("gemini", gemini), check("plow", plow))
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if all(v == "ok" for v in results.values()) else 1


def main():
    parser = argparse.ArgumentParser(description="Omni diagnostics; never prints secrets or message text")
    parser.add_argument("command", choices=["doctor", "status", "health", "retry-reply", "reconcile", "prepare-linear"])
    parser.add_argument("job_id", nargs="?")
    parser.add_argument("--deep", action="store_true", help="Exercise Gemini vision and schema (uses tokens)")
    args = parser.parse_args()
    try:
        load_runtime_environment()
        if (args.deep or args.command == "prepare-linear") and os.geteuid() == 0:
            os.setgroups([])
            os.setgid(10000)
            os.setuid(10000)
        settings = Settings.from_env()
        if args.command == "doctor":
            raise SystemExit(asyncio.run(doctor(settings, deep=args.deep)))
        if args.command == "prepare-linear":
            async def prepare():
                async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:
                    provisioning_store = Store(settings.data_dir)
                    try:
                        await Linear(settings, client).prepare_pending_label(provisioning_store)
                    finally:
                        provisioning_store.close()
            asyncio.run(prepare())
            print("Label ai-pending confirmada no Linear.")
            return
        if args.command == "health":
            age = time.time() - (settings.data_dir / "heartbeat").stat().st_mtime
            raise SystemExit(0 if age < 45 else 1)
        store = Store(settings.data_dir)
        try:
            if args.command == "status":
                rows = store.db.execute("SELECT id,state,delivery,attempts FROM jobs ORDER BY created DESC LIMIT 30")
                print(json.dumps([dict(r) for r in rows], indent=2))
                usage = store.db.execute("SELECT count(*),coalesce(sum(input_tokens+output_tokens+cache_read_tokens),0) FROM session_model_usage").fetchone()
                print(f"Respostas de IA contabilizadas: {usage[0]}; tokens: {usage[1]}")
            elif args.command == "retry-reply":
                store.retry_delivery(args.job_id)
                print("Resposta salva recolocada na fila. Nenhum ticket será criado por este comando.")
            elif args.command == "reconcile":
                job = store.get(args.job_id)
                if not job or job["state"] not in ("held", "unknown", "creating"):
                    raise ValueError("not an uncertain job")
                async def reconcile():
                    async with httpx.AsyncClient(timeout=20) as client:
                        return await Linear(settings, client).reconcile(job["id"])
                ticket = asyncio.run(reconcile())
                if ticket:
                    report = Report.model_validate_json(job["report"]) if job["report"] else None
                    store.update(job["id"], state="ready", ticket=ticket.model_dump_json(),
                                 reply=success_message(ticket, report), delivery="pending", attempts=0)
                    store.cleanup_image(store.get(job["id"]))
                    print("Ticket encontrado. O link será enviado pela fila.")
                else:
                    print("Criação ainda não confirmada. A recriação continua suspensa.")
        finally:
            store.close()
    except (Exception, KeyboardInterrupt):
        print("Não foi possível concluir. Revise a configuração e o identificador do trabalho; segredos foram omitidos.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
