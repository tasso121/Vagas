from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes
from scrapers.base import Job
from ai.runner import ClaudeRunner
from apply import get_apply_handler

class TelegramBot:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.app = Application.builder().token(token).build()
        self.claude = ClaudeRunner()
        self._pending: dict[str, Job] = {}
        self._apply_handlers: dict[str, object] = {}
        self.app.add_handler(CallbackQueryHandler(self._handle_callback))

    async def notify_new_job(self, job: Job):
        key = f"{job.platform}:{job.job_id}"
        self._pending[key] = job
        text = (
            f"🆕 <b>Nova vaga remota</b>\n\n"
            f"💼 {job.title}\n🏢 {job.company}\n📍 100% Remoto\n"
            f"🔗 <a href='{job.url}'>Ver vaga completa</a>"
        )
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Avaliar com IA", callback_data=f"avaliar:{key}"),
            InlineKeyboardButton("❌ Ignorar", callback_data=f"ignorar:{key}"),
        ]])
        await self.app.bot.send_message(chat_id=self.chat_id, text=text, reply_markup=keyboard, parse_mode="HTML")

    async def _handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        parts = query.data.split(":", 1)
        if len(parts) != 2:
            return
        action, key = parts
        dispatch = {
            "avaliar": self._handle_avaliar,
            "ignorar": self._handle_ignorar,
            "candidatar": self._handle_candidatar,
            "descartar": self._handle_descartar,
            "revisar": self._handle_revisar,
            "confirmar": self._handle_confirmar,
            "cancelar": self._handle_cancelar,
        }
        handler = dispatch.get(action)
        if handler:
            await handler(query, key)

    async def _handle_ignorar(self, query, key: str):
        self._pending.pop(key, None)
        await query.edit_message_text("❌ Vaga ignorada.")

    async def _handle_descartar(self, query, key: str):
        self._pending.pop(key, None)
        await query.edit_message_text("❌ Vaga descartada.")

    async def _handle_cancelar(self, query, key: str):
        self._apply_handlers.pop(key, None)
        await query.edit_message_text("❌ Candidatura cancelada.")

    async def _handle_avaliar(self, query, key: str):
        job = self._pending.get(key)
        if not job:
            await query.edit_message_text("⚠️ Vaga não encontrada.")
            return
        await query.edit_message_text("⏳ Avaliando com IA...")
        result = await self.claude.evaluate_job(job_description=job.description)
        if not result:
            await query.edit_message_text("⚠️ Erro na avaliação. Tente novamente.")
            return
        strengths = "\n".join(f"• {s}" for s in result.get("strengths", []))
        gaps = "\n".join(f"• {g}" for g in result.get("gaps", []))
        text = (
            f"📊 <b>Avaliação: {result['grade']} ({result['score']:.1f}/5)</b>\n\n"
            f"✅ <b>Pontos fortes:</b>\n{strengths}\n\n"
            f"⚠️ <b>Gaps:</b>\n{gaps}\n\n"
            f"📝 {result['summary']}"
        )
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🚀 Candidatar", callback_data=f"candidatar:{key}"),
            InlineKeyboardButton("❌ Descartar", callback_data=f"descartar:{key}"),
        ]])
        await query.edit_message_text(text=text, reply_markup=keyboard, parse_mode="HTML")

    async def _handle_candidatar(self, query, key: str):
        pass  # implemented in Task 9

    async def _handle_revisar(self, query, key: str):
        pass  # implemented in Task 9

    async def _handle_confirmar(self, query, key: str):
        pass  # implemented in Task 9

    async def run(self):
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()

    async def stop(self):
        await self.app.updater.stop()
        await self.app.stop()
        await self.app.shutdown()
