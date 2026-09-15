import asyncio
import hashlib
import io
import logging
import re
import time
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from .feedback import ACK, RETRY, success_message
from .models import Problem, Report, UnknownCreation, is_command

log = logging.getLogger("omni")
HELP = "Envie uma imagem com ‘Registra esse bug’, ‘Registra essa tarefa’ ou ‘Registra essa melhoria’, ou responda à imagem com o comando."
UNCERTAIN = "Não consegui confirmar se o Linear criou o ticket. Suspendi a criação para evitar duplicação. Consulte o diagnóstico do Omni."


def prepare_image(path, roots, limit):
    p = Path(path)
    resolved = p.resolve(strict=True)
    if not any(resolved.is_relative_to(root.resolve()) for root in roots) or p.is_symlink():
        raise Problem("invalid_image", "O anexo não está no cache de imagens autorizado.")
    if resolved.stat().st_size > limit:
        raise Problem("large_image", "A imagem ultrapassa 10 MB. Envie uma captura menor.")
    data = resolved.read_bytes()
    try:
        with Image.open(io.BytesIO(data)) as im:
            if im.width * im.height > 25_000_000 or im.format not in ("PNG", "JPEG", "WEBP"):
                raise Problem("invalid_image", "Envie uma imagem PNG, JPEG ou WebP de até 25 megapixels.")
            im.load()
            # Strip metadata and normalize to PNG; no EXIF/GPS is uploaded.
            out = io.BytesIO()
            im.convert("RGB").save(out, format="PNG")
            clean = out.getvalue()
            if len(clean) > limit:
                raise Problem("large_image", "A imagem ultrapassa 10 MB após conversão. Envie uma captura menor.")
            return clean, "image/png"
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as e:
        raise Problem("invalid_image", "Não consegui abrir a imagem. Envie uma captura PNG ou JPEG.") from e


