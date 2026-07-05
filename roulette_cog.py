@discord.ui.button(label="انضم للعبة", style=discord.ButtonStyle.success)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.started: return
        
        if interaction.user not in self.players:
            self.players.append(interaction.user)
            await interaction.response.edit_message(embed=self.build_embed())
            
            # بدء المؤقت فقط عند انضمام أول لاعب
            if len(self.players) == 1:
                await interaction.channel.send("⏳ ستبدأ اللعبة تلقائياً بعد 15 ثانية من الآن!")
                await asyncio.sleep(15) 
                
                # التحقق من أن اللعبة لم تبدأ وأن هناك لاعبين
                if not self.started and len(self.players) >= 2:
                    await self.start_game(interaction)
                elif not self.started and len(self.players) < 2:
                    await interaction.channel.send("❌ تم إلغاء اللعبة لعدم وجود لاعبين كافيين.")
                    self.stop()
