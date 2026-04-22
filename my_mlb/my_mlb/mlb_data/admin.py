from django.contrib import admin
from .models import Team, TeamSeason, Player, PlayerSeason, Position, BattingStats, CatchingStats, FieldingStats

admin.site.register(Team)
admin.site.register(TeamSeason)
admin.site.register(Player)
admin.site.register(PlayerSeason)
admin.site.register(Position)
admin.site.register(BattingStats)
admin.site.register(CatchingStats)
admin.site.register(FieldingStats)