class Workflow:
    def __init__(self, settings, store, gemini, linear, send):
        self.settings, self.store = settings, store
        self.gemini, self.linear, self.send = gemini, linear, send
        self.locks = [asyncio.Lock() for _ in range(64)]
        self.notice_tasks = {}

    def ingest(self, *, chat, message, text, paths, kinds, owner, roots, sender=None, guid=None, reply_to_guid=None, is_reply=False, prepared=None):
        if chat != self.settings.allowed_chat_id or not owner:
            return None
        log.info("ingress msg=%s sender=%s attachments=%d command=%s reply=%s",
                 hashlib.sha256(message.encode()).hexdigest()[:12],
                 hashlib.sha256((sender or "missing").encode()).hexdigest()[:12],
                 len(paths), is_command(text), is_reply)
        previous = self.store.lookup(chat, message)
        if previous:
            return previous["id"]
        if len(text) > 8192:
            return self.store.enqueue(chat, message, "", reply="Envie um comando com até 8192 caracteres.")
        reply, data, mime = None, None, None
        sources = []
        # The sender identity must come from authenticated transport metadata.
        if sender and not text.strip() and len(paths) == 1 and len(kinds) == 1 and kinds[0].startswith("image/"):
            try:
                data, mime = prepared if prepared is not None else prepare_image(paths[0], roots, self.settings.max_image_bytes)
                self.store.buffer_image(chat, sender, message, guid, data, mime)
                log.info("image_buffered")
                return self.match_waiting(chat, sender)
            except (OSError, Problem, ValueError):
                log.warning("image_rejected code=invalid_or_capacity")
                return None
        if sender and text.lstrip().startswith("[attachment:"):
            log.warning("image_only_unavailable")
            return None
        if sender and text.strip():
            sources = self.store.buffered(chat, sender, reply_to_guid) if (reply_to_guid or not is_reply) else []
        if is_command(text) and not paths and not kinds and "[attachment:" not in text and len(sources) == 1:
            data, mime = sources[0]["image"], sources[0]["mime"]

        if (sender and is_command(text) and not paths and not kinds and not sources
                and "[attachment:" not in text and (not is_reply or reply_to_guid)):
            log.info("command_waiting seconds=60")
            return self.store.enqueue(chat, message, text, wait_sender=sender, wait_reference=reply_to_guid)
        if not is_command(text):
            reply = HELP
        elif data is not None:
            pass
        elif len(paths) != 1 or len(kinds) != 1 or not kinds[0].startswith("image/") or "[attachment:" in text:
            reply = "Preciso de exatamente uma imagem disponível por pedido. " + HELP
        else:
            try:
                data, mime = prepared if prepared is not None else prepare_image(paths[0], roots, self.settings.max_image_bytes)
            except (FileNotFoundError, PermissionError):
                reply = "O anexo não está mais disponível. Envie a imagem novamente."
            except Problem as exc:
                reply = exc.message
        # Do not persist chat contents for requests that cannot create a ticket.
        return self.store.enqueue(chat, message, text if data else "", data, mime, reply, sources=sources)

    def match_waiting(self, chat, sender):
        candidates = []
        for job in self.store.waiting(chat, sender):
            sources = self.store.buffered(chat, sender, job["wait_reference"])
            if sources:
                candidates.append((job, sources))
        if not candidates:
            return None
        if len(candidates) != 1 or len(candidates[0][1]) != 1:
            for job, _ in candidates:
                self.store.update(job["id"], state="ready", text="", reply="Há mais de uma combinação possível. Responda à foto desejada com um único comando.")
            log.warning("image_match_ambiguous")
            return None
        job, sources = candidates[0]
        self.store.attach_waiting(job, sources[0])
        log.info("image_matched order=text_first")
        return job["id"]

    async def process(self, job_id):
        async with self.locks[int(hashlib.sha256(job_id.encode()).hexdigest(), 16) % 64]:
            job = self.store.get(job_id)
            if not job or job["state"] in ("done", "held") or job["delivery"] == "paused":
                return
            if job["state"] == "waiting":
                if time.time() < job["deadline"]:
                    return
                self.store.update(job_id, state="ready", text="",
                    reply="Não recebi uma imagem disponível em 60 segundos. Reenvie a captura e responda ao balão com ‘Registra esse bug’.")
                log.warning("command_wait_expired")
                job = self.store.get(job_id)
            try:
                if job["state"] in ("creating", "unknown"):
                    await self.reconcile(job)
                elif job["state"] == "queued":
                    await self.notify(job, "ack")
                    await self.create(job)
            except Problem as exc:
                self.store.update(job_id, state="ready", reply=exc.message)
                log.warning("job_failed code=%s", exc.code)
            except Exception:
                # No exception text, path, provider body, text, or secret in logs.
                # Creating was durably marked BEFORE the mutation. Leave it so
                # recovery reconciles instead of accidentally reissuing it.
                latest = self.store.get(job_id)
                if latest["state"] != "creating":
                    self.store.update(job_id, state="ready", reply="O processamento falhou. Consulte o diagnóstico do Omni.")
                log.error("job_failed code=internal")
                return
            job = self.store.get(job_id)
            if job["reply"]:
                await self.deliver(job)

    async def notify(self, job, kind):
        key = (job["id"], kind)
        if key in self.notice_tasks:
            await asyncio.shield(self.notice_tasks[key])
            return
        if not self.store.claim_notice(*key):
            return
        async def send_notice():
            success = False
            try:
                success = bool(await asyncio.wait_for(self.send(job["chat"], ACK if kind == "ack" else RETRY), timeout=4))
            except (Exception, asyncio.CancelledError):
                pass
            self.store.finish_notice(*key, success)
        task = asyncio.create_task(send_notice())
        self.notice_tasks[key] = task
        try:
            await asyncio.shield(task)
        finally:
            if task.done():
                self.notice_tasks.pop(key, None)

    async def run_notices(self):
        try:
            while True:
                jobs = [j for j in self.store.pending() if j["state"] == "queued" and j["image"]]
                await asyncio.gather(*(self.notify(j, "ack") for j in jobs[:100]))
                await asyncio.sleep(0.1)
        finally:
            tasks = list(self.notice_tasks.values())
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    def fallback_report(self, text):
        title = re.sub(r"^\s*(?:/bug|/task|/feature|registr[ae] esse bug|registr[ae] essa (?:tarefa|melhoria)|cri[ae] (?:um|esse) (?:card|ticket))\b", "", text, count=1, flags=re.I).strip(" :.!?\n")
        return Report(title=title[:180] or "Relato com screenshot", observed_evidence=text[:4000],
                      suggested_severity="indeterminada", missing_information=["Análise de IA indisponível"],
                      readable=True, analysis_status="pending", suggested_labels=["ai-pending"])

    async def create(self, job):
        if not job["image"] or not Path(job["image"]).exists():
            raise Problem("expired_image", "A imagem expirou. Envie uma nova solicitação com a captura.")
        data = Path(job["image"]).read_bytes()
        if job["report"]:
            report = Report.model_validate_json(job["report"])
        else:
            try:
                labels = await self.linear.labels()
            except Problem:
                labels = {}
            if not isinstance(labels, dict):
                labels = {}
            try:
                report = await self.gemini.analyze(job["text"], data, job["mime"],
                    on_retry=lambda: self.notify(job, "retry"), allowed_labels=tuple(x for x in labels if x != "ai-pending"))
            except Problem as exc:
                if exc.code != "unavailable":
                    raise
                report = self.fallback_report(job["text"])
                log.warning("analysis_degraded")
        if not report.readable:
            raise Problem("unreadable", "A imagem está ilegível. Envie outra captura e descreva o problema.")
        self.store.update(job["id"], report=report.model_dump_json())
        await self.linear.doctor()
        asset = job["asset"] or await self.linear.upload(data, job["mime"])
        self.store.update(job["id"], asset=asset, state="creating")
        try:
            ticket = await self.linear.create(job["id"], report, asset)
        except UnknownCreation:
            await self.reconcile(self.store.get(job["id"]))
            return
        self.save_ticket(job, ticket)

    def save_ticket(self, job, ticket):
        current = self.store.get(job["id"])
        report = Report.model_validate_json(current["report"]) if current["report"] else None
        self.store.update(job["id"], state="ready", ticket=ticket.model_dump_json(),
                          reply=success_message(ticket, report))
        self.store.cleanup_image(self.store.get(job["id"]))

    async def reconcile(self, job):
        try:
            ticket = await self.linear.reconcile(job["id"])
        except (Problem, ValueError):
            ticket = None
        if ticket:
            self.save_ticket(job, ticket)
        else:
            # Empty query is not proof that the timed-out mutation cannot commit later.
            self.store.update(job["id"], state="unknown", reply=UNCERTAIN)

    async def deliver(self, job):
        # A crash after send but before commit can duplicate a reply, never a ticket.
        attempt = job["attempts"] + 1
        self.store.update(job["id"], attempts=attempt)
        try:
            success = await self.send(job["chat"], job["reply"])
        except Exception:
            success = False
        if success:
            self.store.update(job["id"], state="held" if job["state"] == "unknown" else "done", delivery="sent")
        elif attempt >= 3:
            self.store.update(job["id"], delivery="paused")
        else:
            await asyncio.sleep(2 ** (attempt-1))

    async def run(self):
        active = {}
        cleanup_at = 0
        try:
            while True:
                if time.monotonic() >= cleanup_at:
                    self.store.expire_images()
                    cleanup_at = time.monotonic() + 30
                for key, task in list(active.items()):
                    if task.done():
                        task.result()
                        del active[key]
                for job in self.store.pending():
                    if len(active) >= self.settings.workers:
                        break
                    if job["id"] not in active and (job["state"] != "waiting" or job["deadline"] <= time.time()):
                        active[job["id"]] = asyncio.create_task(self.process(job["id"]))
                await asyncio.sleep(0.1)
        finally:
            for task in active.values():
                task.cancel()
            await asyncio.gather(*active.values(), return_exceptions=True)
