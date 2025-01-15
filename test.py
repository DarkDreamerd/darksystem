from discord.ext import commands
from discord.ui import Modal, TextInput

bot = commands.Bot(command_prefix="!")

class TestModal(Modal, title="Тестовая форма"):
    name = TextInput(label="Введите имя")

    async def on_submit(self, interaction):
        await interaction.response.send_message(f"Вы ввели: {self.name.value}", ephemeral=True)

@bot.command()
async def test(ctx):
    await ctx.send("Нажмите на кнопку для теста", view=TestButton())

class TestButton(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(discord.ui.Button(label="Открыть форму", custom_id="test_button"))

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.data.get("custom_id") == "test_button":
        await interaction.response.send_modal(TestModal())

bot.run("NjQyMDkwNzY2NzU5NDkzNjYy.GhQTnL.zlX7IC0mO-kwtm5R0rweRM1IO5kbbJR5dSadQg")
