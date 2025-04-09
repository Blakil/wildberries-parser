import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.config.config import config
from src.services.llm_service import LLMService
from src.services.wildberries_service import WildberriesService
from src.services.proxy_service import PiaProxyService


# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize services
proxy_service = PiaProxyService()
llm_service = LLMService(proxy_service)
wb_service = WildberriesService(proxy_service)


# Initialize bot and dispatcher
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Start command handler"""
    await message.answer(
        "👋 Привет! Я бот для анализа позиций товаров Wildberries.\n\n"
        "Отправь мне ссылку на товар с Wildberries, и я определю его ключевые запросы "
        "и найду позиции товара в поисковой выдаче.\n\n"
        "Пример ссылки: https://www.wildberries.ru/catalog/182803851/detail.aspx"
    )


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Help command handler"""
    position_limit = config.MAX_POSITION_LIMIT
    await message.answer(
        "🔍 Как пользоваться ботом:\n\n"
        "1. Отправь мне ссылку на товар Wildberries в формате:\n"
        "   https://www.wildberries.ru/catalog/XXXXXXXXX/detail.aspx\n\n"
        "2. Я проанализирую товар и определю ключевые поисковые запросы\n\n"
        "3. Затем я найду позиции этого товара в поисковой выдаче по каждому запросу\n\n"
        f"4. Если товар не найден в топ-{position_limit} результатов, я сообщу об этом\n\n"
        "Команды:\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать эту справку"
    )


async def process_wildberries_url(message: types.Message, url: str):
    """Process Wildberries product URL"""
    user_id = message.from_user.id
    
    # Send "typing" action
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    # Extract article ID
    article_id = wb_service.extract_article_id(url)
    if not article_id:
        await message.answer("❌ Некорректная ссылка на товар Wildberries. Пожалуйста, проверьте ссылку и попробуйте снова.")
        return
    
    # Send initial response
    processing_message = await message.answer(f"⏳ Анализирую товар {article_id}...")
    
    try:
        # Get product data
        product_data = await wb_service.get_product_data(url, user_id)
        if not product_data:
            await message.answer("❌ Не удалось получить данные о товаре. Возможно, товар не существует или произошла ошибка.")
            await bot.delete_message(chat_id=message.chat.id, message_id=processing_message.message_id)
            return
        
        # Update processing message
        await bot.edit_message_text(
            "🔍 Определяю ключевые запросы для товара...", 
            chat_id=message.chat.id, 
            message_id=processing_message.message_id
        )
        
        # Extract keywords using LLM
        keywords = await llm_service.extract_keywords(product_data, user_id)
        
        # Update processing message
        await bot.edit_message_text(
            f"🔎 Ищу позиции товара по {len(keywords)} запросам...", 
            chat_id=message.chat.id, 
            message_id=processing_message.message_id
        )
        
        # Analyze product by keywords
        if "Ошибка обработки ключевых слов" in keywords or "Ошибка получения ключевых слов" in keywords:
            analysis = None
        else:
            analysis = await wb_service.analyze_product_keywords(url, keywords, user_id)
        
        # Delete processing message
        await bot.delete_message(chat_id=message.chat.id, message_id=processing_message.message_id)
        
        position_limit = config.MAX_POSITION_LIMIT
        
        if analysis:
            product = analysis.product
            caption = (
                    f"🏷️ *{product.name}*\n"
                    f"🏢 Бренд: *{product.brand}*\n"
                    f"💰 Цена: *{product.price:.0f} ₽*\n"
                    f"⭐ Рейтинг: *{product.rating}*\n"
                    f"💬 Отзывы: *{product.feedbacks}*\n"
                    f"🆔 ID: [{product.id}]({product.url})\n\n"
                    f"📊 *Результаты анализа:*"
                )
            # Send product image and details
            try:
                await message.answer_photo(
                    photo=product.image_url,
                    caption=caption,
                    parse_mode="Markdown"
                )
            except Exception as e:
                logging.error(f"Failed to send product image: {e}")
                # Fallback without image
                await message.answer(caption, parse_mode="Markdown")
            
            # Send keyword results
            result_text = "🔑 *Найденные ключевые запросы и позиции:*\n\n"
            for i, result in enumerate(analysis.search_results, 1):
                position = result.product_position if result.product_position else f"ниже {position_limit}"
                result_text += f"{i}. *{result.keyword}* — позиция: *{position}*\n"
        else:
            result_text = "🤖 *Ошибка анализа запросов. Попробуйте позже.*\n\n"
        await message.answer(result_text, parse_mode="Markdown")
        
    except Exception as e:
        logging.error(f"Error processing Wildberries URL: {e}")
        # Delete processing message if exists
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=processing_message.message_id)
        except:
            pass
        await message.answer(f"❌ Произошла ошибка при анализе товара: {str(e)}")


@dp.message()
async def handle_message(message: types.Message):
    if "wildberries.ru/catalog" in message.text:
        await process_wildberries_url(message, message.text)
    else:
        await message.answer(
            "Отправьте мне ссылку на товар с Wildberries в формате:\n"
            "https://www.wildberries.ru/catalog/XXXXXXXXX/detail.aspx"
        )


async def main():
    """Main function to start the bot"""
    # Skip pending updates
    await bot.delete_webhook(drop_pending_updates=True)
    # Start polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    # Run the bot
    asyncio.run(main())
