import sqlite3
import asyncio
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
LOGS_CHANNEL = 1329008209582620743  # ID канала для логов
ARCHIVE_CHANNEL = 1273057504644825089
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

        # Проверяем тип взаимодействия - это должно быть взаимодействие с кнопкой
        if interaction.type == discord.InteractionType.component:
            print(f"Custom ID: {interaction.data.get('custom_id')}")

            # Роли, которые могут взять тикет в работу
            take_ticket_roles = [1271843132681617510, 9876543210]  # ID ролей, которые могут взять тикет
            # Роли, которые могут закрыть тикет
            close_ticket_roles = [1271843132681617510, 2222222222]  # ID ролей, которые могут закрыть тикет
            ARCHIVE_CHANNEL = 1273057504644825089  # ID канала архива
            LOGS_CHANNEL = 1329008209582620743  # ID канала для логов

            # Получаем канал логов
            log_channel = interaction.guild.get_channel(LOGS_CHANNEL)

            # Обработка кнопки "Заявка в семью"
            if interaction.data.get("custom_id") == "application_button":
                # Отправляем модальное окно
                await interaction.response.send_modal(ApplicationForm())
                print("Modal shown successfully.")
                return

            # Обработка кнопки "Взять в работу"
            if interaction.data.get("custom_id") == "take_ticket":
                ticket_channel = interaction.channel  # Получаем канал тикета
                print(f"Attempting to take ticket: {ticket_channel.name}")

                # Проверяем, взят ли тикет в работу
                cursor.execute('''
                    SELECT taken_by, status FROM tickets WHERE channel_id = ?
                ''', (ticket_channel.id,))
                ticket_data = cursor.fetchone()

                if ticket_data and ticket_data[0] is not None:
                    await interaction.response.send_message("Этот тикет уже взят в работу другим рекрутером.", ephemeral=True)
                    return

                # Проверяем, есть ли у пользователя нужная роль
                if any(role.id in take_ticket_roles for role in interaction.user.roles):  
                    try:
                        # Меняем название канала или статус тикета
                        new_name = f"взято-{ticket_channel.name}"
                        await ticket_channel.edit(name=new_name)

                        # Обновляем статус тикета и добавляем информацию о рекрутере, взявшем тикет
                        cursor.execute('''
                            UPDATE tickets SET taken_by = ?, status = 'in_progress' WHERE channel_id = ?
                        ''', (interaction.user.id, ticket_channel.id))
                        conn.commit()

                        print(f"Ticket {ticket_channel.name} has been taken into work. New name: {new_name}")
                        
                        # Получаем информацию о рекрутере
                        recruiter_mention = interaction.user.mention
                        recruiter_tag = interaction.user.discriminator  # Получаем дискорд тэг
                        recruiter_name = interaction.user.name  # Получаем имя рекрутера
                        
                        # Отправляем сообщение в тикет-канал с упоминанием рекрутера
                        embed = discord.Embed(
                            title="Заявка взята в работу",
                            description=f"Заявка по семье теперь обрабатывается рекрутером {recruiter_mention} ({recruiter_name}#{recruiter_tag}).",
                            color=discord.Color.green()
                        )
                        await ticket_channel.send(embed=embed)

                        # Логируем, кто взял заявку в работу
                        if log_channel:
                            await log_channel.send(f"Заявка {ticket_channel.mention} была взята в работу рекрутером {recruiter_mention} ({recruiter_name}#{recruiter_tag}).")

                        # Открываем канал для переписки только для рекрутера и собеседуемого
                        overwrites = {
                            ticket_channel.guild.default_role: discord.PermissionOverwrite(view_channel=True, send_messages=False),  # Все рекрутеры могут видеть, но не писать
                            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),  # Тот, кто взял тикет, может писать
                            ticket_channel.guild.get_member(interaction.user.id): discord.PermissionOverwrite(view_channel=True, send_messages=True),  # Сам собеседуемый может писать
                        }
                        await ticket_channel.set_permissions(interaction.user, overwrite=overwrites[interaction.user])

                        # Подтверждение пользователю
                        await interaction.response.send_message(f"Вы взяли тикет {ticket_channel.mention} в работу.", ephemeral=True)
                    except discord.Forbidden:
                        print("Bot does not have permission to edit the channel.")
                        await interaction.response.send_message("У бота нет прав для изменения канала.", ephemeral=True)
                else:
                    await interaction.response.send_message("У вас нет прав для взятия тикета в работу.", ephemeral=True)

            # Дальнейшие обработки (например, перехват контроля, закрытие и другие)
            
    except Exception as e:
        print("Ошибка в on_interaction (button):", traceback.format_exc())
        await interaction.response.send_message("Произошла ошибка при обработке кнопки.", ephemeral=True)

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

            # Отправка эмбед-сообщения с данными пользователя
            embed = discord.Embed(title="Новая заявка", color=discord.Color.blue())
            embed.add_field(name="Имя Фамилия", value=self.name.value, inline=False)
            embed.add_field(name="Номер паспорта", value=self.static_id.value, inline=False)
            embed.add_field(name="Опыт в гос структурах", value=self.experience.value, inline=False)
            embed.add_field(name="Часовой пояс", value=self.timezone.value, inline=False)
            embed.add_field(name="Источник", value=self.source.value, inline=False)
            embed.set_footer(text=f"От: {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
            
            message = await ticket_channel.send(embed=embed)

            # Сохраняем первое сообщение с эмбед для отправки в архив позже
            global first_message
            first_message = message

            # Логируем поступление заявки
            log_channel = interaction.guild.get_channel(LOGS_CHANNEL)
            if log_channel:
                await log_channel.send(f"Заявка поступила от {interaction.user.mention} ({interaction.user.name}#{interaction.user.discriminator})")

            # Создание кнопок для управления тикетом
            view = TicketControlView(ticket_channel.id)
            await message.edit(view=view)

            # Отправляем сообщение пользователю о том, что тикет создан
            await interaction.response.send_message(f"Ваш тикет создан: {ticket_channel.mention}", ephemeral=True)

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
async def startx(ctx):
    embed = discord.Embed(title="Приветствую!", description="Чтобы оставить заявку, нажмите на кнопку ниже.", color=discord.Color.green())
    await ctx.send(embed=embed, view=ApplicationButton())

# Запуск бота
bot.run("NjQyMDkwNzY2NzU5NDkzNjYy.GkwJTy.Ql0o_fPehyaOiNWLJ5fnjY98M86e7WHdCwYK4w")
