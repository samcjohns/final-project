from django.http import HttpResponse
from django.template import loader
from django.views.decorators.csrf import csrf_exempt
from decimal import Decimal
from django.db.models import Sum

from .models import Player, Team, TeamSeason, PlayerSeason

# Create your views here.
# Home page - Select team or player search
def mlb_data(request):
    template = loader.get_template('index.html')
    return HttpResponse(template.render())

# Player search page
@csrf_exempt
def player_search(request):
    template = loader.get_template('player_search.html')
    return HttpResponse(template.render())

# Player search results page
@csrf_exempt
def player_search_results(request): 
    q_name = request.POST.get('q_name')
    if q_name:
        players = Player.objects.filter(name__icontains=q_name)
    else:
        players = []
    template = loader.get_template('player_search_results.html')
    context = {
        'players': players,
        'q_name': q_name
    }
    return HttpResponse(template.render(context, request))

# Player details page
@csrf_exempt
def player_details(request, player_id):
    player = Player.objects.get(player_id=player_id)
    template = loader.get_template('player_details.html')
    context = {
        'player': player,
        'player_seasons': player.seasons.all()
    }
    return HttpResponse(template.render(context, request))

# # Team search page
@csrf_exempt
def team_search(request):
    template = loader.get_template('team_search.html')
    return HttpResponse(template.render())

# # Team search results page
@csrf_exempt
def team_search_results(request): 
    q_name = request.POST.get('q_name')
    if q_name:
        teams = Team.objects.filter(name__icontains=q_name)
    else:
        teams = []
    template = loader.get_template('team_search_results.html')
    context = {
        'teams': teams,
        'q_name': q_name
    }
    return HttpResponse(template.render(context, request))

# # Team details page
@csrf_exempt
def team_details(request, team_id):
    template = loader.get_template('team_details.html')
    team = Team.objects.get(id=team_id)
    team_seasons = team.seasons.all().prefetch_related('players')
    team_seasons_data = []

    for ts in team_seasons:
        players_qs = ts.players.all()
        total = PlayerSeason.objects.filter(year=ts.year, player__in=players_qs).aggregate(total=Sum('salary'))['total'] or Decimal('0.00')

        player_seasons = PlayerSeason.objects.filter(year=ts.year, player__in=players_qs).select_related('player')
        ps_by_player_id = {ps.player.player_id: ps for ps in player_seasons}

        roster = []
        for p in players_qs:
            roster.append({'player': p, 'player_season': ps_by_player_id.get(p.player_id)})

        team_seasons_data.append({'team_season': ts, 'roster': roster, 'payroll': total})

    context = {'team': team, 'team_seasons_data': team_seasons_data}
    return HttpResponse(template.render(context, request))

# # Team roster page
def team_roster(request, team_id, season_id):
    template = loader.get_template('team_roster.html')
    team = Team.objects.get(id=team_id)
    team_season = TeamSeason.objects.get(id=season_id, team=team)
    players_qs = team_season.players.all()

    player_seasons = PlayerSeason.objects.filter(year=team_season.year, player__in=players_qs).select_related('player')
    ps_by_player_id = {ps.player.player_id: ps for ps in player_seasons}

    roster = []
    for p in players_qs:
        roster.append({'player': p, 'player_season': ps_by_player_id.get(p.player_id)})

    context = {
        'team': team,
        'team_season': team_season,
        'roster': roster,
    }
    return HttpResponse(template.render(context, request))

#FIXME

