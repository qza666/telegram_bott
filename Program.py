import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackContext,
    filters,
    ContextTypes,
    JobQueue
)
from chat import get_answer_from_training_data
from gpt import call_chatgpt
from database import init_db, add_training_data, get_all_questions, delete_question
from datetime import datetime, timedelta, timezone
import random

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

init_db()

# 存储各群聊状态的字典
group_status = {}

# 定义管理员列表和白名单
admins = ["Mrfacai"]  # 在这里添加管理员用户名
whitelist = []

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    group_status[chat_id] = True
    await update.message.reply_text("杠精功能已开启。")

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    group_status[chat_id] = False
    await update.message.reply_text("杠精功能已关闭。")

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    user_question = update.message.text.strip()

    is_dos_reply = False

    if user_question.startswith("帮我骂"):
        is_dos_reply = True
        for _ in range(random.randint(1, 5)):
            answe = call_chatgpt(user_question[3:],2)
            answer = f"{user_question[3:]} {answe}"
            reply_message = await context.bot.send_message(chat_id=chat_id, text=answer)
            schedule_deletion(context, chat_id, reply_message.message_id, update.message.message_id, is_dos_reply)
        return
    elif user_question.startswith("骂"):
        is_dos_reply = True
        answe = call_chatgpt(user_question[1:],2)
        answer = f"{user_question[1:]} {answe}"
        reply_message = await context.bot.send_message(chat_id=chat_id, text=answer)
    else:
        if '+' in user_question or '-' in user_question:
            if '+' in user_question:
                answer = call_chatgpt(user_question,3)
            else:
                answer = call_chatgpt(user_question,4)
        else:
            user = update.message.from_user.username
            if user in whitelist:
                return
            if not group_status.get(chat_id, False):
                return
            is_dos_reply = True
            answer = call_chatgpt(user_question,2)

        reply_message = await context.bot.send_message(chat_id=chat_id, text=answer)

    print(answer)
    schedule_deletion(context, chat_id, reply_message.message_id, update.message.message_id, is_dos_reply)


def schedule_deletion(context: CallbackContext, chat_id: int, bot_message_id: int, user_message_id: int, is_dos_reply: bool) -> None:
    if is_dos_reply:
        deletion_time = datetime.now(timezone.utc) + timedelta(minutes=3)
        logger.info(f"消息删除任务安排在 {deletion_time.isoformat()} 执行")
        context.job_queue.run_once(
            delete_messages,
            when=timedelta(minutes=3),
            data={
                'chat_id': chat_id,
                'message_id': bot_message_id,
                'user_message_id': user_message_id,
                'deletion_time': deletion_time.isoformat()
            }
        )

async def handle_s_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_question = ' '.join(context.args).strip()

    # 尝试从数据库获取答案
    answer = get_answer_from_training_data(user_question)

    is_dos_reply = False

    if answer is None:
        # 如果数据库中没有找到，则调用 GPT
        answer = call_chatgpt(user_question,1)
    else:
        is_dos_reply = False
    
    reply_message = await update.message.reply_text(answer)

    # 设置消息自动删除
    schedule_deletion(context, update.message.chat_id, reply_message.message_id, update.message.message_id, is_dos_reply)


async def delete_messages(context: CallbackContext) -> None:
    job_data = context.job.data  # 使用 .data 而不是 .context 获取传递的数据
    chat_id = job_data['chat_id']
    bot = context.bot
    deletion_time = job_data.get('deletion_time')

    logger.info(f"执行消息删除任务，预定时间：{deletion_time}, 当前时间：{datetime.now(timezone.utc).isoformat()}")
    
    # 删除机器人的消息
    try:
        await bot.delete_message(chat_id, job_data['message_id'])
        logger.info(f"已删除机器人消息 {job_data['message_id']}")
    except Exception as e:
        logger.error(f"删除机器人消息出错: {e}")
    
    # 删除用户的消息
    try:
        await bot.delete_message(chat_id, job_data['user_message_id'])
        logger.info(f"已删除用户消息 {job_data['user_message_id']}")
    except Exception as e:
        logger.error(f"删除用户消息出错: {e}")

async def learn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) < 2:
        await update.message.reply_text("请使用正确的格式：/x 问题 回答")
        return

    question = context.args[0]
    answer = ' '.join(context.args[1:])
    add_training_data(question, answer)
    await update.message.reply_text("已经拿小本本记起来了")

async def list_questions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    questions = get_all_questions()
    if questions:
        await update.message.reply_text("\n".join(questions))
    else:
        await update.message.reply_text("数据库中没有储存任何问题。")

async def delete_question_from_db(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) < 1:
        await update.message.reply_text("请使用正确的格式：/i 问题")
        return

    question = context.args[0]
    delete_question(question)
    await update.message.reply_text(f"问题'{question}'已从数据库中删除。")

async def show_commands(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    commands = (
        "/s 问题        - 提问（翻译+ 情侣-）\n"
        "/x 问题 答案    - 学习新问题及其答案\n"
        "/l          - 显示数据库中的所有问题\n"
        "/i 问题     - 删除数据库中的指定问题\n"
        "/start_dos          - 开启杠精功能\n"
        "/stop_dos           - 关闭杠精功能\n"
        "/b @xxx             - 添加到白名单\n"
        "/cd                   - 显示所有指令"
    )
    await update.message.reply_text(commands)

async def add_to_whitelist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user.username
    if user not in admins:
        await update.message.reply_text("你TM有不是管理员，老子可不听你的指令")
        return

    if len(context.args) < 1:
        await update.message.reply_text("请使用正确的格式：/b @username")
        return

    user_to_add = context.args[0].strip().lstrip('@')
    if user_to_add not in whitelist:
        whitelist.append(user_to_add)
        await update.message.reply_text(f"{user_to_add} 已添加到白名单。")
    else:
        await update.message.reply_text(f"{user_to_add} 已在白名单中。")

async def error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.warning(f'Update {update} caused error {context.error}')

def Program_mian(bot_token) -> None:
    api_token = bot_token

    application = ApplicationBuilder().token(api_token).build()

    # 添加 CommandHandler 和 MessageHandler
    application.add_handler(CommandHandler("s", handle_s_command))
    application.add_handler(CommandHandler("x", learn))
    application.add_handler(CommandHandler("l", list_questions))
    application.add_handler(CommandHandler("i", delete_question_from_db))
    application.add_handler(CommandHandler("start_dos", start_command))
    application.add_handler(CommandHandler("stop_dos", stop_command))
    application.add_handler(CommandHandler("b", add_to_whitelist))
    application.add_handler(CommandHandler("cd", show_commands))
    
    # 处理直接向机器人提问的消息或回复机器人的消息
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ask_question))
    
    application.add_error_handler(error)

    application.run_polling()
