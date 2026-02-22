import asyncio
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.bot.handlers.ai_chat import router as ai_chat_router
from app.bot.handlers.main import router as main_router
from app.config import get_settings
from app.database.migrations import run_migrations, should_run_migrations
from app.web.api import router as web_api_router

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting application lifespan...")
    try:
        # Run migrations if on Render
        if should_run_migrations():
            print("📦 Running database migrations...")
            await run_migrations()
            print("✅ Migrations completed.")
            
        # Initialize bot and dispatcher inside the async context to ensure event loop exists
        print("🤖 Initializing Telegram Bot...")
        if not settings.telegram_bot_token:
            print("❌ ERROR: TELEGRAM_BOT_TOKEN is not set!")
            # Don't crash the whole web server if bot fails, just log it
            app.state.bot = None
            yield
            return

        bot = Bot(token=settings.telegram_bot_token)
        dp = Dispatcher(storage=MemoryStorage())
        dp.include_router(main_router)
        dp.include_router(ai_chat_router)
        
        app.state.bot = bot
        
        # Run Aiogram polling in the background
        print("📡 Starting bot polling...")
        polling_task = asyncio.create_task(dp.start_polling(bot))
        
        print("✨ Application startup complete. Serving requests.")
        yield
        
        print("🛑 Shutting down application...")
        polling_task.cancel()
        try:
            await dp.stop_polling()
        except Exception:
            pass
            
    except Exception as e:
        print(f"💥 CRITICAL STARTUP ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise e

app = FastAPI(lifespan=lifespan, title="Currency Bot Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(web_api_router, prefix="/api")

# Serve the Mini App static files
app.mount("/", StaticFiles(directory="app/web/static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.web.app:app", host="0.0.0.0", port=8000, reload=True)
