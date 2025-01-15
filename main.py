import sqlite3
import discord
import traceback
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput

# Инициализация бота
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Конфигурация ролей и каналов (заполняется через config.json)
ROLE_RECRUITER = 1271843132681617510  # ID роли рекрутера
CATEGORY_TICKETS = 1329008072059912233  # ID категории для тикетов
CHANNEL_LOGS = 1329008209582620743  # ID канала для логов

# Подключение к базе данных
conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# Создание таблицы для тикетов, если её нет
cursor.execute('''
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    channel_id INTEGER,
    name TEXT,
    static_id TEXT,
    experience TEXT,
    timezone TEXT,
    source TEXT,
    status TEXT DEFAULT 'open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')
conn.commit()

# Кнопка "Заявка в семью"
class ApplicationButton(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Button(label="Заявка в семью", style=discord.ButtonStyle.primary, custom_id="application_button"))

# Обработка кнопки "Заявка в семью"
@bot.event
async def on_interaction(interaction: discord.Interaction):
    try:
        print(f"Interaction received: {interaction}")
        if interaction.type == discord.InteractionType.component:
            print(f"Custom ID: {interaction.data.get('custom_id')}")
            if interaction.data.get("custom_id") == "application_button":
                # Проверка, работает ли interaction.response
                if not interaction.response.is_done():
                    await interaction.response.defer()  # Добавляем defer
                await interaction.response.send_modal(ApplicationForm())
                print("Modal shown successfully.")
                return
        if not interaction.response.is_done():
            await interaction.response.send_message("Неизвестное действие.", ephemeral=True)
    except Exception as e:
        print("Ошибка в on_interaction (button):", traceback.format_exc())
        if not interaction.response.is_done():
            await interaction.response.send_message("Произошла ошибка. Попробуйте позже.", ephemeral=True)

# Модальное окно формы заявки
class ApplicationForm(Modal, title="Заявка"):
    name = TextInput(label="Имя Фамилия", placeholder="Введите имя и фамилию", max_length=100)
    static_id = TextInput(label="Номер паспорта в игре (статик)", placeholder="Введите статик", max_length=100)
    experience = TextInput(label="В каких гос структурах были ранее?", style=discord.TextStyle.paragraph)
    timezone = TextInput(label="Ваш часовой пояс (GMT)", placeholder="Пример: GMT+3")
    source = TextInput(label="Откуда узнали о нас?", style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            print("Form submitted.")
            # Проверка на существование категории
            guild = interaction.guild
            category = guild.get_channel(CATEGORY_TICKETS)
            if not category:
                raise ValueError("Категория для тикетов не найдена. Проверьте CATEGORY_TICKETS.")

            # Создание канала для тикета
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
                guild.get_role(ROLE_RECRUITER): discord.PermissionOverwrite(view_channel=True, send_messages=True)
            }
            ticket_channel = await guild.create_text_channel(name=f"тикет-{interaction.user.name}", category=category, overwrites=overwrites)

            # Сохранение данных в базу данных
            cursor.execute('''
            INSERT INTO tickets (user_id, channel_id, name, static_id, experience, timezone, source)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (interaction.user.id, ticket_channel.id, self.name.value, self.static_id.value, self.experience.value, self.timezone.value, self.source.value))
            conn.commit()

            # Отправка эмбед-сообщения с заявкой
            embed = discord.Embed(title="Новая заявка", color=discord.Color.blue())
            embed.add_field(name="Имя Фамилия", value=self.name.value, inline=False)
            embed.add_field(name="Номер паспорта", value=self.static_id.value, inline=False)
            embed.add_field(name="Опыт в гос структурах", value=self.experience.value, inline=False)
            embed.add_field(name="Часовой пояс", value=self.timezone.value, inline=False)
            embed.add_field(name="Источник", value=self.source.value, inline=False)
            embed.set_footer(text=f"От: {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
            
            message = await ticket_channel.send(embed=embed)
            await interaction.response.send_message(f"Ваш тикет создан: {ticket_channel.mention}", ephemeral=True)

            # Добавление кнопок для работы с тикетом
            view = TicketControlView(ticket_channel.id)
            await message.edit(view=view)
        except Exception as e:
            print("Ошибка в on_submit (form):", traceback.format_exc())
            if not interaction.response.is_done():
                await interaction.response.send_message(f"Произошла ошибка при создании тикета: {e}", ephemeral=True)

# Кнопки для управления тикетом
class TicketControlView(View):
    def __init__(self, channel_id):
        super().__init__(timeout=None)
        self.channel_id = channel_id
        self.add_item(Button(label="Взять в работу", style=discord.ButtonStyle.success, custom_id="take_ticket"))
        self.add_item(Button(label="Закрыть тикет", style=discord.ButtonStyle.danger, custom_id="close_ticket"))

@bot.command()
async def start(ctx):
    embed = discord.Embed(title="Приветствую!", description="Чтобы оставить заявку, нажмите на кнопку ниже.", color=discord.Color.green())
    await ctx.send(embed=embed, view=ApplicationButton())

# Запуск бота
bot.run("NjQyMDkwNzY2NzU5NDkzNjYy.GhQTnL.zlX7IC0mO-kwtm5R0rweRM1IO5kbbJR5dSadQg")
